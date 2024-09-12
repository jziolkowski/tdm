import pytest

from tdmgr.util import TasmotaDevice, TasmotaEnvironment


@pytest.mark.parametrize(
    "full_topic, test_topic, expected",
    [
        ("%prefix%/%topic%/", "tele/device/POWER", True),
        ("%prefix%/%topic%/", "stat/device/POWER", True),
        ("office/%prefix%/%topic%/", "office/stat/device/POWER", True),
        ("office/%prefix%/%topic%/", "stat/device/POWER", False),
        ("%prefix%/office/%topic%/", "stat/office/device/POWER", True),
        ("%prefix%/office/%topic%/", "office/stat/device/POWER", False),
    ],
)
def test_find_device(full_topic, test_topic, expected):
    env = TasmotaEnvironment()
    dev = TasmotaDevice(topic='device', fulltopic=full_topic)
    env.devices.append(dev)

    device = env.find_device(test_topic)

    assert (device == dev) is expected
