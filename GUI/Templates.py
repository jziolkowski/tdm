from json import dumps

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QDialog, QMessageBox, QComboBox, QPushButton, QFormLayout, QLabel, QGroupBox, QWidget, \
    QDialogButtonBox, QLineEdit

from GUI import HLayout, VLayout, DictComboBox
from Util import template_adc


class TemplateDialog(QDialog):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(TemplateDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle("Template [{}]".format(device.p['FriendlyName1']))
        self.setMinimumWidth(300)
        self.device = device

        self.gb = {}
        gpios = {"255": "User"}
        gpios.update(self.device.gpios)

        btns = QDialogButtonBox(QDialogButtonBox.Cancel)
        btns.rejected.connect(self.reject)

        gbxTmpl = QGroupBox("Configure template")
        fl = QFormLayout()
        if self.device.p['Template']:
            btns.addButton(QDialogButtonBox.Save)
            btns.accepted.connect(self.accept)

            tpl = self.device.p['Template']
            print(tpl)
            self.leName = QLineEdit()
            self.leName.setMaxLength(14)
            self.leName.setText(tpl['NAME'])
            fl.addRow("Name", self.leName)

            self.gbxBase = DictComboBox(self.device.modules)
            self.gbxBase.setCurrentText(self.device.modules[str(tpl['BASE'])])
            fl.addRow("Based on", self.gbxBase)

            for i, g in enumerate([0, 1, 2, 3, 4, 5, 9, 10, 12, 13, 14, 15, 16]):
                gbx = DictComboBox(gpios)
                gbx.setCurrentText(gpios.get(str(tpl['GPIO'][i])))

                fl.addRow("<font color='{}'>GPIO{}</font>".format('red' if g in [9, 10] else 'black', g), gbx)
                self.gb[i] = gbx

            self.gbxADC = DictComboBox(template_adc)
            fl.addRow("ADC0", self.gbxADC)

        else:
            fl.addWidget(QLabel("Templates not supported.\nUpgrade firmware to versions above 6.5"))

        gbxTmpl.setLayout(fl)

        vl = VLayout()
        vl.addWidgets([gbxTmpl, btns])
        self.setLayout(vl)

    def accept(self):
        payload = {
            "NAME": self.leName.text(),
            "GPIO": [int(gpio.currentData()) for gpio in self.gb.values()],
            "FLAG": int(self.gbxADC.currentData()),
            "BASE": int(self.gbxBase.currentData()),
        }

        self.sendCommand.emit(self.device.cmnd_topic("template"), dumps(payload))
        self.sendCommand.emit(self.device.cmnd_topic("modules"), "")
        QMessageBox.information(self, "Template saved", "Template configuration saved.")
        self.done(QDialog.Accepted)
