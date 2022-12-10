from PyQt5.QtCore import QAbstractTableModel, QModelIndex, QSettings, Qt

from models.common import DeviceRoles
from Util import TasmotaDevice


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
                return d.p.get("LWT", "Offline") == 'Online'

            elif role == DeviceRoles.RestartReasonRole:
                return d.p.get("RestartReason")

            elif role == DeviceRoles.RSSIRole:
                return int(d.p.get("RSSI", 0))

            elif role == DeviceRoles.FirmwareRole:
                return d.p.get("Version", "")

            elif role == DeviceRoles.PowerRole:
                return d.power()

            elif role == DeviceRoles.ShuttersRole:
                return d.shutters()

            elif role == DeviceRoles.ShutterPositionsRole:
                return d.shutter_positions()

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

            # elif role == Qt.DecorationRole and col_name == "Device":
            #     if d.p["LWT"] == "Online":
            #         rssi = int(d.p.get("RSSI", 0))
            #
            #         if 0 < rssi < 50:
            #             return QIcon(":/status_low.png")
            #
            #         elif rssi < 75:
            #             return QIcon(":/status_medium.png")
            #
            #         elif rssi >= 75:
            #             return QIcon(":/status_high.png")
            #
            #     return QIcon(":/status_offline.png")

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
