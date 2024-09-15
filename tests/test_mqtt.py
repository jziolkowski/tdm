import pytest

from tdmgr.mqtt import expand_fulltopic


@pytest.mark.parametrize(
    "fulltopic, expected",
    [
        ("%prefix%/%topic%/", ['tele/#', 'stat/#']),
        ("%prefix%/%topic%", ['tele/#', 'stat/#']),
        ("+/%prefix%/%topic%/", ['+/tele/#', '+/stat/#']),
        ("+/%prefix%/%topic%", ['+/tele/#', '+/stat/#']),
    ],
)
def test_expand_fulltopic(fulltopic, expected):
    result = expand_fulltopic(fulltopic)

    assert result == expected
