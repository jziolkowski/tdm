import os

import pytest

from tdmgr.mqtt import Message
from tdmgr.tasmota.device import TasmotaDevice


def get_payload(version: str, filename: str) -> bytes:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'status_parsing', 'jsonfiles')
    fname = os.path.join(path, version, filename)
    with open(fname, 'rb') as f:
        return f.read()


@pytest.fixture
def device(request):
    topic = "device"
    if hasattr(request, "param"):
        topic = request.param
    yield TasmotaDevice(topic)


@pytest.fixture
def state_message(request, device):
    yield Message(f"tele/{device.p['Topic']}/STATE", request.param, prefix="stat")
