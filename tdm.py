import sys
import csv
from json import loads, JSONDecodeError

from PyQt5.QtCore import QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QMainWindow, QDialog, QStatusBar, QApplication, QMdiArea, QFileDialog

from GUI import *
from GUI.BSSID import BSSIdDialog
from GUI.Broker import BrokerDialog
from GUI.DeviceConsole import DeviceConsoleWidget
from GUI.DeviceTelemetry import DeviceTelemetryWidget
from GUI.DevicesList import DevicesListWidget
from Util import TasmotaDevice, TasmotaEnvironment, parse_topic
from Util.models import *
from Util.mqtt import MqttClient


class MainWindow(QMainWindow):

    telemetry = pyqtSignal(str, str)

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self._version = "0.2.0"
        self.setWindowIcon(QIcon("GUI/icons/logo.png"))
        self.setWindowTitle("Tasmota Device Manager {}".format(self._version))

        self.env = TasmotaEnvironment()

        self.mqtt_queue = []
        self.fulltopic_queue = []

        self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)
        self.setMinimumSize(QSize(1280, 800))

        self.settings.beginGroup("Devices")
        for d in self.settings.childGroups():
            self.settings.beginGroup(d)
            device = TasmotaDevice(d, self.settings.value("full_topic"), self.settings.value("friendly_name"))
            device.env = self.env
            self.env.devices.append(device)

            self.settings.beginGroup("history")
            for k in self.settings.childKeys():
                device.history.append(self.settings.value(k))
            self.settings.endGroup()

            self.settings.endGroup()
        self.settings.endGroup()

        self.device_model = TasmotaDevicesModel2(self.env)

        self.setup_mqtt()
        self.setup_main_layout()
        self.add_devices_tab()
        self.build_mainmenu()
        self.build_toolbars()
        self.setStatusBar(QStatusBar())

        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self.mqtt_publish_queue)
        self.queue_timer.start(250)

        self.auto_timer = QTimer()
        self.auto_timer.timeout.connect(self.autoupdate)

        self.load_window_state()

        if self.settings.value("connect_on_startup", False, bool):
            self.actToggleConnect.trigger()

        self.tele_docks = {}

    def setup_main_layout(self):
        self.mdi = QMdiArea()
        self.mdi.setActivationOrder(QMdiArea.ActivationHistoryOrder)
        self.mdi.setOption(QMdiArea.DontMaximizeSubWindowOnActivation)
        self.mdi.setTabsClosable(True)

        self.setCentralWidget(self.mdi)

    def setup_mqtt(self):
        self.mqtt = MqttClient()
        self.mqtt.connecting.connect(self.mqtt_connecting)
        self.mqtt.connected.connect(self.mqtt_connected)
        self.mqtt.disconnected.connect(self.mqtt_disconnected)
        self.mqtt.connectError.connect(self.mqtt_connectError)
        self.mqtt.messageSignal.connect(self.mqtt_message)

    def add_devices_tab(self):
        self.devices_list = DevicesListWidget(self)
        sub = self.mdi.addSubWindow(self.devices_list)
        sub.setWindowState(Qt.WindowMaximized)
        self.devices_list.deviceSelected.connect(self.selectDevice)

    def load_window_state(self):
        wndGeometry = self.settings.value('window_geometry')
        if wndGeometry:
            self.restoreGeometry(wndGeometry)

    def build_mainmenu(self):
        mSetup = self.menuBar().addMenu("Options")
        mSetup.addAction(QIcon("./GUI/icons/connections.png"), "MQTT Broker", self.setup_broker)
        # mSetup.addAction(QIcon(), "Auto telemetry period", lambda: print('asd'))
        mSetup.addAction(QIcon("./GUI/icons/bssid.png"), "BSSId aliases", self.bssid)

        mDevices = self.menuBar().addMenu("My devices")
        actAdd = mDevices.addAction(QIcon("GUI/icons/add.png"), "Add", self.export)
        actRemove = mDevices.addAction(QIcon("GUI/icons/delete.png"), "Remove", self.export)
        mDevices.addSeparator()

        mDevices.addSeparator()
        mDevices.addAction(QIcon("./GUI/icons/export.png"), "Export list", self.export)

        mDevices.setEnabled(False)

    def build_toolbars(self):
        main_toolbar = Toolbar(orientation=Qt.Horizontal, iconsize=16, label_position=Qt.ToolButtonTextBesideIcon)
        main_toolbar.setObjectName("main_toolbar")
        self.addToolBar(main_toolbar)

        self.actToggleConnect = QAction(QIcon("./GUI/icons/disconnect.png"), "Connect")
        self.actToggleConnect.setCheckable(True)
        self.actToggleConnect.toggled.connect(self.toggle_connect)
        main_toolbar.addAction(self.actToggleConnect)

        self.actToggleAutoUpdate = QAction(QIcon("./GUI/icons/automatic.png"), "Auto telemetry")
        self.actToggleAutoUpdate.setCheckable(True)
        self.actToggleAutoUpdate.toggled.connect(self.toggle_autoupdate)
        main_toolbar.addAction(self.actToggleAutoUpdate)

    def initial_query(self, device, queued=False):
        status = device.cmnd_topic("status")
        tpl = device.cmnd_topic("template")
        modules = device.cmnd_topic("modules")

        if queued:
            self.mqtt_queue.append([status, 0])
            self.mqtt_queue.append([tpl, ""])
            self.mqtt_queue.append([modules, ""])
        else:
            self.mqtt.publish(status, 0, 1)
            self.mqtt.publish(tpl, "", 1)

    def setup_broker(self):
        brokers_dlg = BrokerDialog()
        if brokers_dlg.exec_() == QDialog.Accepted and self.mqtt.state == self.mqtt.Connected:
            self.mqtt.disconnect()

    def toggle_autoupdate(self, state):
        if state == True:
            self.auto_timer.setInterval(5000)
            self.auto_timer.start()
        else:
            self.auto_timer.stop()

    def toggle_connect(self, state):
        if state and self.mqtt.state == self.mqtt.Disconnected:
            self.broker_hostname = self.settings.value('hostname', 'localhost')
            self.broker_port = self.settings.value('port', 1883, int)
            self.broker_username = self.settings.value('username')
            self.broker_password = self.settings.value('password')

            self.mqtt.hostname = self.broker_hostname
            self.mqtt.port = self.broker_port

            if self.broker_username:
                self.mqtt.setAuth(self.broker_username, self.broker_password)
            self.mqtt.connectToHost()
        elif not state and self.mqtt.state == self.mqtt.Connected:
            self.mqtt_disconnect()

    def autoupdate(self):
        if self.mqtt.state == self.mqtt.Connected:
            for d in self.env.devices:
                self.mqtt.publish("{}STATUS".format(d.cmnd_topic()), payload=8)

    def mqtt_connect(self):
        self.broker_hostname = self.settings.value('hostname', 'localhost')
        self.broker_port = self.settings.value('port', 1883, int)
        self.broker_username = self.settings.value('username')
        self.broker_password = self.settings.value('password')

        self.mqtt.hostname = self.broker_hostname
        self.mqtt.port = self.broker_port

        if self.broker_username:
            self.mqtt.setAuth(self.broker_username, self.broker_password)

        if self.mqtt.state == self.mqtt.Disconnected:
            self.mqtt.connectToHost()

    def mqtt_disconnect(self):
        self.mqtt.disconnectFromHost()

    def mqtt_connecting(self):
        self.statusBar().showMessage("Connecting to broker")

    def mqtt_connected(self):
        self.actToggleConnect.setIcon(QIcon("./GUI/icons/connect.png"))
        self.actToggleConnect.setText("Disconnect")
        self.statusBar().showMessage("Connected to {}:{} as {}".format(self.broker_hostname, self.broker_port, self.broker_username if self.broker_username else '[anonymous]'))

        self.mqtt_subscribe()

    def mqtt_subscribe(self):
        topics = ["+/stat/#", "+/tele/#", "stat/#", "tele/#", "+/cmnd/#", "cmnd/#"]

        for d in self.env.devices:
            # todo: verify
            if not d.is_default():
                topics.append(d.stat_topic()+"#")
                topics.append(d.tele_topic()+"#")
                topics.append(d.cmnd_topic()+"#")

        for t in topics:
            self.mqtt.subscribe(t)

    def mqtt_publish_queue(self):
        for q in self.mqtt_queue:
            t, p = q
            self.mqtt.publish(t, p)
            self.mqtt_queue.pop(self.mqtt_queue.index(q))

    def mqtt_disconnected(self):
        self.actToggleConnect.setIcon(QIcon("./GUI/icons/disconnect.png"))
        self.actToggleConnect.setText("Connect")
        self.statusBar().showMessage("Disconnected")

    def mqtt_connectError(self, rc):
        reason = {
            1: "Incorrect protocol version",
            2: "Invalid client identifier",
            3: "Server unavailable",
            4: "Bad username or password",
            5: "Not authorized",
        }
        self.statusBar().showMessage("Connection error: {}".format(reason[rc]))
        self.actToggleConnect.setChecked(False)

    def mqtt_message(self, topic, msg):
        device = self.env.find_device(topic)
        if device:
            device.parse_message(topic, msg)

        if topic.endswith("LWT"):
            if not msg:
                msg = "offline"

            if device:
                device.update_property("LWT", msg)
                if msg == 'Online':
                    device.update_property("LWT", "online")
                    self.initial_query(device, True)

            elif msg == "Online":
                split_topic = topic.split('/')
                possible_topic = split_topic[1]

                if possible_topic in ('tele', 'stat'):
                    possible_topic = split_topic[0]

                # todo: add dialog to custom auto-detect fulltopics
                self.mqtt_queue.append(["cmnd/{}/fulltopic".format(possible_topic), ""])
                self.mqtt_queue.append(["{}/cmnd/fulltopic".format(possible_topic), ""])

        elif topic.endswith("RESULT"):
            try:
                full_topic = loads(msg).get('FullTopic')

                if full_topic:
                    parsed = parse_topic(full_topic, topic)
                    if parsed:
                        d = TasmotaDevice(parsed['topic'], full_topic)
                        d.update_property("LWT", "online")
                        self.env.devices.append(d)
                        self.device_model.addDevice(d)
                        self.initial_query(d, True)

            except JSONDecodeError as e:
                with open("{}/TDM/error.log".format(QDir.homePath()), "a+") as l:
                    l.write("{}\t{}\t{}\t{}\n".format(QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss"), topic, msg, e.msg))

    # todo: rework
    def export(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Export device list as...", directory=QDir.homePath(), filter="CSV files (*.csv)")
        if fname:
            if not fname.endswith(".csv"):
                fname += ".csv"

            with open(fname, "w", encoding='utf8') as f:
                column_titles = ['mac', 'topic', 'friendly_name', 'full_topic', 'cmnd_topic', 'stat_topic', 'tele_topic', 'module', 'module_id', 'firmware', 'core']
                c = csv.writer(f)
                c.writerow(column_titles)

                for r in range(self.device_model.rowCount()):
                    d = self.device_model.index(r,0)
                    c.writerow([
                        self.device_model.mac(d),
                        self.device_model.topic(d),
                        self.device_model.friendly_name(d),
                        self.device_model.fullTopic(d),
                        self.device_model.commandTopic(d),
                        self.device_model.statTopic(d),
                        self.device_model.teleTopic(d),
                        # modules.get(self.device_model.module(d)),
                        self.device_model.module(d),
                        self.device_model.firmware(d),
                        self.device_model.core(d)
                    ])

    def bssid(self):
        BSSIdDialog().exec_()

    @pyqtSlot(TasmotaDevice)
    def selectDevice(self, d):
        self.device = d

    @pyqtSlot()
    def openTelemetry(self):
        if self.idx:
            fname = self.device_model.friendly_name(self.idx)
            topic = self.device_model.topic(self.idx)
            tele_topic = self.device_model.teleTopic(self.idx)
            stat_topic = self.device_model.statTopic(self.idx)
            tele_widget = DeviceTelemetryWidget(fname, topic, tele_topic, stat_topic)
            self.telemetry.connect(tele_widget.parse_telemetry)
            self.addDockWidget(Qt.RightDockWidgetArea, tele_widget)

    @pyqtSlot()
    def openConsole(self):
        console_widget = DeviceConsoleWidget(self.device)
        self.mqtt.messageSignal.connect(console_widget.consoleAppend)
        console_widget.sendCommand.connect(self.mqtt.publish)
        self.addDockWidget(Qt.BottomDockWidgetArea, console_widget)
        console_widget.command.setFocus()

    def closeEvent(self, e):
        self.settings.setValue("version", self._version)
        self.settings.setValue("window_geometry", self.saveGeometry())

        self.settings.beginGroup("Devices")
        for d in self.env.devices:
            self.settings.setValue("{}/full_topic".format(d.p['Topic']), d.p['FullTopic'])
            self.settings.setValue("{}/friendly_name".format(d.p['Topic']), d.p['FriendlyName'][0])
            for i, h in enumerate(d.history):
                self.settings.setValue("{}/history/{}".format(d.p['Topic'], i), h)
        self.settings.endGroup()

        self.settings.sync()
        e.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setOrganizationName("Tasmota")
    app.setApplicationName("TDM")
    app.lastWindowClosed.connect(app.quit)

    MW = MainWindow()
    MW.show()

    sys.exit(app.exec_())