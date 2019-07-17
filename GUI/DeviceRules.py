from json import loads, JSONDecodeError

from PyQt5.QtCore import QSize, QSettings, QDir, pyqtSlot, Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QTableWidget, QHeaderView, QTableWidgetItem, QPushButton, QLabel, QWidget, \
    QMessageBox, QComboBox, QCheckBox, QPlainTextEdit, QGroupBox, QListWidget

from GUI import VLayout, HLayout, Toolbar, CheckableAction, GroupBoxV, GroupBoxH


class DeviceRulesWidget(QWidget):

    def __init__(self, device, *args, **kwargs):
        super(DeviceRulesWidget, self).__init__(*args, **kwargs)
        self.device = device
        self.setWindowTitle("Rules [{}]".format(self.device.p['FriendlyName'][0]))

        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll)
        self.poll_timer.start(1000)

        tb = Toolbar(iconsize=24, label_position=Qt.ToolButtonTextBesideIcon)
        vl = VLayout(margin=0, spacing=0)

        self.cbRule = QComboBox()
        self.cbRule.setMinimumWidth(100)
        self.cbRule.addItems(["Rule{}".format(nr + 1) for nr in range(3)])
        self.cbRule.currentTextChanged.connect(self.load_rule)

        tb.addWidget(self.cbRule)

        self.actEnabled = CheckableAction("Enabled")
        self.actOnce = CheckableAction("Once")
        self.actStopOnError = CheckableAction("Stop on error")
        tb.addActions([self.actEnabled, self.actOnce, self.actStopOnError])

        tb.addSeparator()
        self.actReload = tb.addAction(QIcon("GUI/icons/restart.png"), "Reload")
        self.actClear = tb.addAction("Clear")
        self.actUpload = tb.addAction("Upload")

        tb.addSeparator()
        self.actLoad = tb.addAction("Load...")
        self.actSave = tb.addAction("Save...")

        vl.addWidget(tb)

        hl = HLayout(margin=[3, 0, 0, 0])

        self.gbTriggers = GroupBoxV("Triggers")
        self.triggers = QListWidget()
        self.triggers.addItems(["Button1#State", "Power1#State", "Rules#Timer"])
        self.triggers.setAlternatingRowColors(True)
        self.gbTriggers.addWidget(self.triggers)

        self.gbEditor = GroupBoxV("Rule editor")
        self.editor = QPlainTextEdit()
        self.gbEditor.addWidget(self.editor)

        hl.addWidgets([self.gbTriggers, self.gbEditor])

        vl_helpers = VLayout(margin=[0, 0, 3, 0])

        ###### Polling
        self.gbPolling = GroupBoxH("Automatic polling")
        self.pbPollVars = QPushButton("VARs")
        self.pbPollVars.setCheckable(True)
        self.pbPollMems = QPushButton("MEMs")
        self.pbPollMems.setCheckable(True)
        self.pbPollRTs = QPushButton("RuleTimers")
        self.pbPollRTs.setCheckable(True)

        self.gbPolling.addWidgets([self.pbPollVars, self.pbPollMems, self.pbPollRTs])

        ###### VARS
        self.gbVars = GroupBoxV("VARs")
        self.vars = QListWidget()
        self.vars.setAlternatingRowColors(True)
        self.vars.addItems(["VAR{}: ".format(i) for i in range(1, 6)])
        self.gbVars.addWidget(self.vars)

        ###### MEMS
        self.gbMems = GroupBoxV("MEMs")
        self.mems = QListWidget()
        self.mems.setAlternatingRowColors(True)
        self.mems.addItems(["MEM{}: ".format(i) for i in range(1, 6)])
        self.gbMems.addWidget(self.mems)

        ###### RuleTimers
        self.gbRTs = GroupBoxV("Rule timers")
        self.rts = QListWidget()
        self.rts.setAlternatingRowColors(True)
        self.rts.addItems(["RuleTimer{}: ".format(i) for i in range(1, 9)])
        self.gbRTs.addWidget(self.rts)

        vl_helpers.addWidgets([self.gbPolling, self.gbVars, self.gbMems, self.gbRTs])
        hl.addLayout(vl_helpers)
        hl.setStretch(0, 1)
        hl.setStretch(1, 3)
        hl.setStretch(2, 1)

        vl.addLayout(hl)
        self.setLayout(vl)

        self.load_rule("Rule1")

    def load_rule(self, text):
        print(text)

    def poll(self):
        if self.pbPollVars.isChecked():
            print('var')

        if self.pbPollMems.isChecked():
            print('mem')

        if self.pbPollRTs.isChecked():
            print('rt')

    parse_message = pyqtSlot(str, str)
    def parse_message(self, topic, msg):
        if self.device.matches(topic):
            if self.device.reply == "RESULT":
                try:
                    payload = loads(msg)
                    first = list(payload)[0]

                    if first.startswith('Rule'):
                        print(payload)

                except JSONDecodeError as e:
                    QMessageBox.critical(self, "Rule loading error", "Can't load the rule from device.\n{}".format(e))


