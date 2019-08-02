import re
from collections import namedtuple
from json import loads, JSONDecodeError

from PyQt5.QtCore import QDir, QDateTime

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

DeviceRule = namedtuple("DeviceRule", ['enabled', 'once', 'stop_on_error', 'rules'])


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


class TasmotaDevice(object):
    def __init__(self, topic, fulltopic, friendlyname=""):
        self.p = {
            "LWT": "undefined",
            "Topic": topic,
            "FullTopic": fulltopic,
            "FriendlyName": [friendlyname if friendlyname else topic],
            "Template": {},
        }

        self.env = None
        self.history = []
        self.rules = []

        # property changed callback pointer
        self.property_changed = None

        self.t = None
        # telemetry changed callback pointer
        self.telemetry_changed = None

        self.m = {}
        # module changed callback pointer
        self.module_changed = None

        self.g = {}

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
        old = self.p.get('k')
        if self.property_changed and (not old or old != v):
            self.property_changed(self, k)
        self.p[k] = v

    def module(self):
        mdl = [m for m in self.modules() if m.startswith(str(self.p.get('Module')))]
        if mdl:
            return mdl[0].split(" (")[1].rstrip(")")
        if self.p['LWT'] == 'Online':
            return "Fetching module name..."

    def modules(self):
        mdls = []
        for v in self.m.values():
            mdls += v
        return mdls

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

                        # self.parse_power(payload)

                elif self.reply.startswith("POWER"):
                    self.update_property(self.reply, msg)

                elif self.reply == 'RESULT':
                    for k, v in payload.items():

                        if k.startswith("Modules"):
                            self.m[k] = v
                            self.module_changed(self)

                        elif k == 'NAME':
                            self.p['Template'] = payload
                            if self.module_changed:
                                self.module_changed(self)
                            break

                        elif k.startswith('POWER'):
                            self.update_property(k, v)

                        else:
                            self.update_property(k, v)

            except JSONDecodeError as e:
                with open("{}/TDM/error.log".format(QDir.homePath()), "a+") as l:
                    l.write("{}\t{}\t{}\t{}\n"
                            .format(QDateTime.currentDateTime()
                                    .toString("yyyy-MM-dd hh:mm:ss"), topic, msg, e.msg))

    def power(self):
        return {k: v for k, v in self.p.items() if k.startswith('POWER')}

    def __repr__(self):
        fname = self.p.get('FriendlyName')
        fname = fname[0] if fname else self.p['Topic']

        return "<TasmotaDevice {}: {}>".format(fname, self.p['Topic'])
