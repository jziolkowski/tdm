import csv
import logging
import re

from PyQt5.QtCore import QDir, QFileInfo, QSettings, QSize, Qt, QTimer, QUrl, pyqtSlot
from PyQt5.QtGui import QDesktopServices, QFont, QIcon
from PyQt5.QtWidgets import (
    QAction,
    QDialog,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMdiArea,
    QMessageBox,
    QPushButton,
    QStatusBar,
)

from tdmgr.GUI.console import ConsoleWidget
from tdmgr.GUI.devices import DevicesListWidget
from tdmgr.GUI.dialogs import (
    BrokerDialog,
    BSSIdDialog,
    ClearRetainedDialog,
    PatternsDialog,
    PrefsDialog,
)
from tdmgr.GUI.rules import RulesWidget
from tdmgr.GUI.telemetry import TelemetryWidget
from tdmgr.GUI.widgets import Toolbar
from tdmgr.models.devices import TasmotaDevicesModel
from tdmgr.mqtt import (
    DEFAULT_PATTERNS,
    MQTT_PATH_REGEX,
    Message,
    MqttClient,
    expand_fulltopic,
    initial_commands,
)
from tdmgr.tasmota.device import TasmotaDevice
from tdmgr.tasmota.discovery import lwt_discovery_stage2
from tdmgr.tasmota.environment import TasmotaEnvironment

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(
        self,
        version: str,
        settings: QSettings,
        devices: QSettings,
        debug: bool,
        *args,
        **kwargs,
    ):
        super(MainWindow, self).__init__(*args, **kwargs)
        self._version = version
        self.debug = debug
        self.setWindowIcon(QIcon(":/logo.png"))
        self.setWindowTitle(f"Tasmota Device Manager {self._version}")

        self.menuBar().setNativeMenuBar(False)

        self.unknown = []
        self.custom_patterns = []
        self.env = TasmotaEnvironment()
        self.device = None

        self.topics = []
        self.mqtt_queue = []
        self.fulltopic_queue = []

        self.lwt = dict()

        self.settings = settings
        self.devices = devices
        self.setMinimumSize(QSize(1000, 600))

        # load devices from the devices file, create TasmotaDevices and add the to the environment
        for mac in self.devices.childGroups():
            self.devices.beginGroup(mac)
            device = TasmotaDevice(
                self.devices.value("topic"),
                self.devices.value("full_topic"),
                self.devices.value("device_name"),
            )
            device.debug = self.devices.value("debug", False, bool)
            device.p["Mac"] = mac.replace("-", ":")
            device.env = self.env
            self.env.devices.append(device)

            # load device command history
            self.devices.beginGroup("history")
            for k in self.devices.childKeys():
                device.history.append(self.devices.value(k))
            self.devices.endGroup()

            self.devices.endGroup()

        self.device_model = TasmotaDevicesModel(self.settings, self.devices, self.env)

        self.setup_mqtt()
        self.setup_main_layout()
        self.add_devices_tab()
        self.build_mainmenu()
        # self.build_toolbars()
        self.setStatusBar(QStatusBar())
        #
        pbSubs = QPushButton("Show subscriptions")
        pbSubs.setFlat(True)
        pbSubs.clicked.connect(self.showSubs)
        self.statusBar().addPermanentWidget(pbSubs)

        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self.mqtt_publish_queue)
        self.queue_timer.start(250)

        self.auto_timer = QTimer()
        self.auto_timer.timeout.connect(self.auto_telemetry)

        self.load_window_state()

        if self.settings.value("connect_on_startup", False, bool):
            self.actToggleConnect.trigger()

        self.tele_docks = []
        self.consoles = []
        log.info(f"### TDM {self._version} START ###")

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
        self.devices_list = DevicesListWidget(self)
        sub = self.mdi.addSubWindow(self.devices_list)
        sub.setWindowState(Qt.WindowMaximized)
        self.devices_list.deviceSelected.connect(self.selectDevice)
        self.devices_list.openConsole.connect(self.openConsole)
        self.devices_list.openRulesEditor.connect(self.openRulesEditor)
        self.devices_list.openTelemetry.connect(self.openTelemetry)
        self.devices_list.openWebUI.connect(self.openWebUI)

    def load_window_state(self):
        wndGeometry = self.settings.value("window_geometry")
        if wndGeometry:
            self.restoreGeometry(wndGeometry)

    def build_mainmenu(self):
        mMQTT = self.menuBar().addMenu("MQTT")
        self.actToggleConnect = QAction(QIcon(":/disconnect.png"), "Connect")
        self.actToggleConnect.setCheckable(True)
        self.actToggleConnect.toggled.connect(self.toggle_connect)
        mMQTT.addAction(self.actToggleConnect)

        mMQTT.addAction(QIcon(), "Broker", self.setup_broker)
        mMQTT.addAction(QIcon(), "Autodiscovery patterns", self.patterns)

        mMQTT.addSeparator()
        mMQTT.addAction(QIcon(), "Clear retained topics", self.clear_retained_topics)

        mMQTT.addSeparator()
        mMQTT.addAction(QIcon(), "Auto telemetry period", self.auto_telemetry_period)

        self.actToggleAutoUpdate = QAction(QIcon(":/auto_telemetry.png"), "Auto telemetry")
        self.actToggleAutoUpdate.setCheckable(True)
        self.actToggleAutoUpdate.toggled.connect(self.toggle_autoupdate)
        mMQTT.addAction(self.actToggleAutoUpdate)

        mSettings = self.menuBar().addMenu("Settings")
        mSettings.addAction(QIcon(), "BSSId aliases", self.bssid)
        mSettings.addSeparator()
        mSettings.addAction(QIcon(), "Preferences", self.prefs)
        mSettings.addSeparator()
        mSettings.addAction(QIcon(), "Open config file", self.open_config_file)
        mSettings.addAction(QIcon(), "Open log file location", self.open_log_location)

    def build_toolbars(self):
        main_toolbar = Toolbar(
            orientation=Qt.Horizontal, iconsize=24, label_position=Qt.ToolButtonTextBesideIcon
        )
        main_toolbar.setObjectName("main_toolbar")

    def initial_query(self, device, queued=False):
        cmds = [" ".join(c) for c in initial_commands()]
        backlog = device.cmnd_topic("backlog")
        backlog_payload = ";".join(cmds)

        if queued:
            self.mqtt_queue.append([backlog, backlog_payload])
        else:
            self.mqtt.publish(backlog, backlog_payload, 1)

    def setup_broker(self):
        brokers_dlg = BrokerDialog(self.settings)
        if brokers_dlg.exec_() == QDialog.Accepted and self.mqtt.state == self.mqtt.Connected:
            self.mqtt.disconnect()

    def toggle_autoupdate(self, state):
        if state:
            if self.mqtt.state == self.mqtt.Connected:
                for d in self.env.devices:
                    self.mqtt.publish(d.cmnd_topic("STATUS"), payload=8)
            self.auto_timer.setInterval(self.settings.value("autotelemetry", 5000, int))
            self.auto_timer.start()
        else:
            self.auto_timer.stop()

    def toggle_connect(self, state):
        if state and self.mqtt.state == self.mqtt.Disconnected:
            self.mqtt_connect()
        elif not state and self.mqtt.state == self.mqtt.Connected:
            self.mqtt_disconnect()

    def auto_telemetry(self):
        if self.mqtt.state == self.mqtt.Connected:
            for d in self.env.devices:
                self.mqtt.publish(d.cmnd_topic("STATUS"), payload=8)

    def mqtt_connect(self):
        self.broker_tls = self.settings.value("tls", False, bool)
        self.broker_tls_file = self.settings.value("tls_file", "", str)
        self.broker_tls_insecure = self.settings.value("tls_insecure", False, bool)
        self.broker_tls_version = self.settings.value("tls_version")
        self.broker_hostname = self.settings.value("hostname", "localhost")
        self.broker_port = self.settings.value("port", 1883, int)
        self.broker_username = self.settings.value("username")
        self.broker_password = self.settings.value("password")

        if self.broker_tls:
            self.mqtt.setSSL(
                self.broker_tls_file, self.broker_tls_insecure, self.broker_tls_version
            )
        else:
            self.mqtt.unsetSSL()

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
        self.actToggleConnect.setIcon(QIcon(":/connect.png"))
        self.actToggleConnect.setText("Disconnect")
        self.statusBar().showMessage(
            f"Connected to {self.broker_hostname}:{self.broker_port} as "
            f"{self.broker_username if self.broker_username else '[anonymous]'}"
        )

        self.mqtt_subscribe()

    def mqtt_subscribe(self):
        # clear old topics
        self.topics.clear()
        self.custom_patterns.clear()

        # load custom autodiscovery patterns
        self.settings.beginGroup("Patterns")
        for k in self.settings.childKeys():
            self.custom_patterns.append(self.settings.value(k))
        self.settings.endGroup()

        # TODO: move to TasmotaEnvironment, add unit tests
        # expand fulltopic patterns to subscribable topics
        for pat in DEFAULT_PATTERNS:  # tasmota default and SO19
            self.topics += expand_fulltopic(pat)

        # check if custom patterns can be matched by default patterns
        for pat in self.custom_patterns:
            if pat.startswith("%prefix%") or pat.split("/")[1] == "%prefix%":
                continue  # do nothing, default subcriptions will match this topic
            else:
                self.topics += expand_fulltopic(pat)

        for d in self.env.devices:
            # if device has a non-standard pattern, check if the pattern is found in
            # the custom patterns
            for custom_pattern in self.custom_patterns:
                custom_pattern_match = re.match(
                    custom_pattern.replace("+", f"({MQTT_PATH_REGEX})"), d.p["FullTopic"]
                )
                if not d.is_default() and not custom_pattern_match:
                    # if pattern is not found then add the device topics to subscription list.
                    # if the pattern is found, it will be matched without implicit subscription
                    self.topics += expand_fulltopic(d.p["FullTopic"])

        # passing a list of tuples as recommended by paho
        _topics = [("tasmota/discovery/+/config", 0)] + [(topic, 0) for topic in self.topics]
        self.mqtt.subscribe(_topics)

    @pyqtSlot(str, str)
    def mqtt_publish(self, t, p):
        self.mqtt.publish(t, p)

    def mqtt_publish_queue(self):
        for q in self.mqtt_queue:
            t, p = q
            self.mqtt.publish(t, p)
            self.mqtt_queue.pop(self.mqtt_queue.index(q))

    def mqtt_disconnected(self):
        self.actToggleConnect.setIcon(QIcon(":/disconnect.png"))
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
        self.statusBar().showMessage(f"Connection error: {reason[rc]}")
        self.actToggleConnect.setChecked(False)

    def mqtt_message(self, msg: Message):
        if msg.retained:
            self.env.retained.add(msg.topic)

        # if msg.is_lwt:
        #     self.env.lwts[msg.topic] = msg.payload
        # TODO: make native discovery work (#255)
        # discovery_mode = self.settings.value("discovery_mode", 0, int)
        # if msg.topic.startswith("tasmota/discovery") and discovery_mode != DiscoveryMode.LEGACY:
        #     # Add device using native Tasmota discovery message
        #     if msg.endpoint == "config":
        #         obj = None
        #         try:
        #             obj = DiscoverySchema.model_validate_json(msg.payload)
        #         except ValueError:
        #             log.error("Unable to parse Tasmota discovery message: %s", msg.payload)
        #
        #         if obj and not self.env.find_device(obj.t):
        #             device = TasmotaDevice.from_discovery(obj)
        #             for sub_topic in device.subscribable_topics:
        #                 if sub_topic not in self.topics:
        #                     self.topics.append(sub_topic)
        #                     self.mqtt.subscribe([(sub_topic, 0)])
        #
        #             self.env.devices.append(device)
        #             self.device_model.addDevice(device)
        #             log.info(
        #                 "DISCOVERY(NATIVE): Discovered topic=%s with fulltopic=%s",
        #                 obj.t,
        #                 device.p["FullTopic"],
        #             )
        #             self.initial_query(device, True)
        #
        #             lwt = self.env.lwts.pop(f"{obj.ft}/LWT", obj.ofln)
        #             device.update_property("LWT", lwt)

        if device := self.env.find_device(msg):
            if msg.is_lwt:
                log.debug("MQTT: LWT message for %s: %s", device.p["Topic"], msg.payload)
                device.online = msg.payload

                if device.online:
                    # known device came online, query initial state
                    self.initial_query(device, True)

            else:
                # forward the message for processing
                device.online = True
                device.process_message(msg)

        # TODO: ditto
        # elif discovery_mode != DiscoveryMode.NATIVE:
        else:
            # unknown device, start autodiscovery process
            if msg.is_lwt:
                self.env.lwts[msg.topic] = msg.payload
                log.info("DISCOVERY(LEGACY): LWT from an unknown device %s", msg.topic)

                # STAGE 1
                # load default and user-provided FullTopic patterns and for all the patterns,
                # try matching the LWT topic (it follows the device's FullTopic syntax

                for p in DEFAULT_PATTERNS + self.custom_patterns:
                    match = msg.match_fulltopic(p)
                    if match:
                        # assume that the matched topic is the one configured in device settings
                        if (
                            possible_topic := match.groupdict().get("topic")
                        ) and possible_topic not in ("tele", "stat", "cmnd"):
                            # if the assumed topic is different from tele or stat, there is a chance
                            # that it's a valid topic. query the assumed device for its FullTopic.
                            # False positives won't reply.
                            prf_start, prf_end = match.regs[match.re.groupindex['prefix']]
                            possible_topic_cmnd = (
                                f"{msg.topic[:prf_start]}cmnd{msg.topic[prf_end:]}".replace(
                                    "/LWT", "/FullTopic"
                                )
                            )
                            log.debug(
                                "DISCOVERY(LEGACY): Asking an unknown device for FullTopic at %s",
                                possible_topic_cmnd,
                            )
                            self.mqtt_queue.append([possible_topic_cmnd, ""])

            elif msg.endpoint in ("RESULT", "FULLTOPIC"):
                # reply from an unknown device
                if d := lwt_discovery_stage2(self.env, msg):
                    self.env.devices.append(d)
                    self.device_model.addDevice(d)
                    log.debug("DISCOVERY: Sending initial query to topic %s", d.p["Topic"])
                    self.initial_query(d, True)
                    tele_topic = d.tele_topic("LWT")
                    self.env.lwts.pop(tele_topic, None)
                    d.update_property("LWT", "Online")

    def export(self):
        fname, _ = QFileDialog.getSaveFileName(
            self, "Export device list as...", directory=QDir.homePath(), filter="CSV files (*.csv)"
        )
        if fname:
            if not fname.endswith(".csv"):
                fname += ".csv"

            with open(fname, "w", encoding="utf8") as f:
                column_titles = [
                    "mac",
                    "topic",
                    "friendly_name",
                    "full_topic",
                    "cmnd_topic",
                    "stat_topic",
                    "tele_topic",
                    "module",
                    "module_id",
                    "firmware",
                    "core",
                ]
                c = csv.writer(f)
                c.writerow(column_titles)

                for r in range(self.device_model.rowCount()):
                    d = self.device_model.index(r, 0)
                    c.writerow(
                        [
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
                            self.device_model.core(d),
                        ]
                    )

    def bssid(self):
        BSSIdDialog(self.settings).exec_()

    def patterns(self):
        PatternsDialog(self.settings).exec_()

    def showSubs(self):
        QMessageBox.information(self, "Subscriptions", "\n".join(sorted(self.topics)))

    def clear_retained_topics(self):
        dlg = ClearRetainedDialog(self.env)
        if dlg.exec_() == ClearRetainedDialog.Accepted:
            for row in range(dlg.lw.count()):
                itm = dlg.lw.item(row)
                if itm.checkState() == Qt.Checked:
                    topic = itm.text()
                    self.mqtt.publish(topic, retain=True)
                    self.env.retained.remove(topic)
                    log.info("MQTT: Cleared %s", topic)

    def prefs(self):
        dlg = PrefsDialog(self.settings)
        if dlg.exec_() == QDialog.Accepted:
            # TODO: move saving to dialog accept() event
            devices_short_version = self.settings.value("devices_short_version", True, bool)
            if devices_short_version != dlg.cbDevShortVersion.isChecked():
                self.settings.setValue("devices_short_version", dlg.cbDevShortVersion.isChecked())

            update_consoles = False

            console_font_size = self.settings.value("console_font_size", 9)
            if console_font_size != dlg.sbConsFontSize.value():
                update_consoles = True
                self.settings.setValue("console_font_size", dlg.sbConsFontSize.value())

            console_word_wrap = self.settings.value("console_word_wrap", True, bool)
            if console_word_wrap != dlg.cbConsWW.isChecked():
                update_consoles = True
                self.settings.setValue("console_word_wrap", dlg.cbConsWW.isChecked())

            if update_consoles:
                for c in self.consoles:
                    c.console.setWordWrapMode(dlg.cbConsWW.isChecked())
                    new_font = QFont(c.console.font())
                    new_font.setPointSize(dlg.sbConsFontSize.value())
                    c.console.setFont(new_font)

            if dlg.bgDiscovery.checkedId() != self.settings.value("discovery_mode", 0, int):
                self.settings.setValue("discovery_mode", dlg.bgDiscovery.checkedId())

        self.settings.sync()

    def open_config_file(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.settings.fileName()))

    @staticmethod
    def open_log_location():
        fi = QFileInfo(logging.getLogger().handlers[1].baseFilename)
        QDesktopServices.openUrl(QUrl.fromLocalFile(fi.absolutePath()))

    def auto_telemetry_period(self):
        curr_val = self.settings.value("autotelemetry", 5000, int)
        period, ok = QInputDialog.getInt(
            self,
            "Set AutoTelemetry period",
            "Values under 5000ms may cause increased ESP LoadAvg",
            curr_val,
            1000,
        )
        if ok:
            self.settings.setValue("autotelemetry", period)
            self.settings.sync()

    @pyqtSlot(TasmotaDevice)
    def selectDevice(self, d):
        self.device = d

    @pyqtSlot()
    def openTelemetry(self):
        if self.device:
            tele_widget = TelemetryWidget(self.device)
            self.addDockWidget(Qt.RightDockWidgetArea, tele_widget)
            self.mqtt_publish(self.device.cmnd_topic("STATUS"), "8")
            self.tele_docks.append(tele_widget)
            self.resizeDocks(
                self.tele_docks, [100 // len(self.tele_docks) for _ in self.tele_docks], Qt.Vertical
            )

    @pyqtSlot()
    def openConsole(self):
        if self.device:
            console_widget = ConsoleWidget(self.settings, self.device)
            self.mqtt.messageSignal.connect(console_widget.consoleAppend)
            console_widget.sendCommand.connect(self.mqtt.publish)
            self.addDockWidget(Qt.BottomDockWidgetArea, console_widget)
            console_widget.command.setFocus()
            self.consoles.append(console_widget)
            self.resizeDocks(
                self.consoles, [100 // len(self.consoles) for _ in self.consoles], Qt.Horizontal
            )

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
            self.mqtt_queue.append((self.device.cmnd_topic("Var"), ""))
            self.mqtt_queue.append((self.device.cmnd_topic("Mem"), ""))

    @pyqtSlot()
    def openWebUI(self):
        if self.device and (url := self.device.url):
            QDesktopServices.openUrl(QUrl(url))

    def updateMDI(self):
        if len(self.mdi.subWindowList()) == 1:
            self.mdi.setViewMode(QMdiArea.SubWindowView)
            self.devices_list.setWindowState(Qt.WindowMaximized)

    def closeEvent(self, e):
        self.settings.setValue("version", self._version)
        self.settings.setValue("window_geometry", self.saveGeometry())
        self.settings.setValue("views_order", ";".join(self.devices_list.views.keys()))

        self.settings.beginGroup("Views")
        for view, items in self.devices_list.views.items():
            self.settings.setValue(view, ";".join(items[1:]))
        self.settings.endGroup()

        self.settings.sync()

        if not self.debug:
            for d in self.env.devices:
                mac = d.p.get("Mac")
                topic = d.p["Topic"]
                full_topic = d.p["FullTopic"]
                device_name = d.name

                if mac:
                    self.devices.beginGroup(mac.replace(":", "-"))
                    self.devices.setValue("topic", topic)
                    self.devices.setValue("full_topic", full_topic)
                    self.devices.setValue("device_name", device_name)

                    for i, h in enumerate(d.history):
                        self.devices.setValue(f"history/{i}", h)
                    self.devices.endGroup()
            self.devices.sync()

        e.accept()
