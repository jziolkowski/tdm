from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox

from GUI.widgets import SpinBox, VLayout


class PrefsDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super(PrefsDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle("Preferences")
        # self.setMinimumSize(QSize(300, 200))

        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "tdm", "tdm")

        self.devices_short_version = self.settings.value("devices_short_version", True, bool)

        self.console_word_wrap = self.settings.value("console_word_wrap", True, bool)
        self.console_font_size = self.settings.value("console_font_size", 9, int)

        vl = VLayout()

        gbDevices = QGroupBox("Device list")
        fl_dev = QFormLayout()

        self.cbDevShortVersion = QCheckBox()
        self.cbDevShortVersion.setChecked(self.devices_short_version)

        fl_dev.addRow("Show short Tasmota version", self.cbDevShortVersion)

        fl_dev.setAlignment(self.cbDevShortVersion, Qt.AlignTop | Qt.AlignRight)

        gbDevices.setLayout(fl_dev)

        gbConsole = QGroupBox("Console")
        fl_cons = QFormLayout()

        self.cbConsWW = QCheckBox()
        self.cbConsWW.setChecked(self.console_word_wrap)

        self.sbConsFontSize = SpinBox(minimum=9, maximum=100)
        self.sbConsFontSize.setValue(self.console_font_size)

        gbConsole.setLayout(fl_cons)

        fl_cons.addRow("Word wrap", self.cbConsWW)
        fl_cons.addRow("Font size", self.sbConsFontSize)

        fl_cons.setAlignment(self.cbConsWW, Qt.AlignTop | Qt.AlignRight)
        fl_cons.setAlignment(self.sbConsFontSize, Qt.AlignTop | Qt.AlignRight)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        vl.addElements(gbDevices, gbConsole, btns)

        self.setLayout(vl)
