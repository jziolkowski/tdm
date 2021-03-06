from PyQt5.QtCore import QSettings, QDir
from PyQt5.QtWidgets import QDialog, QLineEdit, QFormLayout, QPushButton, QGroupBox, QCheckBox, QHBoxLayout, QFileDialog, QLabel

from GUI import SpinBox, HLayout, VLayout

import random
import string

class BrokerDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super(BrokerDialog, self).__init__(*args, **kwargs)

        self.setWindowTitle("MQTT Broker")

        self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)

        gbHost = QGroupBox("Hostname and port")
        hfl = QFormLayout()
        self.hostname = QLineEdit()
        self.hostname.setText(self.settings.value("hostname", "localhost"))
        self.port = SpinBox(maximum=65535)
        self.port.setValue(self.settings.value("port", 1883, int))
        hfl.addRow("Hostname", self.hostname)
        hfl.addRow("Port", self.port)
        gbHost.setLayout(hfl)

        gbCerts = QGroupBox("SSL and Certificates")
        hfl = QFormLayout()

        self.caFile = QLabel()
        self.caFile.setText(self.settings.value("caFile", ""))
        self.btnCaFile = QPushButton("Select File")
        self.caFilelayout = QHBoxLayout()
        self.caFilelayout.addWidget(self.caFile)
        self.caFilelayout.addWidget(self.btnCaFile)

        self.clientCertificateFile = QLabel()
        self.clientCertificateFile.setText(self.settings.value("clientCertificateFile", ""))
        self.btnclientCertificateFile = QPushButton("Select File")
        self.clientCertificateFilelayout = QHBoxLayout()
        self.clientCertificateFilelayout.addWidget(self.clientCertificateFile)
        self.clientCertificateFilelayout.addWidget(self.btnclientCertificateFile)
           
        self.clientKeyFile = QLabel()
        self.clientKeyFile.setText(self.settings.value("clientKeyFile", ""))
        self.btnclientKeyFile = QPushButton("Select File")
        self.clientKeyFilelayout = QHBoxLayout()
        self.clientKeyFilelayout.addWidget(self.clientKeyFile)
        self.clientKeyFilelayout.addWidget(self.btnclientKeyFile)
           
        self.sslEnabled = QCheckBox("Enable SSL")
        self.sslEnabled.setChecked(self.settings.value("sslEnabled", False, bool))
       
        hfl.addRow("CA Root File", self.caFilelayout)
        hfl.addRow("Client Certificate File", self.clientCertificateFilelayout)
        hfl.addRow("Client Key File", self.clientKeyFilelayout)
        hfl.addRow("", self.sslEnabled)
        gbCerts.setLayout(hfl)

        gbLogin = QGroupBox("Credentials [optional]")
        lfl = QFormLayout()
        self.username = QLineEdit()
        self.username.setText(self.settings.value("username", ""))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self.password.setText(self.settings.value("password", ""))
        lfl.addRow("Username", self.username)
        lfl.addRow("Password", self.password)
        gbLogin.setLayout(lfl)

        gbClientId = QGroupBox("Client ID [optional]")
        cfl = QFormLayout()
        self.clientId = QLineEdit()
        self.clientId.setText(self.settings.value("clientId", "tdm-" + self.random_generator()))
        cfl.addRow("Client ID", self.clientId)
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
        self.btnclientCertificateFile.clicked.connect(self.clientCertificateFileSelect)
        self.btnclientKeyFile.clicked.connect(self.clientKeyFileSelect)

        btnSave.clicked.connect(self.accept)
        btnCancel.clicked.connect(self.reject)

    def accept(self):
        self.settings.setValue("hostname", self.hostname.text())
        self.settings.setValue("port", self.port.value())
        self.settings.setValue("username", self.username.text())
        self.settings.setValue("password", self.password.text())
        self.settings.setValue("connect_on_startup", self.cbConnectStartup.isChecked())
        self.settings.setValue("clientId", self.clientId.text())
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

    def clientCertificateFileSelect(self):
        fname = QFileDialog.getOpenFileName(self, 'Select Certificate file',
            "{}/TDM/Certificates/".format(QDir.homePath()),
            "Certificate files (*.crt *.key)")

        if fname[0] != "":
            self.clientCertificateFile.setText(fname[0])
   
    def clientKeyFileSelect(self):
        fname = QFileDialog.getOpenFileName(self, 'Select Certificate file',
            "{}/TDM/Certificates/".format(QDir.homePath()),
            "Certificate files (*.crt *.key)")

        if fname[0] != "":
            self.clientKeyFile.setText(fname[0])
    
    ##################################################################
    # utils
    def random_generator(self, size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for x in range(size))