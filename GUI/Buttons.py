from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox

from GUI import HLayout, VLayout, GroupBoxV, HTMLLabel, Command
from Util import setoptions, commands_json as commands


class ButtonsDialog(QDialog):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(ButtonsDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle("Buttons settings [{}]".format(device.p['FriendlyName1']))
        self.setMinimumWidth(300)
        self.device = device

        vl = VLayout()

        vl_cmd = VLayout(0)
        self.cmBtnDebounce = Command("ButtonDebounce", commands["ButtonDebounce"])
        self.cmBtnRetain = Command("ButtonRetain", commands["ButtonRetain"])
        self.cmBtnTopic = Command("ButtonTopic", commands["ButtonTopic"])
        vl_cmd.addWidgets([self.cmBtnDebounce, self.cmBtnRetain])
        vl_cmd.addStretch(1)

        vl_so = VLayout(0)
        self.so11 = Command("SetOption11", setoptions["11"])
        self.so13 = Command("SetOption13", setoptions["13"])
        self.so32 = Command("SetOption32", setoptions["32"])
        self.so40 = Command("SetOption40", setoptions["40"])
        self.so61 = Command("SetOption61", setoptions["61"])
        vl_so.addWidgets([self.so11, self.so13, self.so32, self.so40, self.so61])

        hl_cm_so = HLayout()
        hl_cm_so.addLayout(vl_cmd)
        hl_cm_so.addLayout(vl_so)
        vl.addLayout(hl_cm_so)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        vl.addWidgets([HTMLLabel("<a href=https://github.com/arendst/Sonoff-Tasmota/wiki/Buttons-and-Switches>Buttons and Switches</a>"), btns])
        self.setLayout(vl)
