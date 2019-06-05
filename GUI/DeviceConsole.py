from PyQt5.QtCore import Qt, pyqtSlot, QTime, pyqtSignal, QRegExp, QEvent, QStringListModel, QSize
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt5.QtWidgets import QDockWidget, QPlainTextEdit, QLineEdit, QWidget, QCompleter, QComboBox, QListWidget, \
    QDialog, QLabel

from GUI import VLayout, GroupBoxV
from Util import commands


class DeviceConsoleWidget(QDockWidget):

    sendCommand = pyqtSignal(str, str)

    def __init__(self, device, *args, **kwargs):
        super().__init__()
        self.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.setWindowTitle("Console [{}]".format(device.p["FriendlyName"][0]))
        self.device = device

        w = QWidget()

        vl = VLayout()

        self.console = QPlainTextEdit()
        self.console.setTabChangesFocus(True)

        fnt_mono = QFont("asd")
        fnt_mono.setStyleHint(QFont.Monospace)

        self.console.setFont(fnt_mono)
        self.console.setReadOnly(True)

        self.console_hl = JSONHighLighter(self.console.document())

        self.command = QLineEdit()
        self.command.setFont(fnt_mono)
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

        vl.addWidgets([self.console, self.command])

        w.setLayout(vl)
        self.setWidget(w)

    def command_changed(self, text):
        if text == "":
            self.command.completer().setModel(QStringListModel(sorted(commands)))

    @pyqtSlot(str, str, bool)
    def consoleAppend(self, topic, msg, retained=False):
        if self.device.matches(topic):
            tstamp = QTime.currentTime().toString("HH:mm:ss")
            self.console.appendPlainText("[{}] {} {}".format(tstamp, topic, msg))

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
                        self.command.setText(' ')
                        self.command.completer().complete()
            return False

        return QDockWidget.eventFilter(self, obj, e)

    def command_enter(self):
        cmd_input = self.command.text()
        if len(cmd_input) > 0 and cmd_input != " ":
            split_cmd_input = cmd_input.split(' ')
            cmd = split_cmd_input[0]
            topic = "{}{}".format(self.device.cmnd_topic(), cmd)

            payload = " ".join(split_cmd_input[1:])
            self.consoleAppend(topic, payload)
            self.sendCommand.emit(topic, payload)
            self.command.clear()

            history = self.device.history
            if cmd_input in history:
                history.pop(history.index(cmd_input))
            history.insert(0, cmd_input)
            if len(history) > 25:
                history = history[0:26]


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
        'keyword': keyword,
        'brace': braces,
        'error': error,
        'tstamp': tstamp,
        'command': command
    }

    braces = [
        '\{', '\}'
    ]

    def __init__(self, document):
        QSyntaxHighlighter.__init__(self, document)

        rules = []

        rules += [
            (r'\[.*\] ', 0, self.STYLES['tstamp']),
            (r'\s.*(stat|tele).*\s', 0, self.STYLES['brace']),
            (r'\s.*cmnd.*\s', 0, self.STYLES['command']),
            (r'\"\w*\":', 0, self.STYLES['keyword']),
            (r'\{\"Command\":\"Unknown\"\}', 0, self.STYLES['error']),
        ]

        rules += [(r'%s' % b, 0, self.STYLES['brace']) for b in self.braces]

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
        gbDevice.addItems([d.p['FriendlyName'][0] for d in devices])
        gbxDevice.addWidget(gbDevice)

        self.lwCommands = QListWidget()

        vl.addWidgets([gbxDevice, self.lwCommands, QLabel("Double-click a command to use it, ESC to close.")])
        self.setLayout(vl)

        gbDevice.currentIndexChanged.connect(self.load_history)
        self.lwCommands.doubleClicked.connect(self.select_command)

    def load_history(self, idx):
        self.lwCommands.clear()
        self.lwCommands.addItems(self.devices[idx].history)

    def select_command(self, x):
        self.command = self.lwCommands.item(x.row()).text()
        self.accept()
