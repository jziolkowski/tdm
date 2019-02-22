from json import loads, dumps

from PyQt5.QtCore import Qt, QSettings, QTimer, QDir, QTime, QTime
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QWidget, QTabWidget, QLineEdit, QTabBar, QLabel, QComboBox, QPushButton, QFrame, \
    QTableWidget, QHeaderView, QSizePolicy, QGroupBox, QFormLayout, QSpacerItem, QTreeView, QCheckBox, QRadioButton, QButtonGroup, QTimeEdit, QLabel, \
    QListWidget, QListWidgetItem, QApplication

from GUI import VLayout, HLayout, RuleGroupBox, GroupBoxH, SpinBox, DetailLE, GroupBoxV
from Util import match_topic, modules
from Util.mqtt import MqttClient


class DevicesConfigWidget(QWidget):
    def __init__(self, parent, topic, *args, **kwargs):
        super(DevicesConfigWidget, self).__init__(*args, **kwargs)

        self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)
        self.topic = topic
        self.full_topic = self.settings.value('Devices/{}/full_topic'.format(topic))
        self.friendly_name = self.settings.value('Devices/{}/friendly_name'.format(topic))

        self.cmnd_topic = self.full_topic.replace("%topic%", self.topic).replace("%prefix%", 'cmnd')
        self.tele_topic = self.full_topic.replace("%topic%", self.topic).replace("%prefix%", 'tele') + "+"
        self.stat_topic = self.full_topic.replace("%topic%", self.topic).replace("%prefix%", 'stat') + "+"

        self.setWindowTitle(self.friendly_name)

        self.mqtt = MqttClient()

        self.module = None
        self.modules = []

        self.gpios = []
        self.supported_gpios = []
        self.current_gpios = {}

        self.setLayout(VLayout(margin=[0, 6, 0, 0], spacing=3))

        self.lbModule = QLabel("Connecting...")
        fnt = self.lbModule.font()
        fnt.setPointSize(14)
        fnt.setBold(True)
        self.lbModule.setFont(fnt)
        self.lbModule.setAlignment(Qt.AlignCenter)
        self.lbModule.setMaximumHeight(25)
        self.layout().addWidget(self.lbModule)

        self.build_tabs()

        self.create_timers()

    def create_timers(self):
        self.auto_timer = QTimer()
        self.auto_timer.setInterval(1000)
        self.auto_timer.timeout.connect(self.auto)
        self.auto_timer.start()
        self.mqtt_timer = QTimer()
        self.mqtt_timer.setSingleShot(True)
        self.mqtt_timer.timeout.connect(self.setupMqtt)
        self.mqtt_timer.start(1000)

    def build_tabs(self):
        self.tabs = QTabWidget()

        tabInformation = self.tabInformation()
        self.tabs.addTab(tabInformation, "Information")

        tabModule = self.tabModule()
        self.tabs.addTab(tabModule, "Module and Firmware")

        self.rule_grps = []
        tabRules = self.tabRules()
        self.tabs.addTab(tabRules, "Rules and Timers")
        self.pbRTSet.clicked.connect(self.saveRuleTimers)
        self.pbVMSet.clicked.connect(self.saveVarMem)

        self.rg.pbSave.clicked.connect(self.saveRule)

        self.tabs.currentChanged.connect(self.tabChanged)
        self.tabs.setEnabled(False)
        self.layout().addWidget(self.tabs)

    def auto(self):
        if self.mqtt.state == self.mqtt.Connected:
            if self.pbRTPoll.isChecked():
                self.loadRuleTimers()

            if self.pbVMPoll.isChecked():
                self.loadVarMem()

    def tabChanged(self, tab):
        # if tab == 1:

        if tab == 2:
            self.loadRule(self.rg.cbRule.currentIndex())
            self.loadTimer(self.cbTimer.currentIndex())
            self.loadRuleTimers()
            self.loadVarMem()

    def setupMqtt(self):
        self.mqtt.hostname = self.settings.value('hostname', 'localhost')
        self.mqtt.port = self.settings.value('port', 1883, int)

        if self.settings.value('username'):
            self.mqtt.setAuth(self.settings.value('username'), self.settings.value('password'))

        self.mqtt.connected.connect(self.mqtt_subscribe)
        self.mqtt.messageSignal.connect(self.mqtt_message)
        self.mqtt.connectToHost()

    def mqtt_subscribe(self):
        self.mqtt.subscribe(self.tele_topic)
        self.mqtt.subscribe(self.stat_topic)

        self.initial_query()

        self.tabs.setEnabled(True)

    def mqtt_message(self, topic, msg):
        match = match_topic(self.full_topic, topic)
        if match:
            match = match.groupdict()
            reply = match['reply']

            if reply == "RESULT":
                msg = loads(msg)
                first = list(msg)[0]

                if first.startswith('Rule'):
                    self.parseRule(msg)

                elif first == "T1":
                    self.parseRuleTimer(msg)

                elif first.startswith('Var'):
                    self.parseVarMem(msg, 0)

                elif first.startswith('Mem'):
                    self.parseVarMem(msg, 1)

                elif first == "Module":
                    self.module = msg[first]

                elif first.startswith('Modules'):
                    self.parseModules(msg)

                elif first.startswith('GPIO') and not first.startswith('GPIOs'):
                    self.parseGPIO(msg)

                elif first.startswith('GPIOs'):
                    self.parseGPIOs(msg)

                elif not first.startswith("Timers") and first.startswith("Timer"):
                    self.parseTimer(msg[first])

                elif first == "Timers":
                    self.gbTimers.setChecked(msg[first] == "ON")

                elif first.startswith("Timers"):
                    pass

                else:
                    print(msg)

            elif reply in ("STATE", "STATUS11"):
                msg = loads(msg)
                if reply == "STATUS11":
                    msg = msg['StatusSTS']

                self.wifi_model.item(0, 1).setText("{} ({})".format(msg['Wifi'].get('SSId', "n/a"), msg['Wifi'].get('RSSI', "n/a")))
                self.power = {k: msg[k] for k in msg.keys() if k.startswith("POWER")}
                self.cbxTimerOut.clear()
                self.cbxTimerOut.addItems(self.power)

            elif reply == "STATUS":
                msg = loads(msg)['Status']
                self.lbModule.setText(modules.get(msg.get("Module")))

                for i, fn in enumerate(msg['FriendlyName']):
                    self.program_model.item(6+i, 1).setText(msg['FriendlyName'][i])

                self.mqtt_model.item(4, 1).setText("{}".format(msg.get('Topic', "n/a")))

            elif reply == "STATUS1":
                msg = loads(msg)['StatusPRM']
                self.program_model.item(3, 1).setText("{} @{}".format(msg.get('SaveCount', "n/a"), msg.get('SaveAddress', "n/a")))
                self.program_model.item(4, 1).setText("{}".format(msg.get('BootCount', "n/a")))
                self.program_model.item(5, 1).setText("{}".format(msg.get('RestartReason', "n/a")))
                self.mqtt_model.item(5, 1).setText("{}".format(msg.get('GroupTopic', "n/a")))

            elif reply == "STATUS2":
                msg = loads(msg)['StatusFWR']
                self.program_model.item(0, 1).setText("{}".format(msg.get('Version', "n/a")))
                self.program_model.item(1, 1).setText("{}".format(msg.get('BuildDateTime', "n/a")))
                self.program_model.item(2, 1).setText("{} / {}".format(msg.get('Core', "n/a"), msg.get('SDK', "n/a")))

            elif reply == "STATUS3":
                msg = loads(msg)['StatusLOG']

            elif reply == "STATUS4":
                msg = loads(msg)['StatusMEM']
                self.esp_model.item(0, 1).setText("n/a")
                self.esp_model.item(1, 1).setText("{}".format(msg.get('FlashChipId', "n/a")))
                self.esp_model.item(2, 1).setText("{}".format(msg.get('FlashSize', "n/a")))
                self.esp_model.item(3, 1).setText("{}".format(msg.get('ProgramFlashSize', "n/a")))
                self.esp_model.item(4, 1).setText("n/a")
                self.esp_model.item(5, 1).setText("{}".format(msg.get('Free', "n/a")))
                self.esp_model.item(6, 1).setText("{}".format(msg.get('Heap', "n/a")))

            elif reply == "STATUS5":
                msg = loads(msg)['StatusNET']
                self.wifi_model.item(1, 1).setText("{}".format(msg.get('Hostname', "n/a")))
                self.wifi_model.item(2, 1).setText("{}".format(msg.get('IPAddress', "n/a")))
                self.wifi_model.item(3, 1).setText("{}".format(msg.get('Gateway', "n/a")))
                self.wifi_model.item(4, 1).setText("{}".format(msg.get('Subnetmask', "n/a")))
                self.wifi_model.item(5, 1).setText("{}".format(msg.get('DNSServer', "n/a")))
                self.wifi_model.item(6, 1).setText("{}".format(msg.get('Mac', "n/a")))

            elif reply == "STATUS6":
                msg = loads(msg)['StatusMQT']
                self.mqtt_model.item(0, 1).setText("{}".format(msg.get('MqttHost', "n/a")))
                self.mqtt_model.item(1, 1).setText("{}".format(msg.get('MqttPort', "n/a")))
                self.mqtt_model.item(2, 1).setText("{}".format(msg.get('MqttUser', "n/a")))
                self.mqtt_model.item(3, 1).setText("{}".format(msg.get('MqttClient', "n/a")))
                self.mqtt_model.item(6, 1).setText("{}".format(self.full_topic))
                self.mqtt_model.item(7, 1).setText("cmnd/{}_fb".format(msg.get('MqttClient', "n/a")))

            elif reply == "STATUS7":
                msg = loads(msg)['StatusTIM']
                self._sunrise = msg.get('Sunrise', "")
                self._sunset = msg.get('Sunset', "")
                self.TimerMode.button(1).setText(self.TimerMode.button(1).text().format(msg.get('Sunrise', "")))
                self.TimerMode.button(2).setText(self.TimerMode.button(2).text().format(msg.get('Sunset', "")))

    def initial_query(self):
        self.mqtt.publish(self.cmnd_topic + "status", 0)
        self.mqtt.publish(self.cmnd_topic + "module")
        self.mqtt.publish(self.cmnd_topic + "modules")
        self.mqtt.publish(self.cmnd_topic + "gpio")
        self.mqtt.publish(self.cmnd_topic + "gpios")

    def parseModules(self, msg):
        k = list(msg)[0]
        nr = k[-1]
        v = msg[k]

        if k == "Modules1":
            self.modules = v

        elif k == "Modules2":
            self.modules += v

        elif k == "Modules3":
            self.modules += v
            self.updateCBModules()

    def updateCBModules(self):
        self.cbModule.clear()
        self.cbModule.addItems(self.modules)
        self.cbModule.setCurrentText(self.module)

    def saveModule(self):
        module = self.cbModule.currentText().split(" ")[0]
        self.mqtt.publish(self.cmnd_topic + "module", payload=module)
        self.parent().close()

    def parseGPIO(self, msg):
        for g in list(msg):
            self.current_gpios[g] = (msg[g])
            cb = QComboBox()
            self.gpios.append(cb)
            self.gbGPIO.layout().addRow(QLabel(g), cb)

        pbGPIOSet = QPushButton("Save and close (device will restart)")
        pbGPIOSet.clicked.connect(self.saveGPIOs)
        self.gbGPIO.layout().addWidget(pbGPIOSet)

    def parseGPIOs(self, msg):
        k = list(msg)[0]
        nr = k[-1]
        v = msg[k]

        if k == "GPIOs1":
            self.supported_gpios = v

        elif k == "GPIOs2":
            self.supported_gpios += v

        elif k == "GPIOs3":
            self.supported_gpios += v
            self.updateCBGpios()

    def updateCBGpios(self):
        for i, cb in enumerate(self.gpios):
            cb.clear()
            cb.addItems(self.supported_gpios)
            cb.setCurrentText(self.current_gpios[list(self.current_gpios)[i]])

    def saveGPIOs(self):
        payload = ""
        for i, g in enumerate(list(self.current_gpios)):
            gpio = self.gpios[i].currentText().split(" ")[0]
            payload += "{} {}; ".format(g, gpio)

        self.mqtt.publish(self.cmnd_topic + "backlog", payload=payload)
        self.parent().close()

    def loadRule(self, idx):
        self.mqtt.publish(self.cmnd_topic+"Rule{}".format(idx+1))

    def parseRule(self, msg):
        rule, once, stop, _, rules = list(msg)
        self.rg.cbEnabled.setChecked(msg[rule] == "ON")
        self.rg.cbOnce.setChecked(msg[once] == "ON")
        self.rg.cbStopOnError.setChecked(msg[stop] == "ON")
        self.rg.text.setPlainText(msg['Rules'].replace(" on ", "\non ").replace(" do ", " do\n\t").replace(" endon", "\nendon "))

    def saveRule(self):
        text = self.rg.text.toPlainText().replace("\n", " ").replace("\t", " ").replace("  ", " ")
        backlog = {
            'rule_nr': "Rule{}".format(self.rg.cbRule.currentIndex()+ 1),
            'text': text if len(text) > 0 else '""',
            'enabled': "1" if self.rg.cbEnabled.isChecked() else "0",
            'once': "5" if self.rg.cbOnce.isChecked() else "4",
            'stop': "9" if self.rg.cbStopOnError.isChecked() else "8"
        }
        self.mqtt.publish(self.cmnd_topic + "backlog", payload='{rule_nr} {text}; {rule_nr} {once}; {rule_nr} {stop}; {rule_nr} {enabled}; '.format(**backlog))

    def loadRuleTimers(self):
        self.mqtt.publish(self.cmnd_topic + "ruletimer")

    def parseRuleTimer(self, msg):
        for c in range(8):
            itm = self.twRT.cellWidget(0, c)
            itm.setValue(int(msg["T{}".format(c+1)]))

    def saveRuleTimers(self):
        for t in range(8):
            self.mqtt.publish(self.cmnd_topic + "ruletimer{}".format(t + 1), payload=self.twRT.cellWidget(0, t).value())

    def loadVarMem(self):
        for x in range(5):
            self.mqtt.publish(self.cmnd_topic + "var{}".format(x+1))
            self.mqtt.publish(self.cmnd_topic + "mem{}".format(x+1))

    def parseVarMem(self, msg, row):
        k = list(msg)[0]
        nr = k[-1]
        v = msg[k]
        itm = self.twVM.cellWidget(row, int(nr)-1)
        itm.setText(v)

    def saveVarMem(self):
        for r, cmd in enumerate(['Var', 'Mem']):
            for c in range(5):
                self.mqtt.publish(self.cmnd_topic + "{}{}".format(cmd, c+1), payload="{}".format(self.twVM.cellWidget(r, c).text()))

    def toggleTimers(self, state):
        self.mqtt.publish(self.cmnd_topic + "timers", payload="ON" if state else "OFF")

    def loadTimer(self, idx):
        self.mqtt.publish(self.cmnd_topic+"Timers")
        self.mqtt.publish(self.cmnd_topic+"Timer{}".format(idx+1))

    def parseTimer(self, payload):
        self.blockSignals(True)
        self.cbTimerArm.setChecked(payload['Arm'])
        self.cbTimerRpt.setChecked(payload['Repeat'])
        self.cbxTimerAction.setCurrentIndex(payload['Action'])
        output = payload.get('Output')
        if output:
            self.cbxTimerOut.setEnabled(True)
            self.cbxTimerOut.setCurrentIndex(output-1)
        else:
            self.cbxTimerOut.setEnabled(False)
        self.TimerMode.button(payload['Mode']).setChecked(True)
        h, m = map(int, payload["Time"].split(":"))
        if h < 0:
            self.cbxTimerPM.setCurrentText("-")
            h *= -1
        self.teTimerTime.setTime(QTime(h, m))
        self.cbxTimerWnd.setCurrentText(str(payload['Window']).zfill(2))
        for wd,v in enumerate(payload['Days']):
            self.TimerWeekday.button(wd).setChecked(int(v))

        self.describeTimer()
        self.blockSignals(False)

    def saveTimer(self):
        payload = {
            "Arm": int(self.cbTimerArm.isChecked()),
            "Mode": self.TimerMode.checkedId(),
            "Time": self.teTimerTime.time().toString("hh:mm"),
            "Window": self.cbxTimerWnd.currentIndex(),
            "Days": "".join([str(int(cb.isChecked())) for cb in self.TimerWeekday.buttons()]),
            "Repeat": int(self.cbTimerRpt.isChecked()),
            "Output": self.cbxTimerOut.currentIndex(),
            "Action": self.cbxTimerAction.currentIndex()}
        self.mqtt.publish(self.cmnd_topic + "timer{}".format(self.cbTimer.currentIndex()+1), payload=dumps(payload))

    def copyTrigger(self):
        mode = self.cbxTimerAction.currentText()
        if mode == "Rule":
            trigger = "clock#Timer={}".format(self.cbTimer.currentIndex()+1)
        else:
            trigger = "{}#state={}".format(self.cbxTimerOut.currentText(), self.cbxTimerAction.currentIndex())
        QApplication.clipboard().setText("on {} do\n\t\nendon".format(trigger))

    def describeTimer(self):
        if self.cbTimerArm.isChecked():
            desc = {'days': '', 'repeat': ''}
            desc['timer'] = self.cbTimer.currentText().upper()
            repeat = self.cbTimerRpt.isChecked()
            out = self.cbxTimerOut.currentText()
            act = self.cbxTimerAction.currentText()
            mode = self.TimerMode.checkedId()
            pm = self.cbxTimerPM.currentText()
            time = self.teTimerTime.time()
            wnd = int(self.cbxTimerWnd.currentText())*60

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

    def tabInformation(self):
        info = QWidget()
        vl = VLayout()

        self.program_model = QStandardItemModel()
        for d in ["Program version", "Build date & time", "Core/SDK version", "Flash write count", "Boot count", "Restart reason", "Friendly Name 1", "Friendly Name 2", "Friendly Name 3", "Friendly Name 4"]:
            k = QStandardItem(d)
            k.setEditable(False)
            v = QStandardItem()
            v.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
            v.setEditable(False)
            self.program_model.appendRow([k,v])

        gbPrgm = GroupBoxH("Program")
        gbPrgm.setFlat(True)
        tvPrgm = QTreeView()
        tvPrgm.setHeaderHidden(True)
        tvPrgm.setRootIsDecorated(False)
        tvPrgm.setModel(self.program_model)
        tvPrgm.resizeColumnToContents(0)
        gbPrgm.addWidget(tvPrgm)

        self.esp_model = QStandardItemModel()
        for d in ["ESP Chip Id", "Flash Chip Id", "Flash Size", "Program Flash Size", "Program Size", "Free Program Space", "Free Memory"]:
            k = QStandardItem(d)
            k.setEditable(False)
            v = QStandardItem()
            v.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
            v.setEditable(False)
            self.esp_model.appendRow([k, v])

        gbESP = GroupBoxH("ESP")
        gbESP.setFlat(True)
        tvESP = QTreeView()
        tvESP.setHeaderHidden(True)
        tvESP.setRootIsDecorated(False)
        tvESP.setModel(self.esp_model)
        tvESP.resizeColumnToContents(0)
        gbESP.addWidget(tvESP)

        # self.emul_model = QStandardItemModel()
        # for d in ["Emulation", "mDNS Discovery"]:
        #     k = QStandardItem(d)
        #     k.setEditable(False)
        #     v = QStandardItem()
        #     v.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
        #     v.setEditable(False)
        #     self.emul_model.appendRow([k, v])
        #
        # gbEmul = GroupBoxH("Emulation")
        # gbEmul.setFlat(True)
        # tvEmul = QTreeView()
        # tvEmul.setHeaderHidden(True)
        # tvEmul.setRootIsDecorated(False)
        # tvEmul.setModel(self.emul_model)
        # tvEmul.resizeColumnToContents(0)
        # gbEmul.addWidget(tvEmul)

        self.wifi_model = QStandardItemModel()
        for d in ["AP1 SSId (RSSI)", "Hostname", "IP Address", "Gateway", "Subnet Mask", "DNS Server", "MAC Address"]:
            k = QStandardItem(d)
            k.setEditable(False)
            v = QStandardItem()
            v.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
            v.setEditable(False)
            self.wifi_model.appendRow([k, v])

        gbWifi = GroupBoxH("Wifi")
        gbWifi.setFlat(True)
        tvWifi = QTreeView()
        tvWifi.setHeaderHidden(True)
        tvWifi.setRootIsDecorated(False)
        tvWifi.setModel(self.wifi_model)
        tvWifi.resizeColumnToContents(0)
        gbWifi.addWidget(tvWifi)

        self.mqtt_model = QStandardItemModel()
        for d in ["MQTT Host", "MQTT Port", "MQTT User", "MQTT Client", "MQTT Topic", "MQTT Group Topic", "MQTT Full Topic", "MQTT Fallback Topic"]:
            k = QStandardItem(d)
            k.setEditable(False)
            v = QStandardItem()
            v.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
            v.setEditable(False)
            self.mqtt_model.appendRow([k, v])

        gbMQTT = GroupBoxH("MQTT")
        gbMQTT.setFlat(True)
        tvMQTT = QTreeView()
        tvMQTT.setHeaderHidden(True)
        tvMQTT.setRootIsDecorated(False)
        tvMQTT.setModel(self.mqtt_model)
        tvMQTT.resizeColumnToContents(0)
        gbMQTT.addWidget(tvMQTT)

        hl = HLayout(0)
        vl_lc = VLayout(0, 3)
        vl_rc = VLayout(0, 3)

        vl_lc.addWidgets([gbPrgm, gbESP])
        vl_rc.addWidgets([gbWifi, gbMQTT])

        vl_rc.setStretch(0, 2)
        vl_rc.setStretch(1, 2)
        vl_rc.setStretch(2, 1)

        hl.addLayout(vl_lc)
        hl.addLayout(vl_rc)
        vl.addLayout(hl)
        info.setLayout(vl)
        return info

    def tabModule(self):
        module = QWidget()
        module.setLayout(HLayout())

        self.gbModule = QGroupBox("Module")
        fl_module = QFormLayout()

        self.cbModule = QComboBox()
        fl_module.addRow("Module type", self.cbModule)

        self.pbModuleSet = QPushButton("Save and close (device will restart)")
        self.pbModuleSet.clicked.connect(self.saveModule)
        fl_module.addWidget(self.pbModuleSet)

        self.gbModule.setLayout(fl_module)

        self.gbGPIO = QGroupBox("GPIO")
        fl_gpio = QFormLayout()

        self.gbGPIO.setLayout(fl_gpio)

        mg_vl = VLayout([0, 0, 3, 0])
        mg_vl.addWidgets([self.gbModule, self.gbGPIO])
        mg_vl.setStretch(0,1)
        mg_vl.setStretch(1,3)

        self.gbFirmware = GroupBoxV("Firmware", margin=[3, 0, 0, 0])
        lb = QLabel("Feature under development.")
        lb.setAlignment(Qt.AlignCenter)
        lb.setEnabled(False)
        self.gbFirmware.addWidget(lb)

        module.layout().addLayout(mg_vl)
        module.layout().addWidget(self.gbFirmware)
        return module

    def tabRules(self):
        rules = QWidget()
        rules.setLayout(VLayout())
        hl = HLayout(0)
        vl_l = VLayout(0)
        self.rg = RuleGroupBox(rules, "Rule editor")
        self.rg.setFlat(True)
        self.rg.cbRule.currentIndexChanged.connect(self.loadRule)
        vl_l.addWidget(self.rg)

        gRT = GroupBoxH("Rule timers")
        vl_RT_func = VLayout(margin=[0,0,3,0])
        self.pbRTPoll = QPushButton("Poll")
        self.pbRTPoll.setCheckable(True)
        self.pbRTSet = QPushButton("Set")

        vl_RT_func.addWidgets([self.pbRTPoll, self.pbRTSet])
        vl_RT_func.addStretch(1)
        gRT.layout().addLayout(vl_RT_func)

        self.twRT = QTableWidget(1,8)
        self.twRT.setHorizontalHeaderLabels(["T{}".format(i) for i in range(1, 9)])
        for c in range(8):
            self.twRT.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)
            self.twRT.setCellWidget(0, c, SpinBox(minimum=0, maximum=32766))
        self.twRT.verticalHeader().hide()

        self.twRT.verticalHeader().setDefaultSectionSize(self.twRT.horizontalHeader().height()*2+1)
        self.twRT.setMaximumHeight(self.twRT.horizontalHeader().height() + self.twRT.rowHeight(0))
        gRT.layout().addWidget(self.twRT)

        gVM = GroupBoxH("VAR/MEM")
        vl_VM_func = VLayout(margin=[3, 0, 0, 0])
        self.pbVMPoll = QPushButton("Poll")
        self.pbVMPoll.setCheckable(True)
        self.pbVMSet = QPushButton("Set")

        vl_VM_func.addWidgets([self.pbVMPoll, self.pbVMSet])
        vl_VM_func.addStretch(1)
        gVM.layout().addLayout(vl_VM_func)

        self.twVM = QTableWidget(2, 5)
        self.twVM.setHorizontalHeaderLabels(["{}".format(i) for i in range(1, 9)])
        self.twVM.setVerticalHeaderLabels(["VAR", "MEM"])
        self.twVM.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for c in range(5):
            self.twVM.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)

        for r in range(2):
            for c in range(5):
                self.twVM.setCellWidget(r, c, QLineEdit())

        self.twVM.verticalHeader().setDefaultSectionSize(self.twVM.horizontalHeader().height())
        self.twVM.setMaximumHeight(self.twVM.horizontalHeader().height() + self.twVM.rowHeight(0)*2)
        gVM.layout().addWidget(self.twVM)

        hl_rt_vm = HLayout(0)
        hl_rt_vm.addWidgets([gRT, gVM])

        hl.addLayout(vl_l)

        vl_r = VLayout(0)
        self.gbTimers = GroupBoxV("Timers", spacing=5)
        self.gbTimers.setCheckable(True)
        self.gbTimers.setChecked(False)
        self.gbTimers.toggled.connect(self.toggleTimers)

        self.cbTimer = QComboBox()
        self.cbTimer.addItems(["Timer{}".format(nr+1) for nr in range(16)])
        self.cbTimer.currentIndexChanged.connect(self.loadTimer)

        hl_tmr_arm_rpt = HLayout(0)
        self.cbTimerArm = QCheckBox("Arm")
        self.cbTimerArm.clicked.connect(lambda x: self.describeTimer())
        self.cbTimerRpt = QCheckBox("Repeat")
        self.cbTimerRpt.clicked.connect(lambda x: self.describeTimer())
        hl_tmr_arm_rpt.addWidgets([self.cbTimerArm, self.cbTimerRpt])

        hl_tmr_out_act = HLayout(0)
        self.cbxTimerOut = QComboBox()
        self.cbxTimerOut.currentIndexChanged.connect(lambda x: self.describeTimer())
        self.cbxTimerAction = QComboBox()
        self.cbxTimerAction.addItems(["Off", "On", "Toggle", "Rule"])
        self.cbxTimerAction.currentIndexChanged.connect(lambda x: self.describeTimer())
        hl_tmr_out_act.addWidgets([self.cbxTimerOut, self.cbxTimerAction])

        self.TimerMode = QButtonGroup()
        rbTime = QRadioButton("Time")
        rbSunrise = QRadioButton("Sunrise ({})")
        rbSunset = QRadioButton("Sunset ({})")
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
        gbTimerDesc.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.lbTimerDesc = QLabel()
        self.lbTimerDesc.setAlignment(Qt.AlignCenter)
        self.lbTimerDesc.setWordWrap(True)
        gbTimerDesc.layout().addWidget(self.lbTimerDesc)
        hl_tmr_btns = HLayout(0)
        btnCopyTrigger = QPushButton("Copy trigger")
        btnTimerSave = QPushButton("Save")
        hl_tmr_btns.addWidgets([btnCopyTrigger, btnTimerSave])
        hl_tmr_btns.insertStretch(1)

        btnTimerSave.clicked.connect(self.saveTimer)
        btnCopyTrigger.clicked.connect(self.copyTrigger)

        hl_tmr_time.addWidgets([self.cbxTimerPM, self.teTimerTime, lbWnd, self.cbxTimerWnd])

        self.gbTimers.layout().addWidget(self.cbTimer)
        self.gbTimers.layout().addLayout(hl_tmr_arm_rpt)
        self.gbTimers.layout().addLayout(hl_tmr_out_act)
        self.gbTimers.layout().addWidget(gbTimerMode)
        self.gbTimers.layout().addLayout(hl_tmr_time)
        self.gbTimers.layout().addLayout(hl_tmr_days)
        self.gbTimers.layout().addWidget(gbTimerDesc)
        self.gbTimers.layout().addLayout(hl_tmr_btns)

        vl_r.addWidget(self.gbTimers)

        hl.addLayout(vl_r)
        hl.setStretch(0,2)
        hl.setStretch(1,1)

        rules.layout().addLayout(hl)
        rules.layout().addLayout(hl_rt_vm)
        rules.layout().setStretch(0,3)
        rules.layout().setStretch(1,0)

        return rules

    def closeEvent(self, event):
        self.mqtt.disconnectFromHost()
        event.accept()
