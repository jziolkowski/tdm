from PyQt5.QtGui import QFontDatabase
from PyQt5.QtWidgets import QDialog, QLineEdit, QFormLayout, QLabel, QPlainTextEdit
from json import loads, dumps

class PayloadViewDialog(QDialog):
    def __init__(self, timestamp, topic, payload, *args, **kwargs):
        super(PayloadViewDialog, self).__init__(*args, **kwargs)
        self.setMinimumWidth(500)
        self.setWindowTitle("View payload")

        fl = QFormLayout()

        lb_timestamp = QLabel(timestamp.toString("yyyy.MM.dd hh:mm:ss"))

        le_topic = QLineEdit()
        le_topic.setReadOnly(True)
        le_topic.setText(topic)

        fnt_mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)

        pte_payload = QPlainTextEdit()
        pte_payload.setFont(fnt_mono)
        pte_payload.setMinimumHeight(400)
        pte_payload.setReadOnly(True)
        if payload:
            payload = str(payload)
            if payload.startswith("{") or payload.startswith("["):
                pte_payload.setPlainText(dumps(loads(payload), indent=2))
            else:
                pte_payload.setPlainText(payload)
        else:
            pte_payload.setPlainText("(empty)")


        fl.addWidget(lb_timestamp)
        fl.addRow("Topic", le_topic)
        fl.addRow("Payload", pte_payload)

        self.setLayout(fl)