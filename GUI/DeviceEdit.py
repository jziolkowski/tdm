from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QDialog, QLineEdit, QFormLayout, QPushButton, QGroupBox, QMessageBox, QDataWidgetMapper

from GUI import VLayout, HLayout


class DeviceEditDialog(QDialog):
    def __init__(self, env, device = None, *args, **kwargs):
        super(DeviceEditDialog, self).__init__(*args, **kwargs)
        self.setMinimumWidth(300)
        self.setWindowTitle("Edit '{}'".format(device.p['Topic']) if device else "Add device")

        self.env = env
        self.device = device

        vl = VLayout()

        gbTopic = QGroupBox("MQTT Topic")
        self.topic = QLineEdit()
        self.topic.setPlaceholderText("unique name of your device")
        if self.device:
            self.topic.setText(self.device.p['Topic'])

        self.full_topic = QLineEdit()
        self.full_topic.setPlaceholderText("must contain %prefix% and %topic%")
        if self.device:
            self.full_topic.setText(self.device.p['FullTopic'])
        else:
            self.full_topic.setText("%prefix%/%topic%/")

        tfl = QFormLayout()
        tfl.addRow("Topic", self.topic)
        tfl.addRow("Full topic", self.full_topic)
        gbTopic.setLayout(tfl)

        btnSave = QPushButton("Save")
        btnCancel = QPushButton("Cancel")

        hl_btns = HLayout()
        hl_btns.addStretch(1)
        hl_btns.addWidgets([btnSave, btnCancel])

        vl.addWidgets([gbTopic])
        vl.addLayout(hl_btns)
        self.setLayout(vl)

        btnSave.clicked.connect(self.accept)
        btnCancel.clicked.connect(self.reject)

    def accept(self):
        full_topic = self.full_topic.text()

        if not full_topic.endswith('/'):
            self.full_topic.setText(full_topic + "/")

        if not len(self.topic.text()) > 0:
            QMessageBox.critical(self, "Error", "Topic is required.")

        elif "%prefix%" not in full_topic or "%topic%" not in full_topic:
            QMessageBox.critical(self, "Error", "%prefix% and %topic% are required in FullTopic.")

        elif self.device or not self.env.find_device(self.topic.text()):
            self.done(QDialog.Accepted)

        else:
            QMessageBox.critical(self, "Error", "Device '{}' already on the device list.".format(self.topic.text()))

    def reject(self):
        self.done(QDialog.Rejected)

