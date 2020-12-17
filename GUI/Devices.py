from json import dumps

from PyQt5.QtCore import Qt, QSettings, QSortFilterProxyModel, QUrl, QDir, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWidgets import QWidget, QMessageBox, QMenu, QApplication, QInputDialog, QFileDialog, \
    QAction, QActionGroup, QLabel, QSizePolicy, QLineEdit, QHeaderView, QToolButton, QPushButton, QColorDialog, QDialog, \
    QComboBox

from GUI import VLayout, Toolbar, TableView, SliderAction, default_views, base_view, SpinBox
from GUI.Buttons import ButtonsDialog
from GUI.GPIO import GPIODialog
from GUI.Modules import ModuleDialog
from GUI.Power import PowerDialog
from GUI.SetOptions import SetOptionsDialog
from GUI.Switches import SwitchesDialog
from GUI.Templates import TemplateDialog
from GUI.Timers import TimersDialog

from Util import TasmotaDevice, resets, initial_commands
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
        views_order = self.settings.value("views_order", [])

        self.views = {}
        self.settings.beginGroup("Views")
        views = self.settings.childKeys()
        if views and views_order:
            for view in views_order.split(";"):
                view_list = self.settings.value(view).split(";")
                self.views[view] = base_view + view_list
        else:
            self.views = default_views
        self.settings.endGroup()

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
        self.sorted_device_model.setSortRole(Qt.InitialSortOrderRole)
        self.sorted_device_model.setSortLocaleAware(True)
        self.sorted_device_model.setFilterKeyColumn(-1)

        self.device_list.setModel(self.sorted_device_model)
        self.device_list.setupView(self.views["Home"])
        self.device_list.setSortingEnabled(True)
        self.device_list.setWordWrap(True)
        self.device_list.setItemDelegate(DeviceDelegate())
        self.device_list.sortByColumn(self.model.columnIndex("Device"), Qt.AscendingOrder)
        self.device_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.device_list.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.layout().addWidget(self.device_list)

        self.layout().addWidget(self.tb_views)

        self.device_list.clicked.connect(self.select_device)
        self.device_list.customContextMenuRequested.connect(self.show_list_ctx_menu)

        self.ctx_menu = QMenu()

        self.create_actions()
        self.create_view_buttons()
        # self.create_view_filter()

        self.device_list.doubleClicked.connect(lambda: self.openConsole.emit())

    def create_actions(self):
        actConsole = self.tb.addAction(QIcon(":/console.png"), "Console", self.openConsole.emit)
        actConsole.setShortcut("Ctrl+E")

        actRules = self.tb.addAction(QIcon(":/rules.png"), "Rules", self.openRulesEditor.emit)
        actRules.setShortcut("Ctrl+R")

        actTimers = self.tb.addAction(QIcon(":/timers.png"), "Timers", self.configureTimers)

        actButtons = self.tb.addAction(QIcon(":/buttons.png"), "Buttons", self.configureButtons)
        actButtons.setShortcut("Ctrl+B")

        actSwitches = self.tb.addAction(QIcon(":/switches.png"), "Switches", self.configureSwitches)
        actSwitches.setShortcut("Ctrl+S")

        actPower = self.tb.addAction(QIcon(":/power.png"), "Power", self.configurePower)
        actPower.setShortcut("Ctrl+P")

        # setopts = self.tb.addAction(QIcon(":/setoptions.png"), "SetOptions", self.configureSO)
        # setopts.setShortcut("Ctrl+S")

        self.tb.addSpacer()

        actTelemetry = self.tb.addAction(QIcon(":/telemetry.png"), "Telemetry", self.openTelemetry.emit)
        actTelemetry.setShortcut("Ctrl+T")

        actWebui = self.tb.addAction(QIcon(":/web.png"), "WebUI", self.openWebUI.emit)
        actWebui.setShortcut("Ctrl+U")

        self.ctx_menu.addActions([actRules, actTimers, actButtons, actSwitches, actPower, actTelemetry, actWebui])
        self.ctx_menu.addSeparator()

        self.ctx_menu_cfg = QMenu("Configure")
        self.ctx_menu_cfg.setIcon(QIcon(":/settings.png"))
        self.ctx_menu_cfg.addAction("Module", self.configureModule)
        self.ctx_menu_cfg.addAction("GPIO", self.configureGPIO)
        self.ctx_menu_cfg.addAction("Template", self.configureTemplate)
        # self.ctx_menu_cfg.addAction("Wifi", self.ctx_menu_teleperiod)
        # self.ctx_menu_cfg.addAction("Time", self.cfgTime.emit)
        # self.ctx_menu_cfg.addAction("MQTT", self.ctx_menu_teleperiod)

        # self.ctx_menu_cfg.addAction("Logging", self.ctx_menu_teleperiod)

        self.ctx_menu.addMenu(self.ctx_menu_cfg)
        self.ctx_menu.addSeparator()

        self.ctx_menu.addAction(QIcon(":/refresh.png"), "Refresh", self.ctx_menu_refresh)

        self.ctx_menu.addSeparator()
        self.ctx_menu.addAction(QIcon(":/clear.png"), "Clear retained", self.ctx_menu_clear_retained)
        self.ctx_menu.addAction("Clear Backlog", self.ctx_menu_clear_backlog)
        self.ctx_menu.addSeparator()
        self.ctx_menu.addAction(QIcon(":/copy.png"), "Copy", self.ctx_menu_copy)
        self.ctx_menu.addSeparator()
        self.ctx_menu.addAction(QIcon(":/restart.png"), "Restart", self.ctx_menu_restart)
        self.ctx_menu.addAction(QIcon(), "Reset", self.ctx_menu_reset)
        self.ctx_menu.addSeparator()
        self.ctx_menu.addAction(QIcon(":/delete.png"), "Delete", self.ctx_menu_delete_device)

        # self.tb.addAction(QIcon(), "Multi Command", self.ctx_menu_webui)

        self.agAllPower = QActionGroup(self)
        self.agAllPower.addAction(QIcon(":/P_ON.png"), "All ON")
        self.agAllPower.addAction(QIcon(":/P_OFF.png"), "All OFF")
        self.agAllPower.setEnabled(False)
        self.agAllPower.setExclusive(False)
        self.agAllPower.triggered.connect(self.toggle_power_all)
        self.tb_relays.addActions(self.agAllPower.actions())

        self.agRelays = QActionGroup(self)
        self.agRelays.setVisible(False)
        self.agRelays.setExclusive(False)

        for a in range(1, 9):
            act = QAction(QIcon(":/P{}_OFF.png".format(a)), "")
            act.setShortcut("F{}".format(a))
            self.agRelays.addAction(act)

        self.agRelays.triggered.connect(self.toggle_power)
        self.tb_relays.addActions(self.agRelays.actions())

        self.tb_relays.addSeparator()
        self.actColor = self.tb_relays.addAction(QIcon(":/color.png"), "Color", self.set_color)
        self.actColor.setEnabled(False)

        self.actChannels = self.tb_relays.addAction(QIcon(":/sliders.png"), "Channels")
        self.actChannels.setEnabled(False)
        self.mChannels = QMenu()
        self.actChannels.setMenu(self.mChannels)
        self.tb_relays.widgetForAction(self.actChannels).setPopupMode(QToolButton.InstantPopup)

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
            string = dumps(self.model.data(self.idx))
            if string.startswith('"') and string.endswith('"'):
                string = string[1:-1]
            QApplication.clipboard().setText(string)

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

            for c in initial_commands():
                cmd, payload = c
                cmd = self.device.cmnd_topic(cmd)
                self.mqtt.publish(cmd, payload, 1)

    def ctx_menu_delete_device(self):
        if self.device:
            if QMessageBox.question(self, "Confirm", "Do you want to remove the following device?\n'{}' ({})"
                    .format(self.device.p['DeviceName'], self.device.p['Topic'])) == QMessageBox.Yes:
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
        has_color = bool(color)
        self.actColor.setEnabled(has_color and not self.device.setoption(68))

        self.actChannels.setEnabled(has_color)

        if has_color:
            self.actChannels.menu().clear()

            max_val = 100
            if self.device.setoption(15) == 0:
                max_val = 1023

            for k, v in self.device.pwm().items():
                channel = SliderAction(self, k)
                channel.slider.setMaximum(max_val)
                channel.slider.setValue(int(v))
                self.mChannels.addAction(channel)
                channel.slider.valueChanged.connect(self.set_channel)

            dimmer = self.device.color().get("Dimmer")
            if dimmer:
                saDimmer = SliderAction(self, "Dimmer")
                saDimmer.slider.setValue(int(dimmer))
                self.mChannels.addAction(saDimmer)
                saDimmer.slider.valueChanged.connect(self.set_channel)

    def toggle_power(self, action):
        if self.device:
            idx = self.agRelays.actions().index(action)
            relay = sorted(list(self.device.power().keys()))[idx]
            self.mqtt.publish(self.device.cmnd_topic(relay), "toggle")

    def toggle_power_all(self, action):
        if self.device:
            idx = self.agAllPower.actions().index(action)
            for r in sorted(self.device.power().keys()):
                self.mqtt.publish(self.device.cmnd_topic(r), idx ^ 1)

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

    def set_channel(self, value=0):
        cmd = self.sender().objectName()

        if self.device:
            self.mqtt.publish(self.device.cmnd_topic(cmd), str(value))

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
            self.mqtt.publish(self.device.cmnd_topic("timers"))
            timers = TimersDialog(self.device)
            self.mqtt.messageSignal.connect(timers.parseMessage)
            timers.sendCommand.connect(self.mqtt.publish)
            timers.exec_()

    def configureButtons(self):
        if self.device:
            backlog = []
            buttons = ButtonsDialog(self.device)
            if buttons.exec_() == QDialog.Accepted:
                for c, cw in buttons.command_widgets.items():
                    current_value = self.device.p.get(c)
                    new_value = ""

                    if isinstance(cw.input, SpinBox):
                        new_value = cw.input.value()

                    if isinstance(cw.input, QComboBox):
                        new_value = cw.input.currentIndex()

                    if current_value != new_value:
                        backlog.append("{} {}".format(c, new_value))

                so_error = False
                for so, sow in buttons.setoption_widgets.items():
                    current_value = None
                    try:
                        current_value = self.device.setoption(so)
                    except ValueError:
                        so_error = True

                    new_value = -1

                    if isinstance(sow.input, SpinBox):
                        new_value = sow.input.value()

                    if isinstance(sow.input, QComboBox):
                        new_value = sow.input.currentIndex()

                    if not so_error and current_value and current_value != new_value:
                        backlog.append("SetOption{} {}".format(so, new_value))

                if backlog:
                    backlog.append("status 3")
                    self.mqtt.publish(self.device.cmnd_topic("backlog"), "; ".join(backlog))

    def configureSwitches(self):
        if self.device:
            backlog = []
            switches = SwitchesDialog(self.device)
            if switches.exec_() == QDialog.Accepted:
                for c, cw in switches.command_widgets.items():
                    current_value = self.device.p.get(c)
                    new_value = ""

                    if isinstance(cw.input, SpinBox):
                        new_value = cw.input.value()

                    if isinstance(cw.input, QComboBox):
                        new_value = cw.input.currentIndex()

                    if current_value != new_value:
                        backlog.append("{} {}".format(c, new_value))

                so_error = False
                for so, sow in switches.setoption_widgets.items():
                    current_value = None
                    try:
                        current_value = self.device.setoption(so)
                    except ValueError:
                        so_error = True
                    new_value = -1

                    if isinstance(sow.input, SpinBox):
                        new_value = sow.input.value()

                    if isinstance(sow.input, QComboBox):
                        new_value = sow.input.currentIndex()

                    if not so_error and current_value != new_value:
                        backlog.append("SetOption{} {}".format(so, new_value))

                for sw, sw_mode in enumerate(self.device.p['SwitchMode']):
                    new_value = switches.sm.inputs[sw].currentIndex()

                    if sw_mode != new_value:
                        backlog.append("switchmode{} {}".format(sw+1, new_value))

                if backlog:
                    backlog.append("status")
                    backlog.append("status 3")
                self.mqtt.publish(self.device.cmnd_topic("backlog"), "; ".join(backlog))

    def configurePower(self):
        if self.device:
            backlog = []
            power = PowerDialog(self.device)
            if power.exec_() == QDialog.Accepted:
                for c, cw in power.command_widgets.items():
                    current_value = self.device.p.get(c)
                    new_value = ""

                    if isinstance(cw.input, SpinBox):
                        new_value = cw.input.value()

                    if isinstance(cw.input, QComboBox):
                        new_value = cw.input.currentIndex()

                    if current_value != new_value:
                        backlog.append("{} {}".format(c, new_value))

                so_error = False
                for so, sow in power.setoption_widgets.items():
                    current_value = None
                    try:
                        current_value = self.device.setoption(so)
                    except ValueError:
                        so_error = True
                    new_value = -1


                    if isinstance(sow.input, SpinBox):
                        new_value = sow.input.value()

                    if isinstance(sow.input, QComboBox):
                        new_value = sow.input.currentIndex()

                    if not so_error and current_value != new_value:
                        backlog.append("SetOption{} {}".format(so, new_value))

                new_interlock_value = power.ci.input.currentData()
                new_interlock_grps = " ".join([grp.text().replace(" ", "") for grp in power.ci.groups]).rstrip()

                if new_interlock_value != self.device.p.get("Interlock", "OFF"):
                    backlog.append("interlock {}".format(new_interlock_value))

                if new_interlock_grps != self.device.p.get("Groups", ""):
                    backlog.append("interlock {}".format(new_interlock_grps))

                for i, pt in enumerate(power.cpt.inputs):
                    ptime = "PulseTime{}".format(i+1)
                    current_ptime = self.device.p.get(ptime)
                    if current_ptime:
                        current_value = list(current_ptime.keys())[0]
                        new_value = str(pt.value())

                        if new_value != current_value:
                            backlog.append("{} {}".format(ptime, new_value))

                if backlog:
                    backlog.append("status")
                    backlog.append("status 3")
                    self.mqtt.publish(self.device.cmnd_topic("backlog"), "; ".join(backlog))

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
