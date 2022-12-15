from PyQt5.QtWidgets import QDialog, QInputDialog, QLabel, QListWidget, QMessageBox, QPushButton

from GUI.widgets import HLayout, VLayout


class PatternsDialog(QDialog):
    def __init__(self, settings, *args, **kwargs):
        super(PatternsDialog, self).__init__(*args, **kwargs)
        self.setMinimumHeight(400)
        self.setMinimumWidth(400)
        self.setWindowTitle("Autodiscovery patterns")

        self.settings = settings
        self.settings.beginGroup("Patterns")

        vl = VLayout()
        self.lw = QListWidget()
        self.lw.setAlternatingRowColors(True)

        for k in self.settings.childKeys():
            self.lw.addItem(self.settings.value(k))
        self.lw.sortItems()
        self.settings.endGroup()

        vl.addElements(
            QLabel(
                "Add your modified FullTopic patterns to enable auto-discovery of such devices"
                "\nPatterns MUST include %prefix%, %topic% and trailing /\n"
                "Default Tasmota FullTopics are built-in\n\n"
                "You have to reconnect to your Broker after topic changes."
            ),
            self.lw,
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

        self.row = None
        self.lw.clicked.connect(self.select)
        btnAdd.clicked.connect(self.add)
        btnDel.clicked.connect(self.delete)
        btnSave.clicked.connect(self.accept)
        btnCancel.clicked.connect(self.reject)

    @staticmethod
    def validate_pattern(pattern):
        errors = []

        if not pattern.endswith("/"):
            errors.append("Missing trailing slash")

        for required_token in ["%prefix%", "%topic%"]:
            if required_token not in pattern:
                errors.append(f"{required_token} is required in the pattern.")

        for wrong_token in ["#", "$"]:
            if wrong_token in pattern:
                errors.append(f"Wrong character in pattern: {wrong_token}.")

        return errors

    def select(self, idx):
        self.row = idx.row()

    def add(self):
        pattern, ok = QInputDialog.getText(
            self, "Add pattern", "Add new discovery pattern", text="%prefix%/%topic%/"
        )
        if ok:
            if errors := self.validate_pattern(pattern):
                errors_str = '\n'.join(errors)
                QMessageBox.critical(
                    self, "Error", f"Problem(s) with pattern {pattern}:\n{errors_str}"
                )
            else:
                self.lw.addItem(pattern)
                self.lw.sortItems()

    def delete(self):
        if self.row is not None:
            self.lw.takeItem(self.row)

    def accept(self):
        self.settings.beginGroup("Patterns")
        for k in self.settings.childKeys():
            self.settings.remove(k)

        for row, pattern in enumerate([self.lw.item(x).text() for x in range(self.lw.count())]):
            self.settings.setValue(str(row), pattern)
        self.settings.endGroup()
        self.done(QDialog.Accepted)
