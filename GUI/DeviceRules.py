from json import loads, JSONDecodeError

from PyQt5.QtCore import QSize, QSettings, QDir, pyqtSlot, Qt
from PyQt5.QtWidgets import QDialog, QTableWidget, QHeaderView, QTableWidgetItem, QPushButton, QLabel, QWidget, \
    QMessageBox, QComboBox, QCheckBox

from GUI import VLayout, HLayout


class DeviceRulesWidget(QWidget):

    def __init__(self, device, *args, **kwargs):
        super(DeviceRulesWidget, self).__init__(*args, **kwargs)
        self.device = device
        self.setWindowTitle("Rules [{}]".format(self.device.p['FriendlyName'][0]))

        vl = VLayout()

        self.cbRule = QComboBox()
        self.cbRule.addItems(["Rule{}".format(nr + 1) for nr in range(3)])

        self.cbEnabled = QCheckBox("Enabled")
        self.cbOnce = QCheckBox("Once")
        self.cbStopOnError = QCheckBox("Stop on error")
        self.counter = QLabel("511 left")
        self.counter.setAlignment(Qt.AlignCenter)
        self.pbClear = QPushButton("Clear")
        self.pbSave = QPushButton("Save")

        hl_func = HLayout(0)
        hl_func.addWidgets(
            [self.cbRule, self.cbEnabled, self.cbOnce, self.cbStopOnError, self.pbClear, self.pbSave, self.counter])

        vl.addLayout(hl_func)

        vl.addStretch(1)
        self.setLayout(vl)

    parse_message = pyqtSlot(str, str)
    def parse_message(self, topic, msg):
        if self.device.matches(topic):
            if self.device.reply == "RESULT":
                try:
                    payload = loads(msg)
                    first = list(payload)[0]

                    if first.startswith('Rule'):
                        self.cbEnabled.setChecked(payload.get(first) == "ON")
                        self.cbOnce.setChecked(payload.get('Once') == "ON")
                        self.cbStopOnError.setChecked(payload.get('StopOnError') == "ON")

                except JSONDecodeError as e:
                    QMessageBox.critical(self, "Rule loading error", "Can't load the rule from device.\n{}".format(e))


