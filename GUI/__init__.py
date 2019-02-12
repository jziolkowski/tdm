from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QGroupBox, QTableView, QSpinBox, QAction, QToolBar, QHeaderView

# from GUI.DeviceEdit import DeviceEditDialog
from Util import DevMdl

columns = {
    DevMdl.LWT: ['', False, 16],
    DevMdl.TOPIC: ['', True, 1],
    DevMdl.FULL_TOPIC: ['', True, 1],
    DevMdl.FRIENDLY_NAME: ['Name', False, QHeaderView.Stretch],
    DevMdl.MODULE: ['Module', False, QHeaderView.ResizeToContents],
    DevMdl.MAC: ['MAC', False, QHeaderView.ResizeToContents],
    DevMdl.IP: ['IP', False, QHeaderView.ResizeToContents],
    DevMdl.FIRMWARE: ['Firmware', False, QHeaderView.ResizeToContents],
    DevMdl.RSSI: ['RSSI', False, QHeaderView.ResizeToContents],
    DevMdl.UPTIME: ['Uptime', False, QHeaderView.ResizeToContents],
    DevMdl.POWER: ['Power', False, QHeaderView.ResizeToContents],
    DevMdl.LOADAVG: ['L. avg', False, QHeaderView.ResizeToContents],
    DevMdl.TELEMETRY: ['', True, 1],
}

class VLayout(QVBoxLayout):
    def __init__(self, margin=3, spacing=3, label = '', *args, **kwargs):
        super(VLayout, self).__init__(*args, **kwargs)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

        if label:
            self.addWidget(QLabel(label))

    def addWidgets(self, widgets):
        for w in widgets:
            self.addWidget(w)


class HLayout(QHBoxLayout):
    def __init__(self, margin=3, spacing=3, label='', *args, **kwargs):
        super(HLayout, self).__init__(*args, **kwargs)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

        if label:
            self.addWidget(QLabel(label))

    def addWidgets(self, widgets):
        for w in widgets:
            self.addWidget(w)


class GroupBoxV(QGroupBox):
    def __init__(self, title, *args, **kwargs):
        super(GroupBoxV, self).__init__(*args, **kwargs)

        self.setTitle(title)
        self.setLayout(VLayout())


class GroupBoxH(QGroupBox):
    def __init__(self, title, *args, **kwargs):
        super(GroupBoxH, self).__init__(*args, **kwargs)
        self.setTitle(title)

        self.setLayout(HLayout())


class TableView(QTableView):
    def __init__(self, *args, **kwargs):
        super(TableView, self).__init__(*args, **kwargs)
        self.setAlternatingRowColors(True)

        self.horizontalHeader().setHighlightSections(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.verticalHeader().setVisible(False)
        self.verticalHeader().setHighlightSections(False)
        # self.verticalHeader().setDefaultSectionSize(24)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.SingleSelection)

        self.setEditTriggers(self.NoEditTriggers)

    def setColumnTitles(self, titles):
        for col, title in enumerate(titles):
            self.model().setHeaderData(col, Qt.Horizontal, title)

    def setColumnsHidden(self, columns):
        for col in columns:
            self.setColumnHidden(col, True)

    def setupColumns(self, columns):
        for col, opts in columns.items():
            # self.model().setHeaderData(col, Qt.Horizontal, opts[0])
            self.setColumnHidden(col, opts[1])

            if type(opts[2]) == int:
                self.setColumnWidth(col, opts[2])

            else:
                self.horizontalHeader().setSectionResizeMode(col, opts[2])


class SpinBox(QSpinBox):
    def __init__(self, *args, **kwargs):
        super(SpinBox, self).__init__(*args, **kwargs)
        self.setButtonSymbols(self.NoButtons)
        self.setMinimum(kwargs.get('minimum', 1))
        self.setMaximum(kwargs.get('maximum', 65535))
        self.setAlignment(Qt.AlignCenter)
        self.setMaximumWidth(45)


class CheckableAction(QAction):
    def __init__(self, *args, **kwargs):
        super(CheckableAction, self).__init__(*args, **kwargs)
        self.setCheckable(True)


class Toolbar(QToolBar):
    def __init__(self, orientation = Qt.Horizontal, iconsize=32, label_position=Qt.ToolButtonTextUnderIcon, *args, **kwargs):
        super(QToolBar, self).__init__(*args, **kwargs)
        self.setMovable(False)
        self.setIconSize(QSize(iconsize,iconsize))
        self.setOrientation(orientation)
        self.setToolButtonStyle(label_position)


