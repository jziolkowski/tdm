from typing import Callable, List, Optional, Tuple, Union

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QAction,
    QBoxLayout,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from tdmgr.schemas.result import PulseTimeLegacyResultSchema
from tdmgr.util import TasmotaDevice

base_view = ["Device"]
default_views = {
    "Home": base_view + ["Module", "LoadAvg", "LinkCount", "Uptime"],
    "Health": base_view
    + [
        "Uptime",
        "BootCount",
        "RestartReason",
        "LoadAvg",
        "Sleep",
        "MqttCount",
        "LinkCount",
        "Downtime",
        "RSSI",
    ],
    "Firmware": base_view + ["Version", "Core", "SDK", "ProgramSize", "Free", "OtaUrl"],
    "Wifi": base_view
    + [
        "Hostname",
        "Mac",
        "IPAddress",
        "Gateway",
        "SSId",
        "BSSId",
        "Channel",
        "RSSI",
        "LinkCount",
        "Downtime",
    ],
    "MQTT": base_view
    + [
        "Topic",
        "FullTopic",
        "CommandTopic",
        "StatTopic",
        "TeleTopic",
        "FallbackTopic",
        "GroupTopic",
    ],
}

console_font = QFont("asd")
console_font.setStyleHint(QFont.TypeWriter)

docs_url = "https://tasmota.github.io/docs/"


class LayoutMixin(QBoxLayout):
    def __init__(
        self,
        margin: Union[int, List[int]] = 3,
        spacing: int = 3,
        label: Optional[str] = None,
        *args,
        **kwargs,
    ):
        super(LayoutMixin, self).__init__(*args, **kwargs)
        if isinstance(margin, int):
            self.setContentsMargins(margin, margin, margin, margin)
        elif isinstance(margin, list):
            self.setContentsMargins(margin[0], margin[1], margin[2], margin[3])

        self.setSpacing(spacing)

        if label:
            self.addElements(QLabel(label))

    def addElements(self, *elements):
        for element in elements:
            if isinstance(element, QWidget):
                self.layout().addWidget(element)
            elif isinstance(element, QBoxLayout):
                self.layout().addLayout(element)

    def setStretches(self, *stretches: Tuple[int, int]):
        for stretch in stretches:
            self.layout().setStretch(stretch[0], stretch[1])

    def addSpacer(self):
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.addElements(spacer)


class VLayout(QVBoxLayout, LayoutMixin):
    def __init__(
        self,
        margin: Union[int, List[int]] = 3,
        spacing: int = 3,
        label: Optional[str] = None,
        *args,
        **kwargs,
    ):
        super(VLayout, self).__init__(margin, spacing, label, *args, **kwargs)


class HLayout(QHBoxLayout, LayoutMixin):
    def __init__(
        self,
        margin: Union[int, List[int]] = 3,
        spacing: int = 3,
        label: Optional[str] = None,
        *args,
        **kwargs,
    ):
        super(HLayout, self).__init__(margin, spacing, label, *args, **kwargs)


class GroupBoxBase(QGroupBox):
    def __init__(self, title: str, *args, **kwargs):
        super(GroupBoxBase, self).__init__(*args, **kwargs)
        self.setTitle(title)

    def addElements(self, *elements):
        self.layout: Callable[..., Union[VLayout, HLayout]]
        self.layout().addElements(*elements)


class GroupBoxV(GroupBoxBase):
    def __init__(
        self, title: str, margin: Union[int, List[int]] = 3, spacing: int = 3, *args, **kwargs
    ):
        super(GroupBoxV, self).__init__(title, *args, **kwargs)

        layout = VLayout(margin, spacing)
        self.setLayout(layout)


class GroupBoxH(GroupBoxBase):
    def __init__(
        self, title: str, margin: Union[int, List[int]] = 3, spacing: int = 3, *args, **kwargs
    ):
        super(GroupBoxH, self).__init__(title, *args, **kwargs)

        layout = HLayout(margin, spacing)
        self.setLayout(layout)


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

        self.setIconSize(QSize(24, 24))

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

            if isinstance(opts[2], int):
                self.setColumnWidth(col, opts[2])

            else:
                self.horizontalHeader().setSectionResizeMode(col, opts[2])

        if hidden:
            for col in hidden:
                self.setColumnHidden(int(col), True)

    def setupView(self, view):
        for i, c in enumerate(view):
            if c in ("Device", "Module", "Topic", "FullTopic"):
                self.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
            else:
                self.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)


class SpinBox(QSpinBox):
    def __init__(self, *args, **kwargs):
        super(SpinBox, self).__init__(*args, **kwargs)
        self.setButtonSymbols(self.NoButtons)
        self.setMinimum(kwargs.get("minimum", 1))
        self.setMaximum(kwargs.get("maximum", 65535))
        self.setSingleStep(kwargs.get("singleStep", 1))
        self.setAlignment(Qt.AlignCenter)


class DoubleSpinBox(QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        super(DoubleSpinBox, self).__init__(*args, **kwargs)
        self.setButtonSymbols(self.NoButtons)
        self.setMinimum(kwargs.get("minimum", 1))
        self.setMaximum(kwargs.get("maximum", 65535))
        self.setDecimals(kwargs.get("precision", 1))
        self.setAlignment(Qt.AlignCenter)


class CheckableAction(QAction):
    def __init__(self, *args, **kwargs):
        super(CheckableAction, self).__init__(*args, **kwargs)
        self.setCheckable(True)


class Toolbar(QToolBar):
    def __init__(
        self,
        orientation=Qt.Horizontal,
        iconsize=32,
        label_position=Qt.ToolButtonTextUnderIcon,
        *args,
        **kwargs,
    ):
        super(Toolbar, self).__init__(*args, **kwargs)
        self.setMovable(False)
        self.setIconSize(QSize(iconsize, iconsize))
        self.setOrientation(orientation)
        self.setToolButtonStyle(label_position)

    def addSpacer(self):
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.addWidget(spacer)

    def add_action(self, icon: str, text: str, slot: Callable, shortcut: Optional[str] = None):
        action = self.addAction(QIcon(icon), text, slot)
        if shortcut:
            action.setShortcut(shortcut)


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
    def __init__(self, parent, label="", *args, **kwargs):
        super(SliderAction, self).__init__(parent, *args, **kwargs)

        w = QWidget()
        hl = HLayout(5)
        self.slider = ChannelSlider()
        self.slider.setObjectName(label)
        self.value = QLabel("0")
        hl.addElements(QLabel(label), self.slider, self.value)
        hl.setStretches((0, 1), (1, 2), (2, 1))
        w.setLayout(hl)
        self.setDefaultWidget(w)

        self.slider.valueChanged.connect(lambda x: self.value.setText(str(x)))


class CmdWikiUrl(QLabel):
    def __init__(self, cmd, title="", *args, **kwargs):
        super(CmdWikiUrl, self).__init__(*args, **kwargs)
        self.setTextFormat(Qt.RichText)
        self.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.setOpenExternalLinks(True)
        self.setText(f"<a href={docs_url}Commands/#{cmd.lower()}>{title or cmd}</a>")


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
        hl.addWidget(QLabel(f"<b>{command}</b>"))
        hl.addStretch(1)
        hl.addWidget(CmdWikiUrl(command, "Wiki"))

        hl_input = HLayout(0)

        if meta["type"] == "select":
            self.input = QComboBox()
            for k, v in meta["parameters"].items():
                self.input.addItem(
                    f"{v['description']} {'(default)' if v.get('default') else ''}", k
                )

            if meta.get("editable"):
                self.input.setEditable(True)

            if value:
                self.input.setCurrentIndex(value)

        elif meta["type"] == "value":
            self.input = SpinBox(
                minimum=int(meta["parameters"]["min"]), maximum=int(meta["parameters"]["max"])
            )
            self.input.setMinimumWidth(75)
            if value:
                self.input.setValue(value)
            hl_input.addStretch(1)
            default = meta["parameters"].get("default")
            if default:
                hl_input.addWidget(QLabel(f"Default: {default}"))
        hl_input.addWidget(self.input)

        vl.addLayout(hl)
        desc = QLabel(meta["description"])
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
        hl.addWidget(QLabel(f"<b>{command}</b>"))
        hl.addStretch(1)
        hl.addWidget(CmdWikiUrl(command, "Wiki"))
        vl.addLayout(hl)

        desc = QLabel(meta["description"])
        desc.setWordWrap(True)
        vl.addWidget(desc)

        for i, val in enumerate(value):
            cb = QComboBox()
            for k, v in meta["parameters"].items():
                cb.addItem(
                    f"{k}: {v['description']} {'(default)' if v.get('default') else ''}",
                    k,
                )
            cb.setCurrentIndex(val)
            hl_input = HLayout(0)
            hl_input.addElements(QLabel(f"{i + 1}:"), cb)

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

        desc = QLabel(meta["description"])
        desc.setWordWrap(True)
        vl.addWidget(desc)

        self.input = QComboBox()

        user_data = ["OFF", "ON"]
        for k, v in meta["parameters"].items():
            self.input.addItem(
                "{} {}".format(v["description"], "(default)" if v.get("default") else ""),
                user_data[int(k)],
            )

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
            hl_group.addElements(QLabel(f"Group {i + 1}"), le)
            vl_groups.addLayout(hl_group)
            self.groups.append(le)
        vl.addLayout(vl_groups)

        line = QFrame()
        line.setFrameStyle(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        vl.addWidget(line)
        self.setLayout(vl)


class PulseTime(QWidget):
    def __init__(self, command: str, meta: dict, device: TasmotaDevice):
        super(PulseTime, self).__init__()
        self.setMinimumWidth(250)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))
        self.inputs = []

        vl = VLayout()

        hl = HLayout(0)
        hl.addWidget(QLabel(f"<b>{command}</b>"))
        hl.addStretch(1)
        hl.addWidget(CmdWikiUrl(command, "Wiki"))
        vl.addLayout(hl)

        desc = QLabel(meta["description"])
        desc.setWordWrap(True)
        vl.addWidget(desc)

        vl_groups = VLayout(0)

        if isinstance(device._pulsetime, PulseTimeLegacyResultSchema):
            values = [pt[1].Set for pt in device._pulsetime]
        else:
            values = device._pulsetime.PulseTime.Set

        for idx, value in enumerate(values, start=1):
            sb = SpinBox(
                minimum=int(meta["parameters"]["min"]), maximum=int(meta["parameters"]["max"])
            )
            sb.setValue(value)
            hl_group = HLayout(0)
            hl_group.addElements(QLabel(f"Pulsetime{idx}"), sb)
            vl_groups.addLayout(hl_group)
            self.inputs.append(sb)
        vl.addLayout(vl_groups)

        line = QFrame()
        line.setFrameStyle(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        vl.addWidget(line)
        self.setLayout(vl)
