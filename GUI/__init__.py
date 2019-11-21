from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QGroupBox, QTableView, QSpinBox, QAction, QToolBar, \
    QHeaderView, QComboBox, QDoubleSpinBox, QWidget, QSizePolicy, QSlider, QWidgetAction, QFrame, QLineEdit

base_view = ["FriendlyName"]
default_views = {
    "Home": base_view + ["Module", "Power", "Color", "LoadAvg", "LinkCount", "Uptime"],
    "Health": base_view + ["Uptime", "BootCount", "RestartReason", "LoadAvg", "Sleep", "MqttCount", "LinkCount", "Downtime", "RSSI"],
    "Firmware": base_view + ["Version", "Core", "SDK", "ProgramSize", "Free", "OtaUrl"],
    "Wifi": base_view + ["Hostname", "Mac", "IPAddress", "Gateway", "SSId", "BSSId", "Channel", "RSSI", "LinkCount", "Downtime"],
    "MQTT": base_view + ["Topic", "FullTopic", "CommandTopic", "StatTopic", "TeleTopic", "FallbackTopic", "GroupTopic"],
}

console_font = QFont("asd")
console_font.setStyleHint(QFont.TypeWriter)

class VLayout(QVBoxLayout):
    def __init__(self, margin=3, spacing=3, label='', *args, **kwargs):
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
        self.setSingleStep(kwargs.get('singleStep', 1))
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
        super(Toolbar, self).__init__(*args, **kwargs)
        self.setMovable(False)
        self.setIconSize(QSize(iconsize,iconsize))
        self.setOrientation(orientation)
        self.setToolButtonStyle(label_position)

    def addSpacer(self):
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.addWidget(spacer)


class ChannelSlider(QSlider):
    def __init__(self):
        super().__init__()
        self.setOrientation(Qt.Horizontal)
        self.setMinimum(0)
        self.setMaximum(100)
        self.setMaximumWidth(100)
        self.setSingleStep(1)
        self.setPageStep(10)
        self.setTracking(False)


class DictComboBox(QComboBox):
    def __init__(self, items_dict):
        super().__init__()

        for k, v in items_dict.items():
            self.addItem(v, k)


class SliderAction(QWidgetAction):
    def __init__(self, parent, label='', *args, **kwargs):
        super(SliderAction, self).__init__(parent, *args, **kwargs)

        w = QWidget()
        hl = HLayout(5)
        self.slider = ChannelSlider()
        self.slider.setObjectName(label)
        self.value = QLabel("0")
        hl.addWidgets([QLabel(label), self.slider, self.value])
        hl.setStretch(0, 1)
        hl.setStretch(1, 2)
        hl.setStretch(2, 1)
        w.setLayout(hl)
        self.setDefaultWidget(w)

        self.slider.valueChanged.connect(lambda x: self.value.setText(str(x)))


class CmdWikiUrl(QLabel):
    def __init__(self, cmd, title="", *args, **kwargs):
        super(CmdWikiUrl, self).__init__(*args, **kwargs)
        self.setTextFormat(Qt.RichText)
        self.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.setOpenExternalLinks(True)
        self.setText("<a href=https://github.com/arendst/Sonoff-Tasmota/wiki/Commands#{}>{}</a>".format(cmd, title if title else cmd))


class HTMLLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super(HTMLLabel, self).__init__(*args, **kwargs)
        self.setTextFormat(Qt.RichText)
        self.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.setOpenExternalLinks(True)
        self.setWordWrap(True)


class Command(QWidget):
    def __init__(self, command, meta, value=None, *args, **kwargs):
        # print(command, value)
        super(Command, self).__init__(*args, **kwargs)
        self.setMinimumWidth(250)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))

        vl = VLayout()

        hl = HLayout(0)
        hl.addWidget(QLabel("<b>{}</b>".format(command)))
        hl.addStretch(1)
        hl.addWidget(CmdWikiUrl(command, "Wiki"))

        hl_input = HLayout(0)

        if meta['type'] == "select":
            self.input = QComboBox()
            for k, v in meta['parameters'].items():
                self.input.addItem("{} {}".format(v['description'], "(default)" if v.get("default") else ""), k)

            if meta.get('editable'):
                self.input.setEditable(True)

            if value:
                self.input.setCurrentIndex(value)

        elif meta['type'] == "value":
            self.input = SpinBox(minimum=int(meta['parameters']['min']), maximum=int(meta['parameters']['max']))
            self.input.setMinimumWidth(75)
            if value:
                self.input.setValue(value)
            hl_input.addStretch(1)
            default = meta['parameters'].get('default')
            if default:
                hl_input.addWidget(QLabel("Default: {}".format(default)))
        hl_input.addWidget(self.input)

        vl.addLayout(hl)
        desc = QLabel(meta['description'])
        desc.setWordWrap(True)
        vl.addWidget(desc)
        vl.addLayout(hl_input)

        line = QFrame()
        line.setFrameStyle(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        vl.addWidget(line)
        self.setLayout(vl)


class CommandMultiSelect(QWidget):
    def __init__(self, command, meta, value=None, *args, **kwargs):
        # print(command, value)
        super(CommandMultiSelect, self).__init__(*args, **kwargs)
        self.setMinimumWidth(250)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))
        self.inputs = []

        vl = VLayout()

        hl = HLayout(0)
        hl.addWidget(QLabel("<b>{}</b>".format(command)))
        hl.addStretch(1)
        hl.addWidget(CmdWikiUrl(command, "Wiki"))
        vl.addLayout(hl)

        desc = QLabel(meta['description'])
        desc.setWordWrap(True)
        vl.addWidget(desc)

        for i, val in enumerate(value):
            cb = QComboBox()
            for k, v in meta['parameters'].items():
                cb.addItem("{}: {} {}".format(k, v['description'], "(default)" if v.get("default") else ""), k)
            cb.setCurrentIndex(val)
            hl_input = HLayout(0)
            hl_input.addWidgets([QLabel("{}: ".format(i+1)), cb])

            self.inputs.append(cb)
            vl.addLayout(hl_input)

        line = QFrame()
        line.setFrameStyle(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        vl.addWidget(line)
        self.setLayout(vl)


class Interlock(QWidget):
    def __init__(self, command, meta, value=None, *args, **kwargs):
        super(Interlock, self).__init__(*args, **kwargs)
        self.setMinimumWidth(250)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))
        self.input = None
        self.groups = []

        vl = VLayout()

        hl = HLayout(0)
        hl.addWidget(QLabel("<b>{}</b>".format(command)))
        hl.addStretch(1)
        hl.addWidget(CmdWikiUrl(command, "Wiki"))
        vl.addLayout(hl)

        desc = QLabel(meta['description'])
        desc.setWordWrap(True)
        vl.addWidget(desc)

        self.input = QComboBox()

        user_data = ["OFF", "ON"]
        for k, v in meta['parameters'].items():
            self.input.addItem("{} {}".format(v['description'], "(default)" if v.get("default") else ""), user_data[int(k)])

        if value and value.get("Interlock", "OFF") == "OFF":
            self.input.setCurrentIndex(0)
        else:
            self.input.setCurrentIndex(1)
        vl.addWidget(self.input)

        vl_groups = VLayout(0)
        for i in range(4):
            le = QLineEdit()
            le.setAlignment(Qt.AlignCenter)
            group_value = value.get("Groups", [])
            if group_value:
                group_value_list = group_value.split(" ")
                if i < len(group_value_list):
                    group_value = group_value_list[i]
                    le.setText(group_value)
            hl_group = HLayout(0)
            hl_group.addWidgets([QLabel("Group {}".format(i+1)), le])
            vl_groups.addLayout(hl_group)
            self.groups.append(le)
        vl.addLayout(vl_groups)

        line = QFrame()
        line.setFrameStyle(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        vl.addWidget(line)
        self.setLayout(vl)


class PulseTime(QWidget):
    def __init__(self, command, meta, value=None, *args, **kwargs):
        super(PulseTime, self).__init__(*args, **kwargs)
        self.setMinimumWidth(250)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))
        self.inputs = []

        vl = VLayout()

        hl = HLayout(0)
        hl.addWidget(QLabel("<b>{}</b>".format(command)))
        hl.addStretch(1)
        hl.addWidget(CmdWikiUrl(command, "Wiki"))
        vl.addLayout(hl)

        desc = QLabel(meta['description'])
        desc.setWordWrap(True)
        vl.addWidget(desc)

        vl_groups = VLayout(0)
        for k in sorted(list(value.keys())):
            sb = SpinBox(minimum=int(meta['parameters']['min']), maximum=int(meta['parameters']['max']))
            sb.setValue(value[k])
            hl_group = HLayout(0)
            hl_group.addWidgets([QLabel(k), sb])
            vl_groups.addLayout(hl_group)
            self.inputs.append(sb)
        vl.addLayout(vl_groups)

        line = QFrame()
        line.setFrameStyle(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        vl.addWidget(line)
        self.setLayout(vl)