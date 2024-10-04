import os
from datetime import datetime

from PyQt5.QtCore import QDir, QEvent, QRegExp, QSize, QStringListModel, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QIcon, QSyntaxHighlighter, QTextCharFormat
from PyQt5.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QDockWidget,
    QFileDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QWidget,
)

from tdmgr.GUI.widgets import GroupBoxV, HLayout, VLayout, console_font
from tdmgr.mqtt import Message
from tdmgr.tasmota.commands import commands
from tdmgr.tasmota.device import TasmotaDevice


class ConsoleWidget(QDockWidget):
    sendCommand = pyqtSignal(str, str)

    def __init__(self, settings, device, *args, **kwargs):
        super().__init__()
        self.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.setWindowTitle(f"Console [{device.name}]")
        self.device: TasmotaDevice = device

        self.settings = settings

        console_font_size = self.settings.value("console_font_size", 9, int)
        console_font.setPointSize(console_font_size)

        console_word_wrap = self.settings.value("console_word_wrap", True, bool)

        w = QWidget()

        vl = VLayout()

        self.console = QPlainTextEdit()
        self.console.setTabChangesFocus(True)
        self.console.setWordWrapMode(console_word_wrap)

        self.console.setReadOnly(True)
        self.console.setFont(console_font)

        self.console_hl = JSONHighLighter(self.console.document())

        hl_command_mqttlog = HLayout(0)

        self.command = QLineEdit()
        self.command.setFont(console_font)
        self.command.setPlaceholderText("Type the command and press ENTER to send.")
        self.command.returnPressed.connect(self.command_enter)
        self.command.textChanged.connect(self.command_changed)
        self.command.installEventFilter(self)

        command_cpl = QCompleter(sorted(commands))
        command_cpl.setCaseSensitivity(Qt.CaseInsensitive)
        command_cpl.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.command.setCompleter(command_cpl)
        # command_cpl.popup().installEventFilter(self)

        command_cpl.activated.connect(self.command.clear, Qt.QueuedConnection)

        pbSave = QPushButton(QIcon(":/save.png"), "")
        pbSave.setFlat(True)
        pbSave.setToolTip("Save console")
        pbSave.clicked.connect(self.save_console)

        pbClear = QPushButton(QIcon(":/clear.png"), "")
        pbClear.setFlat(True)
        pbClear.setToolTip("Clear console")
        pbClear.clicked.connect(self.clear_console)

        self.cbMQTTLog = QComboBox()
        self.cbMQTTLog.addItems(
            [
                "Disabled",
                "Error",
                "Error/Info (default)",
                "Error/Info/Debug",
                "Error/Info/More debug",
                "All",
            ]
        )
        mqttlog = self.device.p.get("MqttLog", -1)

        if mqttlog != -1:
            self.cbMQTTLog.setCurrentIndex(int(mqttlog))
        else:
            self.cbMQTTLog.setEnabled(False)

        self.cbMQTTLog.currentIndexChanged.connect(self.change_mqttlog)

        hl_command_mqttlog.addElements(
            self.command, pbSave, pbClear, QLabel("MQTT Log level"), self.cbMQTTLog
        )

        vl.addElements(self.console, hl_command_mqttlog)

        w.setLayout(vl)
        self.setWidget(w)

    def command_changed(self, text):
        if text == "":
            self.command.completer().setModel(QStringListModel(sorted(commands)))

    @pyqtSlot(Message)
    def consoleAppend(self, msg: Message):
        if self.device.message_topic_matches_fulltopic(msg):
            self.console.appendPlainText(
                f"[{msg.timestamp.strftime('%X')}] {msg.topic} {msg.payload}"
            )

    def eventFilter(self, obj, e):
        if obj == self.command and e.type() == QEvent.KeyPress:
            history = self.device.history
            if e.modifiers() & Qt.ControlModifier:
                if e.key() == Qt.Key_H:
                    d = DeviceConsoleHistory(self.device.env.devices)
                    if d.exec_() == QDialog.Accepted:
                        self.command.setText(d.command)

                elif len(history) > 0:
                    if e.key() == Qt.Key_E:
                        self.command.setText(history[0])

                    if e.key() == Qt.Key_Down:
                        self.command.completer().setModel(QStringListModel(history))
                        self.command.setText(" ")
                        self.command.completer().complete()
            return False

        return QDockWidget.eventFilter(self, obj, e)

    def command_enter(self):
        cmd_input = self.command.text()
        if len(cmd_input) > 0 and cmd_input != " ":
            split_cmd_input = cmd_input.split(" ")
            cmd = split_cmd_input[0]

            payload = " ".join(split_cmd_input[1:])
            self.sendCommand.emit(self.device.cmnd_topic(cmd), payload)
            self.command.clear()

            history = self.device.history
            if cmd_input in history:
                history.pop(history.index(cmd_input))
            history.insert(0, cmd_input)
            if len(history) > 25:
                history = history[0:26]

    def change_mqttlog(self, idx):
        self.sendCommand.emit(self.device.cmnd_topic("MqttLog"), str(idx))

    def save_console(self):
        new_fname = os.path.join(
            QDir.homePath(),
            f"TDM_{self.device.name}_{datetime.now().strftime('%Y%m%d-%H%M%S')}.log",
        )

        file, ok = QFileDialog.getSaveFileName(self, "Save console", new_fname, "Log files | *.log")
        if ok:
            with open(file, "w") as f:
                f.write(self.console.toPlainText())

    def clear_console(self):
        self.console.clear()


class JSONHighLighter(QSyntaxHighlighter):
    keyword = QTextCharFormat()
    keyword.setForeground(QColor("darkCyan"))

    braces = QTextCharFormat()
    braces.setFontWeight(QFont.Bold)

    error = QTextCharFormat()
    error.setForeground(QColor("darkRed"))

    command = QTextCharFormat()
    command.setForeground(QColor("darkMagenta"))
    command.setFontWeight(QFont.Bold)

    tstamp = QTextCharFormat()
    tstamp.setForeground(QColor("gray"))

    STYLES = {
        "keyword": keyword,
        "brace": braces,
        "error": error,
        "tstamp": tstamp,
        "command": command,
    }

    braces = [r"\{", r"\}"]

    def __init__(self, document):
        QSyntaxHighlighter.__init__(self, document)

        rules = []

        rules += [
            (r"\[.*\] ", 0, self.STYLES["tstamp"]),
            (r"\s.*(stat|tele).*\s", 0, self.STYLES["brace"]),
            (r"\s.*cmnd.*\s", 0, self.STYLES["command"]),
            (r"\"\w*\"(?=:)", 0, self.STYLES["keyword"]),
            (r":\"\w*\"", 0, self.STYLES["error"]),
            (r"\{\"Command\":\"Unknown\"\}", 0, self.STYLES["error"]),
        ]

        rules += [(r"%s" % b, 0, self.STYLES["brace"]) for b in self.braces]

        self.rules = [(QRegExp(pat), index, fmt) for (pat, index, fmt) in rules]

    def highlightBlock(self, text):
        for expression, nth, fmt in self.rules:
            index = expression.indexIn(text, 0)

            while index >= 0:
                index = expression.pos(nth)
                length = len(expression.cap(nth))
                self.setFormat(index, length, fmt)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)


class DeviceConsoleHistory(QDialog):
    def __init__(self, devices):
        super().__init__()
        self.setWindowFlags(Qt.Tool)
        self.setMinimumSize(QSize(640, 480))
        self.devices = devices
        self.command = ""
        vl = VLayout()

        gbxDevice = GroupBoxV("Commands history for:")
        gbDevice = QComboBox()
        gbDevice.addItems([d.p["FriendlyName1"] for d in devices])
        gbxDevice.addElements(gbDevice)

        self.lwCommands = QListWidget()

        vl.addElements(
            gbxDevice,
            self.lwCommands,
            QLabel("Double-click a command to use it, ESC to close."),
        )
        self.setLayout(vl)

        gbDevice.currentIndexChanged.connect(self.load_history)
        self.lwCommands.doubleClicked.connect(self.select_command)

    def load_history(self, idx):
        self.lwCommands.clear()
        self.lwCommands.addItems(self.devices[idx].history)

    def select_command(self, x):
        self.command = self.lwCommands.item(x.row()).text()
        self.accept()
