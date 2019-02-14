import re
import sys
from json import loads

from PyQt5.QtCore import QTimer, QSortFilterProxyModel
from PyQt5.QtWidgets import QMainWindow, QDialog, QStatusBar, QApplication, QMdiArea, QTreeView, QActionGroup, QWidget, QSizePolicy, QSplitter, QMenu

from GUI import *
from GUI.Broker import BrokerDialog
from GUI.DevicesList import DevicesListWidget
from GUI.PayloadView import PayloadViewDialog
from Util import initial_queries
from Util.models import *
from Util.mqtt import MqttClient


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self._version = "0.1.10"
        self.setWindowIcon(QIcon("GUI/icons/logo.png"))
        self.setWindowTitle("Tasmota Device Manager {}".format(self._version))

        self.main_splitter = QSplitter()
        self.devices_splitter = QSplitter(Qt.Vertical)

        self.fulltopic_queue = []
        self.settings = QSettings()
        self.setMinimumSize(QSize(1280,800))

        self.device_model = TasmotaDevicesModel()
        self.telemetry_model = TasmotaDevicesTree()
        self.console_model = ConsoleModel()

        self.sorted_console_model = QSortFilterProxyModel()
        self.sorted_console_model.setSourceModel(self.console_model)
        self.sorted_console_model.setFilterKeyColumn(CnsMdl.FRIENDLY_NAME)

        self.setup_mqtt()
        self.setup_telemetry_view()
        self.setup_main_layout()
        self.add_devices_tab()
        self.build_toolbars()
        self.setStatusBar(QStatusBar())

        self.queue_timer = QTimer()
        self.queue_timer.setSingleShot(True)
        self.queue_timer.timeout.connect(self.mqtt_ask_for_fulltopic)

        self.build_cons_ctx_menu()

        self.load_window_state()

    def setup_main_layout(self):
        self.mdi = QMdiArea()
        self.mdi.setActivationOrder(QMdiArea.ActivationHistoryOrder)
        self.mdi.setViewMode(QMdiArea.TabbedView)
        self.mdi.setDocumentMode(True)

        mdi_widget = QWidget()
        mdi_widget.setLayout(VLayout())
        mdi_widget.layout().addWidget(self.mdi)

        self.devices_splitter.addWidget(mdi_widget)

        vl_console = VLayout()
        self.console_view = TableView()
        self.console_view.setModel(self.sorted_console_model)
        self.console_view.setupColumns(columns_console)
        self.console_view.setAlternatingRowColors(True)
        self.console_view.setSortingEnabled(True)
        self.console_view.sortByColumn(CnsMdl.TIMESTAMP, Qt.DescendingOrder)
        self.console_view.verticalHeader().setDefaultSectionSize(20)
        self.console_view.setMinimumHeight(200)
        self.console_view.setContextMenuPolicy(Qt.CustomContextMenu)

        vl_console.addWidget(self.console_view)

        console_widget = QWidget()
        console_widget.setLayout(vl_console)

        self.devices_splitter.addWidget(console_widget)
        self.main_splitter.insertWidget(0, self.devices_splitter)
        self.setCentralWidget(self.main_splitter)
        self.console_view.clicked.connect(self.select_cons_entry)
        self.console_view.doubleClicked.connect(self.view_payload)
        self.console_view.customContextMenuRequested.connect(self.show_cons_ctx_menu)

    def setup_telemetry_view(self):
        tele_widget = QWidget()
        vl_tele = VLayout()
        self.tview = QTreeView()
        self.tview.setMinimumWidth(300)
        self.tview.setModel(self.telemetry_model)
        self.tview.setAlternatingRowColors(True)
        self.tview.setUniformRowHeights(True)
        self.tview.setIndentation(15)
        self.tview.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum))
        self.tview.expandAll()
        self.tview.resizeColumnToContents(0)
        vl_tele.addWidget(self.tview)
        tele_widget.setLayout(vl_tele)
        self.main_splitter.addWidget(tele_widget)

    def setup_mqtt(self):
        self.mqtt = MqttClient()
        self.mqtt.connecting.connect(self.mqtt_connecting)
        self.mqtt.connected.connect(self.mqtt_connected)
        self.mqtt.disconnected.connect(self.mqtt_disconnected)
        self.mqtt.connectError.connect(self.mqtt_connectError)
        self.mqtt.messageSignal.connect(self.mqtt_message)

    def add_devices_tab(self):
        tabDevicesList = DevicesListWidget(self)
        self.mdi.addSubWindow(tabDevicesList)
        tabDevicesList.setWindowState(Qt.WindowMaximized)

    def load_window_state(self):
        wndGeometry = self.settings.value('window_geometry')
        if wndGeometry:
            self.restoreGeometry(wndGeometry)
        spltState = self.settings.value('splitter_state')
        if spltState:
            self.main_splitter.restoreState(spltState)

    def build_toolbars(self):
        main_toolbar = Toolbar(orientation=Qt.Horizontal, iconsize=32, label_position=Qt.ToolButtonIconOnly)
        main_toolbar.setObjectName("main_toolbar")
        self.addToolBar(main_toolbar)

        main_toolbar.addAction(QIcon("./GUI/icons/connections.png"), "Configure MQTT broker", self.setup_broker)
        agBroker = QActionGroup(self)
        agBroker.setExclusive(True)

        self.actConnect = CheckableAction(QIcon("./GUI/icons/connect.png"), "Connect to the broker", agBroker)
        self.actDisconnect = CheckableAction(QIcon("./GUI/icons/disconnect.png"), "Disconnect from broker", agBroker)

        self.actDisconnect.setChecked(True)

        self.actConnect.triggered.connect(self.mqtt_connect)
        self.actDisconnect.triggered.connect(self.mqtt_disconnect)

        main_toolbar.addActions(agBroker.actions())
        main_toolbar.addSeparator()

    def initial_query(self, idx):
        for q in initial_queries:
            topic = "{}status".format(self.device_model.commandTopic(idx))
            self.mqtt.publish(topic, q)
            q = q if q else ''
            self.console_log(topic, "Asked for STATUS {}".format(q), q)

    def setup_broker(self):
        brokers_dlg = BrokerDialog()
        if brokers_dlg.exec_() == QDialog.Accepted and self.mqtt.state == self.mqtt.Connected:
            self.mqtt.disconnect()

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
        self.statusBar().showMessage("Connected to {}:{} as {}".format(self.broker_hostname, self.broker_port, self.broker_username if self.broker_username else '[anonymous]'))

        self.mqtt_subscribe()

        for d in range(self.device_model.rowCount()):
            idx = self.device_model.index(d, 0)
            self.initial_query(idx)

    def mqtt_subscribe(self):
        main_topics = ["+/stat/+", "+/tele/+", "stat/#", "tele/#"]

        for d in range(self.device_model.rowCount()):
            idx = self.device_model.index(d, 0)
            if not self.device_model.isDefaultTemplate(idx):
                main_topics.append(self.device_model.commandTopic(idx))
                main_topics.append(self.device_model.statTopic(idx))

        for t in main_topics:
            self.mqtt.subscribe(t)

    def mqtt_ask_for_fulltopic(self):
        for i in range(len(self.fulltopic_queue)):
            self.mqtt.publish(self.fulltopic_queue.pop(0))

    def mqtt_disconnected(self):
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
        self.actDisconnect.setChecked(True)

    def mqtt_message(self, topic, msg):
        if topic.endswith('/LWT'):
            device_topic = self.find_device(topic)
            if not msg:
                msg = "offline"

            if device_topic:
                self.console_log(topic, "LWT update: {}".format(msg), msg)
                idx = self.device_model.deviceByTopic(device_topic)
                self.device_model.updateValue(idx, DevMdl.LWT, msg)

            elif msg == "Online":
                split_topic = topic.split('/')
                device_topic = split_topic[1]
                if device_topic == 'tele':
                    device_topic = split_topic[0]

                self.console_log(topic, "LWT for unknown device {}. Asking for FullTopic.".format(device_topic), msg, False)

                self.fulltopic_queue.append("cmnd/{}/fulltopic".format(device_topic))
                self.fulltopic_queue.append("{}/cmnd/fulltopic".format(device_topic))
                self.queue_timer.start(1500)

        if topic.endswith('/RESULT'):
            topic = topic.rstrip('RESULT')
            full_topic = loads(msg).get('FullTopic')
            new_topic = loads(msg).get('Topic')
            template_name = loads(msg).get('NAME')

            if full_topic:
                #TODO: update FullTopic for existing device AFTER the FullTopic changes externally (the message will arrive from new FullTopic)
                device_topic = self.match_topic(full_topic, topic)
                idx = self.device_model.deviceByTopic(device_topic)
                if not idx.isValid():
                    self.console_log(topic, "FullTopic for {}".format(device_topic), msg, False)

                    new_idx = self.device_model.addDevice(device_topic, full_topic, lwt='online')

                    tele_idx = self.telemetry_model.addDevice(TasmotaDevice, device_topic)
                    #TODO: add QSortFilterProxyModel to telemetry treeview and sort devices after adding
                    self.telemetry_model.devices[device_topic] = tele_idx

                    self.initial_query(new_idx)
                    self.console_log(topic, "Added {} with fulltopic {}, querying for STATE".format(device_topic, full_topic), msg)
                    self.tview.expand(tele_idx)

            if new_topic:
                device_topic = self.find_device(topic)
                if device_topic and device_topic != new_topic:
                    self.console_log(topic, "New topic for {}".format(device_topic), msg)

                    idx = self.device_model.deviceByTopic(device_topic)
                    self.device_model.updateValue(idx, DevMdl.TOPIC, new_topic)

                    tele_idx = self.telemetry_model.devices.get(device_topic)

                    if tele_idx:
                        self.telemetry_model.setDeviceName(tele_idx, new_topic)
                        self.telemetry_model.devices[new_topic] = self.telemetry_model.devices.pop(device_topic)

            if template_name:
                self.device_model.updateValue(self.device, DevMdl.MODULE, template_name)

        else:
            self.device_topic = self.find_device(topic)
            self.device = self.device_model.deviceByTopic(self.device_topic)

            if self.device.isValid():
                if topic.endswith('STATUS'):
                    self.console_log(topic, "Received device status", msg)
                    payload = loads(msg)['Status']
                    self.device_model.updateValue(self.device, DevMdl.FRIENDLY_NAME, payload['FriendlyName'][0])
                    module = payload['Module']
                    if module == '0':
                        self.mqtt.publish(self.device_model.commandTopic(self.device)+"template")
                    else:
                        self.device_model.updateValue(self.device, DevMdl.MODULE, module)


                elif topic.endswith('STATUS1'):
                    self.console_log(topic, "Received program information", msg)
                    payload = loads(msg)['StatusPRM']
                    self.device_model.updateValue(self.device, DevMdl.RESTART_REASON, payload['RestartReason'])

                elif topic.endswith('STATUS2'):
                    self.console_log(topic, "Received firmware information", msg)
                    payload = loads(msg)['StatusFWR']
                    self.device_model.updateValue(self.device, DevMdl.FIRMWARE, payload['Version'])
                    self.device_model.updateValue(self.device, DevMdl.CORE, payload['Core'])

                elif topic.endswith('STATUS3'):
                    self.console_log(topic, "Received syslog information", msg)
                    payload = loads(msg)['StatusLOG']
                    self.device_model.updateValue(self.device, DevMdl.TELEPERIOD, payload['TelePeriod'])

                elif topic.endswith('STATUS5'):
                    self.console_log(topic, "Received network status", msg)
                    payload = loads(msg)['StatusNET']
                    self.device_model.updateValue(self.device, DevMdl.MAC, payload['Mac'])
                    self.device_model.updateValue(self.device, DevMdl.IP, payload['IPAddress'])

                elif topic.endswith('STATUS8'):
                    self.console_log(topic, "Received telemetry", msg)
                    payload = loads(msg)['StatusSNS']
                    self.parse_telemetry(payload)

                elif topic.endswith('STATUS11'):
                    self.console_log(topic, "Received device state", msg)
                    payload = loads(msg)['StatusSTS']
                    self.parse_state(payload)

                elif topic.endswith('SENSOR'):
                    self.console_log(topic, "Received telemetry", msg)
                    payload = loads(msg)
                    self.parse_telemetry(payload)

                elif topic.endswith('STATE'):
                    self.console_log(topic, "Received device state", msg)
                    payload = loads(msg)
                    self.parse_state(payload)

    def parse_state(self, payload):
        self.device_model.updateValue(self.device, DevMdl.BSSID, payload['Wifi']['BSSId'])
        self.device_model.updateValue(self.device, DevMdl.SSID, payload['Wifi']['SSId'])
        self.device_model.updateValue(self.device, DevMdl.CHANNEL, payload['Wifi']['Channel'])
        self.device_model.updateValue(self.device, DevMdl.RSSI, payload['Wifi']['RSSI'])
        self.device_model.updateValue(self.device, DevMdl.UPTIME, payload['Uptime'])

        power = {k:payload[k] for k in payload.keys() if k.startswith("POWER")}
        self.device_model.updateValue(self.device, DevMdl.POWER, power)
        self.device_model.updateValue(self.device, DevMdl.LOADAVG, payload.get('LoadAvg'))

        tele_dev_idx = self.telemetry_model.devices.get(self.device_topic)

        if tele_dev_idx:
            tele_device = self.telemetry_model.getNode(tele_dev_idx)
            self.telemetry_model.setDeviceFriendlyName(tele_dev_idx, self.device_model.data(self.device_model.index(self.device.row(), DevMdl.FRIENDLY_NAME)))

            pr = tele_device.provides()
            for k in pr.keys():
                self.telemetry_model.setData(pr[k], payload.get(k))

    def parse_telemetry(self, payload):
        device = self.telemetry_model.devices.get(self.device_topic)
        if device:
            node = self.telemetry_model.getNode(device)
            time = node.provides()['Time']
            if 'Time' in payload:
                self.telemetry_model.setData(time, payload.pop('Time'))

            temp_unit = "C"
            pres_unit = "hPa"

            if 'TempUnit' in payload:
                temp_unit = payload.pop('TempUnit')

            if 'PressureUnit' in payload:
                pres_unit = payload.pop('PressureUnit')

            for sensor in sorted(payload.keys()):
                if sensor == 'DS18x20':
                    for sns_name in payload[sensor].keys():
                        d = node.devices().get(sensor)
                        if not d:
                            d = self.telemetry_model.addDevice(DS18x20, payload[sensor][sns_name]['Type'], device)
                        self.telemetry_model.getNode(d).setTempUnit(temp_unit)
                        payload[sensor][sns_name]['Id'] = payload[sensor][sns_name].pop('Address')

                        pr = self.telemetry_model.getNode(d).provides()
                        for pk in pr.keys():
                            self.telemetry_model.setData(pr[pk], payload[sensor][sns_name].get(pk))
                        self.tview.expand(d)

                elif sensor.startswith('DS18B20'):
                    d = node.devices().get(sensor)
                    if not d:
                        d = self.telemetry_model.addDevice(DS18x20, sensor, device)
                    self.telemetry_model.getNode(d).setTempUnit(temp_unit)
                    pr = self.telemetry_model.getNode(d).provides()
                    for pk in pr.keys():
                        self.telemetry_model.setData(pr[pk], payload[sensor].get(pk))
                    self.tview.expand(d)

                if sensor == 'COUNTER':
                    d = node.devices().get(sensor)
                    if not d:
                        d = self.telemetry_model.addDevice(CounterSns, "Counter", device)
                    pr = self.telemetry_model.getNode(d).provides()
                    for pk in pr.keys():
                        self.telemetry_model.setData(pr[pk], payload[sensor].get(pk))
                    self.tview.expand(d)

                else:
                    d = node.devices().get(sensor)
                    if not d:
                        d = self.telemetry_model.addDevice(sensor_map.get(sensor, Node), sensor, device)
                    pr = self.telemetry_model.getNode(d).provides()
                    if 'Temperature' in pr:
                        self.telemetry_model.getNode(d).setTempUnit(temp_unit)
                    if 'Pressure' in pr or 'SeaPressure' in pr:
                        self.telemetry_model.getNode(d).setPresUnit(pres_unit)
                    for pk in pr.keys():
                        self.telemetry_model.setData(pr[pk], payload[sensor].get(pk))
                    self.tview.expand(d)
        self.tview.resizeColumnToContents(0)

    #TODO: move to devices model
    def find_device(self, topic):
        found = None
        self.settings.beginGroup('Devices')
        for d in self.settings.childGroups():
            ft = self.settings.value('{}/full_topic'.format(d))
            device = self.match_topic(ft, topic)
            if device == d:
                found = device
                break
        self.settings.endGroup()
        return found

    # TODO: move to devices model
    def match_topic(self, full_topic, topic):
        full_topic += "(?P<reply>.*)"
        full_topic = full_topic.replace("%topic%", "(?P<topic>.*?)")
        full_topic = full_topic.replace("%prefix%", "(?P<prefix>.*?)")
        match = re.fullmatch(full_topic, topic)
        if match:
            return match.groupdict().get('topic')

    def console_log(self, topic, description, payload, known=True):
        device = self.find_device(topic)
        idx = self.device_model.deviceByTopic(device)
        fname = self.device_model.friendly_name(idx)
        self.console_model.addEntry(topic, fname, description, payload, known)
        self.console_view.resizeColumnToContents(1)

    def view_payload(self, idx):
        idx = self.sorted_console_model.mapToSource(idx)
        row = idx.row()
        timestamp = self.console_model.data(self.console_model.index(row, CnsMdl.TIMESTAMP))
        topic = self.console_model.data(self.console_model.index(row, CnsMdl.TOPIC))
        payload = self.console_model.data(self.console_model.index(row, CnsMdl.PAYLOAD))

        dlg = PayloadViewDialog(timestamp, topic, payload)
        dlg.exec_()

    def select_cons_entry(self, idx):
        self.cons_idx = idx

    def build_cons_ctx_menu(self):
        self.cons_ctx_menu = QMenu()
        self.cons_ctx_menu.addAction("View payload", lambda: self.view_payload(self.cons_idx))
        self.cons_ctx_menu.addSeparator()
        self.cons_ctx_menu.addAction("Show only this device", lambda: self.cons_set_filter(self.cons_idx))
        self.cons_ctx_menu.addAction("Show all devices", self.cons_set_filter)

    def show_cons_ctx_menu(self, at):
        self.select_cons_entry(self.console_view.indexAt(at))
        self.cons_ctx_menu.popup(self.console_view.viewport().mapToGlobal(at))

    def cons_set_filter(self, idx=None):
        if idx:
            idx = self.sorted_console_model.mapToSource(idx)
            topic = self.console_model.data(self.console_model.index(idx.row(), CnsMdl.FRIENDLY_NAME))
            self.sorted_console_model.setFilterFixedString(topic)
        else:
            self.sorted_console_model.setFilterFixedString("")

    def closeEvent(self, e):
        self.settings.setValue("window_geometry", self.saveGeometry())
        self.settings.setValue("splitter_state", self.main_splitter.saveState())
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