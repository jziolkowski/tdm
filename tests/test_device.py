import pytest

from tdmgr.util import Message, TasmotaDevice


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
    assert device.matches(topic) is expected


@pytest.mark.parametrize("topic", ["stat/device/RESULT", "stat/device/TEMPLATE"])
def test_process_template(topic):
    device = TasmotaDevice("device")
    message = Message(topic, b'{"NAME":"NodeMCU","GPIO":[1],"FLAG":0,"BASE":18}')
    message.prefix = "stat"

    device.process_message(message)

    assert message.first_key == "NAME"
    assert device.p.get("Template") == "NodeMCU"
