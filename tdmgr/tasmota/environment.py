from enum import Enum

from tdmgr.mqtt import Message
from tdmgr.tasmota.device import TasmotaDevice


class DiscoveryMode(int, Enum):
    BOTH = 0
    NATIVE = 1
    LEGACY = 2


class TasmotaEnvironment:
    def __init__(self):
        self.devices: list[TasmotaDevice] = []
        self.lwts = dict()
        self.retained = set()
        self.mqtt = None

    def add_device(self, device: TasmotaDevice):
        self.devices.append(device)
        device.env = self

    def find_device(self, msg: Message) -> TasmotaDevice:
        for d in self.devices:
            if d.message_topic_matches_fulltopic(msg):
                return d
