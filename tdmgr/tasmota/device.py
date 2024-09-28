import json
import logging
import re
from collections import defaultdict
from functools import lru_cache
from typing import Callable, DefaultDict, List, Optional, Union

from pkg_resources import parse_version
from pydantic import BaseModel, ValidationError
from PyQt5.QtCore import QObject, pyqtSignal

from tdmgr.mqtt import DEFAULT_PATTERNS, MQTT_PATH_REGEX, Message
from tdmgr.schemas.discovery import DiscoverySchema, TopicPrefixes
from tdmgr.schemas.result import (
    PulseTimeLegacyResultSchema,
    PulseTimeResultSchema,
    ShutterResultSchema,
    TemplateResultSchema,
)
from tdmgr.schemas.status import STATUS_SCHEMA_MAP
from tdmgr.tasmota.common import COMMAND_UNKNOWN, MAX_SHUTTERS, Color, DeviceProps, Relay, Shutter

log = logging.getLogger(__name__)


class TasmotaDevice(QObject):
    update_telemetry = pyqtSignal()

    def __init__(self, topic: str, fulltopic: str = "%prefix%/%topic%/", devicename: str = ""):
        super(TasmotaDevice, self).__init__()
        self.p = DeviceProps(
            **{
                "LWT": "undefined",
                "Topic": topic,
                "FullTopic": fulltopic,
                "DeviceName": devicename,
                "Template": {},
                "Online": "Online",
                "Offline": "Offline",
            }
        )

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

        self._pulsetime: Optional[Union[PulseTimeLegacyResultSchema, PulseTimeResultSchema]] = None

        self.processor_map = {
            r"PulseTime\d?": self._process_pulsetime,
            r"Shutter\d?": self._process_shutter,
            r"NAME": self._process_template,
            r"Module$": self._process_module,
            r"Modules\d?": self._process_modules,
            r"GPIO$": self._process_gpio,
            r"GPIO\d?$": self._process_gpio,
            r"GPIOs\d?": self._process_gpios,
        }

        self.subscribers: DefaultDict[BaseModel, List[Callable]] = defaultdict(list)

    @property
    def topic(self) -> str:
        return self.p["Topic"]

    @property
    def fulltopic(self) -> str:
        return self.p["FullTopic"]

    @classmethod
    def from_discovery(cls, obj: DiscoverySchema):
        _ft = obj.ft.replace(obj.t, "%topic%").replace(obj.tp.tele, "%prefix%")
        device = TasmotaDevice(obj.t, _ft, obj.dn)
        device.topic_prefixes = obj.tp
        device.p["Online"] = obj.onln
        device.p["Offline"] = obj.ofln
        device.p["Module"] = obj.md
        return device

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

    def message_topic_matches_fulltopic(self, msg: Message) -> bool:
        if _prefix := re.match(self.fulltopic_regex, msg.topic):
            if not msg.prefix:
                msg.prefix = _prefix.groupdict()["prefix"]
            return True
        return False

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
        old = self.p.get(k)
        if not old or old != v:
            self.p[k] = v
            if self.property_changed:
                self.property_changed(self, k)

    def module(self):
        if mdl := self.p.get("Module"):
            return self.modules.get(str(mdl), mdl)

        if self.p["LWT"] == self.p["Online"]:
            return "(unknown)"

    @property
    def fulltopic_regex(self) -> str:
        _ft_pattern = (
            self.p["FullTopic"]
            .replace("%prefix%", f"(?P<prefix>{MQTT_PATH_REGEX})")
            .replace("%topic%", self.p["Topic"])
        )
        return f"^{_ft_pattern}"

    def register(self, schema: BaseModel, method: Callable):
        if method not in self.subscribers[schema]:
            log.debug("Registered %s for %s schema", method.__name__, schema.__name__)
            self.subscribers[schema].append(method)
        log.debug(
            "Subscribers: %s",
            {
                key.__name__: list(map(lambda v: v.__name__, vals))
                for key, vals in self.subscribers.items()
            },
        )

    def unregister(self, method: Callable):
        for mlist in self.subscribers.values():
            if method in mlist:
                log.debug("Unregistered %s", method.__name__)
                mlist.remove(method)

    # TODO: add to all responses, not just STATUSx
    def notify_subscribers(self, schema: BaseModel, payload: BaseModel):
        for method in self.subscribers[schema]:
            method(payload)

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
        if msg.first_key == "PulseTime1":
            schema = PulseTimeLegacyResultSchema
        else:
            schema = PulseTimeResultSchema
        self._pulsetime = schema.model_validate(msg.dict())

    def _process_shutter(self, msg: Message):
        validated = ShutterResultSchema.model_validate(msg.dict())
        self.notify_subscribers(ShutterResultSchema, validated)

        # TODO: that should be a method
        for k, v in msg.dict().items():
            self.update_property(k, v)

    def _process_template(self, msg: Message):
        _template = TemplateResultSchema.model_validate(msg.dict())
        self.update_property("Template", _template.NAME)

    def _process_logging(self, msg: Message):
        pass

    @lru_cache
    def get_result_processor(self, key) -> Callable:
        for pattern, func in self.processor_map.items():
            if re.match(pattern, key):
                return func

    def _process_result(self, msg: Message):
        # TODO: move this check as a Message property
        if msg.dict() != COMMAND_UNKNOWN:
            if func := self.get_result_processor(msg.first_key):
                func(msg)
            else:
                for k, v in msg.dict().items():
                    self.update_property(k, v)

    def process_status(self, schema: BaseModel, payload: dict):
        try:
            validated = schema.model_validate(payload)
            self.notify_subscribers(schema, validated)

            processed = validated.model_dump(exclude_none=True)

            first_key = next(iter(processed.keys()))
            items = (
                processed[first_key].items()
                if schema.__name__ != "StateSchema"
                else processed.items()
            )

            # TODO: needs to be reworked
            for k, v in items:
                if k == "Wifi":
                    for wk, wv in v.items():
                        self.update_property(wk, wv)
                else:
                    self.update_property(k, v)

        except ValidationError as e:
            log.critical("MQTT: Cannot parse %s", e)

    def process_sensor(self, payload: str):
        sensor_data = json.loads(payload)
        if "StatusSNS" in sensor_data:
            sensor_data = sensor_data["StatusSNS"]
        self.t = sensor_data
        self.update_telemetry.emit()

    def process_message(self, msg: Message):
        if self.debug:
            log.debug("MQTT: %s %s", msg.topic, msg.payload)

        if msg.prefix in (self.topic_prefixes.stat, self.topic_prefixes.tele):
            # /STATE or /STATUS<x> response
            if status_parse_schema := STATUS_SCHEMA_MAP.get(msg.endpoint):
                self.process_status(status_parse_schema, msg.dict())

            # /STATUS8, /STATUS10, /SENSOR are fully dynamic and parsed as-is
            elif msg.endpoint in ("STATUS8", "STATUS10", "SENSOR"):
                self.process_sensor(msg.payload)

            # /LOGGING response
            elif msg.endpoint == "LOGGING":
                self._process_logging(msg)

            # /RESULT or SetOption4
            else:
                self._process_result(msg)

    def is_friendlyname(self, fname: str) -> bool:
        RE_DEFAULT_FNAME = r"(Tasmota|Sonoff|Power)\d?"
        return fname and re.match(RE_DEFAULT_FNAME, fname) is None

    def get_friendlyname(self, idx: int, idx_as_default: bool = True) -> str:
        name = ""
        if (fnames := self.p.get("FriendlyName")) and len(fnames) >= idx:
            fname_idx = idx - 1
            name = (
                fnames[fname_idx]
                if self.is_friendlyname(fnames[fname_idx])
                else f"{idx}"
                if idx_as_default
                else ""
            )
        return name

    def power(self) -> Optional[List[Relay]]:
        def is_locked(idx: int) -> bool:
            if self.p.get("PowerOnState") == 4:
                return True
            powerlock = self.p.get("PowerLock", 32 * "0")
            return powerlock[idx - 1] == "1" if idx <= len(powerlock) else False

        relay_list = list(self.p.matching_items("POWER"))
        relay_count = len(relay_list)

        if (single_relay_state := self.p.get("POWER1", self.p.get("POWER"))) and not self.p.get(
            "POWER2"
        ):
            return [Relay(1, self.get_friendlyname(1, False), single_relay_state, is_locked(1))]

        relays: List[Relay] = []
        if relay_count > 1:
            _relays = dict(relay_list)

            for shutter in self.shutters():
                for s in range(shutter.relay, shutter.relay + 2):
                    _relays.pop(s, None)

            for idx, state in _relays.items():
                relays.append(Relay(idx, self.get_friendlyname(idx), state, is_locked(idx)))

            return relays
        return []

    def shutters(self) -> Optional[List[Shutter]]:
        shutters = []
        for k in range(1, MAX_SHUTTERS + 1):
            if (shutter_relay := self.p.get(f"ShutterRelay{k}")) and shutter_relay != 0:
                shutter = self.p.get(f"Shutter{k}")
                name = self.get_friendlyname(k)
                shutters.append(
                    Shutter(
                        k,
                        shutter_relay,
                        name,
                        shutter["Position"],
                        shutter["Direction"],
                        shutter["Target"],
                    )
                )

        return shutters

    def color(self):
        if color := self.p.get("Color", ""):
            return Color(
                color,
                self.p.get("CT", 0),
                [val for _, val in self.p.matching_items("Dimmer", idx_only=False)],
                self.p.get("HSBColor", ""),
                [val for _, val in self.p.matching_items("Channel")],
                [val for _, val in self.p.matching_items("PWM")],
                *(self.setoption(so) for so in (15, 17, 68)),
            )
        return None

    @property
    def ip_address(self) -> str:
        for ip in [self.p.get("IPAddress"), self.p.get("Ethernet", {}).get("IPAddress")]:
            if ip != "0.0.0.0":
                return ip
        return "0.0.0.0"

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
        if name := self.p.get("DeviceName"):
            return name
        if fnl := self.p.get("FriendlyName"):
            return fnl[0]
        if fn1 := self.p.get("FriendlyName1"):
            return fn1
        return self.p["Topic"]

    @property
    def online(self):
        return self.p.get("LWT", self.p["Offline"]) == self.p["Online"]

    @online.setter
    def online(self, val: Union[bool, dict]):
        if isinstance(val, bool):
            self.update_property("LWT", self.p["Online"])
        else:
            self.update_property("LWT", val)

    @property
    def url(self) -> Optional[str]:
        if self.ip_address != "0.0.0.0":
            return f"http://{self.ip_address}"

    def version(self, short=True):
        if version := self.p.get("Version"):
            if short and "(" in version:
                return parse_version(version[0 : version.index("(")])
            return version

    def version_above(self, target_version: str):
        return (version := self.version()) and version >= parse_version(target_version) or False

    def __repr__(self):
        return f"<TasmotaDevice {self.name}: {self.p['FullTopic']}>"
