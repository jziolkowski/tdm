from copy import deepcopy
from json import loads, JSONDecodeError
import logging

from PyQt5.QtCore import QSize, QSettings, QDir, pyqtSlot, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QSyntaxHighlighter, QTextCharFormat, QColor
from PyQt5.QtWidgets import QDialog, QTableWidget, QHeaderView, QTableWidgetItem, QPushButton, QLabel, QWidget, \
    QMessageBox, QComboBox, QCheckBox, QPlainTextEdit, QGroupBox, QListWidget, QInputDialog

from GUI import VLayout, HLayout, Toolbar, CheckableAction, GroupBoxV, GroupBoxH

import re

# TODO: triggers list
# TODO: open/save rule from/to file


class RulesWidget(QWidget):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(RulesWidget, self).__init__(*args, **kwargs)
        self.device = device
        self.setWindowTitle("Rules [{}]".format(self.device.p['FriendlyName1']))

        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll)
        self.poll_timer.start(1000)

        self.vars = [''] * 16
        self.var = None

        self.mems = [''] * 16
        self.mem = None

        self.rts = [0] * 8
        self.rt = None

        fnt_mono = QFont("asd")
        fnt_mono.setStyleHint(QFont.TypeWriter)

        tb = Toolbar(iconsize=24, label_position=Qt.ToolButtonTextBesideIcon)
        vl = VLayout(margin=0, spacing=0)

        self.cbRule = QComboBox()
        self.cbRule.setMinimumWidth(100)
        self.cbRule.addItems(["Rule{}".format(nr + 1) for nr in range(3)])
        self.cbRule.currentTextChanged.connect(self.load_rule)

        tb.addWidget(self.cbRule)

        self.actEnabled = CheckableAction(QIcon(":/off.png"), "Enabled")
        self.actEnabled.triggered.connect(self.toggle_rule)

        self.actOnce = CheckableAction(QIcon(":/once.png"), "Once")
        self.actOnce.triggered.connect(self.toggle_once)

        self.actStopOnError = CheckableAction(QIcon(":/stop.png"), "Stop on error")
        self.actStopOnError.triggered.connect(self.toggle_stop)

        tb.addActions([self.actEnabled, self.actOnce, self.actStopOnError])
        self.cbRule.setFixedHeight(tb.widgetForAction(self.actEnabled).height()+1)

        self.actUpload = tb.addAction(QIcon(":/upload.png"), "Upload")
        self.actUpload.triggered.connect(self.upload_rule)

        # tb.addSeparator()
        # self.actLoad = tb.addAction(QIcon(":/open.png"), "Load...")
        # self.actSave = tb.addAction(QIcon(":/save.png"), "Save...")

        tb.addSpacer()

        self.counter = QLabel("Remaining: 511")
        tb.addWidget(self.counter)

        vl.addWidget(tb)

        hl = HLayout(margin=[3, 0, 0, 0])

        self.gbTriggers = GroupBoxV("Triggers")
        self.triggers = QListWidget()
        self.triggers.setAlternatingRowColors(True)
        self.gbTriggers.addWidget(self.triggers)

        self.gbEditor = GroupBoxV("Rule editor")
        self.editor = QPlainTextEdit()
        self.editor.setFont(fnt_mono)
        self.editor.setPlaceholderText("loading...")
        self.editor.textChanged.connect(self.update_counter)
        self.gbEditor.addWidget(self.editor)

        # hl.addWidgets([self.gbTriggers, self.gbEditor])
        hl.addWidget(self.gbEditor)

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
        # self.gbVars = GroupBoxV("VARs")
        self.lwVars = QListWidget()
        self.lwVars.setAlternatingRowColors(True)
        self.lwVars.addItems(["VAR{}: <unknown>".format(i) for i in range(1, 17)])
        self.lwVars.clicked.connect(self.select_var)
        self.lwVars.doubleClicked.connect(self.set_var)
        # self.gbVars.addWidget(self.lwVars)

        ###### MEMS
        # self.gbMems = GroupBoxV("MEMs")
        self.lwMems = QListWidget()
        self.lwMems.setAlternatingRowColors(True)
        self.lwMems.addItems(["MEM{}: <unknown>".format(i) for i in range(1, 17)])
        self.lwMems.clicked.connect(self.select_mem)
        self.lwMems.doubleClicked.connect(self.set_mem)
        # self.gbMems.addWidget(self.lwMems)

        ###### RuleTimers
        # self.gbRTs = GroupBoxV("Rule timers")
        self.lwRTs = QListWidget()
        self.lwRTs.setAlternatingRowColors(True)
        self.lwRTs.addItems(["RuleTimer{}: <unknown>".format(i) for i in range(1, 9)])
        self.lwRTs.clicked.connect(self.select_rt)
        self.lwRTs.doubleClicked.connect(self.set_rt)
        # self.gbRTs.addWidget(self.lwRTs)

        # vl_helpers.addWidgets([self.gbPolling, self.gbVars, self.gbMems, self.gbRTs])
        vl_helpers.addWidgets([self.gbPolling, self.lwVars, self.lwMems, self.lwRTs])
        vl_helpers.setStretch(1, 16)
        vl_helpers.setStretch(2, 16)
        vl_helpers.setStretch(3, 8)
        hl.addLayout(vl_helpers)
        hl.setStretch(0, 3)
        hl.setStretch(1, 1)
        # hl.setStretch(2, 1)

        vl.addLayout(hl)
        self.setLayout(vl)

    def load_rule(self, text):
        self.editor.setPlaceholderText("loading...")
        self.sendCommand.emit(self.device.cmnd_topic(text), "")

    def toggle_rule(self, state):
        self.sendCommand.emit(self.device.cmnd_topic(self.cbRule.currentText()), str(int(state)))

    def toggle_once(self, state):
        self.sendCommand.emit(self.device.cmnd_topic(self.cbRule.currentText()), str(4+int(state)))

    def toggle_stop(self, state):
        self.sendCommand.emit(self.device.cmnd_topic(self.cbRule.currentText()), str(8+int(state)))

    def clean_rule(self):
        re_spaces = re.compile(r"\s{2,}")
        rule = self.editor.toPlainText().replace("\t", " ").replace("\n", " ")
        rule = re.sub(re_spaces, ' ', rule)
        return rule

    def upload_rule(self):
        rule = self.clean_rule()
        if len(rule) == 0:
            rule = '""'
        self.sendCommand.emit(self.device.cmnd_topic(self.cbRule.currentText()), rule)

    def update_counter(self):
        self.counter.setText("Remaining: {}".format(511-len(self.clean_rule())))

    def poll(self):
        if self.pbPollVars.isChecked():
            self.sendCommand.emit(self.device.cmnd_topic("var"), "")

        if self.pbPollMems.isChecked():
            self.sendCommand.emit(self.device.cmnd_topic("mem"), "")

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

    def set_mem(self, idx):
        curr = self.mems[self.mem]
        new, ok = QInputDialog.getText(self, "Set mem", "Set mem{} value. Empty to clear.".format(self.mem+1), text=curr)
        if ok:
            if new == '':
                new = '"'
            self.sendCommand.emit(self.device.cmnd_topic("mem{}".format(self.mem+1)), new)

    def select_rt(self, idx):
        self.rt = idx.row()
        
    def set_rt(self, idx):
        curr = self.rts[self.rt]
        new, ok = QInputDialog.getInt(self, "Set ruletimer", "Set ruletimer{} value.".format(self.rt+1), value=curr)
        if ok:
            self.sendCommand.emit(self.device.cmnd_topic("ruletimer{}".format(self.rt+1)), str(new))

    def display_rule(self, payload, rule):
            rules = payload['Rules'].replace(" on ", "\non ").replace(" do ", " do\n\t").replace(" endon", "\nendon ").rstrip(" ")
            if len(rules) == 0:
                self.editor.setPlaceholderText("rule buffer is empty")
            self.editor.setPlainText(rules)

            self.actEnabled.setChecked(payload[rule] == "ON")
            self.actOnce.setChecked(payload['Once'] == 'ON')
            self.actStopOnError.setChecked(payload['StopOnError'] == 'ON')

    @pyqtSlot(str, str)
    def parseMessage(self, topic, msg):
        if self.device.matches(topic):
            payload = None
            if msg.startswith("{"):
                try:
                    payload = loads(msg)
                except JSONDecodeError as e:
                    # JSON parse exception means that most likely the rule contains an unescaped JSON payload
                    # TDM will attempt parsing using a regex instead of json.loads()
                    parsed_rule = re.match(r"{\"(?P<rule>Rule(\d))\":\"(?P<enabled>ON|OFF)\",\"Once\":\"(?P<Once>ON|OFF)\",\"StopOnError\":\"(?P<StopOnError>ON|OFF)\",\"Free\":\d+,\"Rules\":\"(?P<Rules>.*?)\"}$", msg, re.IGNORECASE)
                    # modify the resulting matchdict to follow the keys of original JSON payload
                    payload = deepcopy(parsed_rule.groupdict())
                    rule = payload.pop("rule")
                    payload[rule] = payload.pop("enabled")
                    self.display_rule(payload, rule)
                else:

                    if payload:
                        keys = list(payload.keys())
                        fk = keys[0]

                        if self.device.reply == 'RESULT' and fk == "T1" or self.device.reply == "RULETIMER":
                            for i, rt in enumerate(payload.keys()):
                                self.lwRTs.item(i).setText("RuleTimer{}: {}".format(i+1, payload[rt]))
                                self.rts[i] = payload[rt]

                        elif self.device.reply == 'RESULT' and fk.startswith("Var") or self.device.reply.startswith("VAR"):
                            for k, v in payload.items():
                                row = int(k.replace("Var", "")) - 1
                                self.lwVars.item(row).setText("VAR{}: {}".format(row + 1, v))
                                self.vars[row] = v

                        elif self.device.reply == 'RESULT' and fk.startswith("Mem") or self.device.reply.startswith("MEM"):
                            for k, v in payload.items():
                                row = int(k.replace("Mem", "")) - 1
                                self.lwMems.item(row).setText("MEM{}: {}".format(row + 1, v))
                                self.mems[row] = v

                        elif self.device.reply == 'RESULT' and fk.startswith("Rule") or self.device.reply.startswith("RULE"):
                            self.display_rule(payload, fk)


class RuleHighLighter(QSyntaxHighlighter):
    control = QTextCharFormat()
    control.setForeground(QColor("#fa8d33"))

    trigger = QTextCharFormat()
    trigger.setForeground(QColor("#399ee6"))

    command = QTextCharFormat()
    command.setBackground(QColor("red"))

    control_words = ["on", "do", "endon", "break"]

    def __init__(self, document):
        QSyntaxHighlighter.__init__(self, document)

        rules = []
        rules += [(r'(?:^|\s+)(%s)(?:\s+|$)' % cw, self.control) for cw in self.control_words]

        # TODO: make the command regex work both inline and after line break
        rules += [
            (r'\s+(.*#.*)\s+do', self.trigger),
            # (r'(?:do^\s+|do\s+)(.*)(?:\s+endon|\nendon)', self.command),
            (r'do\r\n\s+(.*)', self.command),
        ]
        self.rules = [(re.compile(pat, re.IGNORECASE), fmt) for (pat, fmt) in rules]

    def highlightBlock(self, text):
        # print(self.document().toRawText())
        for exp, fmt in self.rules:
            for fi in re.finditer(exp, text):
                self.setFormat(fi.start(1), fi.end(1)-fi.start(1), fmt)
                # print(fi.re, fi.groups(), fi.start(1), fi.end(1), fi.end(1)-fi.start(1))
