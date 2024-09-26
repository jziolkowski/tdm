import pytest

from tdmgr.tasmota.common import CTRange


class TestDeviceProps:

    @staticmethod
    @pytest.mark.parametrize("device_power", (["ON", "OFF"],), indirect=True)
    @pytest.mark.parametrize(
        "idx_only, expected",
        [
            (True, 2),
            (False, 3),
        ],
    )
    def test_matching_items(device_power, idx_only, expected):
        from tdmgr.tasmota.common import DeviceProps

        p = DeviceProps(**device_power)
        p.update(**{"POWER": "ON", "Dummy": "Value"})

        res = list(p.matching_items("POWER", idx_only))
        assert len(res) == expected


@pytest.mark.parametrize(
    "v,f,t,expected",
    [
        (12, 100, 255, 30),
        (34, 100, 255, 86),
        (56, 100, 255, 142),
        (78, 100, 255, 198),
        (91, 100, 255, 232),
        (30, 255, 100, 11),
        (86, 255, 100, 33),
        (142, 255, 100, 55),
        (198, 255, 100, 77),
        (232, 255, 100, 90),
        (50, 100, CTRange, 326),
        (326, CTRange, 100, 49),
    ],
)
def test_map(v, f, t, expected):
    from tdmgr.tasmota.common import map_value

    res = map_value(v, f, t)
    assert res == expected
