from PyQt5.QtCore import Qt, QSettings, QSortFilterProxyModel, QUrl, QDir, QSize, QObject, pyqtSignal, QModelIndex
from PyQt5.QtGui import QIcon, QDesktopServices, QKeySequence
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWidgets import QWidget, QMessageBox, QDialog, QMenu, QApplication, QToolButton, QInputDialog, QFileDialog, \
    QAction, QActionGroup, QLabel, QShortcut

from GUI import VLayout, Toolbar, TableView
from GUI.DeviceConfig import DevicesConfigWidget
from GUI.DeviceEdit import DeviceEditDialog
from Util import TasmotaDevice
from Util.models import DeviceDelegate
from Util.nodes import TelemetryDevice


class DevicesListWidget(QWidget):

    deviceSelected = pyqtSignal(TasmotaDevice)

    def __init__(self, parent, *args, **kwargs):
        super(DevicesListWidget, self).__init__(*args, **kwargs)
        self.setWindowTitle("Devices list")
        self.setWindowState(Qt.WindowMaximized)
        self.setLayout(VLayout(margin=0, spacing=0))

        self.mqtt = parent.mqtt
        self.mdi = parent.mdi

        self.device = None

        self.nam = QNetworkAccessManager()
        self.backup = bytes()

        self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)

        base_view = ["LWT", "FriendlyName"]
        self.views = {
            "Home":  base_view + ["Module", "RSSI", "Power", "LoadAvg", "LinkCount", "Uptime"],
            "Health": base_view + ["BootCount", "RestartReason", "LoadAvg", "Sleep", "LinkCount", "RSSI"],
            "Firmware": base_view + ["Version", "Core", "SDK",  "ProgramSize", "Free", "OtaUrl"],
            "Wifi":     base_view + ["Hostname", "Mac", "IPAddress", "Gateway", "SSId", "BSSId", "Channel", "RSSI", "LinkCount", "Downtime"],
            "MQTT":     base_view + ["Topic", "FullTopic", "GroupTopic"],
        }

        self.tb = Toolbar(Qt.Horizontal, 16, Qt.ToolButtonTextBesideIcon)
        self.tb_views = Toolbar(Qt.Horizontal, 16, Qt.ToolButtonTextBesideIcon)

        self.layout().addWidget(self.tb)

        self.device_list = TableView()
        self.model = parent.device_model
        self.model.setupColumns(self.views["Home"])
        self.sorted_device_model = QSortFilterProxyModel()
        self.sorted_device_model.setSourceModel(parent.device_model)
        self.device_list.setModel(self.sorted_device_model)
        self.device_list.setupView(self.views["Home"])
        self.device_list.setSortingEnabled(True)
        self.device_list.setWordWrap(True)
        self.device_list.setItemDelegate(DeviceDelegate())
        self.device_list.sortByColumn(self.model.columnIndex("FriendlyName"), Qt.AscendingOrder)
        self.device_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.layout().addWidget(self.device_list)

        self.layout().addWidget(self.tb_views)

        self.device_list.clicked.connect(self.select_device)
        self.device_list.customContextMenuRequested.connect(self.show_list_ctx_menu)

        self.ctx_menu = QMenu()
        self.ctx_menu_relays = None

        self.actTelemetry = QAction(QIcon(""), "Telemetry")
        self.actTelemetry.triggered.connect(parent.openTelemetry)

        self.actConsole = QAction(QIcon(""), "Console")
        self.actConsole.triggered.connect(parent.openConsole)

        self.create_actions()
        self.create_view_buttons()

        self.device_list.doubleClicked.connect(self.actConsole.trigger)

    def create_actions(self):
        self.ctx_menu_cfg = QMenu("Configure")
        self.ctx_menu_cfg.setIcon(QIcon("GUI/icons/configure.png"))
        self.ctx_menu_cfg.addAction(QIcon(), "Module and GPIO", self.ctx_menu_teleperiod)
        self.ctx_menu_cfg.addAction(QIcon(), "Wifi", self.ctx_menu_teleperiod)
        self.ctx_menu_cfg.addAction(QIcon(), "Time", self.ctx_menu_teleperiod)
        self.ctx_menu_cfg.addAction(QIcon(), "MQTT", self.ctx_menu_teleperiod)
        self.ctx_menu_cfg.addAction(QIcon(), "Firmware and OTA", self.ctx_menu_teleperiod)
        self.ctx_menu_cfg.addAction(QIcon(), "Relays", self.ctx_menu_teleperiod)
        self.ctx_menu_cfg.addAction(QIcon(), "Colors and PWM", self.ctx_menu_teleperiod)
        self.ctx_menu_cfg.addAction(QIcon(), "Buttons and switches", self.ctx_menu_teleperiod)
        self.ctx_menu_cfg.addAction(QIcon(), "Rules", self.ctx_menu_teleperiod)
        self.ctx_menu_cfg.addAction(QIcon(), "Timers", self.ctx_menu_teleperiod)
        self.ctx_menu_cfg.addAction(QIcon(), "Logging", self.ctx_menu_teleperiod)

        # cfg_btn = self.ctx_menu.addMenu(self.ctx_menu_cfg)

        self.ctx_menu.addSeparator()
        # self.ctx_menu.addAction(self.actTelemetry)
        self.ctx_menu.addAction(self.actConsole)
        self.ctx_menu.addSeparator()
        self.ctx_menu.addAction(QIcon("GUI/icons/refresh.png"), "Refresh", self.ctx_menu_refresh)

        self.ctx_menu.addSeparator()
        self.ctx_menu.addAction(QIcon("GUI/icons/on.png"), "Power ON", lambda: self.ctx_menu_power(state="ON"))
        self.ctx_menu.addAction(QIcon("GUI/icons/off.png"), "Power OFF", lambda: self.ctx_menu_power(state="OFF"))

        self.ctx_menu_relays = QMenu("Relays")
        self.ctx_menu_relays.setIcon(QIcon("GUI/icons/switch.png"))
        relays_btn = self.ctx_menu.addMenu(self.ctx_menu_relays)

        self.ctx_menu_relays.setEnabled(False)
        self.ctx_menu.addSeparator()
        self.ctx_menu.addAction(QIcon("GUI/icons/clear.png"), "Clear retained", self.ctx_menu_clean_retained)
        self.ctx_menu.addSeparator()

        self.ctx_menu_copy = QMenu("Copy")
        self.ctx_menu_copy.setIcon(QIcon("GUI/icons/copy.png"))
        copy_btn = self.ctx_menu.addMenu(self.ctx_menu_copy)

        self.ctx_menu.addSeparator()
        self.ctx_menu.addAction(QIcon("GUI/icons/restart.png"), "Restart", self.ctx_menu_restart)
        self.ctx_menu.addAction(QIcon("GUI/icons/web.png"), "Open WebUI", self.ctx_menu_webui)
        self.ctx_menu.addSeparator()

        self.ctx_menu_ota = QMenu("OTA")
        self.ctx_menu_ota.setIcon(QIcon("GUI/icons/ota.png"))
        self.ctx_menu_ota.addAction("Set OTA URL", self.ctx_menu_ota_set_url)
        self.ctx_menu_ota.addAction("Upgrade", self.ctx_menu_ota_set_upgrade)
        ota_btn = self.ctx_menu.addMenu(self.ctx_menu_ota)

        self.ctx_menu.addAction("Config backup", self.ctx_menu_config_backup)

        # self.ctx_menu.addSeparator()
        # self.ctx_menu.addAction(QIcon("GUI/icons/delete.png"), "Remove", self.device_delete)

        self.ctx_menu_copy.addAction("IP", lambda: self.ctx_menu_copy_value("IPAddress"))
        self.ctx_menu_copy.addAction("MAC", lambda: self.ctx_menu_copy_value("Mac"))
        self.ctx_menu_copy.addAction("BSSID", lambda: self.ctx_menu_copy_value("BSSId"))
        self.ctx_menu_copy.addSeparator()
        self.ctx_menu_copy.addAction("Topic", lambda: self.ctx_menu_copy_value("Topic"))
        self.ctx_menu_copy.addAction("FullTopic", lambda: self.ctx_menu_copy_value("FullTopic"))
        self.ctx_menu_copy.addAction("STAT topic", lambda: self.ctx_menu_copy_prefix_topic("STAT"))
        self.ctx_menu_copy.addAction("CMND topic", lambda: self.ctx_menu_copy_prefix_topic("CMND"))
        self.ctx_menu_copy.addAction("TELE topic", lambda: self.ctx_menu_copy_prefix_topic("TELE"))

        self.tb.addActions(self.ctx_menu.actions())
        self.tb.widgetForAction(ota_btn).setPopupMode(QToolButton.InstantPopup)
        # self.tb.widgetForAction(cfg_btn).setPopupMode(QToolButton.InstantPopup)
        self.tb.widgetForAction(relays_btn).setPopupMode(QToolButton.InstantPopup)
        self.tb.widgetForAction(copy_btn).setPopupMode(QToolButton.InstantPopup)

        shortcuts_toggle = [QShortcut(self.device_list) for _ in range(8)]
        for i, s in enumerate(shortcuts_toggle, start=1):
            s.setKey("F{}".format(i))
            s.activated.connect(lambda i=i: self.ctx_menu_power(i, "toggle"))

    def create_view_buttons(self):
        self.tb_views.addWidget(QLabel("View mode: "))
        ag_views = QActionGroup(self)
        ag_views.setExclusive(True)
        for v in self.views.keys():
            a = QAction(v)
            a.triggered.connect(self.change_view)
            a.setCheckable(True)
            ag_views.addAction(a)
        self.tb_views.addActions(ag_views.actions())
        ag_views.actions()[0].setChecked(True)

    def change_view(self, a=None):
        view = self.views[self.sender().text()]
        self.model.setupColumns(view)
        self.device_list.setupView(view)

    def ctx_menu_copy_value(self, column):
        if self.device:
            QApplication.clipboard().setText(self.device.p.get(column))

    def ctx_menu_copy_prefix_topic(self, prefix):
        if self.device:
            if prefix == "STAT":
                topic = self.device.stat_topic()
            elif prefix == "CMND":
                topic = self.device.cmnd_topic()
            elif prefix == "TELE":
                topic = self.device.tele_topic()
            QApplication.clipboard().setText(topic)

    def ctx_menu_clean_retained(self):
        if self.device:
            relays = self.device.power()
            if relays and len(relays.keys()) > 0:
                for r in relays.keys():
                    self.mqtt.publish(self.device.cmnd_topic(r), retain=True)
                QMessageBox.information(self, "Clear retained", "Cleared retained messages.")

    def ctx_menu_power(self, relay=None, state=None):
        if self.device:
            relays = self.device.power()
            if relay:
                if relay == 1 and len(relays) == 1:
                    self.mqtt.publish(self.device.cmnd_topic("power".format(relay)), payload=state)

                elif relays.get("POWER{}".format(relay)):
                    self.mqtt.publish(self.device.cmnd_topic("power{}".format(relay)), payload=state)

            elif not relay and relays:
                for r in relays.keys():
                    self.mqtt.publish(self.device.cmnd_topic(r), payload=state)

    def ctx_menu_restart(self):
        if self.device:
            self.mqtt.publish(self.device.cmnd_topic("restart"), payload="1")

    def ctx_menu_refresh(self):
        if self.device:
            status = self.device.cmnd_topic("status")
            tpl = self.device.cmnd_topic("template")
            modules = self.device.cmnd_topic("modules")

            self.mqtt.publish(status, "0")
            self.mqtt.publish(tpl)
            self.mqtt.publish(modules)

    def ctx_menu_teleperiod(self):
        if self.device:
            teleperiod, ok = QInputDialog.getInt(self, "Set telemetry period", "Input 1 to reset to default\n[Min: 10, Max: 3600]", self.device.p['TelePeriod'], 1, 3600)
            if ok:
                if teleperiod != 1 and teleperiod < 10:
                    teleperiod = 10
            self.mqtt.publish(self.device.cmnd_topic("teleperiod"), teleperiod)

    def ctx_menu_webui(self):
        if self.device:
            QDesktopServices.openUrl(QUrl("http://{}".format(self.device.p['IPAddress'])))

    def ctx_menu_config_backup(self):
        if self.device:
            self.backup = bytes()
            self.dl = self.nam.get(QNetworkRequest(QUrl("http://{}/dl".format(self.device.p['IPAddress']))))
            self.dl.readyRead.connect(self.get_dump)
            self.dl.finished.connect(self.save_dump)

    def ctx_menu_ota_set_url(self):
        if self.device:
            url, ok = QInputDialog.getText(self, "Set OTA URL", '100 chars max. Set to "1" to reset to default.', text=self.device.p['OtaUrl'])
            if ok:
                self.mqtt.publish(self.device.cmnd_topic("otaurl"), payload=url)

    def ctx_menu_ota_set_upgrade(self):
        if self.device:
            if QMessageBox.question(self, "OTA Upgrade", "Are you sure to OTA upgrade from\n{}".format(self.device.p['OtaUrl']), QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                self.mqtt.publish(self.device.cmnd_topic("upgrade"), payload="1")

    def show_list_ctx_menu(self, at):
        self.select_device(self.device_list.indexAt(at))
        self.ctx_menu.popup(self.device_list.viewport().mapToGlobal(at))

    def select_device(self, idx):
        self.device = self.model.deviceAtRow(self.sorted_device_model.mapToSource(idx).row())
        self.deviceSelected.emit(self.device)

        relays = self.device.power()
        if relays and len(relays.keys()) > 1:
            self.ctx_menu_relays.setEnabled(True)
            self.ctx_menu_relays.clear()

            for i, r in enumerate(relays.keys()):
                actR = self.ctx_menu_relays.addAction("{} ON".format(r))
                actR.triggered.connect(lambda st, x=r: self.ctx_menu_power(x, "ON"))

                actR = self.ctx_menu_relays.addAction("{} OFF".format(r))
                actR.triggered.connect(lambda st, x=r: self.ctx_menu_power(x, "OFF"))
                self.ctx_menu_relays.addSeparator()
        else:
            self.ctx_menu_relays.setEnabled(False)
            self.ctx_menu_relays.clear()

    def device_config(self, idx=None):
        if self.idx:
            dev_cfg = DevicesConfigWidget(self.model.topic(self.idx))
            sw = self.mdi.addSubWindow(dev_cfg)
            dev_cfg.setWindowState(Qt.WindowMaximized)

    def device_add(self):
        rc = self.model.rowCount()
        self.model.insertRow(rc)
        dlg = DeviceEditDialog(self.model, rc)
        dlg.full_topic.setText("%prefix%/%topic%/")

        if dlg.exec_() == QDialog.Accepted:
            self.model.setData(self.model.index(rc, DevMdl.FRIENDLY_NAME), self.model.data(self.model.index(rc, DevMdl.TOPIC)))
            topic = dlg.topic.text()
            tele_dev = self.telemetry_model.addDevice(TasmotaDevice, topic)
            self.telemetry_model.devices[topic] = tele_dev
        else:
            self.model.removeRow(rc)

    def device_delete(self):
        if self.idx:
            topic = self.model.topic(self.idx)
            if QMessageBox.question(self, "Confirm", "Do you want to remove '{}' from devices list?".format(topic)) == QMessageBox.Yes:
                self.model.removeRows(self.idx.row(),1)

    def get_dump(self):
        self.backup += self.dl.readAll()

    def save_dump(self):
        fname = self.dl.header(QNetworkRequest.ContentDispositionHeader)
        if fname:
            fname = fname.split('=')[1]
            save_file = QFileDialog.getSaveFileName(self, "Save config backup", "{}/TDM/{}".format(QDir.homePath(), fname))[0]
            if save_file:
                with open(save_file, "wb") as f:
                    f.write(self.backup)

    def closeEvent(self, event):
        event.ignore()