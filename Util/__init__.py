import logging
import re
from json import JSONDecodeError, loads

from pkg_resources import parse_version
from PyQt5.QtCore import QObject, pyqtSignal


prefixes = ["tele", "stat", "cmnd"]
default_patterns = [
    "%prefix%/%topic%/",  # = %prefix%/%topic% (Tasmota default)
    "%topic%/%prefix%/",  # = %topic%/%prefix% (Tasmota with SetOption19 enabled for
    # HomeAssistant AutoDiscovery)
]

custom_patterns = []

resets = [
    "1: reset device settings to firmware defaults",
    "2: erase flash, reset device settings to firmware defaults",
    "3: erase flash SDK parameters",
    "4: reset device settings to firmware defaults, keep Wi-Fi credentials",
    "5: erase flash, reset parameters to firmware defaults, keep Wi-Fi settings",
    "6: erase flash, reset parameters to firmware defaults, keep Wi-Fi and MQTT settings",
    "99: reset device bootcount to zero",
]

template_adc = {
    "0": "None",
    "15": "User",
    "1": "Analog",
    "2": "Temperature",
    "3": "Light",
    "4": "Button",
    "5": "Buttoni",
}


def initial_commands():
    commands = [
        ["status", 0],
        ["template", ""],
        ["modules", ""],
        ["gpio", ""],
        ["gpios", "255"],
        ["buttondebounce", ""],
        ["switchdebounce", ""],
        ["interlock", ""],
        ["blinktime", ""],
        ["blinkcount", ""],
        ["mqttlog", ""],  # will be removed after MqttLog will be added to Status 3
    ]
    for pt in range(8):
        commands.append([f"pulsetime{pt + 1}", ""])
    for sht in range(4):
        commands.append([f"shutterrelay{sht + 1}", ""])
        commands.append([f"shutterposition{sht + 1}", ""])

    return commands


def parse_topic(full_topic, topic):
    """
    :param full_topic: FullTopic to match against
    :param topic: MQTT topic from which the reply arrived
    :return: If match is found, returns dictionary including device Topic,
        prefix (cmnd/tele/stat) and reply endpoint
    """
    full_topic = f"{full_topic}(?P<reply>.*)".replace("%topic%", "(?P<topic>.*?)").replace(
        "%prefix%", "(?P<prefix>.*?)"
    )
    match = re.fullmatch(full_topic, topic)
    if match:
        return match.groupdict()
    return {}


def parse_payload(payload):
    match = re.match(r"(\d+) \((.*)\)", payload)
    if match:
        return dict([match.groups()])
    return {}


def expand_fulltopic(fulltopic):
    fulltopics = []
    for prefix in prefixes:
        topic = (
            fulltopic.replace("%prefix%", prefix).replace("%topic%", "+") + "#"
        )  # expand prefix and topic
        topic = topic.replace("+/#", "#")  # simplify wildcards
        fulltopics.append(topic)
    return fulltopics


class TasmotaEnvironment(object):
    def __init__(self):
        self.devices = []
        self.lwts = []

    def find_device(self, topic):
        for d in self.devices:
            if d.matches(topic):
                return d
        return None


class TasmotaDevice(QObject):
    update_telemetry = pyqtSignal()

    def __init__(self, topic, fulltopic, devicename=""):
        super(TasmotaDevice, self).__init__()
        self.p = {
            "LWT": "undefined",
            "Topic": topic,
            "FullTopic": fulltopic,
            "DeviceName": devicename,
            "Template": {},
        }

        self.debug = False
        self.env = None
        self.history = []

        self.property_changed = None  # property changed callback pointer

        self.t = None

        self.modules = {}  # supported modules
        self.module_changed = None  # module changed callback pointer

        self.gpios = {}  # supported GPIOs
        self.gpio = {}  # gpio config

        self.reply = ""
        self.prefix = ""

    def build_topic(self, prefix):
        return (
            self.p["FullTopic"]
            .replace("%prefix%", prefix)
            .replace("%topic%", self.p["Topic"])
            .rstrip("/")
        )

    def cmnd_topic(self, command=""):
        if command:
            return f"{self.build_topic('cmnd')}/{command}"
        return self.build_topic("cmnd")

    def stat_topic(self):
        return self.build_topic("stat")

    def tele_topic(self, endpoint=""):
        if endpoint:
            return f"{self.build_topic('tele')}/{endpoint}"
        return self.build_topic("tele")

    def is_default(self):
        return self.p["FullTopic"] in ["%prefix%/%topic%/", "%topic%/%prefix%/"]

    def update_property(self, k, v):
        old = self.p.get(k)  # safely get the old value
        if self.property_changed and (
            not old or old != v
        ):  # If property_changed callback is set then check previous value presence and
            self.property_changed(
                self, k
            )  # compare with new value. Trigger the callback if value has changed
        self.p[k] = v  # store the new value

    def module(self):
        if mdl := self.p.get("Module"):
            return self.modules.get(str(mdl), '')

        if self.p["LWT"] == "Online":
            return "Fetching module name..."

    def matches(self, topic):
        if topic == self.p["Topic"]:
            return True
        parsed = parse_topic(self.p["FullTopic"], topic)
        self.reply = parsed.get("reply")
        self.prefix = parsed.get("prefix")
        return parsed.get("topic") == self.p["Topic"]

    def parse_message(self, topic, msg):
        parse_statuses = [f"STATUS{s}" for s in [1, 2, 3, 4, 5, 6, 7, 9]]
        if self.prefix in ("stat", "tele"):
            payload = None

            if self.reply == "STATUS":
                try:
                    payload = loads(msg)
                except JSONDecodeError as e:
                    logging.critical("PARSER: Can't parse STATUS (%s): %s", e, msg)

                if payload:
                    payload = payload.get("Status", {})
                    for k, v in payload.items():
                        if k == "FriendlyName":
                            for fnk, fnv in enumerate(v, start=1):
                                self.update_property(f"FriendlyName{fnk}", fnv)
                        else:
                            self.update_property(k, v)

            elif self.reply in parse_statuses:
                try:
                    payload = loads(msg)
                except JSONDecodeError as e:
                    logging.critical("PARSER: Can't parse %s (%s): %s", self.reply, e, msg)

                if payload:
                    payload = payload[list(payload.keys())[0]]
                    for k, v in payload.items():
                        self.update_property(k, v)

            elif self.reply in ("STATE", "STATUS11"):
                try:
                    payload = loads(msg)
                except JSONDecodeError as e:
                    logging.critical("PARSER: Can't parse %s (%s): %s", self.reply, e, msg)

                if payload:
                    if self.reply == "STATUS11":
                        payload = payload["StatusSTS"]

                    for k, v in payload.items():
                        if isinstance(v, dict):
                            for kk, vv in v.items():
                                self.update_property(kk, vv)
                        else:
                            self.update_property(k, v)

            elif self.reply in ("SENSOR", "STATUS8", "STATUS10"):
                try:
                    payload = loads(msg)
                except JSONDecodeError as e:
                    logging.critical("PARSER: Can't parse %s (%s): %s", self.reply, e, msg)

                if payload:
                    if self.reply in ("STATUS8", "STATUS10"):
                        payload = payload["StatusSNS"]

                    self.t = payload
                    self.update_telemetry.emit()

            elif msg.startswith("{"):
                try:
                    payload = loads(msg)
                except JSONDecodeError as e:
                    logging.critical("PARSER: Can't parse %s (%s): %s", self.reply, e, msg)

                if payload:
                    keys = list(payload.keys())
                    fk = keys[0]

                    if (
                        self.reply == "RESULT"
                        and fk.startswith("Modules")
                        or self.reply == "MODULES"
                    ):
                        for k, v in payload.items():
                            if isinstance(v, list):
                                for mdl in v:
                                    self.modules.update(parse_payload(mdl))
                            elif isinstance(v, dict):
                                self.modules.update(v)
                            self.module_changed(self)

                    elif self.reply == "RESULT" and fk == "NAME" or self.reply == "TEMPLATE":
                        self.p["Template"] = payload
                        if self.module_changed:
                            self.module_changed(self)

                    elif self.reply == "RESULT" and fk.startswith("GPIOs") or self.reply == "GPIOS":
                        for k, v in payload.items():
                            if isinstance(v, list):
                                for gp in v:
                                    self.gpios.update(parse_payload(gp))
                            elif isinstance(v, dict):
                                self.gpios.update(v)

                    elif self.reply == "RESULT" and fk.startswith("GPIO") or self.reply == "GPIO":
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

    def power(self):
        power_dict = {k: v for k, v in self.p.items() if k.startswith("POWER")}
        relay_count = len(power_dict.keys())
        if relay_count == 1:
            return {1: power_dict.get('POWER1', power_dict.get('POWER', 'OFF'))}
        if relay_count > 1:
            relays = dict(
                sorted({int(k.replace('POWER', '')): v for k, v in power_dict.items()}.items())
            )
            for shutter, shutter_relay in self.shutters().items():
                if shutter_relay != 0:
                    for s in range(shutter_relay, shutter_relay + 2):
                        relays.pop(s, None)
            return relays
        return {}

    def shutters(self) -> dict:
        return {
            k: self.p[f"ShutterRelay{k}"]
            for k in range(1, 5)
            if f"ShutterRelay{k}" in self.p and self.p[f"ShutterRelay{k}"] != 0
        }

    def shutter_positions(self) -> dict:
        x = {k: self.p[f"Shutter{k}"] for k in range(1, 5) if f"Shutter{k}" in self.p}
        return x

    def pulsetime(self):
        ptime = {}
        for k, v in self.p.items():
            if k.startswith("PulseTime"):
                val = 0
                if isinstance(v, dict):
                    first_key = list(v.keys())[0]
                    if first_key == "Set":
                        val = v["Set"]
                    else:
                        val = first_key
                elif isinstance(v, str):
                    val = v.split(" ")[0]
                ptime[k] = int(val)
        return ptime

    def pwm(self):
        return {
            k: v
            for k, v in self.p.items()
            if k.startswith("PWM") or (k != "Channel" and k.startswith("Channel"))
        }

    def color(self):
        color = {k: self.p[k] for k in ["Color", "Dimmer", "HSBColor"] if k in self.p.keys()}
        if color:
            color.update({15: self.setoption(15), 17: self.setoption(17), 68: self.setoption(68)})
        return color

    def setoption(self, o):
        if 0 <= o < 32:
            reg = 0
        elif 32 <= o < 50:
            reg = 1
        else:
            reg = 2

        so = self.p.get("SetOption")
        if so:
            if reg in (0, 2, 3):
                options = int(so[reg], 16)
                if reg > 1:
                    o -= 50
                state = int(options >> o & 1)

            else:
                o -= 32
                if len(so[reg]) == 18:
                    split_register = [int(so[reg][opt * 2 : opt * 2 + 2], 16) for opt in range(18)]
                else:
                    split_register = [-1] * 18
                return split_register[o]
            return state
        return -1

    @property
    def name(self):
        return self.p.get("DeviceName") or self.p.get("FriendlyName1", self.p["Topic"])

    @property
    def is_online(self):
        return self.p.get("LWT", "Offline") == 'Online'

    @property
    def url(self):
        if url := self.p.get("IPAddress", None):
            return f"http://{url}"

    def version(self, short=True):
        if version := self.p.get("Version"):
            if short and '(' in version:
                return parse_version(version[0 : version.index("(")])
            return version

    def version_above(self, target_version: str):
        return (version := self.version()) and version >= parse_version(target_version) or False

    def __repr__(self):
        return f"<TasmotaDevice {self.name}: {self.p['Topic']}>"
