from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QDialog, QPushButton, QDialogButtonBox, QListWidget, QListWidgetItem, QLabel

from GUI import VLayout, GroupBoxV, HLayout, GroupBoxH


class ClearLWTDialog(QDialog):
    def __init__(self, env, *args, **kwargs):
        super(ClearLWTDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle("Clear obsolete retained LWTs")
        self.setMinimumSize(QSize(320, 480))

        self.env = env

        vl = VLayout()

        self.lw = QListWidget()

        for lwt in self.env.lwts:
            itm = QListWidgetItem(lwt)
            itm.setCheckState(Qt.Checked)
            self.lw.addItem(itm)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Close)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        vl.addWidgets([QLabel("Select LWTs to be cleared:"), self.lw, btns])
        self.setLayout(vl)


