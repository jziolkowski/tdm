from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QListWidget, QListWidgetItem

from GUI.widgets import VLayout


class ClearRetainedDialog(QDialog):
    def __init__(self, env, *args, **kwargs):
        super(ClearRetainedDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle("Clear retained topics")
        self.setMinimumSize(QSize(320, 480))

        self.env = env

        vl = VLayout()

        sel_btns = QDialogButtonBox()
        sel_btns.setCenterButtons(True)
        btnSelAll = sel_btns.addButton("Select all", QDialogButtonBox.ActionRole)
        btnSelNone = sel_btns.addButton("Select none", QDialogButtonBox.ActionRole)

        self.lw = QListWidget()

        for topic in self.env.retained:
            itm = QListWidgetItem(topic)
            itm.setCheckState(Qt.Unchecked)
            self.lw.addItem(itm)

        btnSelAll.clicked.connect(lambda: self.select(Qt.Checked))
        btnSelNone.clicked.connect(lambda: self.select(Qt.Unchecked))

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Close)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        vl.addElements(sel_btns, self.lw, btns)
        self.setLayout(vl)

    def select(self, state):
        for row in range(self.lw.count()):
            itm = self.lw.item(row)
            itm.setCheckState(state)
