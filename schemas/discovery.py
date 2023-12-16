from collections import namedtuple
from enum import Enum
from ipaddress import IPv4Address
from typing import Dict, List, Union

from pydantic import BaseModel

TopicPrefixes = namedtuple("TopicPrefixes", "cmnd, stat, tele")


class LightType(int, Enum):
    NONE = 0
    SINGLE = 1
    COLDWARM = 2
    RGB = 3
    RGBW = 4
    RGBCW = 5


class DiscoverySchema(BaseModel):
    ip: IPv4Address
    """IPv4 address"""

    dn: str
    """Device name"""

    fn: List[Union[str, None]]
    """List of FriendlyNames"""

    hn: str
    """Hostname"""

    mac: str
    """MAC address"""

    md: str
    """Module"""

    ofln: str
    """Offline LWT payload"""

    onln: str
    """Online LWT payload"""

    state: List[str]
    """States"""

    sw: str
    """Tasmota firmware version"""

    t: str
    """Topic"""

    ft: str
    """FullTopic"""

    tp: TopicPrefixes
    """Topic prefixes"""

    rl: List[Union[int, None]]
    """Relays"""

    swc: List[int]
    """Switches"""

    btn: List[int]
    """Buttons"""

    so: Dict[str, int]
    """Setoptions"""

    lk: int
    """Light CTRGB linked"""

    lt_st: LightType
    """Light type"""

    ver: int
    """Discovery version"""
