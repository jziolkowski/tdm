import pytest

from tdmgr.util import Message, TasmotaDevice


@pytest.fixture
def device(request):
    topic = "device"
    if request.param:
        topic = request.param
    yield TasmotaDevice(topic)


@pytest.fixture
def state_message(request, device):
    yield Message(f"tele/{device.p['Topic']}/STATE", request.param, prefix="stat")
