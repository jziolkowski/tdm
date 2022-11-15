from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

from GUI.widgets import DictComboBox, GroupBoxV, VLayout


class ModulesDialog(QDialog):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(ModulesDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle(f"Module [{device.name}]")
        self.setMinimumWidth(300)
        self.device = device

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        gbxModules = GroupBoxV("Select Module")
        self.gb = DictComboBox(self.device.modules)
        self.gb.setCurrentText(self.device.modules[str(self.device.p["Module"])])
        gbxModules.addElements(self.gb)

        vl = VLayout()
        vl.addElements(gbxModules, btns)
        self.setLayout(vl)

    def accept(self):
        self.sendCommand.emit(self.device.cmnd_topic("module"), self.gb.currentData())
        QMessageBox.information(self, "Module saved", "Device will restart.")
        self.done(QDialog.Accepted)
