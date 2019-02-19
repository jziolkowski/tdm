from PyQt5.QtCore import QSize, QSettings, QDir
from PyQt5.QtWidgets import QDialog, QTableWidget, QHeaderView, QTableWidgetItem, QPushButton

from GUI import VLayout, HLayout


class BSSIdDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super(BSSIdDialog, self).__init__(*args, **kwargs)
        self.setMinimumHeight(400)
        self.setMinimumWidth(400)
        self.setWindowTitle("BSSId aliases")

        self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)
        self.settings.beginGroup("BSSId")

        vl = VLayout()
        cols = ["BSSId", "Alias"]
        self.tw = QTableWidget(0,2)
        self.tw.setHorizontalHeaderLabels(cols)
        self.tw.verticalHeader().hide()

        for c in range(2):
            self.tw.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)

        for k in self.settings.childKeys():
            row = self.tw.rowCount()
            self.tw.insertRow(row)
            self.tw.setItem(row, 0, QTableWidgetItem(k))
            self.tw.setItem(row, 1, QTableWidgetItem(self.settings.value(k)))

        vl.addWidget(self.tw)

        hl_btns = HLayout([0,3,0,3])
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
        self.tw.insertRow(self.tw.rowCount())

    def delete(self):
        if self.idx:
            key = self.tw.item(self.idx.row(), 0).text()
            self.settings.remove(key)
            self.tw.removeRow(self.idx.row())

    def accept(self):
        for r in range(self.tw.rowCount()):
            key = self.tw.item(r, 0).text()
            val = self.tw.item(r, 1).text()
            self.settings.setValue(key, val)
        self.settings.endGroup()
        self.done(QDialog.Accepted)
