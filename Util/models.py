import re

from PyQt5.QtCore import QModelIndex, Qt, QAbstractTableModel, QSettings, QSize, QRect, QDir, QRectF, QPoint
from PyQt5.QtGui import QIcon, QColor, QPixmap, QFont, QPen
from PyQt5.QtWidgets import QStyledItemDelegate, QStyle

LWTRole = Qt.UserRole
RestartReasonRole = Qt.UserRole + 1
RSSIRole = Qt.UserRole + 2
FirmwareRole = Qt.UserRole + 3


class TasmotaDevicesModel(QAbstractTableModel):
    def __init__(self, tasmota_env):
        super().__init__()
        self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)
        self.devices = QSettings("{}/TDM/devices.cfg".format(QDir.homePath()), QSettings.IniFormat)
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
        if key.startswith("POWER") and "Power" in self.columns:
            power_idx = self.columns.index("Power")
            idx = self.index(row, power_idx)
            self.dataChanged.emit(idx, idx)

        elif key in ("RSSI", "LWT", "DeviceName", 'FriendlyName1'):
            idx = self.index(row, self.columns.index("Device"))
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
                        return d.p['Template'].get('NAME', "Fetching template name...")
                    else:
                        return d.module()

                elif col_name == "Version" and val:
                    if self.devices_short_version and "(" in val:
                        return val[0:val.index("(")]
                    return val.replace("(", " (")

                elif col_name in ("Uptime", "Downtime") and val:
                    val = str(val)
                    if val.startswith("0T"):
                        val = val.replace('0T', '')
                    val = val.replace('T', 'd ')

                elif col_name == "Core" and val:
                    return val.replace('_', '.')

                elif col_name == "Time" and val:
                    return val.replace('T', ' ')

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
                    return "cmnd/{}_fb/".format(d.p.get('MqttClient'))

                elif col_name == "BSSId":
                    alias = self.settings.value("BSSId/{}".format(val))
                    if alias:
                        return alias

                elif col_name == "RSSI":
                    val = int(d.p.get("RSSI", 0))
                    return val

                return val

            elif role == LWTRole:
                val = d.p.get('LWT', 'Offline')
                return val

            elif role == RestartReasonRole:
                val = d.p.get('RestartReason')
                return val

            elif role == RSSIRole:
                val = int(d.p.get('RSSI', 0))
                return val

            elif role == FirmwareRole:
                val = d.p.get('Version', "")
                return val

            elif role == Qt.TextAlignmentRole:
                # Left-aligned columns
                if col_name in ("Device", "Module", "RestartReason", "OtaUrl", "Hostname") or col_name.endswith("Topic"):
                    return Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap

                # Right-aligned columns
                elif col_name in ("Uptime"):
                    return Qt.AlignRight | Qt.AlignVCenter

                else:
                    return Qt.AlignCenter

            elif role == Qt.DecorationRole and col_name == "Device":
                if d.p['LWT'] == "Online":
                    rssi = int(d.p.get("RSSI", 0))

                    if rssi > 0 and rssi < 50:
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
                    val = d.p.get('Version')
                    if val:
                        return val[val.index("(")+1:val.index(")")]
                    return ""

                elif col_name == "BSSId":
                    return d.p.get('BSSId')

                elif col_name == "Device":
                    fns = [d.name]

                    for i in range(2, 5):
                        fn = d.p.get("FriendlyName{}".format(i))
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

            topic = device.p['Topic']
            self.settings.beginGroup("Devices")
            if topic in self.settings.childGroups():
                self.settings.remove(topic)
            self.settings.endGroup()

            self.endRemoveRows()
            return True
        return False

    def deleteDevice(self, idx):
        row = idx.row()
        mac = self.deviceAtRow(row).p['Mac'].replace(":", "-")
        self.devices.remove(mac)
        self.devices.sync()
        self.removeRows(row, 1)

    def columnIndex(self, column):
        return self.columns.index(column)


class DeviceDelegate(QStyledItemDelegate):
    def __init__(self):
        super(DeviceDelegate, self).__init__()

    def sizeHint(self, option, index):
        col = index.column()
        col_name = index.model().sourceModel().columns[col]
        if col_name == "LWT":
            return QSize(16, 28)

        elif col_name == "Power":
            num = len(index.data().keys())
            if num <= 4:
                return QSize(24 * len(index.data().keys()), 28)
            else:
                return QSize(24 * 4, 48)

        return QStyledItemDelegate.sizeHint(self, option, index)

    def paint(self, p, option, index):
        if option.state & QStyle.State_Selected:
            p.fillRect(option.rect, option.palette.highlight())

        col = index.column()
        col_name = index.model().sourceModel().columns[col]

        if col_name == "Device":
            if index.data():
                px = QPixmap(":/status_offline.png")
                if index.data(LWTRole) == "Online":
                    rssi = index.data(RSSIRole)

                    if rssi > 0 and rssi < 50:
                        px = QPixmap(":/status_low.png")

                    elif rssi < 75:
                        px = QPixmap(":/status_medium.png")

                    elif rssi >= 75:
                        px = QPixmap(":/status_high.png")

                px_y = (option.rect.height() - 24) / 2
                p.drawPixmap(option.rect.x() + 2, option.rect.y() + px_y, px.scaled(24, 24))

                p.drawText(option.rect.adjusted(28, 0, 0, 0), Qt.AlignVCenter | Qt.AlignLeft, index.data())

                alerts = []
                if index.data(RestartReasonRole) == "Exception":
                    alerts.append("Exception")

                if "minimal" in index.data(FirmwareRole).lower():
                    alerts.append("Minimal")

                if alerts:
                    message = ", ".join(alerts)
                    p.save()
                    pen = QPen(p.pen())
                    pen.setColor(QColor("red"))
                    p.setPen(pen)
                    text_width = p.boundingRect(option.rect, Qt.AlignCenter, message).width()
                    exc_rect = option.rect.adjusted(option.rect.width() - text_width - 8, 4, -4, -4)
                    p.drawText(exc_rect, Qt.AlignCenter, message)
                    p.drawRect(exc_rect)
                    p.restore()


        elif col_name == "RSSI":
            if index.data():
                rect = option.rect.adjusted(4, 4, -4, -4)
                rssi = index.data()
                pen = QPen(p.pen())

                p.save()
                if rssi > 0 and rssi < 50:
                    color = QColor("#ef4522")
                elif rssi > 75:
                    color = QColor("#7eca27")
                elif rssi > 0:
                    color = QColor("#fcdd0f")
                p.fillRect(rect.adjusted(2, 2, -1, -1), color)

                p.drawText(rect, Qt.AlignCenter, str(rssi))

                pen.setColor(QColor("#cccccc"))
                p.setPen(pen)
                p.drawRect(rect)
                p.restore()


        elif col_name == "Power":
            if isinstance(index.data(), dict):
                num = len(index.data().keys())

                if num <= 4:
                    for i, k in enumerate(sorted(index.data().keys())):
                        x = option.rect.x() + i * 24 + (option.rect.width() - num * 24) / 2
                        y = option.rect.y() + (option.rect.height() - 24) / 2

                        if num == 1:
                            p.drawPixmap(x, y, 24, 24, QPixmap(":/P_{}".format(index.data()[k])))

                        else:
                            p.drawPixmap(x, y, 24, 24, QPixmap(":/P{}_{}".format(i + 1, index.data()[k])))

                else:
                    i = 0
                    for row in range(2):
                        for col in range(4):
                            x = col * 24 + option.rect.x()
                            y = option.rect.y() + row * 24

                            if i < num:
                                p.drawPixmap(x, y, 24, 24, QPixmap(":/P{}_{}".format(i + 1, list(index.data().values())[i])))
                            i += 1

        elif col_name == "Color":
            if index.data():
                rect = option.rect.adjusted(4, 4, -4, -4)
                d = index.data()
                pen = QPen(p.pen())

                color = d.get("Color")
                so = d.get(68)
                if color and not so:
                    p.save()
                    if len(color) > 6:
                        color = color[:6]
                    p.fillRect(rect.adjusted(2, 2, -1, -1), QColor("#{}".format(color)))

                    dimmer = d.get("Dimmer")
                    if dimmer:
                        if dimmer >= 60:
                            pen.setColor(QColor("black"))
                        else:
                            pen.setColor(QColor("white"))
                        p.setPen(pen)
                        p.drawText(rect, Qt.AlignCenter, "{}%".format(dimmer))

                    pen.setColor(QColor("#cccccc"))
                    p.setPen(pen)
                    p.drawRect(rect)
                    p.restore()

        else:
            QStyledItemDelegate.paint(self, p, option, index)

