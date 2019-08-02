import re
import sys
import csv
from json import loads, JSONDecodeError

from PyQt5.QtCore import QTimer, pyqtSlot, QSettings, QDir, QSize, Qt, QDateTime, QUrl
from PyQt5.QtGui import QIcon, QDesktopServices
from PyQt5.QtWidgets import QMainWindow, QDialog, QStatusBar, QApplication, QMdiArea, QFileDialog, QAction, QFrame, \
    QInputDialog, QMessageBox

from GUI.Timers import TimersDialog

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
except ImportError:
    pass

from GUI import Toolbar, VLayout
from GUI.BSSID import BSSIdDialog
from GUI.Broker import BrokerDialog
from GUI.Console import ConsoleWidget
from GUI.Rules import RulesWidget
from GUI.Telemetry import TelemetryWidget
from GUI.Devices import ListWidget
from GUI.Patterns import PatternsDialog
from Util import TasmotaDevice, TasmotaEnvironment, parse_topic, default_patterns, prefixes, custom_patterns, \
    expand_fulltopic
from Util.models import TasmotaDevicesModel
from Util.mqtt import MqttClient

# TODO: refactor topic subscriptions so they add custom patterns and device deletion
# TODO: telemetry
# TODO: rework device export


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self._version = "0.2.0"
        self.setWindowIcon(QIcon("GUI/icons/logo.png"))
        self.setWindowTitle("Tasmota Device Manager {}".format(self._version))

        self.env = TasmotaEnvironment()
        self.device = None

        self.topics = []
        self.mqtt_queue = []
        self.fulltopic_queue = []

        self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)
        self.setMinimumSize(QSize(1000, 618))  # because golden ratio :)

        # load devices from the settings file, create TasmotaDevices and add the to the envvironment
        self.settings.beginGroup("Devices")
        for d in self.settings.childGroups():
            self.settings.beginGroup(d)
            device = TasmotaDevice(d, self.settings.value("full_topic"), self.settings.value("friendly_name"))
            device.env = self.env
            self.env.devices.append(device)

            # load device command history
            self.settings.beginGroup("history")
            for k in self.settings.childKeys():
                device.history.append(self.settings.value(k))
            self.settings.endGroup()

            self.settings.endGroup()
        self.settings.endGroup()

        # load custom autodiscovery patterns
        self.settings.beginGroup("Patterns")
        for k in self.settings.childKeys():
            custom_patterns.append(self.settings.value(k))
        self.settings.endGroup()

        self.device_model = TasmotaDevicesModel(self.env)

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
        self.auto_timer.timeout.connect(self.auto_telemetry)

        self.load_window_state()

        if self.settings.value("connect_on_startup", False, bool):
            self.actToggleConnect.trigger()

        self.tele_docks = {}

    def setup_main_layout(self):
        self.mdi = QMdiArea()
        self.mdi.setActivationOrder(QMdiArea.ActivationHistoryOrder)
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
        self.devices_list = ListWidget(self)
        sub = self.mdi.addSubWindow(self.devices_list)
        sub.setWindowState(Qt.WindowMaximized)
        self.devices_list.deviceSelected.connect(self.selectDevice)
        self.devices_list.openConsole.connect(self.openConsole)
        self.devices_list.openRulesEditor.connect(self.openRulesEditor)
        self.devices_list.openWebUI.connect(self.openWebUI)

        self.devices_list.cfgTimers.connect(self.configureTimers)
        self.devices_list.cfgModule.connect(self.configureModule)

    def load_window_state(self):
        wndGeometry = self.settings.value('window_geometry')
        if wndGeometry:
            self.restoreGeometry(wndGeometry)

    def build_mainmenu(self):
        mSetup = self.menuBar().addMenu("Options")
        mSetup.addAction(QIcon(), "MQTT Broker", self.setup_broker)
        mSetup.addAction(QIcon(), "Auto telemetry period", lambda: print('asd'))
        mSetup.addAction(QIcon(), "BSSId aliases", self.bssid)
        mSetup.addAction(QIcon(), "Autodiscovery patterns", self.patterns)

        # mDevices.addAction(QIcon("GUI/icons/export.png"), "Export list", self.export)

    def build_toolbars(self):
        main_toolbar = Toolbar(orientation=Qt.Horizontal, iconsize=24, label_position=Qt.ToolButtonTextBesideIcon)
        main_toolbar.setObjectName("main_toolbar")
        self.addToolBar(main_toolbar)

        self.actToggleConnect = QAction(QIcon("./GUI/icons/disconnect.png"), "Connect")
        self.actToggleConnect.setCheckable(True)
        self.actToggleConnect.toggled.connect(self.toggle_connect)
        main_toolbar.addAction(self.actToggleConnect)

        self.actToggleAutoUpdate = QAction(QIcon("./GUI/icons/auto_telemetry.png"), "Auto telemetry")
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

    def auto_telemetry(self):
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
        # expand fulltopic patterns to subscribable topics
        for pat in default_patterns:    # tasmota default and SO19
            self.topics += expand_fulltopic(pat)

        for d in self.env.devices:
            # if device has a non-standard pattern, check if the pattern is found in the custom patterns
            if not d.is_default() and d.p['FullTopic'] not in custom_patterns:
                # if pattern is not found then add the device topics to subscription list.
                # if the pattern is found, it will be matched without implicit subscription
                self.topics += expand_fulltopic(d.p['FullTopic'])

        # check if custom patterns can be matched by default patterns
        for pat in custom_patterns:
            if pat.startswith("%prefix%") or pat.split('/')[1] == "%prefix%":
                continue    # do nothing, default subcriptions will match this topic
            else:
                self.topics += expand_fulltopic(pat)

        # passing a list of tuples as recommended by paho
        self.mqtt.subscribe([(topic, 0) for topic in self.topics])


    @pyqtSlot(str, str)
    def mqtt_publish(self, t, p):
        self.mqtt.publish(t, p)

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
        # try to find a device by matching known FullTopics against the MQTT topic of the message
        device = self.env.find_device(topic)
        if device:
            # forward the message for processing
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
                # received LWT from an unknown device
                # first part of Tasmota Autodiscovery algorithm
                # begin by loading default and user-provided FullTopic patterns

                for p in default_patterns + custom_patterns:
                    # for all the patterns, match the LWT topic (it follows the device's FullTopic syntax
                    match = re.fullmatch(p.replace("%topic%", "(?P<topic>.*?)").replace("%prefix%", "(?P<prefix>.*?)") + ".*$", topic)
                    if match:
                        # assume that the matched topic is the one configured in device settings
                        possible_topic = match.groupdict().get('topic')
                        if possible_topic not in ('tele', 'stat'):
                            # if the assumed topic is different from tele or stat, there is a chance that it's a valid topic
                            # query the assumed device for its FullTopic. False positives won't reply.
                            self.mqtt_queue.append([p.replace("%prefix%", "cmnd").replace("%topic%", possible_topic) + "FullTopic", ""])

        elif topic.endswith("RESULT"):
            # we have a reply from an unknown device
            if not device:
                # second part of Tasmota Autodiscovery algorithm
                try:
                    full_topic = loads(msg).get('FullTopic')
                    if full_topic:
                        # the device replies with its FullTopic
                        # here the Topic is extracted using the returned FullTopic, identifying the device
                        parsed = parse_topic(full_topic, topic)
                        if parsed:
                            # the topic matches, we can add the device to our environment and Device List
                            d = TasmotaDevice(parsed['topic'], full_topic)
                            d.update_property("LWT", "online")
                            self.env.devices.append(d)
                            self.device_model.addDevice(d)
                            self.initial_query(d, True)

                except JSONDecodeError as e:
                    with open("{}/TDM/error.log".format(QDir.homePath()), "a+") as l:
                        l.write("{}\t{}\t{}\t{}\n".format(QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss"), topic, msg, e.msg))

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

    def patterns(self):
        PatternsDialog().exec_()

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
            tele_widget = TelemetryWidget(fname, topic, tele_topic, stat_topic)
            self.telemetry.connect(tele_widget.parse_telemetry)
            self.addDockWidget(Qt.RightDockWidgetArea, tele_widget)

    @pyqtSlot()
    def openConsole(self):
        if self.device:
            console_widget = ConsoleWidget(self.device)
            self.mqtt.messageSignal.connect(console_widget.consoleAppend)
            console_widget.sendCommand.connect(self.mqtt.publish)
            self.addDockWidget(Qt.BottomDockWidgetArea, console_widget)
            console_widget.command.setFocus()

    @pyqtSlot()
    def openRulesEditor(self):
        if self.device:
            rules = RulesWidget(self.device)
            self.mqtt.messageSignal.connect(rules.parseMessage)
            rules.sendCommand.connect(self.mqtt_publish)
            self.mdi.setViewMode(QMdiArea.TabbedView)
            self.mdi.addSubWindow(rules)
            rules.setWindowState(Qt.WindowMaximized)
            rules.destroyed.connect(self.updateMDI)
            self.mqtt_queue.append((self.device.cmnd_topic("ruletimer"), ""))
            self.mqtt_queue.append((self.device.cmnd_topic("rule1"), ""))
            for i in range(1, 6):
                self.mqtt_queue.append((self.device.cmnd_topic("Var{}".format(i)), ""))
                self.mqtt_queue.append((self.device.cmnd_topic("Mem{}".format(i)), ""))

    @pyqtSlot()
    def openWebUI(self):
        if self.device and self.device.p.get('IPAddress'):
            url = QUrl("http://{}".format(self.device.p['IPAddress']))

            try:
                webui = QWebEngineView()
                webui.load(url)

                frm_webui = QFrame()
                frm_webui.setWindowTitle("WebUI [{}]".format(self.device.p['FriendlyName'][0]))
                frm_webui.setFrameShape(QFrame.StyledPanel)
                frm_webui.setLayout(VLayout(0))
                frm_webui.layout().addWidget(webui)
                frm_webui.destroyed.connect(self.updateMDI)

                self.mdi.addSubWindow(frm_webui)
                self.mdi.setViewMode(QMdiArea.TabbedView)
                frm_webui.setWindowState(Qt.WindowMaximized)

            except NameError:
                QDesktopServices.openUrl(QUrl("http://{}".format(self.device.p['IPAddress'])))

    @pyqtSlot()
    def configureTimers(self):
        if self.device:
            timers = TimersDialog(self.device)
            self.mqtt.messageSignal.connect(timers.parseMessage)
            timers.sendCommand.connect(self.mqtt_publish)
            self.mqtt_queue.append((self.device.cmnd_topic("timers"), ""))
            timers.exec_()

    @pyqtSlot()
    def configureModule(self):
        if self.device:
            modules = self.device.modules()
            curr_module = self.device.module()
            idx = -1
            for idx, module in enumerate(modules):
                if curr_module in module:
                    break

            module, ok = QInputDialog.getItem(self, "Configure module [{}]".format(self.device.p['FriendlyName'][0]),
                                              "Select device module", modules, idx, False)
            if ok:
                new_idx = modules.index(module)
                if new_idx != idx:
                    module_idx = module.split(" ")[0]
                    self.mqtt.publish(self.device.cmnd_topic("module"), module_idx)
                    QMessageBox.information(self, "Module changed",
                                        "Device will restart. Please wait a few seconds.")
                else:
                    QMessageBox.information(self, "Module not changed",
                                            "You have selected the current module.")

    def updateMDI(self):
        if len(self.mdi.subWindowList()) == 1:
            self.mdi.setViewMode(QMdiArea.SubWindowView)
            self.devices_list.setWindowState(Qt.WindowMaximized)

    def closeEvent(self, e):
        self.settings.setValue("version", self._version)
        self.settings.setValue("window_geometry", self.saveGeometry())

        # save devices
        self.settings.beginGroup("Devices")
        for d in self.env.devices:
            self.settings.setValue("{}/full_topic".format(d.p['Topic']), d.p['FullTopic'])
            if d.p.get('Mac'):
                self.settings.setValue("{}/Mac".format(d.p['Topic']), d.p['Mac'])
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