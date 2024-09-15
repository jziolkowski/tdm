from json import dumps

from PyQt5.QtCore import Qt, QTime, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QRadioButton,
    QTimeEdit,
)

from tdmgr.GUI.widgets import GroupBoxH, GroupBoxV, HLayout, VLayout
from tdmgr.mqtt import Message
from tdmgr.tasmota.device import TasmotaDevice


class TimersDialog(QDialog):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super(TimersDialog, self).__init__(*args, **kwargs)
        self.device: TasmotaDevice = device
        self.timers = {}
        self.armKey = "Arm"
        self.setWindowTitle(f"Timers [{self.device.name}]")

        vl = VLayout()

        self.gbTimers = GroupBoxV("Enabled", spacing=5)
        self.gbTimers.setCheckable(True)
        self.gbTimers.toggled.connect(self.toggleTimers)

        self.cbTimer = QComboBox()
        self.cbTimer.addItems([f"Timer{nr + 1}" for nr in range(16)])
        self.cbTimer.currentTextChanged.connect(self.loadTimer)

        hl_tmr_arm_rpt = HLayout(0)
        self.cbTimerArm = QCheckBox("Arm")
        self.cbTimerArm.clicked.connect(lambda x: self.describeTimer())
        self.cbTimerRpt = QCheckBox("Repeat")
        self.cbTimerRpt.clicked.connect(lambda x: self.describeTimer())
        hl_tmr_arm_rpt.addElements(self.cbTimerArm, self.cbTimerRpt)

        hl_tmr_out_act = HLayout(0)
        self.cbxTimerOut = QComboBox()
        self.cbxTimerOut.addItems(map(str, self.device.power().keys()))
        self.cbxTimerOut.currentIndexChanged.connect(lambda x: self.describeTimer())
        self.cbxTimerAction = QComboBox()
        self.cbxTimerAction.addItems(["Off", "On", "Toggle", "Rule"])
        self.cbxTimerAction.currentIndexChanged.connect(lambda x: self.describeTimer())
        hl_tmr_out_act.addElements(self.cbxTimerOut, self.cbxTimerAction)

        self.TimerMode = QButtonGroup()
        rbtns = [
            QRadioButton("Time"),
            QRadioButton(f"Sunrise ({self.device.p['Sunrise']})"),
            QRadioButton(f"Sunset ({self.device.p['Sunset']})"),
        ]
        for id, btn in enumerate(rbtns):
            self.TimerMode.addButton(btn, id)
        self.TimerMode.buttonClicked.connect(lambda x: self.describeTimer())
        gbTimerMode = GroupBoxH("Mode")
        gbTimerMode.addElements(*self.TimerMode.buttons())

        hl_tmr_time = HLayout(0)
        self.cbxTimerPM = QComboBox()
        self.cbxTimerPM.addItems(["+", "-"])
        self.cbxTimerPM.currentIndexChanged.connect(lambda x: self.describeTimer())
        self.cbxTimerPM.setEnabled(False)

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

        hl_tmr_time.addElements(self.cbxTimerPM, self.teTimerTime, lbWnd, self.cbxTimerWnd)

        self.gbTimers.addElements(
            self.cbTimer, hl_tmr_arm_rpt, hl_tmr_out_act, gbTimerMode, hl_tmr_time, hl_tmr_days
        )

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        reload = btns.addButton("Reload", QDialogButtonBox.ResetRole)

        btns.accepted.connect(self.saveTimer)
        btns.rejected.connect(self.reject)
        reload.clicked.connect(lambda: self.loadTimer(self.cbTimer.currentText()))

        vl.addElements(self.gbTimers, gbTimerDesc, btns)
        self.setLayout(vl)

    def toggleTimers(self, state):
        self.sendCommand.emit(self.device.cmnd_topic("timers"), "ON" if state else "OFF")

    def loadTimer(self, timer=""):
        if not timer:
            timer = self.cbTimer.currentText()
        payload = self.timers[timer]

        if payload:
            self.blockSignals(True)
            if "Enable" in payload:
                self.cbTimerArm.setChecked(payload["Enable"])
                self.armKey = "Enable"
            else:
                self.cbTimerArm.setChecked(payload["Arm"])
                self.armKey = "Arm"
            self.cbTimerRpt.setChecked(payload["Repeat"])
            self.cbxTimerAction.setCurrentIndex(payload["Action"])

            output = payload.get("Output")
            if output:
                self.cbxTimerOut.setEnabled(True)
                self.cbxTimerOut.setCurrentIndex(output - 1)
            else:
                self.cbxTimerOut.setEnabled(False)

            mode = payload.get("Mode", 0)
            self.TimerMode.button(mode).setChecked(True)

            h, m = map(int, payload["Time"].split(":"))
            if h < 0:
                self.cbxTimerPM.setCurrentText("-")
                h *= -1
            self.teTimerTime.setTime(QTime(h, m))
            self.cbxTimerWnd.setCurrentText(str(payload["Window"]).zfill(2))
            for wd, v in enumerate(payload["Days"]):
                self.TimerWeekday.button(wd).setChecked(int(v))

            self.blockSignals(False)
            self.describeTimer()

    def describeTimer(self):
        if self.cbTimerArm.isChecked():
            desc = {"days": "", "repeat": "", "timer": self.cbTimer.currentText().upper()}
            repeat = self.cbTimerRpt.isChecked()
            out = self.cbxTimerOut.currentText()
            act = self.cbxTimerAction.currentText()
            mode = self.TimerMode.checkedId()
            pm = self.cbxTimerPM.currentText()
            time = self.teTimerTime.time()
            wnd = int(self.cbxTimerWnd.currentText()) * 60

            if mode == 0:
                if wnd == 0:
                    desc["time"] = f"at {time.toString('hh:mm')}"
                else:
                    desc["time"] = (
                        f"somewhere between {time.addSecs(wnd * -1).toString('hh:mm')} "
                        f"and {time.addSecs(wnd).toString('hh:mm')}"
                    )
            else:
                prefix = "before" if pm == "-" else "after"
                mode_desc = "sunrise" if mode == 1 else "sunset"
                window = f"somewhere in a {wnd // 30} minute window centered around "
                desc["time"] = f"{time.hour()}h{time.minute()}m {prefix} {mode_desc}"

                if wnd > 0:
                    desc["time"] = window + desc["time"]

            if repeat:
                day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
                days = [cb.isChecked() for cb in self.TimerWeekday.buttons()]
                if days.count(True) == 7:
                    desc["days"] = "everyday"
                else:
                    days_list = [day_names[d] for d in range(7) if days[d]]
                    desc["days"] = f"on every {', '.join(days_list)}"
            else:
                desc["repeat"] = "only ONCE"

            if act == "Rule":
                desc["action"] = f"trigger clock#Timer={self.cbTimer.currentIndex() + 1}"
                text = (
                    f"{desc['timer']} will {desc['action']} {desc['time']} {desc['days']} "
                    f"{desc['repeat']}"
                )

            elif self.cbxTimerOut.count() > 0:
                if act == "Toggle":
                    desc["action"] = f"TOGGLE {out.upper()}"
                else:
                    desc["action"] = f"set {out.upper()} to {act.upper()}"

                text = (
                    f"{desc['timer']} will {desc['action']} {desc['time']} {desc['days']} "
                    f"{desc['repeat']}"
                )
            else:
                text = f"{desc['timer']} will do nothing because there are no relays configured."

            self.lbTimerDesc.setText(text)

        else:
            self.lbTimerDesc.setText(
                f"{self.cbTimer.currentText().upper()} is not armed, it will do nothing."
            )

    def saveTimer(self):
        payload = {
            self.armKey: int(self.cbTimerArm.isChecked()),
            "Mode": self.TimerMode.checkedId(),
            "Time": self.teTimerTime.time().toString("hh:mm"),
            "Window": self.cbxTimerWnd.currentIndex(),
            "Days": "".join([str(int(cb.isChecked())) for cb in self.TimerWeekday.buttons()]),
            "Repeat": int(self.cbTimerRpt.isChecked()),
            "Output": self.cbxTimerOut.currentIndex() + 1,
            "Action": self.cbxTimerAction.currentIndex(),
        }
        self.sendCommand.emit(self.device.cmnd_topic(self.cbTimer.currentText()), dumps(payload))
        QMessageBox.information(
            self, "Timer saved", f"{self.cbTimer.currentText()} data sent to device."
        )

    # TODO: use schema
    @pyqtSlot(Message)
    def parseMessage(self, msg: Message):
        """
        Tasmota < 9.4.0.5 : There are a total of 4 messages in reply to `Timers` command:
            {"Timers": "ON" }
            {"Timers1" : {"Timer1":{"Enable":0,"Mode":0,"Time":"00:00","Window":0,"Days":"0000000",
            "Repeat":0,
            "Action":0}, ....
            ...
            {"Timers4" : {"Timer13":{"Enable":0,"Mode":0,"Time":"00:00","Window":0,"Days":"0000000",
            "Repeat":0,
            "Action":0}, ....

        Tasmota >= 9.4.0.5 : There is only 1 message that covers all
            { "Timers": "ON", "Timer1":{"Enable":0,"Mode":0,"Time":"00:00","Window":0,
            "Days":"0000000","Repeat":0,
            "Action":0}, ....
        """
        if self.device.message_topic_matches_fulltopic(msg):
            if msg.is_result or msg.endpoint == "TIMERS":
                payload = msg.dict()
                all = list(payload)
                if msg.first_key == "Timers":
                    self.gbTimers.setChecked(payload[msg.first_key] == "ON")

                    if len(all) > 1:
                        payload.pop("Timers")
                        self.timers.update(payload)
                        self.loadTimer(self.cbTimer.currentText())

                elif msg.first_key.startswith("Timers"):
                    self.timers.update(payload[msg.first_key])
                    if msg.first_key == "Timers4":
                        self.loadTimer(self.cbTimer.currentText())
