import random
import ssl
import string

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QPushButton,
)

from GUI.widgets import HLayout, SpinBox, VLayout


class BrokerDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super(BrokerDialog, self).__init__(*args, **kwargs)

        self.setWindowTitle("MQTT Broker")

        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "tdm", "tdm")

        gbtls = QGroupBox(" TLS [optional]")
        tlsLayout = QFormLayout()
        self.use_tls = QCheckBox("tls")
        self.use_tls.setChecked(self.settings.value("tls", False, bool))

        self.tls_file = QLineEdit()
        self.tls_file.setText(self.settings.value("tlsfile", "/etc/opentls/certs/ca.crt"))
        self.tls_insecure = QCheckBox("TLS insecure")
        self.tls_insecure.setChecked(self.settings.value("tls_insecure", False, bool))

        self.tls_version = QComboBox(self)
        self.tls_version.addItem("TLSv1.2", ssl.PROTOCOL_TLSv1_2)
        self.tls_version.addItem("TLSv1.1", ssl.PROTOCOL_TLSv1_1)
        self.tls_version.addItem("TLSv1", ssl.PROTOCOL_TLSv1)

        tlsLayout.addRow("Use tls", self.use_tls)
        tlsLayout.addRow("Cert file", self.tls_file)
        tlsLayout.addRow("TLS insecure", self.tls_insecure)
        tlsLayout.addRow("TLS Version", self.tls_version)
        gbtls.setLayout(tlsLayout)

        gbHost = QGroupBox("Hostname and port")
        hfl = QFormLayout()
        self.hostname = QLineEdit()
        self.hostname.setText(self.settings.value("hostname", "localhost"))
        self.port = SpinBox(maximum=65535)
        self.port.setValue(self.settings.value("port", 1883, int))
        hfl.addRow("Hostname", self.hostname)
        hfl.addRow("Port", self.port)
        gbHost.setLayout(hfl)

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
        self.clientId.setText(self.settings.value("client_id", "tdm-" + self.random_generator()))
        cfl.addRow("Client ID", self.clientId)
        gbClientId.setLayout(cfl)

        self.cbConnectStartup = QCheckBox("Connect on startup")
        self.cbConnectStartup.setChecked(self.settings.value("connect_on_startup", False, bool))

        hlBtn = HLayout()
        btnSave = QPushButton("Save")
        btnCancel = QPushButton("Cancel")
        hlBtn.addElements(btnSave, btnCancel)

        vl = VLayout()
        vl.addElements(gbHost, gbtls, gbLogin, gbClientId, self.cbConnectStartup)
        vl.addLayout(hlBtn)

        self.setLayout(vl)

        btnSave.clicked.connect(self.accept)
        btnCancel.clicked.connect(self.reject)

    def accept(self):
        self.settings.setValue("hostname", self.hostname.text())
        self.settings.setValue("port", self.port.value())
        self.settings.setValue("username", self.username.text())
        self.settings.setValue("password", self.password.text())
        self.settings.setValue("connect_on_startup", self.cbConnectStartup.isChecked())
        self.settings.setValue("client_id", self.clientId.text())
        self.settings.setValue("tls", self.use_tls.isChecked())
        self.settings.setValue("tls_file", self.tls_file.text())
        self.settings.setValue("tls_insecure", self.tls_insecure.isChecked())
        if self.tls_version.currentText() == "TLSv1.2":
            self.settings.setValue("tls_version", ssl.PROTOCOL_TLSv1_2)
        elif self.tls_version.currentText() == "TLSv1.1  ":
            self.settings.setValue("tls_version", ssl.PROTOCOL_TLSv1_1)
        elif self.tls_version.currentText() == "TLSv1":
            self.settings.setValue("tls_version", ssl.PROTOCOL_TLSv1)

        # self.settings.setValue("client_id", self.clientId.text())
        self.settings.sync()
        self.done(QDialog.Accepted)

    def random_generator(self, size=6, chars=string.ascii_uppercase + string.digits):
        return "".join(random.choice(chars) for x in range(size))
