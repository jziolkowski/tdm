from enum import Enum, auto

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, QRect, QRectF, QSettings, QSize, Qt
from PyQt5.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
)
from PyQt5.QtWidgets import QStyle, QStyledItemDelegate


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
            d = self.tasmota_env.devices[row]

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
        # col = index.column()
        # col_name = index.model().sourceModel().columns[col]

        fm_module = QFontMetrics(self.module_font)
        self.module_rect = fm_module.boundingRect(
            option.rect, Qt.AlignCenter, index.data(DeviceRoles.ModuleRole)
        )
        self.module_rect_h = self.module_rect.height()

        fm_device = option.fontMetrics
        self.devicename_rect = fm_device.boundingRect(option.rect, Qt.AlignCenter, "Ay")

        fm_hardware = QFontMetrics(self.font_8pt)
        self.hardware_rect = fm_hardware.boundingRect(
            option.rect, Qt.AlignCenter, index.data(DeviceRoles.HardwareRole)
        )
        # print(self.hardware_rect)

        heights = [self.devicename_rect.height(), self.module_rect.height()]

        s = QSize(
            QStyledItemDelegate().sizeHint(option, index).width(), 2 * len(heights) + sum(heights)
        )
        return s

    def paint(self, p, option, index):
        power_x = 0
        selected = option.state & QStyle.State_Selected

        if selected:
            p.fillRect(option.rect, option.palette.highlight())
            mark_rect = QRect(option.rect)
            mark_rect.setWidth(5)
            # p.fillRect(mark_rect, QColor(index.row(), index.row(), index.row()))
            pen = self.hltext_pen
        else:
            pen = self.text_pen
        p.setPen(pen)

        col = index.column()
        col_name = index.model().sourceModel().columns[col]

        if col_name == "Device":
            # draw signal strength icon
            px = QPixmap(":/signal0.png")
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

                px_y = 2
                px_rect = QRect(option.rect.x() + 2, option.rect.y() + px_y, 24, 24)
                p.drawPixmap(px_rect, px.scaled(24, 24))
                rssi_rect = QRect(
                    option.rect.x() + 2, option.rect.y() + 2 + px_rect.height(), 24, 8
                )
                p.save()
                p.setFont(self.font_8pt)
                p.drawText(rssi_rect, Qt.AlignCenter, str(rssi))
                p.restore()
                # p.drawRect(px_rect)
            # draw device friendly name (italic gray for offline)
            p.save()
            module_rect = option.rect.adjusted(28, 2, 0, 0)
            module_rect.setHeight(self.module_rect_h)

            hardware_rect = QRect(
                module_rect.right() + 2,
                module_rect.top(),
                module_rect.width(),
                self.hardware_rect_h,
            )

            device_rect = QRect(
                module_rect.left(),
                module_rect.bottom() + 2,
                module_rect.width(),
                self.devicename_rect.height(),
            )
            for rect in [module_rect, device_rect, hardware_rect]:
                p.drawRect(rect)

            if index.data(DeviceRoles.LWTRole) != "Online":
                pen = QPen(self.mid_pen)
                font = QFont()
                font.setItalic(True)
                p.setFont(font)
                p.setPen(pen)
            p.setFont(self.module_font)
            p.drawText(
                module_rect, Qt.AlignVCenter | Qt.AlignLeft, f"{index.data(DeviceRoles.ModuleRole)}"
            )
            p.setFont(self.font_8pt)
            p.setPen(self.mid_pen)
            p.drawText(
                hardware_rect,
                Qt.AlignVCenter | Qt.AlignLeft,
                str(index.data(DeviceRoles.HardwareRole)),
            )
            p.restore()
            p.drawText(device_rect, Qt.AlignVCenter | Qt.AlignLeft, index.data())

            alerts = []
            if index.data(DeviceRoles.RestartReasonRole) == "Exception":
                alerts.append("Exception")

            if "minimal" in index.data(DeviceRoles.FirmwareRole).lower():
                alerts.append("Minimal")

            p.setRenderHint(QPainter.Antialiasing, True)
            rect_h = 24
            y = option.rect.y() + 0.5 + (option.rect.height() - rect_h) / 2
            if alerts:
                message = ", ".join(alerts)
                p.save()

                alerts_width = p.boundingRect(option.rect, Qt.AlignCenter, message).width() + 4
                device_name_width = (
                    36 + p.boundingRect(option.rect, Qt.AlignCenter, index.data()).width()
                )

                exc_rect = QRectF(device_name_width, y, alerts_width, rect_h)

                path = QPainterPath()
                path.addRoundedRect(exc_rect, 3, 3)

                inner_path = QPainterPath()
                inner_path.addRoundedRect(exc_rect.adjusted(2, 2, -2, -2), 3, 3)

                if selected:
                    pen = self.hltext_pen
                else:
                    pen = QPen(QColor("red"))
                p.setPen(pen)

                p.drawPath(path)
                p.drawText(exc_rect, Qt.AlignCenter, message)
                p.restore()

            # draw relay icons
            power_data = index.data(DeviceRoles.PowerRole)
            if isinstance(power_data, dict):
                num = len(power_data.keys())
                power_x = option.rect.right() - num * 27 - 2

                for i, k in enumerate(sorted(power_data.keys())):
                    rect = QRectF(power_x + 27 * i, y, rect_h, rect_h)
                    path = QPainterPath()
                    path.addRoundedRect(rect, 3, 3)

                    inner_path = QPainterPath()
                    inner_path.addRoundedRect(rect.adjusted(2, 2, -2, -2), 3, 3)

                    p.save()
                    if power_data[k] == "ON":
                        pen = self.hltext_pen
                        p.setPen(pen)
                        p.fillPath(inner_path, QColor("#8BC34A"))

                    else:
                        p.setPen(self.mid_pen)

                    if num > 1:
                        p.drawText(rect, Qt.AlignCenter, f"{i + 1}")

                    p.setPen(self.mid_pen)
                    p.drawPath(path)

                    p.restore()

            # draw color frame
            color_data = index.data(DeviceRoles.ColorRole)
            if isinstance(color_data, dict):
                color = color_data.get("Color")
                so = color_data.get(68)
                if color and not so:
                    rect = QRectF(power_x - 53, y, 50, rect_h)
                    path = QPainterPath()
                    path.addRoundedRect(rect, 3, 3)

                    inner_path = QPainterPath()
                    inner_path.addRoundedRect(rect.adjusted(2, 2, -2, -2), 3, 3)

                    if len(color) > 6:
                        color = color[:6]
                    p.fillPath(inner_path, QColor("#{}".format(color)))
                    p.save()
                    p.setPen(self.mid_pen)
                    p.drawPath(path)
                    p.restore()

                    dimmer = color_data.get("Dimmer")
                    if dimmer:
                        p.drawText(rect, Qt.AlignCenter, "{}%".format(dimmer))

            p.setRenderHint(QPainter.Antialiasing, False)

        # elif col_name == "Wifi.RSSI":
        #     if index.data():
        #         rect = option.rect.adjusted(4, 4, -4, -4)
        #         rssi = index.data()
        #         pen = QPen(p.pen())
        #
        #         p.save()
        #
        #         if 0 < rssi < 35:
        #             color = QColor("#e74c3c")
        #
        #         elif rssi < 50:
        #             color = QColor("#ec8826")
        #
        #         elif rssi < 85:
        #             color = QColor("#f1c40f")
        #
        #         elif rssi >= 85:
        #             color = QColor("#8bc34a")
        #
        #         p.fillRect(rect.adjusted(2, 2, -1, -1), color)
        #
        #         p.drawText(rect, Qt.AlignCenter, str(rssi))
        #
        #         pen.setColor(QColor("#cccccc"))
        #         p.setPen(pen)
        #         p.drawRect(rect)
        #         p.restore()

        else:
            QStyledItemDelegate.paint(self, p, option, index)
