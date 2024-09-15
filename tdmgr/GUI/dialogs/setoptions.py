from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QLabel

from tdmgr.GUI.widgets import DictComboBox, GroupBoxV, VLayout
from tdmgr.tasmota.setoptions import setoptions


class SetOptionsDialog(QDialog):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(SetOptionsDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle(f"SetOptions [{device.name}]")
        self.setMinimumWidth(300)
        self.device = device

        self.gbs = []

        vl = VLayout()

        for i, so in setoptions.items():
            gb = GroupBoxV(f"SetOption{i}")
            cb = DictComboBox(so["parameters"])
            gb.addElements(QLabel(so["description"]), cb)

            vl.addWidget(gb)

        # self.gb = DictComboBox(self.device.modules)
        # self.gb.setCurrentText(self.device.modules[str(self.device.p['Module'])])
        # gbxModules.addWidget(self.gb)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        vl.addWidget(btns)
        self.setLayout(vl)

    def accept(self):
        # self.sendCommand.emit(self.device.cmnd_topic("module"), self.gb.currentData())
        # QMessageBox.information(self, "Module saved", "Device will restart.")
        self.done(QDialog.Accepted)
