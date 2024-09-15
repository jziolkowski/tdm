import json
import logging
import re
import socket
import ssl
from datetime import datetime
from functools import lru_cache
from json import JSONDecodeError
from typing import Match, Union

import paho.mqtt.client as mqtt
from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

log = logging.getLogger(__name__)

MQTT_PATH_REGEX = "[^+#*>$/]+"  # all symbols accepted except forbidden by MQTT topic spec

DEFAULT_PREFIXES = ["tele", "stat"]

DEFAULT_PATTERNS = [
    "%prefix%/%topic%/",  # = %prefix%/%topic% (Tasmota default)
    "%topic%/%prefix%/",  # = %topic%/%prefix% (Tasmota with SetOption19 enabled for
    # HomeAssistant AutoDiscovery)
]


def initial_commands():
    commands = [
        "template",
        "modules",
        "gpio",
        "buttondebounce",
        "switchdebounce",
        "interlock",
        "blinktime",
        "blinkcount",
        "pulsetime",
    ]

    commands = [(command, "") for command in commands]
    commands += [("status", "0"), ("gpios", "255")]

    for sht in range(8):
        commands.append([f"shutterrelay{sht + 1}", ""])
        commands.append([f"shutterposition{sht + 1}", ""])

    return commands


def expand_fulltopic(fulltopic):
    if fulltopic[-1] != '/':
        fulltopic = f"{fulltopic}/"
    fulltopics = []
    for prefix in DEFAULT_PREFIXES:
        topic = (
            fulltopic.replace("%prefix%", prefix).replace("%topic%", "+") + "#"
        )  # expand prefix and topic
        topic = topic.replace("+/#", "#")  # simplify wildcards
        fulltopics.append(topic)
    return fulltopics


class Message:
    def __init__(self, topic: str, payload: bytes = b"", retained: bool = False, **kwargs):
        self.topic: str = topic
        self.prefix: str = kwargs.get("prefix", "")
        self.payload: str = payload.decode('utf-8')
        self.retained: bool = retained
        self.payload: Union[dict, str]
        self.timestamp: datetime = datetime.now()

    @property
    def endpoint(self) -> str:
        return self.topic.split('/')[-1]

    @property
    def is_lwt(self) -> bool:
        return self.endpoint == "LWT"

    @property
    def is_result(self) -> bool:
        return self.endpoint == "RESULT"

    @property
    def first_key(self) -> str:
        return next(iter(self.dict().keys())) if self.dict() else ""

    @lru_cache
    def dict(self) -> dict:
        if self.payload.startswith("{"):
            try:
                return json.loads(self.payload)
            except JSONDecodeError as e:
                log.critical("Cannot parse %s: %s (%s)", self.endpoint, self.payload, e)
        return {}

    def match_fulltopic(self, pattern: str) -> Union[Match, None]:
        _replaced_pattern = (
            pattern.replace("+", f"({MQTT_PATH_REGEX})")
            .replace("%topic%", f"(?P<topic>{MQTT_PATH_REGEX})")
            .replace("%prefix%", f"(?P<prefix>{MQTT_PATH_REGEX})")
        )
        _match = re.fullmatch(
            f"^{_replaced_pattern}{MQTT_PATH_REGEX}$",
            self.topic,
        )
        if _match:
            self.prefix = _match.groupdict()["prefix"]
        return _match


class MqttClient(QObject):
    Disconnected = 0
    Connecting = 1
    Connected = 2

    MQTT_3_1 = mqtt.MQTTv31
    MQTT_3_1_1 = mqtt.MQTTv311

    connected = pyqtSignal()
    connecting = pyqtSignal()
    connectError = pyqtSignal(int)
    disconnected = pyqtSignal()

    stateChanged = pyqtSignal(int)
    hostnameChanged = pyqtSignal(str)
    portChanged = pyqtSignal(int)
    keepAliveChanged = pyqtSignal(int)
    cleanSessionChanged = pyqtSignal(bool)
    protocolVersionChanged = pyqtSignal(int)

    messageSignal = pyqtSignal(Message)

    def __init__(self, parent=None):
        super(MqttClient, self).__init__(parent)

        self.m_hostname = ""
        self.m_port = 1883
        self.m_tls_is_set = False
        self.ssl = False
        self.m_tls_insecure = True
        self.m_tls_version = ssl.PROTOCOL_TLSv1_2
        self.m_cert_file = "/cert/cert/ca.crt"
        self.m_keepAlive = 60
        self.m_cleanSession = True
        self.m_protocolVersion = MqttClient.MQTT_3_1

        self.m_state = MqttClient.Disconnected

        self.m_client = mqtt.Client(
            clean_session=self.m_cleanSession, protocol=self.protocolVersion
        )

        self.m_client.on_connect = self.on_connect
        self.m_client.on_message = self.on_message
        self.m_client.on_disconnect = self.on_disconnect

    @pyqtProperty(int, notify=stateChanged)
    def state(self):
        return self.m_state

    @state.setter
    def state(self, state):
        if self.m_state == state:
            return
        self.m_state = state
        self.stateChanged.emit(state)

    @pyqtProperty(str, notify=hostnameChanged)
    def hostname(self):
        return self.m_hostname

    @hostname.setter
    def hostname(self, hostname):
        if self.m_hostname == hostname:
            return
        self.m_hostname = hostname
        self.hostnameChanged.emit(hostname)

    @pyqtProperty(int, notify=portChanged)
    def port(self):
        return self.m_port

    @port.setter
    def port(self, port):
        if self.m_port == port:
            return
        self.m_port = port
        self.portChanged.emit(port)

    def setAuth(self, username, password):
        self.m_client.username_pw_set(username, password)

    @pyqtProperty(int, notify=keepAliveChanged)
    def keepAlive(self):
        return self.m_keepAlive

    @keepAlive.setter
    def keepAlive(self, keepAlive):
        if self.m_keepAlive == keepAlive:
            return
        self.m_keepAlive = keepAlive
        self.keepAliveChanged.emit(keepAlive)

    @pyqtProperty(bool, notify=cleanSessionChanged)
    def cleanSession(self):
        return self.m_cleanSession

    @cleanSession.setter
    def cleanSession(self, cleanSession):
        if self.m_cleanSession == cleanSession:
            return
        self.m_cleanSession = cleanSession
        self.cleanSessionChanged.emit(cleanSession)

    @pyqtProperty(int, notify=protocolVersionChanged)
    def protocolVersion(self):
        return self.m_protocolVersion

    @protocolVersion.setter
    def protocolVersion(self, protocolVersion):
        if self.m_protocolVersion == protocolVersion:
            return
        if protocolVersion in (MqttClient.MQTT_3_1, MqttClient.MQTT_3_1_1):
            self.m_protocolVersion = protocolVersion
            self.protocolVersionChanged.emit(protocolVersion)

    #################################################################
    @pyqtSlot()
    def connectToHost(self):
        if self.m_hostname:
            self.connecting.emit()
            try:
                # TLS setup
                if self.ssl and not self.m_tls_is_set:
                    if self.m_tls_insecure:
                        self.m_client.tls_set(tls_version=self.m_tls_version)
                    else:
                        self.m_client.tls_set(self.m_cert_file, tls_version=self.m_tls_version)

                    self.m_client.tls_insecure_set(self.m_tls_insecure)
                    self.m_tls_is_set = True

                self.m_client.connect(self.m_hostname, port=self.port, keepalive=self.keepAlive)

                self.state = MqttClient.Connecting
                self.m_client.loop_start()
            except socket.timeout:
                self.connectError.emit(3)

    @pyqtSlot()
    def setSSL(self, broker_tls_file, broker_tls_insecure, broker_tls_version):
        self.ssl = True
        self.m_tls_insecure = broker_tls_insecure
        self.m_tls_version = broker_tls_version
        self.m_cert_file = broker_tls_file

    @pyqtSlot()
    def unsetSSL(self):
        self.ssl = False

    @pyqtSlot()
    def disconnectFromHost(self):
        self.m_client.loop_stop()
        self.m_client.disconnect()

    def subscribe(self, path):
        if self.state == MqttClient.Connected:
            self.m_client.subscribe(path)
            log.info("Subscribed to %s", ", ".join([p[0] for p in path]))

    @pyqtSlot(str, str)
    def publish(self, topic, payload=None, qos=0, retain=False):
        if self.state == MqttClient.Connected:
            self.m_client.publish(topic, payload, qos, retain)

    #################################################################
    # callbacks
    def on_message(self, mqttc, obj, msg):
        try:
            message = Message(msg.topic, msg.payload, msg.retain)
            self.messageSignal.emit(message)
        except UnicodeDecodeError as e:
            log.error("MESSAGE DECODE ERROR: %s (%s=%s)", e, msg.topic, msg.payload.__repr__())

    def on_connect(self, *args):
        rc = args[3]
        if rc == 0:
            self.state = MqttClient.Connected
            self.connected.emit()
        else:
            self.state = MqttClient.Disconnected
            self.connectError.emit(rc)

    def on_disconnect(self, *args):
        self.state = MqttClient.Disconnected
        self.disconnected.emit()
