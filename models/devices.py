import struct
from socket import inet_aton

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt

from models.common import DeviceRoles
from Util import TasmotaDevice


class TasmotaDevicesModel(QAbstractTableModel):
    def __init__(self, settings, devices, tasmota_env):
        super().__init__()
        self.settings = settings
        self.devices = devices
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

        if any(
            [
                key.startswith("POWER"),
                key in ("RSSI", "LWT", "COLOR"),
                key.startswith("ShutterRelay"),
                key.startswith("Shutter"),
            ]
        ):
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
            row, col_name = idx.row(), self.columns[idx.column()]
            d: TasmotaDevice = self.tasmota_env.devices[row]

            val = d.p.get(col_name, "")

            if role in [Qt.DisplayRole, Qt.EditRole]:
                if col_name == "Device":
                    return d.name

                if col_name == "Module":
                    if val == 0:
                        return d.p["Template"].get("NAME", "Fetching template name...")
                    else:
                        return d.module()

                if col_name == "Version" and val:
                    if self.devices_short_version and "(" in val:
                        return val[0 : val.index("(")]
                    return val.replace("(", " (")

                if col_name in ("Uptime", "Downtime") and val:
                    # val = str(val)
                    if val.startswith("0T"):
                        val = val.replace("0T", "")
                    return val.replace("T", "d ")

                if col_name == "Core" and val:
                    return val.replace("_", ".")

                if col_name == "Time" and val:
                    return val.replace("T", " ")

                if col_name == "Power":
                    return d.power()

                if col_name == "Color":
                    return d.color()

                if col_name == "CommandTopic":
                    return d.cmnd_topic()

                if col_name == "StatTopic":
                    return d.stat_topic()

                if col_name == "TeleTopic":
                    return d.tele_topic()

                if col_name == "FallbackTopic":
                    return f"cmnd/{d.p.get('MqttClient')}_fb/"

                if col_name == "BSSId" and (alias := self.settings.value(f"BSSId/{val}")):
                    return alias

                if col_name == "RSSI":
                    return int(d.p.get("RSSI", 0))

                return val

            if role == DeviceRoles.LWTRole:
                return d.is_online

            if role == DeviceRoles.RestartReasonRole:
                return d.p.get("RestartReason")

            if role == DeviceRoles.RSSIRole:
                return int(d.p.get("RSSI", 0))

            if role == DeviceRoles.FirmwareRole:
                return d.p.get("Version", "")

            if role == DeviceRoles.PowerRole:
                return d.power()

            if role == DeviceRoles.ShuttersRole:
                return d.shutters()

            if role == DeviceRoles.ShutterPositionsRole:
                return d.shutter_positions()

            if role == DeviceRoles.ColorRole:
                return d.color()

            if role == DeviceRoles.ModuleRole:
                return d.module()

            if role == DeviceRoles.HardwareRole:
                return getattr(d.p, 'Hardware', 'ESP8266')

            if role == Qt.TextAlignmentRole:
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
                if col_name in ("Uptime"):
                    return Qt.AlignRight | Qt.AlignVCenter
                return Qt.AlignCenter

            if role == Qt.InitialSortOrderRole:
                if val:
                    if col_name in ("Uptime", "Downtime"):
                        days, hms = val.split("T")
                        h, m, s = hms.split(":")
                        return int(s) + int(m) * 60 + int(h) * 3600 + int(days) * 86400
                    if col_name in ("IPAddress", "Gateway") or col_name.startswith("DNSServer"):
                        return struct.unpack("!L", inet_aton(val))[0]
                return idx.data()

            if role == Qt.ToolTipRole:
                if col_name == "Version":
                    if val := d.p.get("Version"):
                        return val[val.index("(") + 1 : val.index(")")]
                    return ""

                if col_name == "BSSId":
                    return d.p.get("BSSId")

                if col_name == "Device":
                    fns = [d.name]

                    for i in range(2, 5):
                        if fn := d.p.get(f"FriendlyName{i}"):
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
