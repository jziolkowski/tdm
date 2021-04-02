from PyQt5.QtCore import QSettings, QDir
from PyQt5.QtWidgets import QDialog, QLineEdit, QComboBox, QFormLayout, QPushButton, QGroupBox, QCheckBox, QHBoxLayout, QFileDialog, QLabel
from PyQt5.QtGui import QIcon

from GUI import SpinBox, HLayout, VLayout

import random
import string

class BrokerDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super(BrokerDialog, self).__init__(*args, **kwargs)
        
        self.setWindowIcon(QIcon("icons/server-cloud.png"))
        self.setWindowTitle("MQTT Broker")
        self.setMinimumHeight(400)
        self.setMinimumWidth(800)

        self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)

        gbHost = QGroupBox("Hostname and port")
        hfl = QFormLayout()
        self.hostname = QLineEdit()
        self.hostname.setText(self.settings.value("hostname", "localhost"))
        self.cbxPort = QComboBox()
        self.cbxPort.addItems(["1883","8883","443"])
        self.cbxPort.setCurrentText(str(self.settings.value("port", 1883, int)))
        self.cbxPort.currentIndexChanged.connect(self.portChanged)
        self.port = int(self.cbxPort.currentText())
        lblTransport = QLabel("  Transport: ")
        self.transport = QLabel(self.settings.value("transport", "tcp"))
        lblKeepAlive = QLabel("  Keep Alive Seconds: ")
        self.keepAlive = SpinBox(maximum=240)
        self.keepAlive.setValue(self.settings.value("keepalive", 60, int))
        hfl.addRow("Hostname: ", self.hostname)
        
        pka = HLayout()
        pka.addWidgets([self.cbxPort, lblTransport, self.transport, lblKeepAlive, self.keepAlive])
        hfl.addRow("Port: ", pka)
        gbHost.setLayout(hfl)

        gbCerts = QGroupBox("SSL and Certificates")
        hfl = QFormLayout()

        self.caFile = QLabel()
        self.caFile.setText(self.settings.value("caFile", "None"))
        self.btnCaFile = QPushButton("Select File")
        self.bthCaFileClear = QPushButton("Clear")
        self.caFilelayout = QHBoxLayout()
        self.caFilelayout.addWidget(self.caFile)
        self.caFilelayout.addWidget(self.btnCaFile)
        self.caFilelayout.addWidget(self.bthCaFileClear)

        self.clientCertificateFile = QLabel()
        self.clientCertificateFile.setText(self.settings.value("clientCertificateFile", "None"))
        self.btnclientCertificateFile = QPushButton("Select File")
        self.btnclientCertificateFileClear = QPushButton("Clear")
        self.clientCertificateFilelayout = QHBoxLayout()
        self.clientCertificateFilelayout.addWidget(self.clientCertificateFile)
        self.clientCertificateFilelayout.addWidget(self.btnclientCertificateFile)
        self.clientCertificateFilelayout.addWidget(self.btnclientCertificateFileClear)
           
        self.clientKeyFile = QLabel()
        self.clientKeyFile.setText(self.settings.value("clientKeyFile", "None"))
        self.btnclientKeyFile = QPushButton("Select File")
        self.btnclientKeyFileClear = QPushButton("Clear")
        self.clientKeyFilelayout = QHBoxLayout()
        self.clientKeyFilelayout.addWidget(self.clientKeyFile)
        self.clientKeyFilelayout.addWidget(self.btnclientKeyFile)
        self.clientKeyFilelayout.addWidget(self.btnclientKeyFileClear)
           
        self.sslEnabled = QCheckBox("Enable SSL")
        self.sslEnabled.setChecked(self.settings.value("sslEnabled", False, bool))
       
        hfl.addRow("CA Root File: ", self.caFilelayout)
        hfl.addRow("Client Certificate File: ", self.clientCertificateFilelayout)
        hfl.addRow("Client Key File: ", self.clientKeyFilelayout)
        hfl.addRow("Secure Sockets Layer: ", self.sslEnabled)
        gbCerts.setLayout(hfl)

        gbLogin = QGroupBox("Credentials [optional]")
        lfl = QFormLayout()
        self.username = QLineEdit()
        self.username.setText(self.settings.value("username", ""))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self.password.setText(self.settings.value("password", ""))
        lfl.addRow("Username: ", self.username)
        lfl.addRow("Password: ", self.password)
        gbLogin.setLayout(lfl)

        gbClientId = QGroupBox("Client ID & Clean Session [optional]")
        cfl = QFormLayout()
        self.clientId = QLineEdit()
        self.clientId.setText(self.settings.value("clientId", "tdm-" + self.random_generator()))
        self.cleanSession = QCheckBox("Clean Session")
        self.cleanSession.setChecked(self.settings.value("cleansession", True, bool))
        ccs = HLayout()
        ccs.addWidgets([self.clientId, self.cleanSession])
        cfl.addRow("Client ID", ccs)
        gbClientId.setLayout(cfl)

        self.cbConnectStartup = QCheckBox("Connect on startup")
        self.cbConnectStartup.setChecked(self.settings.value("connect_on_startup", False, bool))

        hlBtn = HLayout()
        btnSave = QPushButton("Save")
        btnCancel = QPushButton("Cancel")
        hlBtn.addWidgets([btnSave, btnCancel])

        vl = VLayout()
        vl.addWidgets([gbHost, gbCerts, gbClientId, gbLogin, self.cbConnectStartup])
        vl.addLayout(hlBtn)

        self.setLayout(vl)

        self.btnCaFile.clicked.connect(self.caFileSelect)
        self.bthCaFileClear.clicked.connect(self.CaFileClear)

        self.btnclientCertificateFile.clicked.connect(self.clientCertificateFileSelect)
        self.btnclientCertificateFileClear.clicked.connect(self.clientCertificateFileClear)
        
        self.btnclientKeyFile.clicked.connect(self.clientKeyFileSelect)
        self.btnclientKeyFileClear.clicked.connect(self.clientKeyFileClear)

        btnSave.clicked.connect(self.accept)
        btnCancel.clicked.connect(self.reject)

    def portChanged(self):
        self.port = int(self.cbxPort.currentText())
        if self.port == 443:
            self.transport.setText("websockets")
        else:    
            self.transport.setText("tcp")

    def accept(self):
        self.settings.setValue("hostname", self.hostname.text())
        self.settings.setValue("port", self.port)
        self.settings.setValue("transport", self.transport.text())
        self.settings.setValue("keepalive", self.keepAlive.value())
        self.settings.setValue("username", self.username.text())
        self.settings.setValue("password", self.password.text())
        self.settings.setValue("connect_on_startup", self.cbConnectStartup.isChecked())
        self.settings.setValue("clientId", self.clientId.text())
        self.settings.setValue("cleansession", self.cleanSession.isChecked())
        self.settings.setValue("caFile", self.caFile.text())
        self.settings.setValue("clientCertificateFile", self.clientCertificateFile.text())
        self.settings.setValue("clientKeyFile", self.clientKeyFile.text())
        self.settings.setValue("sslEnabled", self.sslEnabled.isChecked())
        self.settings.sync()
        self.done(QDialog.Accepted)

    def caFileSelect(self):
        fname = QFileDialog.getOpenFileName(self, 'Select Certificate file',
            "{}/TDM/Certificates/".format(QDir.homePath()),
            "Certificate files (*.crt *.key)")

        if fname[0] != "":
            self.caFile.setText(fname[0])
    
    def CaFileClear(self):
        self.caFile.setText("None")

    def clientCertificateFileSelect(self):
        fname = QFileDialog.getOpenFileName(self, 'Select Certificate file',
            "{}/TDM/Certificates/".format(QDir.homePath()),
            "Certificate files (*.crt *.key)")

        if fname[0] != "":
            self.clientCertificateFile.setText(fname[0])

    def clientCertificateFileClear(self):
        self.clientCertificateFile.setText("None")
   
    def clientKeyFileSelect(self):
        fname = QFileDialog.getOpenFileName(self, 'Select Certificate file',
            "{}/TDM/Certificates/".format(QDir.homePath()),
            "Certificate files (*.crt *.key)")

        if fname[0] != "":
            self.clientKeyFile.setText(fname[0])

    def clientKeyFileClear(self):
        self.clientKeyFile.setText("None")
    
    ##################################################################
    # utils
    def random_generator(self, size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for x in range(size))