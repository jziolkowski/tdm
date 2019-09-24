from json import dumps

from PyQt5.QtCore import Qt, QSettings, QSortFilterProxyModel, QUrl, QDir, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWidgets import QWidget, QMessageBox, QMenu, QApplication, QInputDialog, QFileDialog, \
    QAction, QActionGroup, QLabel, QSizePolicy, QLineEdit, QHeaderView, QToolButton, QPushButton, QColorDialog

from GUI import VLayout, Toolbar, TableView, PWMSlider
from GUI.GPIO import GPIODialog
from GUI.Modules import ModuleDialog
from GUI.SetOptions import SetOptionsDialog
from GUI.Templates import TemplateDialog
from GUI.Timers import TimersDialog

from Util import TasmotaDevice, resets
from Util.models import DeviceDelegate


class ListWidget(QWidget):
    deviceSelected = pyqtSignal(TasmotaDevice)
    openRulesEditor = pyqtSignal()
    openConsole = pyqtSignal()
    openTelemetry = pyqtSignal()
    openWebUI = pyqtSignal()

    def __init__(self, parent, *args, **kwargs):
        super(ListWidget, self).__init__(*args, **kwargs)
        self.setWindowTitle("Devices list")
        self.setWindowState(Qt.WindowMaximized)
        self.setLayout(VLayout(margin=0, spacing=0))

        self.mqtt = parent.mqtt
        self.env = parent.env

        self.device = None
        self.idx = None

        self.nam = QNetworkAccessManager()
        self.backup = bytes()

        self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)

        base_view = ["FriendlyName"]
        self.views = {
            "Home":  base_view + ["Module", "Power", "Color", "LoadAvg", "LinkCount", "Uptime"],
            "Health": base_view + ["Uptime", "BootCount", "RestartReason", "LoadAvg", "Sleep", "MqttCount", "LinkCount", "Downtime", "RSSI"],
            "Firmware": base_view + ["Version", "Core", "SDK",  "ProgramSize", "Free", "OtaUrl"],
            "Wifi":     base_view + ["Hostname", "Mac", "IPAddress", "Gateway", "SSId", "BSSId", "Channel", "RSSI", "LinkCount", "Downtime"],
            "MQTT":     base_view + ["Topic", "FullTopic", "CommandTopic", "StatTopic", "TeleTopic", "FallbackTopic", "GroupTopic"],
        }

        self.tb = Toolbar(Qt.Horizontal, 24, Qt.ToolButtonTextBesideIcon)
        self.tb_relays = Toolbar(Qt.Horizontal, 24, Qt.ToolButtonIconOnly)
        # self.tb_filter = Toolbar(Qt.Horizontal, 24, Qt.ToolButtonTextBesideIcon)
        self.tb_views = Toolbar(Qt.Horizontal, 24, Qt.ToolButtonTextBesideIcon)

        self.pwm_sliders = []

        self.layout().addWidget(self.tb)
        self.layout().addWidget(self.tb_relays)
        # self.layout().addWidget(self.tb_filter)

        self.device_list = TableView()
        self.device_list.setIconSize(QSize(24, 24))
        self.model = parent.device_model
        self.model.setupColumns(self.views["Home"])

        self.sorted_device_model = QSortFilterProxyModel()
        self.sorted_device_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.sorted_device_model.setSourceModel(parent.device_model)
        self.sorted_device_model.setFilterKeyColumn(-1)

        self.device_list.setModel(self.sorted_device_model)
        self.device_list.setupView(self.views["Home"])
        self.device_list.setSortingEnabled(True)
        self.device_list.setWordWrap(True)
        self.device_list.setItemDelegate(DeviceDelegate())
        self.device_list.sortByColumn(self.model.columnIndex("FriendlyName"), Qt.AscendingOrder)
        self.device_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.device_list.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.layout().addWidget(self.device_list)

        self.layout().addWidget(self.tb_views)

        self.device_list.clicked.connect(self.select_device)
        self.device_list.customContextMenuRequested.connect(self.show_list_ctx_menu)

        self.ctx_menu = QMenu()
        self.ctx_menu_relays = None

        self.create_actions()
        self.create_view_buttons()
        # self.create_view_filter()

        self.device_list.doubleClicked.connect(lambda: self.openConsole.emit())

    def create_actions(self):
        self.ctx_menu_cfg = QMenu("Configure")
        self.ctx_menu_cfg.setIcon(QIcon("GUI/icons/settings.png"))
        self.ctx_menu_cfg.addAction("Module", self.configureModule)
        self.ctx_menu_cfg.addAction("GPIO", self.configureGPIO)
        self.ctx_menu_cfg.addAction("Template", self.configureTemplate)
        # self.ctx_menu_cfg.addAction("Wifi", self.ctx_menu_teleperiod)
        # self.ctx_menu_cfg.addAction("Time", self.cfgTime.emit)
        # self.ctx_menu_cfg.addAction("MQTT", self.ctx_menu_teleperiod)
        # self.ctx_menu_cfg.addAction("Firmware and OTA", self.ctx_menu_teleperiod)
        # self.ctx_menu_cfg.addAction("Relays", self.ctx_menu_teleperiod)
        # self.ctx_menu_cfg.addAction("Colors and PWM", self.ctx_menu_teleperiod)
        # self.ctx_menu_cfg.addAction("Buttons and switches", self.ctx_menu_teleperiod)
        self.ctx_menu_cfg.addAction("Timers", self.configureTimers)
        # self.ctx_menu_cfg.addAction("Logging", self.ctx_menu_teleperiod)

        self.ctx_menu.addMenu(self.ctx_menu_cfg)
        self.ctx_menu.addSeparator()

        self.ctx_menu.addAction(QIcon("GUI/icons/refresh.png"), "Refresh", self.ctx_menu_refresh)

        self.ctx_menu.addSeparator()
        self.ctx_menu.addAction(QIcon("GUI/icons/clear.png"), "Clear retained", self.ctx_menu_clear_retained)
        self.ctx_menu.addAction("Clear Backlog", self.ctx_menu_clear_backlog)
        self.ctx_menu.addSeparator()
        self.ctx_menu.addAction(QIcon("GUI/icons/copy.png"), "Copy", self.ctx_menu_copy)
        self.ctx_menu.addSeparator()
        self.ctx_menu.addAction(QIcon("GUI/icons/restart.png"), "Restart", self.ctx_menu_restart)
        self.ctx_menu.addAction(QIcon(), "Reset", self.ctx_menu_reset)
        self.ctx_menu.addSeparator()
        self.ctx_menu.addAction(QIcon("GUI/icons/delete.png"), "Delete", self.ctx_menu_delete_device)

        ##### Toolbar
        # add = self.tb.addAction(QIcon("GUI/icons/add.png"), "Add...", self.add_device)
        # add.setShortcut("Ctrl+N")
        #
        # self.tb.addSeparator()
        console = self.tb.addAction(QIcon("GUI/icons/console.png"), "Console", self.openConsole.emit)
        console.setShortcut("Ctrl+E")

        rules = self.tb.addAction(QIcon("GUI/icons/rules.png"), "Rules", self.openRulesEditor.emit)
        rules.setShortcut("Ctrl+R")

        telemetry = self.tb.addAction(QIcon("GUI/icons/telemetry.png"), "Telemetry", self.openTelemetry.emit)
        telemetry.setShortcut("Ctrl+T")

        webui = self.tb.addAction(QIcon("GUI/icons/web.png"), "WebUI", self.openWebUI.emit)
        webui.setShortcut("Ctrl+U")

        # setopts = self.tb.addAction(QIcon("GUI/icons/setoptions.png"), "SetOptions", self.configureSO)
        # setopts.setShortcut("Ctrl+S")

        # self.tb.addAction(QIcon(), "Multi Command", self.ctx_menu_webui)

        self.tb_relays.addWidget(QLabel("Power:"))

        self.agAllPower = QActionGroup(self)
        self.agAllPower.addAction(QIcon("GUI/icons/P_ON.png"), "All ON")
        self.agAllPower.addAction(QIcon("GUI/icons/P_OFF.png"), "All OFF")
        self.agAllPower.setEnabled(False)
        self.agAllPower.setExclusive(False)
        self.agAllPower.triggered.connect(self.toggle_power_all)
        self.tb_relays.addActions(self.agAllPower.actions())

        self.agRelays = QActionGroup(self)
        self.agRelays.setVisible(False)
        self.agRelays.setExclusive(False)

        for a in range(1, 9):
            act = QAction(QIcon("GUI/icons/P{}_OFF.png".format(a)), "")
            act.setShortcut("F{}".format(a))
            self.agRelays.addAction(act)

        self.agRelays.triggered.connect(self.toggle_power)
        self.tb_relays.addActions(self.agRelays.actions())

        self.actColor = self.tb_relays.addAction(QIcon("GUI/icons/color.png"), "Color", self.set_color)
        self.actColor.setEnabled(False)


        # for pwm in range(5):
        #     s = PWMSlider()
        #     s.setEnabled(False)
        #     s.sliderReleased.connect(self.setPWM)
        #     self.pwm_sliders.append(s)
        #     self.tb_relays.addWidget(s)

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

        stretch = QWidget()
        stretch.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.tb_views.addWidget(stretch)
        # actEditView = self.tb_views.addAction("Edit views...")

    # def create_view_filter(self):
    #     # self.tb_filter.addWidget(QLabel("Show devices: "))
    #     # self.cbxLWT = QComboBox()
    #     # self.cbxLWT.addItems(["All", "Online"d, "Offline"])
    #     # self.cbxLWT.currentTextChanged.connect(self.build_filter_regex)
    #     # self.tb_filter.addWidget(self.cbxLWT)
    #
    #     self.tb_filter.addWidget(QLabel(" Search: "))
    #     self.leSearch = QLineEdit()
    #     self.leSearch.setClearButtonEnabled(True)
    #     self.leSearch.textChanged.connect(self.build_filter_regex)
    #     self.tb_filter.addWidget(self.leSearch)
    #
    # def build_filter_regex(self, txt):
    #     query = self.leSearch.text()
    #     # if self.cbxLWT.currentText() != "All":
    #     #     query = "{}|{}".format(self.cbxLWT.currentText(), query)
    #     self.sorted_device_model.setFilterRegExp(query)

    def change_view(self, a=None):
        view = self.views[self.sender().text()]
        self.model.setupColumns(view)
        self.device_list.setupView(view)

    def ctx_menu_copy(self):
        if self.idx:
            QApplication.clipboard().setText(dumps(self.model.data(self.idx)))

    def ctx_menu_clear_retained(self):
        if self.device:
            relays = self.device.power()
            if relays and len(relays.keys()) > 0:
                for r in relays.keys():
                    self.mqtt.publish(self.device.cmnd_topic(r), retain=True)
                QMessageBox.information(self, "Clear retained", "Cleared retained messages.")

    def ctx_menu_clear_backlog(self):
        if self.device:
            self.mqtt.publish(self.device.cmnd_topic("backlog"), "")
            QMessageBox.information(self, "Clear Backlog", "Backlog cleared.")

    def ctx_menu_restart(self):
        if self.device:
            self.mqtt.publish(self.device.cmnd_topic("restart"), payload="1")
            for k in list(self.device.power().keys()):
                self.device.p.pop(k)

    def ctx_menu_reset(self):
        if self.device:
            reset, ok = QInputDialog.getItem(self, "Reset device and restart", "Select reset mode", resets, editable=False)
            if ok:
                self.mqtt.publish(self.device.cmnd_topic("reset"), payload=reset.split(":")[0])
                for k in list(self.device.power().keys()):
                    self.device.p.pop(k)

    def ctx_menu_refresh(self):
        if self.device:
            for k in list(self.device.power().keys()):
                self.device.p.pop(k)
            status = self.device.cmnd_topic("status")
            tpl = self.device.cmnd_topic("template")
            modules = self.device.cmnd_topic("modules")

            self.mqtt.publish(status, "0")
            self.mqtt.publish(tpl)
            self.mqtt.publish(modules)

    def ctx_menu_delete_device(self):
        if self.device:
            if QMessageBox.question(self, "Confirm", "Do you want to remove the following device?\n'{}' ({})"
                    .format(self.device.p['FriendlyName1'], self.device.p['Topic'])) == QMessageBox.Yes:
                self.model.deleteDevice(self.idx)

    def ctx_menu_teleperiod(self):
        if self.device:
            teleperiod, ok = QInputDialog.getInt(self, "Set telemetry period", "Input 1 to reset to default\n[Min: 10, Max: 3600]", self.device.p['TelePeriod'], 1, 3600)
            if ok:
                if teleperiod != 1 and teleperiod < 10:
                    teleperiod = 10
            self.mqtt.publish(self.device.cmnd_topic("teleperiod"), teleperiod)

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
        self.idx = self.sorted_device_model.mapToSource(idx)
        self.device = self.model.deviceAtRow(self.idx.row())
        self.deviceSelected.emit(self.device)

        relays = self.device.power()

        self.agAllPower.setEnabled(len(relays) >= 1)

        for i, a in enumerate(self.agRelays.actions()):
            a.setVisible(len(relays) > 1 and i < len(relays))

        color = self.device.color().get("Color", False)
        self.actColor.setEnabled(bool(color) and not self.device.setoption(68))

        # for i, pwm in enumerate(self.pwm_sliders):
        #     print(self.device.color().get("Color", False) and i < len(list(self.device.pwm().keys())))
        #     pwm.setVisible(self.device.color().get("Color", False) and i < len(list(self.device.pwm().keys())))
        #
        #     if self.device.setoption(15):
        #         k = self.device.pwm().get("Channel{}".format(i+1))  # Get value for Channel (SO15=1)
        #         if k:
        #             pwm.setMaximum(100)
        #             pwm.setValue(k)
        #     else:
        #         k = self.device.pwm().get("Pwm{}".format(i + 1))    # If no Channel, try value for PWM1 (SO15=0)
        #         if k:
        #             pwm.setMaximum(1023)
        #             pwm.setValue(k)

    def toggle_power(self, action):
        if self.device:
            idx = self.agRelays.actions().index(action)
            relay = list(self.device.power().keys())[idx]
            self.mqtt.publish(self.device.cmnd_topic(relay), "toggle")

    def toggle_power_all(self, action):
        if self.device:
            idx = self.agAllPower.actions().index(action)
            for r in self.device.power().keys():
                self.mqtt.publish(self.device.cmnd_topic(r), str(not bool(idx)))

    def set_color(self):
        if self.device:
            color = self.device.color().get("Color")
            if color:
                dlg = QColorDialog()
                new_color = dlg.getColor(QColor("#{}".format(color)))
                if new_color.isValid():
                    new_color = new_color.name()
                    if new_color != color:
                        self.mqtt.publish(self.device.cmnd_topic("color"), new_color)

    def setPWM(self):
        if self.device:
            idx = self.pwm_sliders.index(self.sender())
            pwm = self.pwm_sliders[idx]
            self.mqtt.publish(self.device.cmnd_topic("Channel{}".format(idx+1)), str(pwm.value()))

    def configureSO(self):
        if self.device:
            dlg = SetOptionsDialog(self.device)
            dlg.sendCommand.connect(self.mqtt.publish)
            dlg.exec_()

    def configureModule(self):
        if self.device:
            dlg = ModuleDialog(self.device)
            dlg.sendCommand.connect(self.mqtt.publish)
            dlg.exec_()

    def configureGPIO(self):
        if self.device:
            dlg = GPIODialog(self.device)
            dlg.sendCommand.connect(self.mqtt.publish)
            dlg.exec_()

    def configureTemplate(self):
        if self.device:
            dlg = TemplateDialog(self.device)
            dlg.sendCommand.connect(self.mqtt.publish)
            dlg.exec_()

    def configureTimers(self):
        if self.device:
            timers = TimersDialog(self.device)
            self.mqtt.messageSignal.connect(timers.parseMessage)
            timers.sendCommand.connect(self.mqtt.publish)
            timers.exec_()

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

    def check_fulltopic(self, fulltopic):
        fulltopic += "/" if not fulltopic.endswith('/') else ''
        return "%prefix%" in fulltopic and "%topic%" in fulltopic

    def closeEvent(self, event):
        event.ignore()
