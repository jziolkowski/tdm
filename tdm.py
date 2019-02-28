import sys
import csv
from json import loads

from PyQt5.QtCore import QSortFilterProxyModel, QDir, QTimer
from PyQt5.QtWidgets import QMainWindow, QDialog, QStatusBar, QApplication, QMdiArea, QTreeView, QWidget, \
    QSplitter, QMenu, QFileDialog

from GUI import *
from GUI.BSSID import BSSIdDialog
from GUI.Broker import BrokerDialog
from GUI.DevicesList import DevicesListWidget
from GUI.PayloadView import PayloadViewDialog
from Util import initial_queries
from Util.models import *
from Util.mqtt import MqttClient


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self._version = "0.1.17"
        self.setWindowIcon(QIcon("GUI/icons/logo.png"))
        self.setWindowTitle("Tasmota Device Manager {}".format(self._version))

        self.main_splitter = QSplitter()
        self.devices_splitter = QSplitter(Qt.Vertical)

        self.mqtt_queue = []
        self.devices = {}

        self.fulltopic_queue = []
        old_settings = QSettings()

        self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)
        self.setMinimumSize(QSize(1280,800))

        for k in old_settings.allKeys():
            self.settings.setValue(k, old_settings.value(k))
            old_settings.remove(k)

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
        self.queue_timer.timeout.connect(self.mqtt_publish_queue)
        self.queue_timer.start(500)

        self.auto_timer = QTimer()
        self.auto_timer.timeout.connect(self.autoupdate)

        self.load_window_state()

        if self.settings.value("connect_on_startup", False):
            self.actToggleConnect.trigger()

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
        hl_filter = HLayout()
        self.cbFilter = QCheckBox("Console filtering")
        self.cbxFilterDevice = QComboBox()
        self.cbxFilterDevice.setEnabled(False)
        self.cbxFilterDevice.setFixedWidth(200)
        self.cbxFilterDevice.setModel(self.device_model)
        self.cbxFilterDevice.setModelColumn(DevMdl.FRIENDLY_NAME)
        hl_filter.addWidgets([self.cbFilter, self.cbxFilterDevice])
        hl_filter.addStretch(0)
        vl_console.addLayout(hl_filter)

        self.console_view = TableView()
        self.console_view.setModel(self.console_model)
        self.console_view.setupColumns(columns_console)
        self.console_view.setAlternatingRowColors(True)
        self.console_view.verticalHeader().setDefaultSectionSize(20)
        self.console_view.setMinimumHeight(200)

        vl_console.addWidget(self.console_view)

        console_widget = QWidget()
        console_widget.setLayout(vl_console)

        self.devices_splitter.addWidget(console_widget)
        self.main_splitter.insertWidget(0, self.devices_splitter)
        self.setCentralWidget(self.main_splitter)
        self.console_view.clicked.connect(self.select_cons_entry)
        self.console_view.doubleClicked.connect(self.view_payload)

        self.cbFilter.toggled.connect(self.toggle_console_filter)
        self.cbxFilterDevice.currentTextChanged.connect(self.select_console_filter)

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
        main_toolbar = Toolbar(orientation=Qt.Horizontal, iconsize=16, label_position=Qt.ToolButtonTextBesideIcon)
        main_toolbar.setObjectName("main_toolbar")
        self.addToolBar(main_toolbar)

        main_toolbar.addAction(QIcon("./GUI/icons/connections.png"), "Broker", self.setup_broker)
        self.actToggleConnect = QAction(QIcon("./GUI/icons/disconnect.png"), "MQTT")
        self.actToggleConnect.setCheckable(True)
        self.actToggleConnect.toggled.connect(self.toggle_connect)
        main_toolbar.addAction(self.actToggleConnect)

        self.actToggleAutoUpdate = QAction(QIcon("./GUI/icons/automatic.png"), "Auto telemetry")
        self.actToggleAutoUpdate.setCheckable(True)
        self.actToggleAutoUpdate.toggled.connect(self.toggle_autoupdate)
        main_toolbar.addAction(self.actToggleAutoUpdate)

        main_toolbar.addSeparator()
        main_toolbar.addAction(QIcon("./GUI/icons/bssid.png"), "BSSId", self.bssid)
        main_toolbar.addAction(QIcon("./GUI/icons/export.png"), "Export list", self.export)

    def initial_query(self, idx, queued=False):
        for q in initial_queries:
            topic = "{}status".format(self.device_model.commandTopic(idx))
            if queued:
                self.mqtt_queue.append([topic, q])
            else:
                self.mqtt.publish(topic, q, 1)
            self.console_log(topic, "Asked for STATUS {}".format(q), q)

    def setup_broker(self):
        brokers_dlg = BrokerDialog()
        if brokers_dlg.exec_() == QDialog.Accepted and self.mqtt.state == self.mqtt.Connected:
            self.mqtt.disconnect()

    def toggle_autoupdate(self, state):
        if state:
            self.auto_timer.setInterval(5000)
            self.auto_timer.start()

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
            for d in range(self.device_model.rowCount()):
                idx = self.device_model.index(d, 0)
                cmnd = self.device_model.commandTopic(idx)
                self.mqtt.publish(cmnd+"STATUS", payload=8)

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

    def mqtt_publish_queue(self):
        for q in self.mqtt_queue:
            t, p = q
            self.mqtt.publish(t, p)
            self.mqtt_queue.pop(self.mqtt_queue.index(q))

    def mqtt_disconnected(self):
        self.actToggleConnect.setIcon(QIcon("./GUI/icons/disconnect.png"))
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
        self.actToggleConnectt.setChecked(False)

    def mqtt_message(self, topic, msg):
        found = self.device_model.findDevice(topic)
        if found.reply == 'LWT':
            if not msg:
                msg = "offline"

            if found.index.isValid():
                self.console_log(topic, "LWT update: {}".format(msg), msg)
                self.device_model.updateValue(found.index, DevMdl.LWT, msg)
                self.initial_query(found.index, queued=True)

            elif msg == "Online":
                self.console_log(topic, "LWT for unknown device '{}'. Asking for FullTopic.".format(found.topic), msg, False)
                self.mqtt_queue.append(["cmnd/{}/fulltopic".format(found.topic), ""])
                self.mqtt_queue.append(["{}/cmnd/fulltopic".format(found.topic), ""])


        elif found.reply == 'RESULT':
            full_topic = loads(msg).get('FullTopic')
            new_topic = loads(msg).get('Topic')
            template_name = loads(msg).get('NAME')

            if full_topic:
                # TODO: update FullTopic for existing device AFTER the FullTopic changes externally (the message will arrive from new FullTopic)
                if not found.index.isValid():
                    self.console_log(topic, "FullTopic for {}".format(found.topic), msg, False)

                    new_idx = self.device_model.addDevice(found.topic, full_topic, lwt='online')
                    tele_idx = self.telemetry_model.addDevice(TasmotaDevice, found.topic)
                    self.telemetry_model.devices[found.topic] = tele_idx
                    #TODO: add QSortFilterProxyModel to telemetry treeview and sort devices after adding

                    self.initial_query(new_idx)
                    self.console_log(topic, "Added {} with fulltopic {}, querying for STATE".format(found.topic, full_topic), msg)
                    self.tview.expand(tele_idx)
                    self.tview.resizeColumnToContents(0)

            if new_topic:
                if found.index.isValid() and found.topic != new_topic:
                    self.console_log(topic, "New topic for {}".format(found.topic), msg)

                    self.device_model.updateValue(found.index, DevMdl.TOPIC, new_topic)

                    tele_idx = self.telemetry_model.devices.get(found.topic)

                    if tele_idx:
                        self.telemetry_model.setDeviceName(tele_idx, new_topic)
                        self.telemetry_model.devices[new_topic] = self.telemetry_model.devices.pop(found.topic)

            if template_name:
                self.device_model.updateValue(found.index, DevMdl.MODULE, template_name)

        elif found.index.isValid():
            if found.reply == 'STATUS':
                self.console_log(topic, "Received device status", msg)
                payload = loads(msg)['Status']
                self.device_model.updateValue(found.index, DevMdl.FRIENDLY_NAME, payload['FriendlyName'][0])
                self.telemetry_model.setDeviceFriendlyName(self.telemetry_model.devices[found.topic], payload['FriendlyName'][0])
                # self.tview.resizeColumnToContents(0)
                module = payload['Module']
                if module == '0':
                    self.mqtt.publish(self.device_model.commandTopic(found.index)+"template")
                else:
                    self.device_model.updateValue(found.index, DevMdl.MODULE, module)

            elif found.reply == 'STATUS1':
                self.console_log(topic, "Received program information", msg)
                payload = loads(msg)['StatusPRM']
                self.device_model.updateValue(found.index, DevMdl.RESTART_REASON, payload.get('RestartReason'))

            elif found.reply == 'STATUS2':
                self.console_log(topic, "Received firmware information", msg)
                payload = loads(msg)['StatusFWR']
                self.device_model.updateValue(found.index, DevMdl.FIRMWARE, payload['Version'])
                self.device_model.updateValue(found.index, DevMdl.CORE, payload['Core'])

            elif found.reply == 'STATUS3':
                self.console_log(topic, "Received syslog information", msg)
                payload = loads(msg)['StatusLOG']
                self.device_model.updateValue(found.index, DevMdl.TELEPERIOD, payload['TelePeriod'])

            elif found.reply == 'STATUS5':
                self.console_log(topic, "Received network status", msg)
                payload = loads(msg)['StatusNET']
                self.device_model.updateValue(found.index, DevMdl.MAC, payload['Mac'])
                self.device_model.updateValue(found.index, DevMdl.IP, payload['IPAddress'])

            elif found.reply == 'STATUS8':
                self.console_log(topic, "Received telemetry", msg)
                payload = loads(msg)['StatusSNS']
                self.parse_telemetry(found.index, payload)

            elif found.reply == 'STATUS11':
                self.console_log(topic, "Received device state", msg)
                payload = loads(msg)['StatusSTS']
                self.parse_state(found.index, payload)

            elif found.reply == 'SENSOR':
                self.console_log(topic, "Received telemetry", msg)
                payload = loads(msg)
                self.parse_telemetry(found.index, payload)

            elif found.reply == 'STATE':
                self.console_log(topic, "Received device state", msg)
                payload = loads(msg)
                self.parse_state(found.index, payload)

            elif found.reply.startswith('POWER'):
                self.console_log(topic, "Received {} state".format(found.reply), msg)
                payload = {found.reply: msg}
                self.parse_power(found.index, payload)

    def parse_power(self, index, payload, from_state=False):
        old = self.device_model.power(index)
        power = {k: payload[k] for k in payload.keys() if k.startswith("POWER")}
        # TODO: fix so that number of relays get updated properly after module/no. of relays change
        needs_update = False
        if old:
            # if from_state and len(old) != len(power):
            #     needs_update = True
            #
            # else:
            for k in old.keys():
                needs_update |= old[k] != power.get(k, old[k])
                if needs_update:
                    break
        else:
            needs_update = True

        if needs_update:
            self.device_model.updateValue(index, DevMdl.POWER, power)

    def parse_state(self, index, payload):
        bssid = payload['Wifi'].get('BSSId')
        if not bssid:
            bssid = payload['Wifi'].get('APMac')
        self.device_model.updateValue(index, DevMdl.BSSID, bssid)
        self.device_model.updateValue(index, DevMdl.SSID, payload['Wifi']['SSId'])
        self.device_model.updateValue(index, DevMdl.CHANNEL, payload['Wifi'].get('Channel', "n/a"))
        self.device_model.updateValue(index, DevMdl.RSSI, payload['Wifi']['RSSI'])
        self.device_model.updateValue(index, DevMdl.UPTIME, payload['Uptime'])
        self.device_model.updateValue(index, DevMdl.LOADAVG, payload.get('LoadAvg'))
        self.device_model.updateValue(index, DevMdl.LINKCOUNT, payload['Wifi'].get('LinkCount', "n/a"))
        self.device_model.updateValue(index, DevMdl.DOWNTIME, payload['Wifi'].get('Downtime', "n/a"))

        self.parse_power(index, payload, True)

        tele_idx = self.telemetry_model.devices.get(self.device_model.topic(index))

        if tele_idx:
            tele_device = self.telemetry_model.getNode(tele_idx)
            self.telemetry_model.setDeviceFriendlyName(tele_idx, self.device_model.friendly_name(index))

            pr = tele_device.provides()
            for k in pr.keys():
                self.telemetry_model.setData(pr[k], payload.get(k))

    def parse_telemetry(self, index, payload):
        device = self.telemetry_model.devices.get(self.device_model.topic(index))
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
        # self.tview.resizeColumnToContents(0)

    def console_log(self, topic, description, payload, known=True):
        longest_tp = 0
        longest_fn = 0
        short_topic = "/".join(topic.split("/")[0:-1])
        fname = self.devices.get(short_topic, "")
        if not fname:
            device = self.device_model.findDevice(topic)
            fname = self.device_model.friendly_name(device.index)
            self.devices.update({short_topic: fname})
        self.console_model.addEntry(topic, fname, description, payload, known)

        if len(topic) > longest_tp:
            longest_tp = len(topic)
            self.console_view.resizeColumnToContents(1)

        if len(fname) > longest_fn:
            longest_fn = len(fname)
            self.console_view.resizeColumnToContents(1)

    def view_payload(self, idx):
        if self.cbFilter.isChecked():
            idx = self.sorted_console_model.mapToSource(idx)
        row = idx.row()
        timestamp = self.console_model.data(self.console_model.index(row, CnsMdl.TIMESTAMP))
        topic = self.console_model.data(self.console_model.index(row, CnsMdl.TOPIC))
        payload = self.console_model.data(self.console_model.index(row, CnsMdl.PAYLOAD))

        dlg = PayloadViewDialog(timestamp, topic, payload)
        dlg.exec_()

    def select_cons_entry(self, idx):
        self.cons_idx = idx

    def export(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Export device list as...", directory=QDir.homePath(), filter="CSV files (*.csv)")
        if fname:
            if not fname.endswith(".csv"):
                fname += ".csv"

            with open(fname, "w", encoding='utf8') as f:
                column_titles = ['mac', 'topic', 'friendly_name', 'full_topic', 'cmnd_topic', 'stat_topic', 'tele_topic', 'module', 'firmware', 'core']
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
                        modules.get(self.device_model.module(d)),
                        self.device_model.firmware(d),
                        self.device_model.core(d)
                    ])

    def bssid(self):
        BSSIdDialog().exec_()
        # if dlg.exec_() == QDialog.Accepted:

    def toggle_console_filter(self, state):
        self.cbxFilterDevice.setEnabled(state)
        if state:
            self.console_view.setModel(self.sorted_console_model)
        else:
            self.console_view.setModel(self.console_model)

    def select_console_filter(self, fname):
        self.sorted_console_model.setFilterFixedString(fname)

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