from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QTabWidget, QWidget

from GUI import HLayout, VLayout, GroupBoxV, HTMLLabel, Command, CommandMultiSelect
from Util import setoptions, commands_json as commands


class LightDialog(QDialog):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(LightDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle("Light settings [{}]".format(device.p['FriendlyName1']))
        self.setMinimumWidth(300)
        self.device = device

        self.setoption_list = [68, 15, 16, 17, 20]
        self.setoption_widgets = {}

        vl = VLayout()

        vl_so = VLayout(0, 0)
        for so in self.setoption_list:
            cw = Command("SetOption{}".format(so), setoptions[str(so)], self.device.setoption(so))
            vl_so.addWidget(cw)
            self.setoption_widgets[so] = cw

        tabs = QTabWidget()
        tab_so = QWidget()
        tab_so.setLayout(vl_so)
        tabs.addTab(tab_so, "SetOptions")
        vl.addWidget(tabs)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        self.setLayout(vl)
