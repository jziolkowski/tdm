from json import loads, JSONDecodeError

from PyQt5.QtCore import QSize, QSettings, QDir, pyqtSlot, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QSyntaxHighlighter, QTextCharFormat, QColor
from PyQt5.QtWidgets import QDialog, QTableWidget, QHeaderView, QTableWidgetItem, QPushButton, QLabel, QWidget, \
    QMessageBox, QComboBox, QCheckBox, QPlainTextEdit, QGroupBox, QListWidget, QInputDialog

from GUI import VLayout, HLayout, Toolbar, CheckableAction, GroupBoxV, GroupBoxH

import re

class DeviceRulesWidget(QWidget):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(DeviceRulesWidget, self).__init__(*args, **kwargs)
        self.device = device
        self.setWindowTitle("Rules [{}]".format(self.device.p['FriendlyName'][0]))

        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll)
        self.poll_timer.start(1000)

        self.vars = ['', '', '', '', '']
        self.var = None

        self.mem = None
        self.rt = None

        fnt_mono = QFont("asd")
        fnt_mono.setStyleHint(QFont.Monospace)

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
        self.editor.setFont(fnt_mono)
        self.editor.setPlaceholderText("loading...")
        self.gbEditor.addWidget(self.editor)

        hl.addWidgets([self.gbTriggers, self.gbEditor])

        self.rules_hl = RuleHighLighter(self.editor.document())

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
        self.lwVars = QListWidget()
        self.lwVars.setAlternatingRowColors(True)
        self.lwVars.addItems(["VAR{}: loading...".format(i) for i in range(1, 6)])
        self.lwVars.clicked.connect(self.select_var)
        self.lwVars.doubleClicked.connect(self.set_var)
        self.gbVars.addWidget(self.lwVars)

        ###### MEMS
        self.gbMems = GroupBoxV("MEMs")
        self.mems = QListWidget()
        self.mems.setAlternatingRowColors(True)
        self.mems.addItems(["MEM{}: loading...".format(i) for i in range(1, 6)])
        self.mems.clicked.connect(self.select_mem)
        self.gbMems.addWidget(self.mems)

        ###### RuleTimers
        self.gbRTs = GroupBoxV("Rule timers")
        self.rts = QListWidget()
        self.rts.setAlternatingRowColors(True)
        self.rts.addItems(["RuleTimer{}: loading...".format(i) for i in range(1, 9)])
        self.rts.clicked.connect(self.select_rt)
        self.gbRTs.addWidget(self.rts)

        vl_helpers.addWidgets([self.gbPolling, self.gbVars, self.gbMems, self.gbRTs])
        hl.addLayout(vl_helpers)
        hl.setStretch(0, 1)
        hl.setStretch(1, 3)
        hl.setStretch(2, 1)

        vl.addLayout(hl)
        self.setLayout(vl)

    def load_rule(self, text):
        self.sendCommand.emit(self.device.cmnd_topic(text), "")

    def poll(self):
        if self.pbPollVars.isChecked():
            self.sendCommand.emit(self.device.cmnd_topic("backlog"), "var1; var2; var3; var4; var5")

        if self.pbPollMems.isChecked():
            self.sendCommand.emit(self.device.cmnd_topic("backlog"), "mem1; mem2; mem3; mem4; mem5")

        if self.pbPollRTs.isChecked():
            self.sendCommand.emit(self.device.cmnd_topic("ruletimer"), "")

    def select_var(self, idx):
        self.var = idx.row()

    def set_var(self, idx):
        curr = self.vars[self.var]
        new, ok = QInputDialog.getText(self, "Set VAR", "Set VAR{} value. Empty to clear.".format(self.var+1), text=curr)
        if ok:
            if new == '':
                new = '"'
            self.sendCommand.emit(self.device.cmnd_topic("var{}".format(self.var+1)), new)

    def select_mem(self, idx):
        self.mem = idx.row()

    def select_rt(self, idx):
        self.rt = idx.row()

    parse_message = pyqtSlot(str, str)
    def parse_message(self, topic, msg):
        if self.device.matches(topic):
            if self.device.reply == "RESULT":
                try:
                    payload = loads(msg)
                    first = list(payload)[0]

                    if first.startswith('Rule'):
                        self.editor.setPlainText(payload['Rules'].replace(" on ", "\non ").replace(" do ", " do\n ").replace(" endon", "\nendon ").rstrip(" "))

                    elif first.startswith('Var'):
                        row = int(first.replace("Var", ""))-1
                        self.lwVars.item(row).setText("VAR{}: {}".format(row+1, payload[first]))
                        self.vars[row] = payload[first]

                    elif first == 'T1':
                        for i, rt in enumerate(payload.keys()):
                            self.rts.item(i).setText("RuleTimer{}: {}".format(i+1, payload[rt]))

                except JSONDecodeError as e:
                    QMessageBox.critical(self, "Rule loading error", "Can't load the rule from device.\n{}".format(e))


class RuleHighLighter(QSyntaxHighlighter):
    control = QTextCharFormat()
    control.setForeground(QColor("#fa8d33"))

    trigger = QTextCharFormat()
    trigger.setForeground(QColor("#399ee6"))

    command = QTextCharFormat()
    command.setBackground(QColor("red"))

    control_words = ["on", "do", "endon"]

    def __init__(self, document):
        QSyntaxHighlighter.__init__(self, document)

        rules = []
        rules += [(r'(?:^|\s+)(%s)(?:\s+|$)' % cw, self.control) for cw in self.control_words]

        rules += [
            (r'\s+(.*#.*)\s+do', self.trigger),
            # (r'(?:do^\s+|do\s+)(.*)(?:\s+endon|\nendon)', self.command),
            (r'do\r\n\s+(.*)', self.command),
        ]
        self.rules = [(re.compile(pat, re.IGNORECASE), fmt) for (pat, fmt) in rules]

    def highlightBlock(self, text):
        print(self.document().toRawText())
        for exp, fmt in self.rules:
            for fi in re.finditer(exp, text):
                self.setFormat(fi.start(1), fi.end(1)-fi.start(1), fmt)
                print(fi.re, fi.groups(), fi.start(1), fi.end(1), fi.end(1)-fi.start(1))
