from PyQt5.QtCore import pyqtSignal, Qt, QUrl
from PyQt5.QtWidgets import QDialog, QMessageBox, QComboBox, QPushButton, QFormLayout, QLabel, QGroupBox, QWidget, \
    QDialogButtonBox, QTableWidget, QTableWidgetItem

from GUI import HLayout, VLayout, DictComboBox, GroupBoxV, SpinBox, SetOption


class ButtonsDialog(QDialog):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(ButtonsDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle("Buttons settings [{}]".format(device.p['FriendlyName1']))
        self.setMinimumWidth(300)
        self.device = device

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)

        vl = VLayout()

        # self.so11 = SetOption(11, "Swap button single and double press functionality\n"
        #                           "0: Disabled (default)\n"
        #                           "1: Enabled")
        # self.so11.editor.setCurrentText(str(self.device.setoption(11)))
        #
        # self.so13 = SetOption(13, "Allow immediate action on single button press\n"
        #                           "0: single, multi-press and hold button actions (default)\n"
        #                           "1: only single press action for immediate response.\n"
        #                           "Disable by holding for 4 x button hold time (see SetOption32)")
        # self.so13.editor.setCurrentText(str(self.device.setoption(13)))
        #
        # self.so32 = SetOption(32, "Number of 0.1 seconds to hold button before sending HOLD action message\ndefault: 40")
        # self.so32.editor.setMinimum(1)
        # self.so32.editor.setMaximum(100)
        # self.so32.editor.setValue(self.device.setoption(32))
        #
        # vl.addWidgets([self.so11, self.so13, self.so32, btns])
        self.config = QTableWidget(3, 2)

        self.config.setItem(0, 0, QTableWidgetItem("SetOption11"))
        self.config.setItem(1, 0, QTableWidgetItem("SetOption13"))
        self.config.setItem(2, 0, QTableWidgetItem("SetOption32"))

        # for row in range(self.config.rowCount()):
        #     self.config.item(row, 0).setFlags(QTableWidgetItem.)

        vl.addWidgets([self.config, btns])
        self.setLayout(vl)
        

    # def accept(self):
    #     self.sendCommand.emit(self.device.cmnd_topic("module"), self.gb.currentData())
    #     QMessageBox.information(self, "Module saved", "Device will restart.")
    #     self.done(QDialog.Accepted)
