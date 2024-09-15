from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QTabWidget, QWidget

from tdmgr.GUI.widgets import Command, CommandMultiSelect, HTMLLabel, VLayout, docs_url
from tdmgr.tasmota.commands import commands
from tdmgr.tasmota.setoptions import setoptions


class SwitchesDialog(QDialog):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(SwitchesDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle(f"Switches settings [{device.name}]")
        self.setMinimumWidth(300)
        self.device = device

        self.commands_list = ["SwitchDebounce", "SwitchRetain"]
        self.command_widgets = {}

        self.setoption_list = [32]
        self.setoption_widgets = {}

        vl = VLayout()

        vl_cmd = VLayout(0, 0)
        for cmd in self.commands_list:
            cw = Command(cmd, commands[cmd], self.device.p.get(cmd))
            vl_cmd.addWidget(cw)
            self.command_widgets[cmd] = cw
        self.sm = CommandMultiSelect(
            "SwitchMode", commands["SwitchMode"], self.device.p.get("SwitchMode")
        )
        vl_cmd.addWidget(self.sm)
        vl_cmd.addStretch(1)

        vl_so = VLayout(0, 0)
        for so in self.setoption_list:
            cw = Command(f"SetOption{so}", setoptions[str(so)], self.device.setoption(so))
            vl_so.addWidget(cw)
            self.setoption_widgets[so] = cw
        vl_so.addStretch(1)

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
        vl.addElements(
            HTMLLabel(f"<a href={docs_url}/Buttons-and-Switches>Buttons and Switches</a>"),
            btns,
        )
        self.setLayout(vl)
