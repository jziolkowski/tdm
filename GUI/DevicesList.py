from PyQt5.QtCore import Qt, QSettings, QSortFilterProxyModel, QUrl, QDir
from PyQt5.QtGui import QIcon, QDesktopServices
from PyQt5.QtWidgets import QWidget, QMessageBox, QDialog, QMenu, QApplication, QToolButton

from GUI import VLayout, Toolbar, TableView, columns
from GUI.DeviceConfig import DevicesConfigWidget
from GUI.DeviceEdit import DeviceEditDialog
from Util import DevMdl, initial_queries
from Util.models import DeviceDelegate
from Util.nodes import TasmotaDevice


class DevicesListWidget(QWidget):
    def __init__(self, parent, *args, **kwargs):
        super(DevicesListWidget, self).__init__(*args, **kwargs)
        self.setWindowTitle("Devices list")
        self.setWindowState(Qt.WindowMaximized)
        self.setLayout(VLayout(margin=0, spacing=0))

        self.mqtt = parent.mqtt
        self.mdi = parent.mdi
        self.idx = None

        self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)
        self.hidden_columns = self.settings.value("hidden_columns", [1, 2])

        self.tb = Toolbar(Qt.Horizontal, 16, Qt.ToolButtonTextBesideIcon)
        self.tb.addAction(QIcon("GUI/icons/add.png"), "Add", self.device_add)

        self.layout().addWidget(self.tb)

        self.device_list = TableView()
        self.model = parent.device_model
        self.telemetry_model = parent.telemetry_model
        self.sorted_device_model = QSortFilterProxyModel()
        self.sorted_device_model.setSourceModel(parent.device_model)
        self.device_list.setModel(self.sorted_device_model)
        self.device_list.setupColumns(columns, self.hidden_columns)
        self.device_list.setSortingEnabled(True)
        self.device_list.setWordWrap(True)
        self.device_list.setItemDelegate(DeviceDelegate())
        self.device_list.sortByColumn(DevMdl.TOPIC, Qt.AscendingOrder)
        self.device_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.layout().addWidget(self.device_list)

        self.device_list.clicked.connect(self.select_device)
        self.device_list.doubleClicked.connect(self.device_config)
        self.device_list.customContextMenuRequested.connect(self.show_list_ctx_menu)

        self.device_list.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.device_list.horizontalHeader().customContextMenuRequested.connect(self.show_header_ctx_menu)

        self.ctx_menu = QMenu()
        self.ctx_menu_relays = None
        self.create_actions()

        self.build_header_ctx_menu()

    def create_actions(self):
        self.ctx_menu.addAction(QIcon("GUI/icons/configure.png"), "Configure", self.device_config)
        self.ctx_menu.addAction(QIcon("GUI/icons/delete.png"), "Remove", self.device_delete)
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

        self.ctx_menu_copy.addAction("IP", lambda: self.ctx_menu_copy_value(DevMdl.IP))
        self.ctx_menu_copy.addAction("MAC", lambda: self.ctx_menu_copy_value(DevMdl.MAC))
        self.ctx_menu_copy.addAction("BSSID", self.ctx_menu_copy_bssid)
        self.ctx_menu_copy.addSeparator()
        self.ctx_menu_copy.addAction("Topic", lambda: self.ctx_menu_copy_value(DevMdl.TOPIC))
        self.ctx_menu_copy.addAction("FullTopic", lambda: self.ctx_menu_copy_value(DevMdl.FULL_TOPIC))
        self.ctx_menu_copy.addAction("STAT topic", lambda: self.ctx_menu_copy_prefix_topic("STAT"))
        self.ctx_menu_copy.addAction("CMND topic", lambda: self.ctx_menu_copy_prefix_topic("CMND"))
        self.ctx_menu_copy.addAction("TELE topic", lambda: self.ctx_menu_copy_prefix_topic("TELE"))

        self.tb.addActions(self.ctx_menu.actions())
        self.tb.widgetForAction(relays_btn).setPopupMode(QToolButton.InstantPopup)
        self.tb.widgetForAction(copy_btn).setPopupMode(QToolButton.InstantPopup)

    def ctx_menu_copy_value(self, column):
        if self.idx:
            row = self.idx.row()
            value = self.model.data(self.model.index(row, column))
            QApplication.clipboard().setText(value)

    def ctx_menu_copy_bssid(self):
        if self.idx:
            QApplication.clipboard().setText(self.model.bssid(self.idx))

    def ctx_menu_copy_prefix_topic(self, prefix):
        if self.idx:
            if prefix == "STAT":
                topic = self.model.statTopic(self.idx)
            elif prefix == "CMND":
                topic = self.model.commandTopic(self.idx)
            elif prefix == "TELE":
                topic = self.model.teleTopic(self.idx)
            QApplication.clipboard().setText(topic)

    def ctx_menu_clean_retained(self):
        if self.idx:
            relays = self.model.data(self.model.index(self.idx.row(), DevMdl.POWER))
            if relays and len(relays.keys()) > 0:
                cmnd_topic = self.model.cmndTopic(self.idx)

                for r in relays.keys():
                    self.mqtt.publish(cmnd_topic + r, retain=True)
                QMessageBox.information(self, "Clear retained", "Cleared reatined messages.")

    def ctx_menu_power(self, relay=None, state=None):
        if self.idx:
            relays = self.model.data(self.model.index(self.idx.row(), DevMdl.POWER))
            cmnd_topic = self.model.commandTopic(self.idx)
            if relay:
                self.mqtt.publish(cmnd_topic+relay, payload=state)

            elif relays:
                for r in relays.keys():
                    self.mqtt.publish(cmnd_topic+r, payload=state)

    def ctx_menu_restart(self):
        if self.idx:
            self.mqtt.publish("{}/restart".format(self.model.commandTopic(self.idx)), payload="1")

    def ctx_menu_refresh(self):
        if self.idx:
            for q in initial_queries:
                self.mqtt.publish("{}/status".format(self.model.commandTopic(self.idx)), payload=q)

    def ctx_menu_telemetry(self):
        if self.idx:
            self.mqtt.publish("{}/status".format(self.model.commandTopic(self.idx)), payload=8)

    def ctx_menu_webui(self):
        if self.idx:
            QDesktopServices.openUrl(QUrl("http://{}".format(self.model.ip(self.idx))))

    def show_list_ctx_menu(self, at):
        self.select_device(self.device_list.indexAt(at))
        self.ctx_menu.popup(self.device_list.viewport().mapToGlobal(at))

    def build_header_ctx_menu(self):
        self.hdr_ctx_menu = QMenu()
        for c in columns.keys():
            a = self.hdr_ctx_menu.addAction(columns[c][0])
            a.setData(c)
            a.setCheckable(True)
            a.setChecked(not self.device_list.isColumnHidden(c))
            a.toggled.connect(self.header_ctx_menu_toggle_col)

    def show_header_ctx_menu(self, at):
        self.hdr_ctx_menu.popup(self.device_list.horizontalHeader().viewport().mapToGlobal(at))

    def header_ctx_menu_toggle_col(self, state):
        self.device_list.setColumnHidden(self.sender().data(), not state)
        hidden_columns = [int(c) for c in columns.keys() if self.device_list.isColumnHidden(c)]
        self.settings.setValue("hidden_columns", hidden_columns)
        self.settings.sync()

    def select_device(self, idx):
        self.idx = self.sorted_device_model.mapToSource(idx)
        self.device = self.model.data(self.model.index(idx.row(), DevMdl.TOPIC))

        relays = self.model.data(self.model.index(self.idx.row(), DevMdl.POWER))
        if relays and len(relays.keys()) > 1:
            self.ctx_menu_relays.setEnabled(True)
            self.ctx_menu_relays.setEnabled(True)
            self.ctx_menu_relays.clear()

            for r in relays.keys():
                actR = self.ctx_menu_relays.addAction("{} ON".format(r))
                actR.triggered.connect(lambda st, x=r: self.ctx_menu_power(x, "ON"))
                actR = self.ctx_menu_relays.addAction("{} OFF".format(r))
                actR.triggered.connect(lambda st, x=r: self.ctx_menu_power(x, "OFF"))
                self.ctx_menu_relays.addSeparator()
        else:
            self.ctx_menu_relays.setEnabled(False)
            self.ctx_menu_relays.clear()

    def device_config(self, idx=None):
        dev_cfg = DevicesConfigWidget(self, self.model.topic(self.idx))
        self.mdi.addSubWindow(dev_cfg)
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
                tele_idx = self.telemetry_model.devices.get(topic)
                if tele_idx:
                    self.telemetry_model.removeRows(tele_idx.row(),1)

    def closeEvent(self, event):
        event.ignore()
