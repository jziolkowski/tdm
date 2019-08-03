from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QGroupBox, QTableView, QSpinBox, QAction, QToolBar, \
    QHeaderView, QCheckBox, QPushButton, QPlainTextEdit, QLineEdit, QComboBox, QFrame, QDoubleSpinBox, QTreeWidgetItem, \
    QWidget, QSizePolicy


class VLayout(QVBoxLayout):
    def __init__(self, margin=3, spacing=3, label = '', *args, **kwargs):
        super(VLayout, self).__init__(*args, **kwargs)
        if isinstance(margin, int):
            self.setContentsMargins(margin, margin, margin, margin)
        elif isinstance(margin, list):
            self.setContentsMargins(margin[0], margin[1], margin[2], margin[3])

        self.setSpacing(spacing)

        if label:
            self.addWidget(QLabel(label))

    def addWidgets(self, widgets):
        for w in widgets:
            self.addWidget(w)

    def addSpacer(self):
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.addWidget(spacer)

class HLayout(QHBoxLayout):
    def __init__(self, margin=3, spacing=3, label='', *args, **kwargs):
        super(HLayout, self).__init__(*args, **kwargs)
        if isinstance(margin, int):
            self.setContentsMargins(margin, margin, margin, margin)
        elif isinstance(margin, list):
            self.setContentsMargins(margin[0], margin[1], margin[2], margin[3])
        self.setSpacing(spacing)

        if label:
            self.addWidget(QLabel(label))

    def addWidgets(self, widgets):
        for w in widgets:
            self.addWidget(w)

    def addSpacer(self):
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.addWidget(spacer)

class GroupBoxV(QGroupBox):
    def __init__(self, title, margin=3, spacing=3, *args, **kwargs):
        super(GroupBoxV, self).__init__(*args, **kwargs)

        self.setTitle(title)

        layout = VLayout()
        layout.setSpacing(spacing)

        if isinstance(margin, int):
            layout.setContentsMargins(margin, margin, margin, margin)
        elif isinstance(margin, list):
            layout.setContentsMargins(margin[0], margin[1], margin[2], margin[3])

        self.setLayout(layout)

    def addWidget(self, w):
        self.layout().addWidget(w)

    def addWidgets(self, widgets):
        for w in widgets:
            self.layout().addWidget(w)

    def addLayout(self, w):
        self.layout().addLayout(w)


class GroupBoxH(QGroupBox):
    def __init__(self, title, margin=None, spacing=None, *args, **kwargs):
        super(GroupBoxH, self).__init__(title)
        self.setLayout(HLayout())

    def addWidget(self, w):
        self.layout().addWidget(w)

    def addWidgets(self, widgets):
        for w in widgets:
            self.layout().addWidget(w)

    def addLayout(self, w):
        self.layout().addLayout(w)


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

    def setupColumns(self, columns, hidden=None):
        for col, opts in columns.items():
            if not hidden:
                self.setColumnHidden(col, opts[1])

            if type(opts[2]) == int:
                self.setColumnWidth(col, opts[2])

            else:
                self.horizontalHeader().setSectionResizeMode(col, opts[2])

        if hidden:
            for col in hidden:
                self.setColumnHidden(int(col), True)

    def setupView(self, view):
        for i, c in enumerate(view):
            if c in ("FriendlyName", "Module", "Topic", "FullTopic"):
                self.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
            else:
                self.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)


class SpinBox(QSpinBox):
    def __init__(self, *args, **kwargs):
        super(SpinBox, self).__init__(*args, **kwargs)
        self.setButtonSymbols(self.NoButtons)
        self.setMinimum(kwargs.get('minimum', 1))
        self.setMaximum(kwargs.get('maximum', 65535))
        self.setAlignment(Qt.AlignCenter)


class DoubleSpinBox(QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        super(DoubleSpinBox, self).__init__(*args, **kwargs)
        self.setButtonSymbols(self.NoButtons)
        self.setMinimum(kwargs.get('minimum', 1))
        self.setMaximum(kwargs.get('maximum', 65535))
        self.setDecimals(kwargs.get('precision', 1))
        self.setAlignment(Qt.AlignCenter)


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

    def addSpacer(self):
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.addWidget(spacer)


class RuleEditor(QPlainTextEdit):
    def __init__(self, *args, **kwargs):
        super(RuleEditor, self).__init__(*args, **kwargs)

        fnt_mono = QFont("Monospace")
        fnt_mono.setStyleHint(QFont.TypeWriter)
        self.setFont(fnt_mono)

        self.completer = None

    # def setCompleter(self, c):
    #     if self.completer:


class RuleGroupBox(GroupBoxV):
    def __init__(self, parent, title, *args, **kwargs):
        super(RuleGroupBox, self).__init__(title, parent=parent, *args, **kwargs)

        self.cbRule = QComboBox()
        self.cbRule.addItems(["Rule{}".format(nr + 1) for nr in range(3)])

        self.cbEnabled = QCheckBox("Enabled")
        self.cbOnce = QCheckBox("Once")
        self.cbStopOnError = QCheckBox("Stop on error")
        counter = QLabel("511 left")
        counter.setAlignment(Qt.AlignCenter)
        pbClear = QPushButton("Clear")
        self.pbSave = QPushButton("Save")

        hl_func = HLayout(0)
        hl_func.addWidgets([self.cbRule, self.cbEnabled, self.cbOnce, self.cbStopOnError, pbClear, self.pbSave, counter])

        self.layout().addLayout(hl_func)

        self.text = RuleEditor()
        self.layout().addWidget(self.text)

        pbClear.clicked.connect(lambda: self.text.clear())
        self.text.textChanged.connect(lambda: counter.setText("{} left".format(511-len(self.text.toPlainText()))))


class DetailLE(QLineEdit):
    def __init__(self, detail, *args, **kwargs):
        super(DetailLE, self).__init__(detail, *args, **kwargs)

        # self.setText(detail)
        self.setReadOnly(True)
        self.setAlignment(Qt.AlignCenter)


class DeviceParam(QFrame):
    def __init__(self, title, input, btns, funcs):
        super(DeviceParam, self).__init__()
        hl = HLayout(0)
        self.input = input
        hl.addWidgets([QLabel(title), self.input])

        for b, f in zip(btns, funcs):
            pb = QPushButton(b)
            pb.clicked.connect(f)
            hl.addWidget(pb)

        for i in range(hl.count()):
            hl.setStretch(i, 2 if i == 1 else 1)

        self.setLayout(hl)


class TelemetryDevice(QTreeWidgetItem):
    def __init__(self, name=""):
        super().__init__()
        self.unit = ""
        self.icon = ""
        self.setData(0, Qt.DisplayRole, name)
        self.setData(1, Qt.DisplayRole, "")

    def setIcon(self, icon):
        self.icon = icon

    def setValue(self, value):
        self.setData(1, Qt.DisplayRole, value)

    def setUnit(self, unit):
        self.unit = unit

    def data(self, col, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if col == 1:
                return "{} {}".format(QTreeWidgetItem.data(self, 1, Qt.DisplayRole), self.unit)

        if role == Qt.DecorationRole and col == 0:
            return QIcon("GUI/icons/{}.png".format(self.icon))

        return QTreeWidgetItem.data(self, col, role)


class TimeItem(TelemetryDevice):
    def __init__(self):
        super().__init__("Time")
        self.setIcon("time")


class TextItem(TelemetryDevice):
    def __init__(self):
        super().__init__()


class CounterItem(TelemetryDevice):
    def __init__(self):
        super().__init__("Counter")
        self.setIcon("counter")
        self.items = {}

    def setValues(self, values):
        for k in values.keys():
            item = self.items.get(k)
            if not item:
                item = TextItem()
                item.setData(0, Qt.DisplayRole, k)
                self.items[k] = item
                self.addChild(item)
            item.setData(1, Qt.DisplayRole, values[k])

