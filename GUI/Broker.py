from PyQt5.QtCore import QSettings, QDir
from PyQt5.QtWidgets import QDialog, QLineEdit, QFormLayout, QPushButton, QGroupBox, QCheckBox

from GUI import SpinBox, HLayout, VLayout


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

        self.cbConnectStartup = QCheckBox("Connect on startup")
        self.cbConnectStartup.setChecked(int(self.settings.value("connect_on_startup",0)))

        hlBtn = HLayout()
        btnSave = QPushButton("Save")
        btnCancel = QPushButton("Cancel")
        hlBtn.addWidgets([btnSave, btnCancel])

        vl = VLayout()
        vl.addWidgets([gbHost, gbLogin, self.cbConnectStartup])
        vl.addLayout(hlBtn)

        self.setLayout(vl)

        btnSave.clicked.connect(self.accept)
        btnCancel.clicked.connect(self.reject)

    def accept(self):
        self.settings.setValue("hostname", self.hostname.text())
        self.settings.setValue("port", self.port.value())
        self.settings.setValue("username", self.username.text())
        self.settings.setValue("password", self.password.text())
        self.settings.setValue("connect_on_startup", int(self.cbConnectStartup.isChecked()))
        self.settings.sync()
        self.done(QDialog.Accepted)
