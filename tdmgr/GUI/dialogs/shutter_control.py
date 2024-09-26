from typing import Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPushButton

from tdmgr.GUI.widgets import GroupBoxV, HLayout, Slider, SpinBox, VLayout
from tdmgr.schemas.result import ShutterResultSchema
from tdmgr.tasmota.common import Shutter
from tdmgr.tasmota.device import TasmotaDevice

DIRECTION_MAP = {-1: "[CLOSING]", 0: "", 1: "[OPENING]"}


class ShutterWidget(GroupBoxV):
    command = pyqtSignal(str)
    position_command = pyqtSignal(str, int)

    def __init__(self, shutter: Shutter, has_tilt: bool, *args, **kwargs):
        super(ShutterWidget, self).__init__("Shutter", *args, **kwargs)
        self.shutter = shutter

        hl_position = HLayout()

        self.slider = Slider()
        self.position = SpinBox(minimum=0, maximum=100)

        self.slider.valueChanged.connect(self.position.setValue)
        self.position.valueChanged.connect(self.slider.setValue)

        self.set = QPushButton("Set")
        self.set.setMaximumWidth(50)
        self.set.clicked.connect(
            lambda: self.position_command.emit(
                f"ShutterPosition{self.shutter.idx}", self.position.value()
            )
        )

        self.stop = QPushButton("Stop")
        self.stop.setMaximumWidth(50)
        self.stop.clicked.connect(lambda: self.command.emit(f"ShutterStop{self.shutter.idx}"))

        self.open = QPushButton("Open")
        self.open.setMaximumWidth(50)
        self.open.clicked.connect(lambda: self.command.emit(f"ShutterOpen{self.shutter.idx}"))

        self.close = QPushButton("Close")
        self.close.setMaximumWidth(50)
        self.close.clicked.connect(lambda: self.command.emit(f"ShutterClose{self.shutter.idx}"))

        hl_position.addElements(
            QLabel("Position"),
            self.slider,
            self.position,
            self.stop,
            self.set,
            self.open,
            self.close,
        )

        # hl_tilt = HLayout()
        #
        # hl_tilt.addElements(QLabel("Tilt"))

        self.addElements(hl_position)
        # if has_tilt:
        #     self.addElements(hl_tilt)

        self.update_title()

    def update_title(self, state: Optional[str] = ""):
        shutter = f"Shutter {self.shutter.idx}"
        fname = f" ({self.shutter.name})" if self.shutter.name != self.shutter.idx else ""
        self.setTitle(f"{shutter}{fname}: {state}")


class ShutterControlDialog(QDialog):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(ShutterControlDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle(f"Shutter control [{device.name}]")
        self.setMinimumWidth(400)
        self.device: TasmotaDevice = device
        self.device.register(ShutterResultSchema, self.parseShutterResultSchema)

        self.widgets = {}

        vl = VLayout()

        for shutter in self.device.shutters():
            #     has_tilt = False
            #     if sht := self.device.p.get(f"SHT{key}"):
            #         has_tilt = sht.get("TiltConfig", []) != [0, 0, 0, 0, 0]
            #
            widget = ShutterWidget(shutter, False)
            widget.command.connect(self.action)
            widget.position_command.connect(self.action)

            self.widgets[f"Shutter{shutter.idx}"] = widget
            vl.addWidget(widget)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        vl.addElements(btns)
        self.setLayout(vl)

    def reject(self):
        self.device.unregister(self.parseShutterResultSchema)
        self.done(QDialog.Rejected)

    def action(self, *args):
        cmnd, payload = map(str, (args + ("",))[:2])
        self.sendCommand.emit(self.device.cmnd_topic(cmnd), payload)

    def parseShutterResultSchema(self, payload):
        for k, v in payload.dict().items():
            if (widget := self.widgets.get(k)) and v:
                # TODO: verify with inverted state if direction map is correct
                widget.update_title(DIRECTION_MAP[v['Direction']])
                widget.slider.setValue(v['Position'])
