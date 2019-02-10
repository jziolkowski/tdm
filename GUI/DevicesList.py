from PyQt5.QtCore import Qt, QSettings, pyqtSignal, QSortFilterProxyModel
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QMessageBox, QDialog

from GUI import VLayout, Toolbar, TableView, columns
from GUI.DeviceEdit import DeviceEditDialog
from Util import DevMdl


class DevicesListWidget(QWidget):
    def __init__(self, model, *args, **kwargs):
        super(DevicesListWidget, self).__init__(*args, **kwargs)
        self.setWindowTitle("Devices list")
        self.setWindowState(Qt.WindowMaximized)
        self.setLayout(VLayout(margin=0))

        self.settings = QSettings()
        self.settings.beginGroup('Devices')

        self.tb = Toolbar(Qt.Horizontal, 16, Qt.ToolButtonTextBesideIcon)
        self.tb.addAction(QIcon("GUI/icons/add.png"), "Add", self.device_add)
        self.tb.addSeparator()

        self.actDevEdit = self.tb.addAction(QIcon("GUI/icons/edit.png"), "Edit topics", self.device_edit)
        self.actDevEdit.setEnabled(False)

        self.actDevDelete = self.tb.addAction(QIcon("GUI/icons/delete.png"), "Delete", self.device_delete)
        self.actDevDelete.setEnabled(False)

        self.layout().addWidget(self.tb)

        self.device_list = TableView()
        self.model = model
        self.sorted_device_model = QSortFilterProxyModel()
        self.sorted_device_model.setSourceModel(model)
        self.device_list.setModel(self.sorted_device_model)
        self.device_list.setupColumns(columns)
        self.device_list.setSortingEnabled(True)
        self.device_list.sortByColumn(DevMdl.TOPIC, Qt.AscendingOrder)
        self.layout().addWidget(self.device_list)

        self.device_list.clicked.connect(self.select_device)

    def select_device(self, idx):
        self.idx = idx
        self.actDevEdit.setEnabled(True)
        self.actDevDelete.setEnabled(True)
        self.device = self.model.data(self.model.index(idx.row(), DevMdl.TOPIC))

    def device_add(self):
        rc = self.model.rowCount()
        self.model.insertRow(rc)
        dlg = DeviceEditDialog(self.model, rc)
        self.model.setData(self.model.index(rc, DevMdl.FULL_TOPIC), "%prefix%/%topic%/")
        if dlg.exec_() == QDialog.Accepted:
            self.model.setData(self.model.index(rc, DevMdl.FRIENDLY_NAME), self.model.data(self.model.index(rc, DevMdl.TOPIC)))
        else:
            self.model.removeRow(rc)

    def device_edit(self):
        dlg = DeviceEditDialog(self.model, self.idx.row()).exec_()

    def device_delete(self):
        topic = self.model.data(self.model.index(self.idx.row(), DevMdl.TOPIC))
        if QMessageBox.question(self, "Confirm", "Do you want to remove '{}' from devices list?".format(topic)) == QMessageBox.Yes:
            org_idx = self.sorted_device_model.mapToSource(self.idx)
            org_idx.model().removeRows(org_idx.row(),1)
            self.settings.remove(topic)
            self.settings.sync()

    def closeEvent(self, event):
        event.ignore()
