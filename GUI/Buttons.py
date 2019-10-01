from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QTabWidget, QWidget

from GUI import HLayout, VLayout, GroupBoxV, HTMLLabel, Command, CommandMultiSelect
from Util import setoptions, commands_json as commands


class ButtonsDialog(QDialog):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(ButtonsDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle("Buttons settings [{}]".format(device.p['FriendlyName1']))
        self.setMinimumWidth(300)
        self.device = device

        self.commands_list = ["ButtonDebounce", "ButtonRetain"]
        self.command_widgets = {}

        self.setoption_list = [11, 13, 32, 40, 61]
        self.setoption_widgets = {}

        vl = VLayout()
        vl_cmd = VLayout(0, 0)
        for cmd in self.commands_list:
            cw = Command(cmd, commands[cmd], self.device.p.get(cmd))
            vl_cmd.addWidget(cw)
            self.command_widgets[cmd] = cw
        vl_cmd.addStretch(1)

        vl_so = VLayout(0, 0)
        for so in self.setoption_list:
            cw = Command("SetOption{}".format(so), setoptions[str(so)], self.device.setoption(so))
            vl_so.addWidget(cw)
            self.setoption_widgets[so] = cw

        tabs = QTabWidget()
        tab_cm = QWidget()
        tab_cm.setLayout(vl_cmd)
        tabs.addTab(tab_cm, "Settings")

        tab_so = QWidget()
        tab_so.setLayout(vl_so)
        tabs.addTab(tab_so, "SetOptions")
        vl.addWidget(tabs)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        vl.addWidgets([HTMLLabel("<a href=https://github.com/arendst/Sonoff-Tasmota/wiki/Buttons-and-Switches>Buttons and Switches</a>"), btns])
        self.setLayout(vl)
