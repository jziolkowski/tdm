from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QMessageBox, QFormLayout, QLabel, QGroupBox, QDialogButtonBox

from GUI import VLayout, DictComboBox


class GPIODialog(QDialog):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(GPIODialog, self).__init__(*args, **kwargs)
        self.setWindowTitle("GPIO [{}]".format(device.p['FriendlyName1']))
        self.setMinimumWidth(300)
        self.device = device

        self.gb = {}

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)

        gbxGPIO = QGroupBox("Select GPIO")
        fl = QFormLayout()
        if self.device.gpio:
            btns.addButton(QDialogButtonBox.Save)
            btns.accepted.connect(self.accept)

            for gp_name, gp_id in self.device.gpio.items():
                gb = DictComboBox(self.device.gpios)
                gb.setCurrentText(self.device.gpios[gp_id])
                self.gb[gp_name] = gb
                fl.addRow(gp_name, gb)
        else:
            fl.addWidget(QLabel("No configurable GPIOs"))
        gbxGPIO.setLayout(fl)

        vl = VLayout()
        vl.addWidgets([gbxGPIO, btns])
        self.setLayout(vl)

    def accept(self):
        payload = ["{} {}".format(k, gb.currentData()) for k, gb in self.gb.items()]
        self.sendCommand.emit(self.device.cmnd_topic("backlog"), "; ".join(payload))
        QMessageBox.information(self, "GPIO saved", "Device will restart.")
        self.done(QDialog.Accepted)
