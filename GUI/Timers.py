import logging
from json import loads, JSONDecodeError, dumps

from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt, QTime
from PyQt5.QtWidgets import QDialog, QMessageBox, QComboBox, QCheckBox, QButtonGroup, QRadioButton, QTimeEdit, QLabel, \
    QDialogButtonBox

from GUI import VLayout, GroupBoxV, HLayout, GroupBoxH

# TODO: make time +/- default disabled
# TODO: check disabling AM/PM suffix in time before/after
# TODO: reset time above/after when switching away from 'Time'

class TimersDialog(QDialog):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(TimersDialog, self).__init__(*args, **kwargs)
        self.device = device
        self.timers = {}
        self.setWindowTitle("Timers [{}]".format(self.device.p['FriendlyName1']))

        vl = VLayout()

        self.gbTimers = GroupBoxV("Enabled", spacing=5)
        self.gbTimers.setCheckable(True)
        self.gbTimers.toggled.connect(self.toggleTimers)

        self.cbTimer = QComboBox()
        self.cbTimer.addItems(["Timer{}".format(nr + 1) for nr in range(16)])
        self.cbTimer.currentTextChanged.connect(self.loadTimer)

        hl_tmr_arm_rpt = HLayout(0)
        self.cbTimerArm = QCheckBox("Arm")
        self.cbTimerArm.clicked.connect(lambda x: self.describeTimer())
        self.cbTimerRpt = QCheckBox("Repeat")
        self.cbTimerRpt.clicked.connect(lambda x: self.describeTimer())
        hl_tmr_arm_rpt.addWidgets([self.cbTimerArm, self.cbTimerRpt])

        hl_tmr_out_act = HLayout(0)
        self.cbxTimerOut = QComboBox()
        self.cbxTimerOut.addItems(self.device.power().keys())
        self.cbxTimerOut.currentIndexChanged.connect(lambda x: self.describeTimer())
        self.cbxTimerAction = QComboBox()
        self.cbxTimerAction.addItems(["Off", "On", "Toggle", "Rule"])
        self.cbxTimerAction.currentIndexChanged.connect(lambda x: self.describeTimer())
        hl_tmr_out_act.addWidgets([self.cbxTimerOut, self.cbxTimerAction])

        self.TimerMode = QButtonGroup()
        rbTime = QRadioButton("Time")
        rbSunrise = QRadioButton("Sunrise ({})".format(self.device.p['Sunrise']))
        rbSunset = QRadioButton("Sunset ({})".format(self.device.p['Sunset']))
        self.TimerMode.addButton(rbTime, 0)
        self.TimerMode.addButton(rbSunrise, 1)
        self.TimerMode.addButton(rbSunset, 2)
        self.TimerMode.buttonClicked.connect(lambda x: self.describeTimer())
        gbTimerMode = GroupBoxH("Mode")
        gbTimerMode.addWidgets(self.TimerMode.buttons())

        hl_tmr_time = HLayout(0)
        self.cbxTimerPM = QComboBox()
        self.cbxTimerPM.addItems(["+", "-"])
        self.cbxTimerPM.currentIndexChanged.connect(lambda x: self.describeTimer())

        self.TimerMode.buttonClicked[int].connect(lambda x: self.cbxTimerPM.setEnabled(x != 0))
        self.teTimerTime = QTimeEdit()
        self.teTimerTime.setButtonSymbols(QTimeEdit.NoButtons)
        self.teTimerTime.setAlignment(Qt.AlignCenter)
        self.teTimerTime.timeChanged.connect(lambda x: self.describeTimer())

        lbWnd = QLabel("Window:")
        lbWnd.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.cbxTimerWnd = QComboBox()
        self.cbxTimerWnd.addItems([str(x).zfill(2) for x in range(0, 16)])
        self.cbxTimerWnd.currentIndexChanged.connect(lambda x: self.describeTimer())

        hl_tmr_days = HLayout(0)
        self.TimerWeekday = QButtonGroup()
        self.TimerWeekday.setExclusive(False)
        for i, wd in enumerate(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
            cb = QCheckBox(wd)
            cb.clicked.connect(lambda x: self.describeTimer())
            hl_tmr_days.addWidget(cb)
            self.TimerWeekday.addButton(cb, i)

        gbTimerDesc = GroupBoxV("Timer description", 5)
        gbTimerDesc.setMinimumHeight(200)
        self.lbTimerDesc = QLabel()
        self.lbTimerDesc.setAlignment(Qt.AlignCenter)
        self.lbTimerDesc.setWordWrap(True)
        gbTimerDesc.layout().addWidget(self.lbTimerDesc)

        hl_tmr_time.addWidgets([self.cbxTimerPM, self.teTimerTime, lbWnd, self.cbxTimerWnd])

        self.gbTimers.layout().addWidget(self.cbTimer)
        self.gbTimers.layout().addLayout(hl_tmr_arm_rpt)
        self.gbTimers.layout().addLayout(hl_tmr_out_act)
        self.gbTimers.layout().addWidget(gbTimerMode)
        self.gbTimers.layout().addLayout(hl_tmr_time)
        self.gbTimers.layout().addLayout(hl_tmr_days)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        reload = btns.addButton("Reload", QDialogButtonBox.ResetRole)

        btns.accepted.connect(self.saveTimer)
        btns.rejected.connect(self.reject)
        reload.clicked.connect(lambda: self.loadTimer(self.cbTimer.currentText()))

        vl.addWidgets([self.gbTimers, gbTimerDesc, btns])
        self.setLayout(vl)

    def toggleTimers(self, state):
        self.sendCommand.emit(self.device.cmnd_topic('timers'), "ON" if state else "OFF")

    def loadTimer(self, timer=""):
        if not timer:
            timer = self.cbTimer.currentText()
        payload = self.timers[timer]

        if payload:
            self.blockSignals(True)
            self.cbTimerArm.setChecked(payload['Arm'])
            self.cbTimerRpt.setChecked(payload['Repeat'])
            self.cbxTimerAction.setCurrentIndex(payload['Action'])

            output = payload.get('Output')
            if output:
                self.cbxTimerOut.setEnabled(True)
                self.cbxTimerOut.setCurrentIndex(output - 1)
            else:
                self.cbxTimerOut.setEnabled(False)

            mode = payload.get('Mode', 0)
            self.TimerMode.button(mode).setChecked(True)

            h, m = map(int, payload["Time"].split(":"))
            if h < 0:
                self.cbxTimerPM.setCurrentText("-")
                h *= -1
            self.teTimerTime.setTime(QTime(h, m))
            self.cbxTimerWnd.setCurrentText(str(payload['Window']).zfill(2))
            for wd, v in enumerate(payload['Days']):
                self.TimerWeekday.button(wd).setChecked(int(v))

            self.blockSignals(False)
            self.describeTimer()

    def describeTimer(self):
        if self.cbTimerArm.isChecked():
            desc = {'days': '', 'repeat': '', 'timer': self.cbTimer.currentText().upper()}
            repeat = self.cbTimerRpt.isChecked()
            out = self.cbxTimerOut.currentText()
            act = self.cbxTimerAction.currentText()
            mode = self.TimerMode.checkedId()
            pm = self.cbxTimerPM.currentText()
            time = self.teTimerTime.time()
            wnd = int(self.cbxTimerWnd.currentText()) * 60

            if mode == 0:
                if wnd == 0:
                    desc['time'] = "at {}".format(time.toString("hh:mm"))
                else:
                    desc['time'] = "somewhere between {} and {}".format(time.addSecs(wnd * -1).toString("hh:mm"), time.addSecs(wnd).toString("hh:mm"))
            else:
                prefix = "before" if pm == "-" else "after"
                mode_desc = "sunrise" if mode == 1 else "sunset"
                window = "somewhere in a {} minute window centered around ".format(wnd // 30)
                desc['time'] = "{}h{}m {} {}".format(time.hour(), time.minute(), prefix, mode_desc)

                if wnd > 0:
                    desc['time'] = window + desc['time']

            if repeat:
                day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
                days = [cb.isChecked() for cb in self.TimerWeekday.buttons()]
                if days.count(True) == 7:
                    desc['days'] = "everyday"
                else:
                    days_list = [day_names[d] for d in range(7) if days[d]]
                    desc['days'] = "on every {}".format(", ".join(days_list))
            else:
                desc['repeat'] = "only ONCE"

            if act == "Rule":
                desc['action'] = "trigger clock#Timer={}".format(self.cbTimer.currentIndex() + 1)
                text = "{timer} will {action} {time} {days} {repeat}".format(**desc)

            elif self.cbxTimerOut.count() > 0:

                if act == "Toggle":
                    desc['action'] = "TOGGLE {}".format(out.upper())
                else:
                    desc['action'] = "set {} to {}".format(out.upper(), act.upper())

                text = "{timer} will {action} {time} {days} {repeat}".format(**desc)
            else:
                text = "{timer} will do nothing because there are no relays configured.".format(**desc)

            self.lbTimerDesc.setText(text)

        else:
            self.lbTimerDesc.setText("{} is not armed, it will do nothing.".format(self.cbTimer.currentText().upper()))

    def saveTimer(self):
        payload = {
            "Arm": int(self.cbTimerArm.isChecked()),
            "Mode": self.TimerMode.checkedId(),
            "Time": self.teTimerTime.time().toString("hh:mm"),
            "Window": self.cbxTimerWnd.currentIndex(),
            "Days": "".join([str(int(cb.isChecked())) for cb in self.TimerWeekday.buttons()]),
            "Repeat": int(self.cbTimerRpt.isChecked()),
            "Output": self.cbxTimerOut.currentIndex()+1,
            "Action": self.cbxTimerAction.currentIndex()}
        self.sendCommand.emit(self.device.cmnd_topic(self.cbTimer.currentText()), dumps(payload))
        QMessageBox.information(self, "Timer saved", "{} data sent to device.".format(self.cbTimer.currentText()))

    @pyqtSlot(str, str)
    def parseMessage(self, topic, msg):
        if self.device.matches(topic):
            if self.device.reply == "RESULT" or self.device.reply == "TIMERS":
                try:
                    payload = loads(msg)
                    first = list(payload)[0]

                except JSONDecodeError as e:
                    error = "Timer loading error", "Can't load the timer from device.\n{}".format(e)
                    logging.critical(error)
                    QMessageBox.critical(self, error)

                else:
                    if first == 'Timers':
                        self.gbTimers.setChecked(payload[first] == "ON")

                    elif first.startswith('Timers'):
                        self.timers.update(payload[first])

                    if first == 'Timers4':
                        self.loadTimer(self.cbTimer.currentText())

