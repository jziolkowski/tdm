from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import (
    QDialog,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem, QMessageBox,
)

from GUI.widgets import HLayout, VLayout


class PatternsDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super(PatternsDialog, self).__init__(*args, **kwargs)
        self.setMinimumHeight(400)
        self.setMinimumWidth(400)
        self.setWindowTitle("Autodiscovery patterns")

        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "tdm", "tdm")
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

        vl.addElements(
            QLabel(
                "Add your modified FullTopic patterns to enable auto-discovery of such devices"
                "\nPatterns MUST include %prefix%, %topic% and trailing /\n"
                "Default Tasmota FullTopics are built-in\n\n"
                "You have to reconnect to your Broker after topic changes."
            ),
            self.tw,
        )

        hl_btns = HLayout([0, 3, 0, 3])
        btnAdd = QPushButton("Add")
        btnDel = QPushButton("Delete")
        btnCancel = QPushButton("Cancel")
        btnSave = QPushButton("Save")
        hl_btns.addElements(btnAdd, btnDel, btnSave, btnCancel)
        hl_btns.insertStretch(2)
        vl.addLayout(hl_btns)

        self.setLayout(vl)

        self.idx = None
        self.tw.clicked.connect(self.select)
        btnAdd.clicked.connect(self.add)
        btnDel.clicked.connect(self.delete)
        btnSave.clicked.connect(self.accept)
        btnCancel.clicked.connect(self.reject)

        self.tw.cellChanged.connect(self.validate_pattern)

    def validate_pattern(self, row, col):
        val = self.tw.item(row, 0).text()
        errors = []

        if not val.endswith("/"):
            errors.append("Missing trailing slash")

        for required_token in ["%prefix%", "%topic%"]:
            if required_token not in val:
                errors.append(f"{required_token} is required in the pattern.")

        for wrong_token in ["#", "$"]:
            if wrong_token in val:
                errors.append(f"Wrong character in pattern: {wrong_token}.")

        if errors:
            errors_str = '\n'.join(errors)
            QMessageBox.critical(self, "Error", f"Problem(s) with pattern {val}:\n {errors_str}")

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
            self.settings.setValue(str(r), val)
        self.settings.endGroup()
        self.done(QDialog.Accepted)
