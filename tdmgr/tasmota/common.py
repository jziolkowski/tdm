import re
from collections import namedtuple
from typing import Union

from PyQt5.QtGui import QColor

MAX_RELAYS = 32
MAX_SHUTTERS = 8
MAX_PWM = 16
COMMAND_UNKNOWN = {"Command": "Unknown"}

Relay = namedtuple("Relay", "idx, name, state, locked")
Shutter = namedtuple("Shutter", "idx, relay, name, position, direction, target")
Color = namedtuple("Color", "color, ct, dimmers, hsbcolor, channels, pwm, SO15, SO17, SO68")

ValueRange = namedtuple("ValueRange", "min, max")
CTRange = ValueRange(153, 500)


class DeviceProps(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def matching_items(self, pattern: str, idx_only: bool = True):
        pattern = re.compile(
            f"{pattern}(?P<idx>\\d+)" if idx_only else f"{pattern}(?P<idx>\\d+)|{pattern}$"
        )
        for k in sorted(self.keys()):
            if match := pattern.match(k):
                if idx := match.groupdict()['idx']:
                    yield int(idx), self[k]
                else:
                    yield None, self[k]


def map_value(
    value: int, from_range: Union[int, ValueRange], to_range: Union[int, ValueRange]
) -> int:

    if isinstance(from_range, int):
        from_range = ValueRange(0, from_range)

    if isinstance(to_range, int):
        to_range = ValueRange(0, to_range)

    return int(
        to_range.min
        + (to_range.max - to_range.min)
        * ((value - from_range.min) / (from_range.max - from_range.min))
    )


class TasmotaColor(QColor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def fromTasmotaHSB(cls, hsb: str) -> QColor:
        hue, sat, brt = map(int, hsb.split(","))
        return super().fromHsv(hue, map_value(sat, 100, 255), map_value(brt, 100, 255))

    def getTasmotaHSB(self) -> str:
        hue, sat, brt, _ = self.getHsv()
        sat = map_value(sat, 255, 100)
        brt = map_value(brt, 100, 255)
        return ",".join(map(str, (hue, sat, brt)))
