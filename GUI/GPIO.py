from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QDialog, QMessageBox, QComboBox, QPushButton, QFormLayout, QLabel, QGroupBox, QWidget, \
    QDialogButtonBox

from GUI import HLayout, VLayout


class GPIODialog(QDialog):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(GPIODialog, self).__init__(*args, **kwargs)
        self.setWindowTitle("GPIO [{}]".format(device.p['FriendlyName'][0]))
        self.setMinimumWidth(300)
        self.device = device

        self.gb = {}
        gpios = self.device.gpios()

        gbxGPIO = QGroupBox("Select GPIO")
        fl = QFormLayout()
        for k, v in self.device.gpio.items():
            if v != "Not supported":
                gb = QComboBox()
                gb.addItems(gpios)
                gb.setCurrentText(v)
                self.gb[k] = gb
                fl.addRow(k, gb)
            else:
                fl.addWidget(QLabel("No configurable GPIOs"))
        gbxGPIO.setLayout(fl)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        vl = VLayout()
        vl.addWidgets([gbxGPIO, btns])
        self.setLayout(vl)

    def accept(self):
        payload = ["{} {}".format(k, gb.currentText().split(" ")[0]) for k, gb in self.gb.items()]
        self.sendCommand.emit(self.device.cmnd_topic("backlog"), "; ".join(payload))
        QMessageBox.information(self, "GPIO saved", "Device will restart.")
        self.done(QDialog.Accepted)
