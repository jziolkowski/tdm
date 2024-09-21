import pytest

from tdmgr.mqtt import Message
from tdmgr.tasmota.device import Relay, TasmotaDevice
from tests.conftest import get_payload


@pytest.mark.parametrize(
    "fulltopic, topic, expected",
    [
        ("%prefix%/%topic%/", "tele/some_topic/SENSOR", True),
        ("%topic%/%prefix%/", "tele/some_topic/SENSOR", False),
        ("%prefix%/office/%topic%/", "tele/office/some_topic/SENSOR", True),
        ("%prefix%/%topic%/", "tele/office/some_topic/SENSOR", False),
    ],
)
def test_matches(fulltopic, topic, expected):
    device = TasmotaDevice("some_topic", fulltopic)
    msg = Message(topic)
    assert device.message_topic_matches_fulltopic(msg) is expected


@pytest.mark.parametrize("topic", ["stat/device/RESULT", "stat/device/TEMPLATE"])
def test_process_template(topic):
    device = TasmotaDevice("device")
    message = Message(topic, b'{"NAME":"NodeMCU","GPIO":[1],"FLAG":0,"BASE":18}')
    message.prefix = "stat"

    device.process_message(message)

    assert message.first_key == "NAME"
    assert device.p.get("Template") == "NodeMCU"


@pytest.mark.parametrize("version", ("14.2.0.4",))
@pytest.mark.parametrize(
    "filename, expected",
    [
        ("STATUS5.json", "192.168.0.1"),
        ("STATUS5.1.json", "192.168.7.187"),
    ],
)
def test_ip_address(device, version, filename, expected):
    payload = get_payload(version, filename)
    msg = Message("stat/topic/STATUS5", payload, prefix="stat")
    device.process_message(msg)

    assert device.ip_address == expected


@pytest.mark.parametrize(
    "fname, expected",
    [
        ("", ""),
        ("Tasmota1", ""),
        ("a", "a"),
    ],
)
def test_power_single(device, fname, expected):
    device.p.update(**{"POWER": "ON", "FriendlyName": [fname]})

    res = device.power()
    assert res
    assert len(res) == 1
    assert res[0] == Relay(1, expected, "ON")


@pytest.mark.parametrize("device_power", (["ON", "OFF"],), indirect=True)
@pytest.mark.parametrize(
    "fname, expected",
    [
        ("", ""),
        ("", ""),
        ("", "Tasmota1"),
        ("", ""),
        ("a", ""),
        ("a", ""),
    ],
)
def test_power_multiple(device, device_power, fname, expected):
    device.p.update(**{**device_power, "FriendlyName": fname})

    res = device.power()
    assert res
    assert len(res) == 2
    assert res[0] == Relay(1, expected[0], "ON")
    assert res[1] == Relay(2, expected[1], "OFF")
