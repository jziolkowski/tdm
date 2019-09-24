from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QDialog, QMessageBox, QComboBox, QPushButton, QFormLayout, QLabel, QGroupBox, QWidget, \
    QDialogButtonBox

from GUI import HLayout, VLayout, DictComboBox, GroupBoxV
from Util import setoptions

class SetOptionsDialog(QDialog):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(SetOptionsDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle("SetOptions [{}]".format(device.p['FriendlyName1']))
        self.setMinimumWidth(300)
        self.device = device

        self.gbs = []

        vl = VLayout()

        for i, so in setoptions.items():
            gb = GroupBoxV("SetOption{}".format(i))
            cb = DictComboBox(so['parameters'])
            gb.addWidgets([QLabel(so['description']), cb])

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
