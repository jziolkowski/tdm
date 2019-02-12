from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QDialog, QLineEdit, QFormLayout, QPushButton, QGroupBox, QMessageBox, QDataWidgetMapper

from GUI import VLayout, HLayout
from Util import DevMdl


class DeviceEditDialog(QDialog):
    def __init__(self, model, row, *args, **kwargs):
        super(DeviceEditDialog, self).__init__(*args, **kwargs)
        self.setMinimumWidth(400)
        self.setWindowTitle("Edit device")

        self.settings = QSettings()
        self.settings.beginGroup("Devices")
        self.mapper = QDataWidgetMapper()
        self.mapper.setModel(model)
        self.mapper.setSubmitPolicy(QDataWidgetMapper.ManualSubmit)

        vl = VLayout()

        gbTopic = QGroupBox("MQTT Topic")
        self.topic = QLineEdit()
        self.topic.setPlaceholderText("unique name of your device")
        self.mapper.addMapping(self.topic, DevMdl.TOPIC)

        self.full_topic = QLineEdit()
        self.full_topic.setPlaceholderText("must contain %prefix% and %topic%")
        self.mapper.addMapping(self.full_topic, DevMdl.FULL_TOPIC)

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

        self.mapper.setCurrentIndex(row)

        btnSave.clicked.connect(self.accept)
        btnCancel.clicked.connect(self.reject)

    def accept(self):
        full_topic = self.full_topic.text()

        if not full_topic.endswith('/'):
            self.full_topic.setText(full_topic + "/")

        if not len(self.topic.text()) > 0:
            QMessageBox.critical(self, "Error", "Topic is required.")

        elif not "%topic%" in full_topic:
            QMessageBox.critical(self, "Error", "%topic% is required in FullTopic.")

        elif not "%prefix%" in full_topic:
            QMessageBox.critical(self, "Error", "%prefix% is required in FullTopic.")

        elif self.topic.text() not in self.settings.childGroups():
            self.mapper.submit()
            self.done(QDialog.Accepted)

        else:
            QMessageBox.critical(self, "Error", "Device '{}' already on the device list.".format(self.topic.text()))


    def reject(self):
        self.mapper.revert()
        self.done(QDialog.Rejected)

