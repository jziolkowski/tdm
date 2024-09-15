import pytest

from tdmgr.mqtt import Message


def test_message():
    message = Message("some/topic", b"some_payload", True)

    assert message.topic == "some/topic"
    assert message.payload == "some_payload"
    assert message.retained
    assert not message.is_lwt


def test_message_is_lwt():
    message = Message("office/device/LWT")
    assert message.is_lwt


@pytest.mark.parametrize(
    "topic, endpoint",
    [
        ("some/endpoint", "endpoint"),
        ("office/stat/device/RESULT", "RESULT"),
    ],
)
def test_message_endpoint(topic, endpoint):
    message = Message(topic)
    assert message.endpoint == endpoint


@pytest.mark.parametrize(
    "pattern, topic",
    [
        ("%prefix%/%topic%/", "cmnd/topic/POWER"),
        ("%topic%/%prefix%/", "topic/cmnd/POWER"),
        ("%prefix%/tasmota/%topic%/", "cmnd/tasmota/topic/POWER"),
        ("+/%prefix%/%topic%/", "office/cmnd/topic/POWER"),
        ("+/%prefix%/+/%topic%/", "basement/cmnd/office/topic/POWER"),
        ("+/+/%prefix%/+/%topic%/", "basement/wine_room/cmnd/fans/topic/POWER1"),
    ],
)
def test_topic_matches_pattern(pattern, topic):
    message = Message(topic)
    result = message.match_fulltopic(pattern)

    assert result
    result_groupdict = result.groupdict()

    assert "prefix" in result_groupdict
    assert "topic" in result_groupdict
    assert result_groupdict["prefix"] == "cmnd"
    assert result_groupdict["topic"] == "topic"


def test_message_dict():
    message = Message("topic", b'{"key": "value", "second_key": 42}')

    result = message.dict()
    assert "key" in result
    assert result["second_key"] == 42


def test_message_dict_failed(caplog):
    message = Message("topic/RESULT", b"not json")
    assert message.dict() == {}
