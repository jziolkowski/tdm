import pytest

from util import TasmotaDevice


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
