from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QDialog, QMessageBox, QComboBox, QPushButton, QFormLayout, QLabel, QGroupBox, QWidget, \
    QDialogButtonBox, QLineEdit

from GUI import HLayout, VLayout


class TemplateDialog(QDialog):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(TemplateDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle("Template [{}]".format(device.p['FriendlyName'][0]))
        self.setMinimumWidth(300)
        self.device = device

        self.gb = {}
        gpios = ["0 (None)", "255 (USER)"] + self.device.gpios()

        gbxTmpl = QGroupBox("Configure template")
        fl = QFormLayout()
        if self.device.p['Template']:
            tpl = self.device.p['Template']
            self.leName = QLineEdit()
            self.leName.setText(tpl['NAME'])
            fl.addRow("Name", self.leName)

            self.gbxBase = QComboBox()
            self.gbxBase.addItems(self.device.modules())
            fl.addRow("Base", self.gbxBase)

            for i, g in enumerate([0, 1, 2, 3, 4, 5, 9, 10, 12, 13, 14, 15, 16]):
                current_item = None
                gbx = QComboBox()
                for itm in gpios:
                    gbx.addItem(itm)
                    itm_split = itm.split(" ")[0]
                    if itm_split == tpl['GPIO'][i]:
                        current_item = i
                gbx.setCurrentIndex(current_item)

                fl.addRow("<font color='{}'>GPIO{}</font>".format('red' if g in [9, 10] else 'black', i), gbx)
                self.gb[i] = gbx

        else:
            fl.addWidget(QLabel("Templates not supported.\nUpgrade firmware to versions above 6.5"))


        # for k, v in self.device.gpio.items():
        #     if v != "Not supported":
        #         gb = QComboBox()
        #         gb.addItems(gpios)
        #         gb.setCurrentText(v)
        #         self.gb[k] = gb
        #         fl.addRow(k, gb)
        #     else:
        #         fl.addWidget(QLabel("No configurable GPIOs"))
        gbxTmpl.setLayout(fl)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        vl = VLayout()
        vl.addWidgets([gbxTmpl, btns])
        self.setLayout(vl)

    def accept(self):
        # payload = ["{} {}".format(k, gb.currentText().split(" ")[0]) for k, gb in self.gb.items()]
        # self.sendCommand.emit(self.device.cmnd_topic("backlog"), "; ".join(payload))
        QMessageBox.information(self, "Template saved", "Device will restart.")
        self.done(QDialog.Accepted)
