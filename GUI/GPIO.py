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

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)

        gbxGPIO = QGroupBox("Select GPIO")
        fl = QFormLayout()
        if self.device.gpio:
            btns.addButton(QDialogButtonBox.Save)
            btns.accepted.connect(self.accept)

            for gp_name, gp_id in self.device.gpio.items():
                gb = QComboBox()
                for gps_id, gps_name in self.device.gpios.items():
                    gb.addItem(gps_name, gps_id)
                    if gp_id == gps_id:
                        gb.setCurrentText(gps_name)
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
