import os
from json import dumps
from typing import Optional

from PyQt5.QtCore import QDir, QSortFilterProxyModel, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QApplication,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from tdmgr.GUI.common import make_relay_pixmap
from tdmgr.GUI.delegates.devices import DeviceDelegate
from tdmgr.GUI.dialogs import (
    ButtonsDialog,
    GPIODialog,
    ModulesDialog,
    PowerDialog,
    SetOptionsDialog,
    SwitchesDialog,
    TemplateDialog,
    TimersDialog,
)
from tdmgr.GUI.dialogs.shutter_control import ShutterControlDialog
from tdmgr.GUI.widgets import (
    SliderAction,
    SpinBox,
    TableView,
    Toolbar,
    VLayout,
    base_view,
    default_views,
)
from tdmgr.mqtt import MqttClient, initial_commands
from tdmgr.tasmota.commands import resets
from tdmgr.tasmota.common import MAX_RELAYS, CTRange, TasmotaColor, map_value
from tdmgr.tasmota.device import TasmotaDevice


class DevicesListWidget(QWidget):
    deviceSelected = pyqtSignal(TasmotaDevice)
    openRulesEditor = pyqtSignal()
    openConsole = pyqtSignal()
    openTelemetry = pyqtSignal()
    openWebUI = pyqtSignal()

    def __init__(self, parent, *args, **kwargs):
        super(DevicesListWidget, self).__init__(*args, **kwargs)
        self.setWindowTitle("Devices list")
        self.setWindowState(Qt.WindowMaximized)
        vl = VLayout(margin=0, spacing=0)

        self.mqtt: MqttClient = parent.mqtt
        self.env = parent.env

        self.device: Optional[TasmotaDevice] = None
        self.idx = None

        self.nam = QNetworkAccessManager()
        self.backup = bytes()

        self.settings = parent.settings
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
        self.tb_views = Toolbar(Qt.Horizontal, 24, Qt.ToolButtonTextBesideIcon)

        self.pwm_sliders = []

        vl.addElements(self.tb, self.tb_relays)

        self.device_list = TableView()
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

        vl.addElements(self.device_list, self.tb_views)
        self.setLayout(vl)

        self.device_list.clicked.connect(self.select_device)
        self.device_list.customContextMenuRequested.connect(self.show_list_ctx_menu)

        self.ctx_menu = QMenu()

        self.create_actions()
        self.create_view_buttons()

        self.device_list.doubleClicked.connect(lambda: self.openConsole.emit())

    def create_actions(self):
        self.ctx_menu.addActions(
            [
                self.tb.add_action(":/console.png", "Console", self.openConsole.emit, "Ctrl+E"),
                self.tb.add_action(":/rules.png", "Rules", self.openRulesEditor.emit, "Ctrl+R"),
                self.tb.add_action(":/timers.png", "Timers", self.configureTimers),
                self.tb.add_action(":/buttons.png", "Buttons", self.configureButtons, "Ctrl+B"),
                self.tb.add_action(":/switches.png", "Switches", self.configureSwitches, "Ctrl+S"),
                self.tb.add_action(":/power.png", "Power", self.configurePower, "Ctrl+P"),
            ]
        )
        self.tb.addSpacer()

        self.ctx_menu.addActions(
            [
                self.tb.add_action(
                    ":/telemetry.png", "Telemetry", self.openTelemetry.emit, "Ctrl+T"
                ),
                self.tb.add_action(":/web.png", "WebUI", self.openWebUI.emit, "Ctrl+U"),
            ]
        )

        self.ctx_menu.addSeparator()

        self.ctx_menu_cfg = QMenu("Configure")
        self.ctx_menu_cfg.setIcon(QIcon(":/settings.png"))
        self.ctx_menu_cfg.addAction("Module", self.configureModule)
        self.ctx_menu_cfg.addAction("GPIO", self.configureGPIO)
        self.ctx_menu_cfg.addAction("Template", self.configureTemplate)
        self.ctx_menu_cfg.addAction("OTA Url", self.configureOtaUrl)

        self.ctx_menu.addMenu(self.ctx_menu_cfg)
        self.ctx_menu.addSeparator()

        self.ctx_menu.addAction(QIcon(":/refresh.png"), "Refresh", self.ctx_menu_refresh)

        self.ctx_menu.addSeparator()
        self.ctx_menu.addAction("Clear Backlog", self.ctx_menu_clear_backlog)
        self.ctx_menu.addSeparator()
        self.ctx_menu.addAction(QIcon(":/copy.png"), "Copy", self.ctx_menu_copy)
        self.ctx_menu.addSeparator()
        self.ctx_menu.addAction(QIcon(":/restart.png"), "Restart", self.ctx_menu_restart)
        self.ctx_menu.addAction("OTA Upgrade", self.ctx_menu_ota_upgrade)
        self.ctx_menu.addAction(QIcon(), "Reset", self.ctx_menu_reset)
        self.ctx_menu.addSeparator()
        self.ctx_menu.addAction(QIcon(":/delete.png"), "Delete", self.ctx_menu_delete_device)

        self.agAllPower = QActionGroup(self)
        for label, shortcut, fill in [
            ("ON", "Ctrl+F1", True),
            ("OFF", "Ctrl+F2", False),
        ]:
            px = make_relay_pixmap(label, filled=fill)
            act = self.agAllPower.addAction(QIcon(px), f"All relays {label}")
            act.setShortcut(shortcut)
        self.agAllPower.setEnabled(False)
        self.agAllPower.setExclusive(False)
        self.agAllPower.triggered.connect(self.toggle_power_all)
        self.tb_relays.addActions(self.agAllPower.actions())

        self.agRelays = QActionGroup(self)
        self.agRelays.setVisible(False)
        self.agRelays.setExclusive(False)

        for a in range(1, 33):
            px = make_relay_pixmap(a, False)
            act = QAction(QIcon(px), f"Relay {a} TOGGLE")
            if a <= 8:
                act.setShortcut(f"F{a}")
            else:
                act.setShortcut(f"Shift+F{a}")
            self.agRelays.addAction(act)

        self.agRelays.triggered.connect(self.toggle_power)
        self.tb_relays.addActions(self.agRelays.actions())

        self.actShutters = self.tb_relays.addAction(
            QIcon(":/shutter.png"), "Shutters", self.shutterControl
        )
        self.actShutters.setEnabled(False)
        self.tb_relays.addAction(self.actShutters)

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

    def ctx_menu_clear_backlog(self):
        if self.device:
            self.mqtt.publish(self.device.cmnd_topic("backlog"), "")
            QMessageBox.information(self, "Clear Backlog", "Backlog cleared.")

    def ctx_menu_restart(self):
        if self.device:
            self.mqtt.publish(self.device.cmnd_topic("restart"), payload="1")
            self.remove_power_items()

    def ctx_menu_reset(self):
        if self.device:
            reset, ok = QInputDialog.getItem(
                self,
                "Reset device and restart",
                "Select reset mode",
                resets,
                editable=False,
            )
            if ok:
                self.mqtt.publish(self.device.cmnd_topic("reset"), payload=reset.split(":")[0])
                self.remove_power_items()

    def ctx_menu_refresh(self):
        if self.device:
            self.remove_power_items()

            for c in initial_commands():
                cmd, payload = c
                cmd = self.device.cmnd_topic(cmd)
                self.mqtt.publish(cmd, payload, 1)

    def remove_power_items(self):
        for k in [""] + list(range(1, MAX_RELAYS + 1)):
            self.device.p.pop(f"POWER{k}", None)

    def ctx_menu_delete_device(self):
        if self.device:
            if (
                QMessageBox.question(
                    self,
                    "Confirm",
                    f"Do you want to remove the following device?\n'{self.device.p['DeviceName']}' "
                    f"({self.device.p['Topic']})",
                )
                == QMessageBox.Yes
            ):
                self.model.deleteDevice(self.idx)

    def ctx_menu_teleperiod(self):
        if self.device:
            teleperiod, ok = QInputDialog.getInt(
                self,
                "Set telemetry period",
                "Input 1 to reset to default\n[Min: 10, Max: 3600]",
                self.device.p["TelePeriod"],
                1,
                3600,
            )
            if ok:
                if teleperiod != 1 and teleperiod < 10:
                    teleperiod = 10
            self.mqtt.publish(self.device.cmnd_topic("teleperiod"), teleperiod)

    def ctx_menu_config_backup(self):
        if self.device:
            self.backup = bytes()
            self.dl = self.nam.get(QNetworkRequest(QUrl(f"http://{self.device.p['IPAddress']}/dl")))
            self.dl.readyRead.connect(self.get_dump)
            self.dl.finished.connect(self.save_dump)

    def ctx_menu_ota_upgrade(self):
        if self.device:
            reply = QMessageBox.question(
                self,
                "OTA Upgrade",
                f"Are you sure to OTA upgrade from\n{self.device.p['OtaUrl']}",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.mqtt.publish(self.device.cmnd_topic("upgrade"), payload="1")

    def show_list_ctx_menu(self, at):
        self.select_device(self.device_list.indexAt(at))
        self.ctx_menu.popup(self.device_list.viewport().mapToGlobal(at))

    def select_device(self, idx):
        self.idx = self.sorted_device_model.mapToSource(idx)
        self.device: TasmotaDevice = self.model.deviceAtRow(self.idx.row())
        self.deviceSelected.emit(self.device)

        self.agAllPower.setEnabled(False)
        self.agRelays.setVisible(False)
        if relays := self.device.power():
            self.agAllPower.setEnabled(True)
            relay_keys = [r.idx for r in relays]
            for i, a in enumerate(self.agRelays.actions()):
                a.setVisible(i + 1 in relay_keys)

        if self.device.shutters():
            self.actShutters.setEnabled(True)

        self.actColor.setEnabled(False)
        self.actChannels.setEnabled(False)
        if color := self.device.color():
            self.actColor.setEnabled(bool(color.hsbcolor) and color.SO68 == 0)
            self.actChannels.setEnabled(True)

            self.actChannels.menu().clear()

            max_val = 1023 if color.SO15 == 0 else 100

            if color.SO68 == 1:
                for idx, value in enumerate(color.channels, start=1):
                    channel = SliderAction(self, f"Channel{idx}")
                    channel.slider.setMaximum(max_val)
                    channel.slider.setValue(value)
                    self.mChannels.addAction(channel)
                    channel.slider.valueChanged.connect(self.set_channel)

            if color.ct:
                ct = SliderAction(self, "CT")
                ct.slider.setRange(*CTRange)
                ct.slider.setObjectName("CT")
                ct.slider.setValue(map_value(color.ct, CTRange, 100))
                self.mChannels.addAction(ct)
                ct.slider.valueChanged.connect(self.set_channel)

            if dimmer := color.dimmers:
                for idx, value in enumerate(dimmer, start=1):
                    saDimmer = SliderAction(self, f"Dimmer{idx}")
                    saDimmer.slider.setValue(value)
                    self.mChannels.addAction(saDimmer)
                    saDimmer.slider.valueChanged.connect(self.set_channel)

    def toggle_power(self, action):
        if self.device:
            idx = self.agRelays.actions().index(action)
            self.mqtt.publish(self.device.cmnd_topic(f"POWER{idx+1}"), "toggle")

    def toggle_power_all(self, action):
        idx = self.agAllPower.actions().index(action)
        if self.device:
            if self.device.version_above("6.6.0.9"):
                self.mqtt.publish(self.device.cmnd_topic("POWER0"), idx ^ 1)
            else:
                for r in [r.idx for r in self.device.power()]:
                    self.mqtt.publish(self.device.cmnd_topic(r), idx ^ 1)

    def move_shutter(self, action):
        idx = 1 + self.agShutters.actions().index(action)
        shutter = (idx + 1) // 2
        direction = self.device.p[f"Shutter{shutter}"]["Direction"]
        action = (
            "ShutterStop" if direction != 0 else "ShutterClose" if idx % 2 == 0 else "ShutterOpen"
        )
        self.mqtt.publish(self.device.cmnd_topic(f"{action}{shutter}"))

    def set_color(self):
        if self.device:
            if color := self.device.color():
                current = TasmotaColor.fromTasmotaHSB(color.hsbcolor)

                dlg = QColorDialog()
                new = TasmotaColor(dlg.getColor(current))
                if new.isValid():
                    if new != current:
                        self.mqtt.publish(self.device.cmnd_topic("HSBColor"), new.getTasmotaHSB())

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
            dlg = ModulesDialog(self.device)
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

    def configureOtaUrl(self):
        if self.device:
            url, ok = QInputDialog.getText(
                self,
                "Set OTA URL",
                '100 chars max. Set to "1" to reset to default.',
                text=self.device.p["OtaUrl"],
            )
            if ok:
                self.mqtt.publish(self.device.cmnd_topic("otaurl"), payload=url)

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
                        backlog.append(f"{c} {new_value}")

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
                        backlog.append(f"SetOption{so} {new_value}")

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
                        backlog.append(f"{c} {new_value}")

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
                        backlog.append(f"SetOption{so} {new_value}")

                for sw, sw_mode in enumerate(self.device.p["SwitchMode"]):
                    new_value = switches.sm.inputs[sw].currentIndex()

                    if sw_mode != new_value:
                        backlog.append(f"switchmode{sw + 1} {new_value}")

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
                        backlog.append(f"{c} {new_value}")

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
                        backlog.append(f"SetOption{so} {new_value}")

                new_interlock_value = power.ci.input.currentData()
                new_interlock_grps = " ".join(
                    [grp.text().replace(" ", "") for grp in power.ci.groups]
                ).rstrip()

                if new_interlock_value != self.device.p.get("Interlock", "OFF"):
                    backlog.append(f"interlock {new_interlock_value}")

                if new_interlock_grps != self.device.p.get("Groups", ""):
                    backlog.append(f"interlock {new_interlock_grps}")

                for i, pt in enumerate(power.cpt.inputs):
                    ptime = f"PulseTime{i + 1}"
                    current_ptime = self.device.p.get(ptime)
                    if current_ptime:
                        current_value = list(current_ptime.keys())[0]
                        new_value = str(pt.value())

                        if new_value != current_value:
                            backlog.append(f"{ptime} {new_value}")

                if backlog:
                    backlog.append("status")
                    backlog.append("status 3")
                    self.mqtt.publish(self.device.cmnd_topic("backlog"), "; ".join(backlog))

    def shutterControl(self):
        shutters = ShutterControlDialog(self.device)
        shutters.sendCommand.connect(self.mqtt.publish)
        self.mqtt.publish(self.device.cmnd_topic("shutterposition"))
        shutters.exec_()

    def get_dump(self):
        self.backup += self.dl.readAll()

    def save_dump(self):
        fname = self.dl.header(QNetworkRequest.ContentDispositionHeader)
        if fname:
            fname = fname.split("=")[1]
            save_file = QFileDialog.getSaveFileName(
                self, "Save config backup", os.path.join((QDir.homePath(), fname))
            )[0]
            if save_file:
                with open(save_file, "wb") as f:
                    f.write(self.backup)

    def check_fulltopic(self, fulltopic):
        fulltopic += "/" if not fulltopic.endswith("/") else ""
        return "%prefix%" in fulltopic and "%topic%" in fulltopic

    def closeEvent(self, event):
        event.ignore()
