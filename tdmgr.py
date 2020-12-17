#!/usr/bin/env python
import os
import re
import sys
import csv
from json import loads, JSONDecodeError

import logging

from PyQt5.QtCore import QTimer, pyqtSlot, QSettings, QDir, QSize, Qt, QDateTime, QUrl
from PyQt5.QtGui import QIcon, QDesktopServices, QFont
from PyQt5.QtWidgets import QMainWindow, QDialog, QStatusBar, QApplication, QMdiArea, QFileDialog, QAction, QFrame, \
    QInputDialog, QMessageBox, QPushButton

from GUI.ClearLWT import ClearLWTDialog
# from GUI.OpenHAB import OpenHABDialog
from GUI.Prefs import PrefsDialog

from GUI import icons

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
    expand_fulltopic, initial_commands
from Util.models import TasmotaDevicesModel
from Util.mqtt import MqttClient

# TODO: rework device export

__version__ = "0.2.7"
__tasmota_minimum__ = "6.6.0.17"


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self._version = __version__
        self.setWindowIcon(QIcon(":/logo.png"))
        self.setWindowTitle("Tasmota Device Manager {}".format(self._version))

        self.unknown = []
        self.env = TasmotaEnvironment()
        self.device = None

        self.topics = []
        self.mqtt_queue = []
        self.fulltopic_queue = []

        # ensure TDM directory exists in the user directory
        if not os.path.isdir("{}/TDM".format(QDir.homePath())):
            os.mkdir("{}/TDM".format(QDir.homePath()))

        self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)
        self.devices = QSettings("{}/TDM/devices.cfg".format(QDir.homePath()), QSettings.IniFormat)
        self.setMinimumSize(QSize(1000, 600))

        # configure logging
        logging.basicConfig(filename="{}/TDM/tdm.log".format(QDir.homePath()),
                            level=self.settings.value("loglevel", "INFO"),
                            datefmt="%Y-%m-%d %H:%M:%S",
                            format='%(asctime)s [%(levelname)s] %(message)s')
        logging.info("### TDM START ###")

        # load devices from the devices file, create TasmotaDevices and add the to the envvironment
        for mac in self.devices.childGroups():
            self.devices.beginGroup(mac)
            device = TasmotaDevice(self.devices.value("topic"), self.devices.value("full_topic"), self.devices.value("device_name"))
            device.debug = self.devices.value("debug", False, bool)
            device.p['Mac'] = mac.replace("-", ":")
            device.env = self.env
            self.env.devices.append(device)

            # load device command history
            self.devices.beginGroup("history")
            for k in self.devices.childKeys():
                device.history.append(self.devices.value(k))
            self.devices.endGroup()
            
            self.devices.endGroup()

        self.device_model = TasmotaDevicesModel(self.env)

        self.setup_mqtt()
        self.setup_main_layout()
        self.add_devices_tab()
        self.build_mainmenu()
        # self.build_toolbars()
        self.setStatusBar(QStatusBar())

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

        self.tele_docks = {}
        self.consoles = []

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
        self.devices_list.openTelemetry.connect(self.openTelemetry)
        self.devices_list.openWebUI.connect(self.openWebUI)

    def load_window_state(self):
        wndGeometry = self.settings.value('window_geometry')
        if wndGeometry:
            self.restoreGeometry(wndGeometry)

    def build_mainmenu(self):
        mMQTT  = self.menuBar().addMenu("MQTT")
        self.actToggleConnect = QAction(QIcon(":/disconnect.png"), "Connect")
        self.actToggleConnect.setCheckable(True)
        self.actToggleConnect.toggled.connect(self.toggle_connect)
        mMQTT.addAction(self.actToggleConnect)

        mMQTT.addAction(QIcon(), "Broker", self.setup_broker)
        mMQTT.addAction(QIcon(), "Autodiscovery patterns", self.patterns)

        mMQTT.addSeparator()
        mMQTT.addAction(QIcon(), "Clear obsolete retained LWTs", self.clear_LWT)

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

        # mExport = self.menuBar().addMenu("Export")
        # mExport.addAction(QIcon(), "OpenHAB", self.openhab)

    def build_toolbars(self):
        main_toolbar = Toolbar(orientation=Qt.Horizontal, iconsize=24, label_position=Qt.ToolButtonTextBesideIcon)
        main_toolbar.setObjectName("main_toolbar")

    def initial_query(self, device, queued=False):
        for c in initial_commands():
            cmd, payload = c
            cmd = device.cmnd_topic(cmd)

            if queued:
                self.mqtt_queue.append([cmd, payload])
            else:
                self.mqtt.publish(cmd, payload, 1)

    def setup_broker(self):
        brokers_dlg = BrokerDialog()
        if brokers_dlg.exec_() == QDialog.Accepted and self.mqtt.state == self.mqtt.Connected:
            self.mqtt.disconnect()

    def toggle_autoupdate(self, state):
        if state == True:
            if self.mqtt.state == self.mqtt.Connected:
                for d in self.env.devices:
                    self.mqtt.publish(d.cmnd_topic('STATUS'), payload=8)
            self.auto_timer.setInterval(self.settings.value("autotelemetry", 5000, int))
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
                self.mqtt.publish(d.cmnd_topic('STATUS'), payload=8)

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
        self.actToggleConnect.setIcon(QIcon(":/connect.png"))
        self.actToggleConnect.setText("Disconnect")
        self.statusBar().showMessage("Connected to {}:{} as {}".format(self.broker_hostname, self.broker_port, self.broker_username if self.broker_username else '[anonymous]'))

        self.mqtt_subscribe()

    def mqtt_subscribe(self):
        # clear old topics
        self.topics.clear()
        custom_patterns.clear()

        # load custom autodiscovery patterns
        self.settings.beginGroup("Patterns")
        for k in self.settings.childKeys():
            custom_patterns.append(self.settings.value(k))
        self.settings.endGroup()

        # expand fulltopic patterns to subscribable topics
        for pat in default_patterns:    # tasmota default and SO19
            self.topics += expand_fulltopic(pat)

        # check if custom patterns can be matched by default patterns
        for pat in custom_patterns:
            if pat.startswith("%prefix%") or pat.split('/')[1] == "%prefix%":
                continue  # do nothing, default subcriptions will match this topic
            else:
                self.topics += expand_fulltopic(pat)

        for d in self.env.devices:
            # if device has a non-standard pattern, check if the pattern is found in the custom patterns
            if not d.is_default() and d.p['FullTopic'] not in custom_patterns:
                # if pattern is not found then add the device topics to subscription list.
                # if the pattern is found, it will be matched without implicit subscription
                self.topics += expand_fulltopic(d.p['FullTopic'])

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
        self.statusBar().showMessage("Connection error: {}".format(reason[rc]))
        self.actToggleConnect.setChecked(False)

    def mqtt_message(self, topic, msg):
        # try to find a device by matching known FullTopics against the MQTT topic of the message
        device = self.env.find_device(topic)
        if device:
            if topic.endswith("LWT"):
                if not msg:
                    msg = "Offline"
                device.update_property("LWT", msg)

                if msg == 'Online':
                    # known device came online, query initial state
                    self.initial_query(device, True)

            else:
                # forward the message for processing
                device.parse_message(topic, msg)
                if device.debug:
                    logging.debug("MQTT: %s %s", topic, msg)

        else:            # unknown device, start autodiscovery process
            if topic.endswith("LWT"):
                self.env.lwts.append(topic)
                logging.info("DISCOVERY: LWT from an unknown device %s", topic)

                # STAGE 1
                # load default and user-provided FullTopic patterns and for all the patterns,
                # try matching the LWT topic (it follows the device's FullTopic syntax

                for p in default_patterns + custom_patterns:
                    match = re.fullmatch(p.replace("%topic%", "(?P<topic>.*?)").replace("%prefix%", "(?P<prefix>.*?)") + ".*$", topic)
                    if match:
                        # assume that the matched topic is the one configured in device settings
                        possible_topic = match.groupdict().get('topic')
                        if possible_topic not in ('tele', 'stat'):
                            # if the assumed topic is different from tele or stat, there is a chance that it's a valid topic
                            # query the assumed device for its FullTopic. False positives won't reply.
                            possible_topic_cmnd = p.replace("%prefix%", "cmnd").replace("%topic%", possible_topic) + "FullTopic"
                            logging.debug("DISCOVERY: Asking an unknown device for FullTopic at %s", possible_topic_cmnd)
                            self.mqtt_queue.append([possible_topic_cmnd, ""])

            elif topic.endswith("RESULT") or topic.endswith("FULLTOPIC"):      # reply from an unknown device
                # STAGE 2
                full_topic = loads(msg).get('FullTopic')
                if full_topic:
                    # the device replies with its FullTopic
                    # here the Topic is extracted using the returned FullTopic, identifying the device
                    parsed = parse_topic(full_topic, topic)
                    if parsed:
                        # got a match, we query the device's MAC address in case it's a known device that had its topic changed
                        logging.debug("DISCOVERY: topic %s is matched by fulltopic %s", topic, full_topic)

                        d = self.env.find_device(topic=parsed['topic'])
                        if d:
                            d.update_property("FullTopic", full_topic)
                        else:
                            logging.info("DISCOVERY: Discovered topic=%s with fulltopic=%s", parsed['topic'], full_topic)
                            d = TasmotaDevice(parsed['topic'], full_topic)
                            self.env.devices.append(d)
                            self.device_model.addDevice(d)
                            logging.debug("DISCOVERY: Sending initial query to topic %s", parsed['topic'])
                            self.initial_query(d, True)
                            tele_topic = d.tele_topic("LWT")
                            if tele_topic in self.env.lwts:
                                self.env.lwts.remove(tele_topic)
                        d.update_property("LWT", "Online")

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

    # def openhab(self):
    #     OpenHABDialog(self.env).exec_()

    def showSubs(self):
        QMessageBox.information(self, "Subscriptions", "\n".join(sorted(self.topics)))

    def clear_LWT(self):
        dlg = ClearLWTDialog(self.env)
        if dlg.exec_() == ClearLWTDialog.Accepted:
            for row in range(dlg.lw.count()):
                itm = dlg.lw.item(row)
                if itm.checkState() == Qt.Checked:
                    topic = itm.text()
                    self.mqtt.publish(topic, retain=True)
                    self.env.lwts.remove(topic)
                    logging.info("MQTT: Cleared %s", topic)

    def prefs(self):
        dlg = PrefsDialog()
        if dlg.exec_() == QDialog.Accepted:
            update_devices = False

            devices_short_version = self.settings.value("devices_short_version", True, bool)
            if devices_short_version != dlg.cbDevShortVersion.isChecked():
                update_devices = True
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

        self.settings.sync()

    def auto_telemetry_period(self):
        curr_val = self.settings.value("autotelemetry", 5000, int)
        period, ok = QInputDialog.getInt(self, "Set AutoTelemetry period", "Values under 5000ms may cause increased ESP LoadAvg", curr_val, 1000)
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
            self.mqtt_publish(self.device.cmnd_topic('STATUS'), "8")

    @pyqtSlot()
    def openConsole(self):
        if self.device:
            console_widget = ConsoleWidget(self.device)
            self.mqtt.messageSignal.connect(console_widget.consoleAppend)
            console_widget.sendCommand.connect(self.mqtt.publish)
            self.addDockWidget(Qt.BottomDockWidgetArea, console_widget)
            console_widget.command.setFocus()
            self.consoles.append(console_widget)

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
        if self.device and self.device.p.get('IPAddress'):
            url = QUrl("http://{}".format(self.device.p['IPAddress']))

            try:
                webui = QWebEngineView()
                webui.load(url)

                frm_webui = QFrame()
                frm_webui.setWindowTitle("WebUI [{}]".format(self.device.p['FriendlyName1']))
                frm_webui.setFrameShape(QFrame.StyledPanel)
                frm_webui.setLayout(VLayout(0))
                frm_webui.layout().addWidget(webui)
                frm_webui.destroyed.connect(self.updateMDI)

                self.mdi.addSubWindow(frm_webui)
                self.mdi.setViewMode(QMdiArea.TabbedView)
                frm_webui.setWindowState(Qt.WindowMaximized)

            except NameError:
                QDesktopServices.openUrl(QUrl("http://{}".format(self.device.p['IPAddress'])))

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

        for d in self.env.devices:
            mac = d.p.get('Mac')
            topic = d.p['Topic']
            full_topic = d.p['FullTopic']
            device_name = d.name

            if mac:
                self.devices.beginGroup(mac.replace(":", "-"))
                self.devices.setValue("topic", topic)
                self.devices.setValue("full_topic", full_topic)
                self.devices.setValue("device_name", device_name)

                for i, h in enumerate(d.history):
                    self.devices.setValue("history/{}".format(i), h)
                self.devices.endGroup()
        self.devices.sync()

        e.accept()


def start():
    app = QApplication(sys.argv)
    app.setOrganizationName("Tasmota")
    app.setApplicationName("TDM")
    app.lastWindowClosed.connect(app.quit)
    app.setStyle("Fusion")

    MW = MainWindow()
    MW.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    try:
        start()
    except Exception as e:
        logging.exception("EXCEPTION: %s", e)
        print("TDM has crashed. Sorry for that. Check tdm.log for more information.")
