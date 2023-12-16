import json
import logging
import re
from enum import Enum
from functools import lru_cache
from typing import Callable

from pkg_resources import parse_version
from pydantic import BaseModel, ValidationError
from PyQt5.QtCore import QObject, pyqtSignal

from schemas.discovery import DiscoverySchema, TopicPrefixes
from schemas.result import PulseTimeLegacyResultSchema, PulseTimeResultSchema, TemplateResultSchema
from schemas.status import STATUS_SCHEMA_MAP
from util.mqtt import DEFAULT_PATTERNS, MQTT_PATH_REGEX, Message

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
        "template",
        "modules",
        "gpio",
        # "buttondebounce",
        # "switchdebounce",
        # "interlock",
        # "blinktime",
        # "blinkcount",
        # "pulsetime"
    ]

    commands = [(command, "") for command in commands]
    commands += [("status", "0"), ("gpios", "255")]

    for sht in range(4):
        commands.append([f"shutterrelay{sht + 1}", ""])
        commands.append([f"shutterposition{sht + 1}", ""])

    return commands


def parse_payload(payload):
    match = re.match(r"(\d+) \((.*)\)", payload)
    if match:
        return dict([match.groups()])
    return {}


class DiscoveryMode(int, Enum):
    BOTH = 0
    NATIVE = 1
    LEGACY = 2


class TasmotaEnvironment(object):
    def __init__(self):
        self.devices = []
        self.lwts = dict()
        self.retained = set()

    def find_device(self, topic) -> 'TasmotaDevice':
        for d in self.devices:
            if d.matches(topic):
                return d


class TasmotaDevice(QObject):
    update_telemetry = pyqtSignal()

    def __init__(self, topic: str, fulltopic: str, devicename: str = ""):
        super(TasmotaDevice, self).__init__()
        self.p = {
            "LWT": "undefined",
            "Topic": topic,
            "FullTopic": fulltopic,
            "DeviceName": devicename,
            "Template": {},
            "Online": "Online",
            "Offline": "Offline",
        }

        # self.props = Properties(Topic=topic, FullTopic=fulltopic, DeviceName=devicename)

        self.debug = False
        self.env = None
        self.history = []

        self.topic_prefixes = TopicPrefixes("cmnd", "stat", "tele")

        self.property_changed = None  # property changed callback pointer

        self.t = None

        self.modules = {}  # supported modules
        self.module_changed = None  # module changed callback pointer

        self.gpios = {}  # supported GPIOs
        self.gpio = {}  # gpio config

        # self._status_processors = self._get_status_processors()
        self._result_processors = self._get_result_processors()

        self.processor_map = {
            r"PulseTime\d?": self._process_pulsetime,
            r"NAME": self._process_template,
            r"Module$": self._process_module,
            r"Modules\d?": self._process_modules,
            r"GPIO$": self._process_gpio,
            r"GPIO\d?$": self._process_gpio,
            r"GPIOs\d?": self._process_gpios,
        }

    @classmethod
    def from_discovery(cls, obj: DiscoverySchema):
        logging.debug(obj)
        _ft = obj.ft.replace(obj.t, "%topic%").replace(obj.tp.tele, "%prefix%")
        device = TasmotaDevice(obj.t, _ft, obj.dn)
        device.topic_prefixes = obj.tp
        device.p["Online"] = obj.onln
        device.p["Offline"] = obj.ofln
        device.p["Module"] = obj.md
        return device

    def _get_result_processors(self):
        PROCESSOR_METHOD_PREFIX = '_process_response_'
        method_names = [
            method_name
            for method_name in self.__class__.__dict__
            if method_name.startswith(PROCESSOR_METHOD_PREFIX)
        ]
        return {
            method_name.replace(PROCESSOR_METHOD_PREFIX, ''): getattr(self, method_name)
            for method_name in method_names
        }

    def build_topic(self, prefix):
        return (
            self.p["FullTopic"]
            .replace("%prefix%", prefix)
            .replace("%topic%", self.p["Topic"])
            .rstrip("/")
        )

    def cmnd_topic(self, command=""):
        return f"{self.build_topic(self.topic_prefixes.cmnd)}/{command}".rstrip("/")

    def stat_topic(self, command=""):
        return f"{self.build_topic(self.topic_prefixes.stat)}/{command}".rstrip("/")

    def tele_topic(self, endpoint=""):
        return f"{self.build_topic(self.topic_prefixes.tele)}/{endpoint}".rstrip("/")

    def is_default(self):
        return self.p["FullTopic"] in DEFAULT_PATTERNS

    @property
    def subscribable_topics(self):
        topics = []
        for topic_prefix in (self.topic_prefixes.tele, self.topic_prefixes.stat):
            _ft = self.p["FullTopic"].replace("%prefix%", topic_prefix).replace("%topic%", "+")
            if _ft[-1] != "/":
                _ft = f"{_ft}/"
            _ft = f"{_ft}+"
            _ft.replace("+/+", "#")
        return topics

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
            return self.modules.get(str(mdl), mdl)

        if self.p["LWT"] == self.p["Online"]:
            return "Fetching module name..."

    @property
    def fulltopic_regex(self) -> str:
        _ft_pattern = (
            self.p["FullTopic"]
            .replace("%prefix%", f"(?P<prefix>{MQTT_PATH_REGEX})")
            .replace("%topic%", self.p["Topic"])
        )
        return f'^{_ft_pattern}'

    def matches(self, topic: str) -> bool:
        return re.match(self.fulltopic_regex, topic) is not None

    def _process_module(self, msg: Message):
        print(msg.payload)

    def _process_modules(self, msg: Message):
        self.modules.update(**msg.dict()[msg.first_key])

    def _process_gpio(self, msg: Message):
        self.gpio.update(**msg.dict())

    def _process_gpios(self, msg: Message):
        self.gpios.update(**msg.dict()[msg.first_key])

    def _process_pulsetime(self, msg: Message):
        # PulseTime returns all timers since 6.6.0.15
        if "PulseTime1" in msg.dict():
            schema = PulseTimeLegacyResultSchema
        else:
            schema = PulseTimeResultSchema
        _ = schema.model_validate(msg.dict())

    def _process_template(self, msg: Message):
        _ = TemplateResultSchema.model_validate(msg.dict())

    def _process_logging(self, msg: Message):
        pass

    @lru_cache
    def get_result_processor(self, key) -> Callable:
        for pattern, func in self.processor_map.items():
            if re.match(pattern, key):
                return func
        else:
            logging.error("PROCESSING: No processor for result %s", key)

    def _process_result(self, msg: Message):
        if msg.dict() != {"Command": "Unknown"}:
            if func := self.get_result_processor(msg.first_key):
                func(msg)

    def process_status(self, schema: BaseModel, payload: dict):
        try:
            processed = schema.model_validate(payload).model_dump(exclude_none=True)
            first_key = next(iter(processed.keys()))
            items = (
                processed[first_key].items()
                if schema.__name__ != 'StateSchema'
                else processed.items()
            )
            for k, v in items:
                self.update_property(k, v)

        except ValidationError as e:
            print(e)
            print(payload)

    def process_sensor(self, payload: str):
        sensor_data = json.loads(payload)
        if "StatusSNS" in sensor_data:
            sensor_data = sensor_data["StatusSNS"]
        # print(sensor_data)

    def process_message(self, msg: Message):
        if self.debug:
            logging.debug("MQTT: %s %s", msg.topic, msg.payload)

        if msg.prefix in (self.topic_prefixes.stat, self.topic_prefixes.tele):
            # /RESULT
            if msg.endpoint == "RESULT":
                self._process_result(msg)

            # /STATE or /STATUS<x> response
            elif status_parse_schema := STATUS_SCHEMA_MAP.get(msg.endpoint):
                self.process_status(status_parse_schema, msg.dict())

            # /STATUS8, /STATUS10, /SENSOR are fully dynamic and parsed as-is
            elif msg.endpoint in ('STATUS8', 'STATUS10', 'SENSOR'):
                self.process_sensor(msg.payload)

            # /LOGGING response
            elif msg.endpoint == "LOGGING":
                self._process_logging(msg)

            else:
                logging.error("PROCESSING: No processor for endpoint %s", msg.endpoint)
                print(msg.payload)

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
