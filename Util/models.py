from enum import Enum, auto

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, QRect, QRectF, QSettings, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPalette, QPen, QPixmap
from PyQt5.QtWidgets import QStyle, QStyledItemDelegate

from Util import TasmotaDevice


class DeviceRoles(int, Enum):
    LWTRole = Qt.UserRole
    RestartReasonRole = auto()
    RSSIRole = auto()
    FirmwareRole = auto()
    PowerRole = auto()
    ColorRole = auto()
    ModuleRole = auto()
    HardwareRole = auto()


class SetOptionRoles(int, Enum):
    NrRole = Qt.UserRole
    MetaRole = auto()


RSSI_LOW = QColor("#e74c3c")
RSSI_MEDIUM = QColor("#ec8826")
RSSI_GOOD = QColor("#f1c40f")
RSSI_FULL = QColor("#8bc34a")

RECT_ADJUSTMENT = (2, 2, -1, -1)


class TasmotaDevicesModel(QAbstractTableModel):
    def __init__(self, tasmota_env):
        super().__init__()
        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "tdm", "tdm")
        self.devices = QSettings(QSettings.IniFormat, QSettings.UserScope, "tdm", "devices")
        self.tasmota_env = tasmota_env
        self.columns = []

        self.devices_short_version = self.settings.value("devices_short_version", True, bool)

        for d in self.tasmota_env.devices:
            d.property_changed = self.notify_change
            d.module_changed = self.module_change

    def setupColumns(self, columns):
        self.beginResetModel()
        self.columns = columns
        self.endResetModel()

    def deviceAtRow(self, row):
        if len(self.tasmota_env.devices) > 0:
            return self.tasmota_env.devices[row]
        return None

    def notify_change(self, d, key):
        row = self.tasmota_env.devices.index(d)
        # if key.startswith("POWER") and "Power" in self.columns:
        #     power_idx = self.columns.index("Power")
        #     idx = self.index(row, power_idx)
        #     self.dataChanged.emit(idx, idx)

        if key in ("RSSI", "LWT", "COLOR") or key.startswith("POWER"):
            device_name_idx = self.columns.index("Device")
            idx = self.index(row, device_name_idx)
            self.dataChanged.emit(idx, idx)

        elif key in self.columns:
            col = self.columns.index(key)
            idx = self.index(row, col)
            self.dataChanged.emit(idx, idx)

    def module_change(self, d):
        self.notify_change(d, "Module")

    def columnCount(self, parent=None):
        return len(self.columns)

    def rowCount(self, parent=None):
        return len(self.tasmota_env.devices)

    def flags(self, idx):
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def headerData(self, col, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.columns[col]

    def data(self, idx, role=Qt.DisplayRole):
        if idx.isValid():
            row = idx.row()
            col = idx.column()
            col_name = self.columns[col]
            d: TasmotaDevice = self.tasmota_env.devices[row]

            if role in [Qt.DisplayRole, Qt.EditRole]:
                val = d.p.get(col_name, "")

                if col_name == "Device":
                    val = d.name

                elif col_name == "Module":
                    if val == 0:
                        return d.p["Template"].get("NAME", "Fetching template name...")
                    else:
                        return d.module()

                elif col_name == "Version" and val:
                    if self.devices_short_version and "(" in val:
                        return val[0 : val.index("(")]
                    return val.replace("(", " (")

                elif col_name in ("Uptime", "Downtime") and val:
                    val = str(val)
                    if val.startswith("0T"):
                        val = val.replace("0T", "")
                    val = val.replace("T", "d ")

                elif col_name == "Core" and val:
                    return val.replace("_", ".")

                elif col_name == "Time" and val:
                    return val.replace("T", " ")

                elif col_name == "Power":
                    return d.power()

                elif col_name == "Color":
                    return d.color()

                elif col_name == "CommandTopic":
                    return d.cmnd_topic()

                elif col_name == "StatTopic":
                    return d.stat_topic()

                elif col_name == "TeleTopic":
                    return d.tele_topic()

                elif col_name == "FallbackTopic":
                    return f"cmnd/{d.p.get('MqttClient')}_fb/"

                elif col_name == "BSSId":
                    alias = self.settings.value(f"BSSId/{val}")
                    if alias:
                        return alias

                elif col_name == "RSSI":
                    val = int(d.p.get("RSSI", 0))
                    return val

                return val

            elif role == DeviceRoles.LWTRole:
                return d.p.get("LWT", "Offline")

            elif role == DeviceRoles.RestartReasonRole:
                return d.p.get("RestartReason")

            elif role == DeviceRoles.RSSIRole:
                return int(d.p.get("RSSI", 0))

            elif role == DeviceRoles.FirmwareRole:
                return d.p.get("Version", "")

            elif role == DeviceRoles.PowerRole:
                return d.power()

            elif role == DeviceRoles.ColorRole:
                return d.color()

            elif role == DeviceRoles.ModuleRole:
                return d.module()

            elif role == DeviceRoles.HardwareRole:
                return getattr(d.p, 'Hardware', 'ESP8266')

            elif role == Qt.TextAlignmentRole:
                # Left-aligned columns
                if col_name in (
                    "Device",
                    "Module",
                    "RestartReason",
                    "OtaUrl",
                    "Hostname",
                ) or col_name.endswith("Topic"):
                    return Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap

                # Right-aligned columns
                elif col_name in ("Uptime"):
                    return Qt.AlignRight | Qt.AlignVCenter

                else:
                    return Qt.AlignCenter

            elif role == Qt.DecorationRole and col_name == "Device":
                if d.p["LWT"] == "Online":
                    rssi = int(d.p.get("RSSI", 0))

                    if 0 < rssi < 50:
                        return QIcon(":/status_low.png")

                    elif rssi < 75:
                        return QIcon(":/status_medium.png")

                    elif rssi >= 75:
                        return QIcon(":/status_high.png")

                return QIcon(":/status_offline.png")

            elif role == Qt.InitialSortOrderRole:
                if col_name in ("Uptime", "Downtime"):
                    val = d.p.get(col_name, "")
                    if val:
                        d, hms = val.split("T")
                        h, m, s = hms.split(":")
                        return int(s) + int(m) * 60 + int(h) * 3600 + int(d) * 86400
                else:
                    return idx.data()

            elif role == Qt.ToolTipRole:
                if col_name == "Version":
                    val = d.p.get("Version")
                    if val:
                        return val[val.index("(") + 1 : val.index(")")]
                    return ""

                elif col_name == "BSSId":
                    return d.p.get("BSSId")

                elif col_name == "Device":
                    fns = [d.name]

                    for i in range(2, 5):
                        fn = d.p.get(f"FriendlyName{i}")
                        if fn:
                            fns.append(fn)
                    return "\n".join(fns)

    def addDevice(self, device):
        self.beginInsertRows(QModelIndex(), 0, 0)
        device.property_changed = self.notify_change
        device.module_changed = self.module_change
        self.endInsertRows()

    def removeRows(self, pos, rows, parent=QModelIndex()):
        if pos + rows <= self.rowCount():
            self.beginRemoveRows(parent, pos, pos + rows - 1)
            device = self.deviceAtRow(pos)
            self.tasmota_env.devices.pop(self.tasmota_env.devices.index(device))

            topic = device.p["Topic"]
            self.settings.beginGroup("Devices")
            if topic in self.settings.childGroups():
                self.settings.remove(topic)
            self.settings.endGroup()

            self.endRemoveRows()
            return True
        return False

    def deleteDevice(self, idx):
        row = idx.row()
        mac = self.deviceAtRow(row).p["Mac"].replace(":", "-")
        self.devices.remove(mac)
        self.devices.sync()
        self.removeRows(row, 1)

    def columnIndex(self, column):
        return self.columns.index(column)


class DeviceDelegate(QStyledItemDelegate):
    def __init__(self):
        super(DeviceDelegate, self).__init__()

        self.font_8pt = QFont()
        self.font_8pt.setPointSize(8)

        self.module_font = QFont(self.font_8pt)
        self.module_font.setCapitalization(QFont.AllUppercase)
        self.module_font.setWeight(75)

        self.module_rect_h = 0
        self.devicename_rect_h = 0
        self.hardware_rect_h = 0

        palette = QPalette()
        self.mid_pen = QPen(palette.color(QPalette.Mid))
        self.text_pen = QPen(palette.color(QPalette.Text))
        self.hltext_pen = QPen(palette.color(QPalette.HighlightedText))

    def sizeHint(self, option, index):
        if self.get_column_name(index) in ('Device', 'Power'):
            fm_device = option.fontMetrics
            devicename_rect = fm_device.boundingRect(option.rect, Qt.AlignCenter, "Ay")

            row_height = self.get_relays_row_height(index)
            hint_height = max(42, devicename_rect.height(), row_height)
            # print(hint_height)
            return QSize(QStyledItemDelegate().sizeHint(option, index).height(), hint_height)
        return QStyledItemDelegate().sizeHint(option, index)

    def get_relays_row_height(self, index):
        relay_rows = self.get_relay_rows(index)
        return 5 + relay_rows * 24 + (relay_rows - 1) * 2

    @staticmethod
    def get_relay_rows(index):
        return len(index.data(DeviceRoles.PowerRole).keys()) // 8 or 1

    @staticmethod
    def get_column_name(index):
        return index.model().sourceModel().columns[index.column()]

    @staticmethod
    def get_relay_label_and_state(index, relay_idx):
        power_data = index.data(DeviceRoles.PowerRole)
        if len(power_data.keys()) == 1:
            return '', power_data.get('POWER')
        return f'{relay_idx}', power_data.get(f'POWER{relay_idx}')

    def draw_relay_rect(self, p: QPainter, rect: QRectF, index, relay_idx):
        label, state = self.get_relay_label_and_state(index, relay_idx)

        inner_rect = rect.adjusted(*RECT_ADJUSTMENT)

        p.save()
        if state == "ON":
            pen = self.hltext_pen
            p.setPen(pen)
            p.fillRect(inner_rect, QColor("#8BC34A"))

        else:
            p.setPen(self.mid_pen)

        p.drawText(rect, Qt.AlignCenter, label)

        p.setPen(self.mid_pen)
        p.drawRect(rect)

        p.restore()

    def paint(self, p: QPainter, option, index):
        relays_x = 0
        rect_h = 24
        y = option.rect.y() + (option.rect.height() - rect_h) / 2
        selected = option.state & QStyle.State_Selected

        if selected:
            p.fillRect(option.rect, option.palette.highlight())
            # mark_rect = QRect(option.rect)
            # mark_rect.setWidth(5)
            pen = self.hltext_pen
        else:
            pen = self.text_pen
        p.setPen(pen)

        col_name = self.get_column_name(index)

        if col_name == "Device":
            # draw signal strength icon
            px = QPixmap(":/signal0.png")
            rssi = 'offln'
            if index.data(DeviceRoles.LWTRole) == "Online":
                rssi = index.data(DeviceRoles.RSSIRole)
                if 0 < rssi < 35:
                    px = QPixmap(":/signal1.png")

                elif rssi < 50:
                    px = QPixmap(":/signal2.png")

                elif rssi < 85:
                    px = QPixmap(":/signal3.png")

                elif rssi >= 85:
                    px = QPixmap(":/signal4.png")

            px_y = option.rect.y() + (option.rect.height() - 38) / 2
            px_rect = QRect(option.rect.x() + 2, px_y, 24, 24)
            p.drawPixmap(px_rect, px.scaled(24, 24))
            rssi_rect = QRectF(option.rect.x() + 2, px_rect.y() + px_rect.height() + 2, 24, 12)
            p.save()
            p.setFont(self.font_8pt)
            p.drawText(rssi_rect, Qt.AlignCenter, str(rssi))
            p.restore()
            # p.drawRect(px_rect)
            # p.drawRect(rssi_rect)
            # draw device friendly name (italic gray for offline)
            p.save()

            device_rect = option.rect.adjusted(30, 2, 0, 0)
            if index.data(DeviceRoles.LWTRole) != "Online":
                pen = QPen(self.mid_pen)
                font = QFont()
                font.setItalic(True)
                p.setFont(font)
                p.setPen(pen)

            p.restore()
            p.drawText(device_rect, Qt.AlignVCenter | Qt.AlignLeft, index.data())

            alerts = []
            if index.data(DeviceRoles.RestartReasonRole) == "Exception":
                alerts.append("Exception")

            if "minimal" in index.data(DeviceRoles.FirmwareRole).lower():
                alerts.append("Minimal")

            if alerts:
                message = " | ".join(alerts)
                p.save()

                alerts_width = p.boundingRect(option.rect, Qt.AlignCenter, message).width() + 8
                device_name_width = (
                    40 + p.boundingRect(option.rect, Qt.AlignCenter, index.data()).width()
                )

                exc_rect = QRectF(device_name_width, y, alerts_width, rect_h)
                if selected:
                    pen = self.hltext_pen
                else:
                    pen = QPen(QColor("red"))
                p.setPen(pen)

                p.drawRect(exc_rect)
                p.drawText(exc_rect, Qt.AlignCenter, message)
                p.restore()

            # draw relay icons

            if (power_data := index.data(DeviceRoles.PowerRole)) and isinstance(power_data, dict):
                num_relays = len(power_data.keys())

                relay_rows = self.get_relay_rows(index)
                relay_rows_height = self.get_relays_row_height(index)
                if relay_rows == 1:
                    relays_y = y
                else:
                    relays_y = option.rect.y() + 2 + (option.rect.height() - relay_rows_height) / 2

                relay_cols = num_relays if num_relays <= 8 else 8
                relay_cols_width = 24 * relay_cols + (relay_cols - 1) * 3
                relays_x = option.rect.right() - relay_cols_width - 5

                for relay_row in range(relay_rows):
                    for relay_col in range(relay_cols):
                        relay_idx = 1 + relay_row * 8 + relay_col
                        if relay_idx <= num_relays:
                            rect = QRectF(
                                relays_x + 27 * relay_col,
                                relays_y + 3 * relay_row + relay_row * rect_h,
                                rect_h,
                                rect_h,
                            )

                            self.draw_relay_rect(p, rect, index, relay_idx)

            # draw color frame
            color_data = index.data(DeviceRoles.ColorRole)
            if isinstance(color_data, dict):
                so = color_data.get(68)
                if (color := color_data.get("Color")) and not so:
                    rect = QRectF(relays_x - 53, y, 50, rect_h)

                    inner_rect = rect.adjusted(*RECT_ADJUSTMENT)
                    p.fillRect(inner_rect, QColor(f"#{color[:6]}"))

                    p.save()
                    p.setPen(self.mid_pen)
                    p.drawRect(rect)
                    p.restore()

                    if dimmer := color_data.get("Dimmer"):
                        p.drawText(rect, Qt.AlignCenter, f"{dimmer}")

        elif col_name == "RSSI":
            self.draw_rssi_rect(p, option.rect, index)

        else:
            QStyledItemDelegate.paint(self, p, option, index)

    def draw_rssi_rect(self, p: QPainter, rect, index):
        if index.data():
            rect = rect.adjusted(*RECT_ADJUSTMENT)
            rssi = index.data(DeviceRoles.RSSIRole)
            pen = QPen(p.pen())

            p.save()

            if 0 < rssi < 35:
                color = RSSI_LOW

            elif rssi < 50:
                color = RSSI_MEDIUM

            elif rssi < 85:
                color = RSSI_GOOD

            elif rssi >= 85:
                color = RSSI_FULL

            p.fillRect(rect.adjusted(*RECT_ADJUSTMENT), color)
            p.drawText(rect, Qt.AlignCenter, str(rssi))

            pen.setColor(QColor("#cccccc"))
            p.setPen(pen)
            p.drawRect(rect)
            p.restore()
