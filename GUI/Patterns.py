from PyQt5.QtCore import QSize, QSettings, QDir
from PyQt5.QtWidgets import QDialog, QTableWidget, QHeaderView, QTableWidgetItem, QPushButton, QLabel

from GUI import VLayout, HLayout


class PatternsDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super(PatternsDialog, self).__init__(*args, **kwargs)
        self.setMinimumHeight(400)
        self.setMinimumWidth(400)
        self.setWindowTitle("Autodiscovery patterns")

        self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)
        self.settings.beginGroup("Patterns")

        vl = VLayout()
        cols = ["Pattern"]
        self.tw = QTableWidget(0, 1)
        self.tw.setHorizontalHeaderLabels(cols)
        self.tw.verticalHeader().hide()

        self.tw.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        for k in self.settings.childKeys():
            row = self.tw.rowCount()
            self.tw.insertRow(row)
            self.tw.setItem(row, 0, QTableWidgetItem(self.settings.value(k)))

        vl.addWidgets([QLabel("Add your modified FullTopic patterns to enable auto-discovery of such devices\n"
                              "Patterns MUST include %prefix%, %topic% and trailing /\n"
                              "Default Tasmota FullTopics are built-in\n\n"
                              "You have to reconnect to your Broker after topic changes."), self.tw])

        hl_btns = HLayout([0, 3, 0, 3])
        btnAdd = QPushButton("Add")
        btnDel = QPushButton("Delete")
        btnCancel = QPushButton("Cancel")
        btnSave = QPushButton("Save")
        hl_btns.addWidgets([btnAdd, btnDel, btnSave, btnCancel])
        hl_btns.insertStretch(2)
        vl.addLayout(hl_btns)

        self.setLayout(vl)

        self.idx = None
        self.tw.clicked.connect(self.select)
        btnAdd.clicked.connect(self.add)
        btnDel.clicked.connect(self.delete)
        btnSave.clicked.connect(self.accept)
        btnCancel.clicked.connect(self.reject)

    def select(self, idx):
        self.idx = idx

    def add(self):
        row = self.tw.rowCount()
        self.tw.insertRow(row)
        self.tw.setItem(row, 0, QTableWidgetItem("%prefix%/%topic%/"))

    def delete(self):
        if self.idx:
            self.tw.removeRow(self.idx.row())

    def accept(self):
        for k in self.settings.childKeys():
            self.settings.remove(k)

        for r in range(self.tw.rowCount()):
            val = self.tw.item(r, 0).text()
            # check for trailing /
            if (not val.endswith('/')):
                val += '/'
            self.settings.setValue(str(r), val)
        self.settings.endGroup()
        self.done(QDialog.Accepted)
