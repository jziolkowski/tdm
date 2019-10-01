import re
from collections import namedtuple
from json import loads, JSONDecodeError, load

from PyQt5.QtCore import QDir, QDateTime, pyqtSignal, QObject

commands = [
    "Backlog", "BlinkCount", "BlinkTime", "ButtonDebounce", "FanSpeed", "Interlock", "LedMask", "LedPower", "LedPower", "LedState", "Power", "PowerOnState", "PulseTime", "SwitchDebounce", "SwitchMode",
    "Delay", "Emulation", "Event", "FriendlyName", "Gpios", "Gpio", "I2Cscan", "LogHost", "LogPort", "Modules", "Module", "OtaUrl", "Pwm", "PwmFrequency", "PwmRange", "Reset", "Restart", "Template", "SaveData", "SerialLog", "Sleep", "State", "Status", "SysLog", "Timezone", "TimeSTD", "TimeDST", "Upgrade", "Upload", "WebLog",
    "AP", "Hostname", "IPAddress1", "IPAddress2", "IPAddress3", "IPAddress4", "NtpServer", "Password", "Ssid", "WebPassword", "WebSend", "WebServer", "WebRefresh", "WebColor", "WifiConfig",
    "ButtonRetain", "ButtonTopic", "FullTopic", "GroupTopic", "MqttClient", "MqttFingerprint", "MqttHost", "MqttPassword", "MqttPort", "MqttRetry", "MqttUser", "PowerRetain", "Prefix1", "Prefix2", "Prefix3", "Publish", "Publish2", "SensorRetain", "StateText1", "StateText2", "StateText3", "StateText4", "SwitchRetain", "SwitchTopic", "TelePeriod", "Topic",
    "Rule", "RuleTimer", "Mem", "Var", "Add", "Sub", "Mult", "Scale", "CalcRes",
    "Latitude", "Longitude", "Timers", "Timer",
    "AdcParam", "Altitude", "AmpRes", "Counter", "CounterDebounce", "CounterType", "EnergyRes", "HumRes", "PressRes", "Sensor13", "Sensor15", "Sensor20", "Sensor27", "Sensor34", "TempRes", "VoltRes", "WattRes", "WeightRes",
    "AmpRes", "CurrentHigh", "CurrentLow", "CurrentSet", "EnergyRes", "EnergyReset", "EnergyReset1", "EnergyReset2", "EnergyReset3", "FreqRes", "FrequencySet", "MaxPower", "MaxPowerHold", "MaxPowerWindow", "PowerDelta", "PowerHigh", "PowerLow", "PowerSet", "Status", "VoltageHigh", "VoltageLow", "VoltageSet", "VoltRes", "WattRes",
    "Channel", "Color", "Color2", "Color3", "Color4", "Color5", "Color6", "CT", "Dimmer", "Fade", "HsbColor", "HsbColor1", "HsbColor2", "HsbColor3", "Led", "LedTable", "Pixels", "Rotation", "Scheme", "Speed", "Wakeup", "WakeupDuration", "White", "Width1", "Width2", "Width3", "Width4",
    "RfCode", "RfHigh", "RfHost", "RfKey", "RfLow", "RfRaw", "RfSync",
    "IRsend", "IRhvac",
    "SetOption0", "SetOption1", "SetOption2", "SetOption3", "SetOption4", "SetOption8", "SetOption10", "SetOption11", "SetOption12", "SetOption13", "SetOption15", "SetOption16", "SetOption17", "SetOption18", "SetOption19", "SetOption20", "SetOption21", "SetOption24", "SetOption26", "SetOption28", "SetOption29", "SetOption30", "SetOption31", "SetOption32", "SetOption33", "SetOption34", "SetOption36", "SetOption37", "SetOption38", "SetOption51", "SetOption52", "SetOption53", "SetOption54", "SetOption55", "SetOption56", "SetOption57", "SetOption58", "SetOption59", "SetOption60", "SetOption61", "SetOption62", "SetOption63", "SetOption64",
    "Baudrate", "SBaudrate", "SerialDelimiter", "SerialDelimiter", "SerialSend", "SerialSend2", "SerialSend3", "SerialSend4", "SerialSend5", "SSerialSend", "SSerialSend2", "SSerialSend3", "SSerialSend4", "SSerialSend5",
    "MP3DAC", "MP3Device", "MP3EQ", "MP3Pause", "MP3Play", "MP3Reset", "MP3Stop", "MP3Track", "MP3Volume",
    "DomoticzIdx", "DomoticzKeyIdx", "DomoticzSensorIdx", "DomoticzSwitchIdx", "DomoticzUpdateTimer",
    "KnxTx_Cmnd", "KnxTx_Val", "KNX_ENABLED", "KNX_ENHANCED", "KNX_PA", "KNX_GA", "KNX_GA", "KNX_CB", "KNX_CB",
    "Display", "DisplayAddress", "DisplayDimmer", "DisplayMode", "DisplayModel", "DisplayRefresh", "DisplaySize", "DisplayRotate", "DisplayText", "DisplayCols", "DisplayRows", "DisplayFont",
]

prefixes = ["tele", "stat", "cmnd"]
default_patterns = [
    "%prefix%/%topic%/",    # = %prefix%/%topic% (Tasmota default)
    "%topic%/%prefix%/"     # = %topic%/%prefix% (Tasmota with SetOption19 enabled for HomeAssistant AutoDiscovery)
]

custom_patterns = []

resets = [
    "1: reset device settings to firmware defaults",
    "2: erase flash, reset device settings to firmware defaults",
    "3: erase flash SDK parameters",
    "4: reset device settings to firmware defaults, keep Wi-Fi credentials",
    "5: erase flash, reset parameters to firmware defaults, keep Wi-Fi settings",
    "6: erase flash, reset parameters to firmware defaults, keep Wi-Fi and MQTT settings"
]

template_adc = {
    "0": "None",
    "15": "User",
    "1": "Analog",
    "2": "Temperature",
    "3": "Light",
    "4": "Button",
    "5": "Buttoni"
}

with open("Util/setoptions.json") as so:
    setoptions = load(so)

# TODO: add all commands to the JSON file and get rid of the list above
with open("Util/commands.json") as cm:
    commands_json = load(cm)


def initial_commands():
    commands = [
        ["status", 0],
        ["template", ""],
        ["modules", ""],
        ["gpio", ""],
        ["gpios", "255"],
        # ["timers", ""],
        ["buttondebounce", ""],
        ["switchdebounce", ""],
        ["interlock", ""],
        ["blinktime", ""],
        ["blinkcount", ""],
    ]
    for pt in range(8):
        commands.append(["pulsetime{}".format(pt+1), ""])

    return commands



def parse_topic(full_topic, topic):
    """
    :param full_topic: FullTopic to match against
    :param topic: MQTT topic from which the reply arrived
    :return: If match is found, returns dictionary including device Topic, prefix (cmnd/tele/stat) and reply endpoint
    """
    full_topic = "{}(?P<reply>.*)".format(full_topic).replace("%topic%", "(?P<topic>.*?)").replace("%prefix%", "(?P<prefix>.*?)")
    match = re.fullmatch(full_topic, topic)
    if match:
        return match.groupdict()
    return {}


def parse_payload(payload):
    match = re.match("(\d+) \((.*)\)", payload)
    if match:
        return dict([match.groups()])
    return {}


def expand_fulltopic(fulltopic):
    fulltopics = []
    for prefix in prefixes:
        topic = fulltopic.replace("%prefix%", prefix).replace("%topic%", "+") + "#"  # expand prefix and topic
        topic = topic.replace("+/#", "#")  # simplify wildcards
        fulltopics.append(topic)
    return fulltopics


class TasmotaEnvironment(object):
    def __init__(self):
        self.devices = []

    def find_device(self, topic):
        for d in self.devices:
            if d.matches(topic):
                return d
        return None


class TasmotaDevice(QObject):
    update_telemetry = pyqtSignal()
    def __init__(self, topic, fulltopic, friendlyname=""):
        super(TasmotaDevice, self).__init__()
        self.p = {
            "LWT": "undefined",
            "Topic": topic,
            "FullTopic": fulltopic,
            "FriendlyName1": friendlyname if friendlyname else topic,
            "Template": {},
        }

        self.env = None
        self.history = []

        self.property_changed = None    # property changed callback pointer

        self.t = None

        self.modules = {}                     # supported modules
        self.module_changed = None      # module changed callback pointer

        self.gpios = {}                     # supported GPIOs
        self.gpio = {}                  # gpio config

        self.reply = ""
        self.prefix = ""

    def build_topic(self, prefix):
        return self.p['FullTopic'].replace("%prefix%", prefix).replace("%topic%", self.p['Topic']).rstrip("/")

    def cmnd_topic(self, command=""):
        if command:
            return "{}/{}".format(self.build_topic("cmnd"), command)
        return self.build_topic("cmnd")

    def stat_topic(self):
        return self.build_topic("stat")

    def tele_topic(self):
        return self.build_topic("tele")

    def is_default(self):
        return self.p['FullTopic'] in ["%prefix%/%topic%/", "%topic%/%prefix%/"]

    def update_property(self, k, v):
        old = self.p.get('k')   # safely get the old value
        if self.property_changed and (not old or old != v):     # If property_changed callback is set then check previous value presence and
            self.property_changed(self, k)                      # compare with new value. Trigger the callback if value has changed
        self.p[k] = v                                           # store the new value

    def module(self):
        mdl = self.p.get('Module')
        if mdl:
            return self.modules.get(str(mdl))

        if self.p['LWT'] == 'Online':
            return "Fetching module name..."

    def matches(self, topic):
        if topic == self.p['Topic']:
            return True
        parsed = parse_topic(self.p['FullTopic'], topic)
        self.reply = parsed.get('reply')
        self.prefix = parsed.get('prefix')
        return parsed.get('topic') == self.p['Topic']

    def parse_message(self, topic, msg):
        parse_statuses = ["STATUS{}".format(s) for s in [1, 2, 3, 4, 5, 6, 7]]
        if self.prefix in ("stat", "tele"):

            try:
                payload = loads(msg)

                if self.reply == 'STATUS':
                    payload = payload['Status']
                    for k, v in payload.items():
                        if k == "FriendlyName":
                            for fnk, fnv in enumerate(v, start=1):
                                self.update_property("FriendlyName{}".format(fnk), fnv)
                        else:
                            self.update_property(k, v)

                elif self.reply in parse_statuses:
                    payload = payload[list(payload.keys())[0]]
                    for k, v in payload.items():
                        self.update_property(k, v)

                elif self.reply in ('STATE', 'STATUS11'):
                    if self.reply == 'STATUS11':
                        payload = payload['StatusSTS']

                    for k, v in payload.items():
                        if isinstance(v, dict):
                            for kk, vv in v.items():
                                self.update_property(kk, vv)
                        else:
                            self.update_property(k, v)

                elif self.reply in ('SENSOR', 'STATUS8', 'STATUS10'):
                    if self.reply in ('STATUS8', 'STATUS10'):
                        payload = payload['StatusSNS']

                    self.t = payload
                    self.update_telemetry.emit()

                elif self.reply == 'RESULT':
                    keys = list(payload.keys())
                    fk = keys[0]

                    if fk.startswith("Modules"):
                        for k, v in payload.items():
                            if isinstance(v, list):
                                for mdl in v:
                                    self.modules.update(parse_payload(mdl))
                            elif isinstance(v, dict):
                                self.modules.update(v)
                            self.module_changed(self)

                    elif fk == 'NAME':
                        self.p['Template'] = payload
                        if self.module_changed:
                            self.module_changed(self)

                    elif fk.startswith("GPIOs"):
                        for k, v in payload.items():
                            if isinstance(v, list):
                                for gp in v:
                                    self.gpios.update(parse_payload(gp))
                            elif isinstance(v, dict):
                                self.gpios.update(v)

                    elif fk.startswith("GPIO"):
                        for gp, gp_val in payload.items():
                            if not gp == "GPIO":
                                if isinstance(gp_val, str):
                                    gp_id = gp_val.split(" (")[0]
                                    self.gpio[gp] = gp_id
                                elif isinstance(gp_val, dict):
                                    self.gpio[gp] = list(gp_val.keys())[0]

                    else:
                        for k, v in payload.items():
                            self.update_property(k, v)

            except JSONDecodeError as e:
                    with open("{}/TDM/error.log".format(QDir.homePath()), "a+") as l:
                        l.write("{}\t{}\t{}\t{}\n"
                                .format(QDateTime.currentDateTime()
                                        .toString("yyyy-MM-dd hh:mm:ss"), topic, msg, e.msg))

    def power(self):
        return {k: v for k, v in self.p.items() if k.startswith('POWER')}

    def pulsetime(self):
        return {k: {"Set": list(v.keys())[0], "Active": list(v.values())[0]['Active']} for k, v in self.p.items() if k.startswith('PulseTime')}

    def pwm(self):
        return {k: v for k, v in self.p.items() if k.startswith('PWM') or (k != "Channel" and k.startswith("Channel"))}

    def color(self):
        color = {k: self.p[k] for k in ["Color", "Dimmer", "HSBColor"] if k in self.p.keys()}
        color.update({
            17: self.setoption(17),
            68: self.setoption(68)
        })
        return color

    def setoption(self, o):
        if 0 <= o < 32:
            reg = 0
        elif 32 <= o < 50:
            reg = 1
        else:
            reg = 2

        so = self.p.get('SetOption')
        if so:
            if reg in (0, 2):
                options = int(so[reg], 16)
                if reg == 2:
                    o -= 50
                state = int(options >> o & 1)

            else:
                o -= 32
                split_register = [int(so[reg][opt * 2:opt * 2 + 2], 16) for opt in range(18)]
                return split_register[o]
            return state
        return -1

    def __repr__(self):
        fname = self.p.get('FriendlyName1')
        fname = fname if fname else self.p['Topic']

        return "<TasmotaDevice {}: {}>".format(fname, self.p['Topic'])
