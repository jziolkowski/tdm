import paho.mqtt.client as mqtt

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSlot

import ssl
import logging

from Util import initial_commands

class MqttClient(QtCore.QObject):
    Disconnected = 0
    Connecting = 1
    Connected = 2

    tlsSetEnabled = False

    MQTT_3_1 = mqtt.MQTTv31
    MQTT_3_1_1 = mqtt.MQTTv311

    connected = QtCore.pyqtSignal()
    connecting = QtCore.pyqtSignal()
    connectError = QtCore.pyqtSignal(int)
    disconnected = QtCore.pyqtSignal()

    stateChanged = QtCore.pyqtSignal(int)
    hostnameChanged = QtCore.pyqtSignal(str)
    portChanged = QtCore.pyqtSignal(int)
    
    sslEnabledChanged = QtCore.pyqtSignal(bool)
    caFileChanged = QtCore.pyqtSignal(str)
    clientCertificateFileChanged = QtCore.pyqtSignal(str)
    clientKeyFileChanged = QtCore.pyqtSignal(str)
    transportChanged = QtCore.pyqtSignal(str)

    clientIdChanged = QtCore.pyqtSignal(str)
    
    keepAliveChanged = QtCore.pyqtSignal(int)
    cleanSessionChanged = QtCore.pyqtSignal(bool)
    protocolVersionChanged = QtCore.pyqtSignal(int)

    messageSignal = QtCore.pyqtSignal(str, str, bool)

    def __init__(self, parent=None):
        super(MqttClient, self).__init__(parent)
        
        # MQTT connection default settings variables
        self.m_hostname = ""
        self.m_port = 1883
        self.m_keepAlive = 60
        self.m_state = MqttClient.Disconnected

        # MQTT client default setting vairables
        self.m_clientId = ""
        self.m_cleanSession = True
        self.m_protocolVersion = MqttClient.MQTT_3_1_1
        self.m_transport = "tcp"

        # MQTT Secure connection default settings variables
        self.m_sslEnabled = False
        self.m_caFile = None
        self.m_clientCertificateFile = None
        self.m_clientKeyFile = None

        # Initialize client default settings
        self.m_client = mqtt.Client(client_id=self.m_clientId,
            clean_session=self.m_cleanSession,
            protocol=self.protocolVersion,
            transport=self.m_transport)

        self.m_client.on_connect = self.on_connect
        self.m_client.on_message = self.on_message
        self.m_client.on_disconnect = self.on_disconnect
    
    # Wire all MQTT settings variables change (gets and sets) methods
    @QtCore.pyqtProperty(str, notify=hostnameChanged)
    def hostname(self):
        return self.m_hostname

    @hostname.setter
    def hostname(self, hostname):
        if self.m_hostname == hostname: return
        self.m_hostname = hostname
        self.hostnameChanged.emit(hostname)

    @QtCore.pyqtProperty(int, notify=portChanged)
    def port(self):
        return self.m_port

    @port.setter
    def port(self, port):
        if self.m_port == port: return
        if port in (443, 1883, 8883):
            self.m_port = port
            self.portChanged.emit(port)

    @QtCore.pyqtProperty(int, notify=keepAliveChanged)
    def keepAlive(self):
        return self.m_keepAlive

    @keepAlive.setter
    def keepAlive(self, keepAlive):
        if self.m_keepAlive == keepAlive: return
        self.m_keepAlive = keepAlive
        self.keepAliveChanged.emit(keepAlive)
    
    @QtCore.pyqtProperty(int, notify=stateChanged)
    def state(self):
        return self.m_state

    @state.setter
    def state(self, state):
        if self.m_state == state: return
        self.m_state = state
        self.stateChanged.emit(state)

    @QtCore.pyqtProperty(str, notify=clientIdChanged)
    def clientId(self):
        return self.m_clientId

    @clientId.setter
    def clientId(self, clientId):
        if self.m_clientId == clientId: return
        self.m_clientId = clientId
        self.clientIdChanged.emit(clientId)
        
    @QtCore.pyqtProperty(bool, notify=cleanSessionChanged)
    def cleanSession(self):
        return self.m_cleanSession

    @cleanSession.setter
    def cleanSession(self, cleanSession):
        if self.m_cleanSession == cleanSession: return
        self.m_cleanSession = cleanSession
        self.cleanSessionChanged.emit(cleanSession)

    @QtCore.pyqtProperty(int, notify=protocolVersionChanged)
    def protocolVersion(self):
        return self.m_protocolVersion

    @protocolVersion.setter
    def protocolVersion(self, protocolVersion):
        if self.m_protocolVersion == protocolVersion: return
        if protocolVersion in (MqttClient.MQTT_3_1, MqttClient.MQTT_3_1_1):
            self.m_protocolVersion = protocolVersion
            self.protocolVersionChanged.emit(protocolVersion)

    @QtCore.pyqtProperty(str, notify=transportChanged)
    def transport(self):
        return self.m_transport

    @transport.setter
    def transport(self, transport):
        if self.m_transport == transport: return
        if transport in ("tcp", "websockets"):
            self.m_transport = transport
            self.transportChanged.emit(transport)

    @QtCore.pyqtProperty(bool, notify=sslEnabledChanged)
    def sslEnabled(self):
        return self.m_sslEnabled

    @sslEnabled.setter
    def sslEnabled(self, sslEnabled):
        if self.m_sslEnabled == sslEnabled: return
        self.m_sslEnabled = sslEnabled
        self.sslEnabledChanged.emit(sslEnabled)

    @QtCore.pyqtProperty(str, notify=caFileChanged)
    def caFile(self):
        return self.m_caFile

    @caFile.setter
    def caFile(self, caFile):
        if self.m_caFile == caFile: return
        self.m_caFile = caFile
        self.caFileChanged.emit(caFile)

    @QtCore.pyqtProperty(str, notify=clientCertificateFileChanged)
    def clientCertificateFile(self):
        return self.m_clientCertificateFile

    @clientCertificateFile.setter
    def clientCertificateFile(self, clientCertificateFile):
        if self.m_clientCertificateFile == clientCertificateFile: return
        self.m_clientCertificateFile = clientCertificateFile
        self.clientCertificateFileChanged.emit(clientCertificateFile)

    @QtCore.pyqtProperty(str, notify=clientKeyFileChanged)
    def clientKeyFile(self):
        return self.m_clientKeyFile

    @clientKeyFile.setter
    def clientKeyFile(self, clientKeyFile):
        if self.m_clientKeyFile == clientKeyFile: return
        self.m_clientKeyFile = clientKeyFile
        self.clientKeyFileChanged.emit(clientKeyFile)

    # Method to set the MQTT username and password if used (optional)
    def setAuth(self, username, password):
        self.m_client.username_pw_set(username, password)

    #################################################################
    # MQTT connect, disconnect, subscribe and publish methods 
    #################################################################
    @QtCore.pyqtSlot()
    def connectToHost(self):
        # Notify and display status that MQTT is in process of connecting
        if self.m_hostname:
            self.connecting.emit()

            # Update latest values for MQTT client
            self.m_client._client_id = self.m_clientId
            self.m_client._clean_session = self.m_cleanSession
            self.m_client._protocol = self.m_protocolVersion
            self.m_client._transport = self.m_transport
            
            # Try to MQTT connect based on settings display exception if not successful
            try:
                # MQTT secure connect via 8883 or 443 with or without client certificates or username
                # and password, otherwise connect via unsecure with/without username and password
                if self.sslEnabled and self.m_port in (443,8883):
                    # MQTT client secure TLS settings must be set for a secure connection
                    if not MqttClient.tlsSetEnabled:
                        self.m_client.tls_set(ca_certs=self.m_caFile,
                            certfile=self.m_clientCertificateFile,
                            keyfile=self.m_clientKeyFile,
                            cert_reqs=ssl.CERT_REQUIRED,
                            tls_version=ssl.PROTOCOL_TLS,
                            ciphers=None)
                        MqttClient.tlsSetEnabled = True
                else:
                    self.sslEnabled = False
                    MqttClient.tlsSetEnabled = False

                self.m_client.connect(self.m_hostname,
                    port=self.port,
                    keepalive=self.keepAlive)

                self.state = MqttClient.Connecting
                self.m_client.loop_start()
            except:
                self.connectError.emit(3)
        else:
            self.connectError.emit("Hostname has not be setup in broker settings")

    @QtCore.pyqtSlot()
    def disconnectFromHost(self):
        self.m_client.loop_stop()
        self.m_client.disconnect()

    def subscribe(self, path):
        if self.state == MqttClient.Connected:
            self.m_client.subscribe(path)
            logging.info("MQTT: Subscribed to %s", ", ".join([p[0] for p in path]))

    @pyqtSlot(str, str)
    def publish(self, topic, payload = None, qos=0, retain=False):
        if self.state == MqttClient.Connected:
            self.m_client.publish(topic, payload, qos, retain)

    #################################################################
    # MQTT Callbacks methods: message, connect and disconnect
    #################################################################
    def on_message(self, mqttc, obj, msg):
        topic = msg.topic
        try:
            mstr = msg.payload.decode("utf8")
            retained = msg.retain
            self.messageSignal.emit(topic, mstr, retained)
        except UnicodeDecodeError as e:
            logging.error('MQTT MESSAGE DECODE ERROR: %s', e)

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