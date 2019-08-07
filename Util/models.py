from PyQt5.QtCore import QModelIndex, Qt, QAbstractTableModel, QSettings, QSize, QRect, QDir, QRectF, QPoint
from PyQt5.QtGui import QIcon, QColor, QPixmap, QFont, QPen
from PyQt5.QtWidgets import QStyledItemDelegate, QStyle

class TasmotaDevicesModel(QAbstractTableModel):
    def __init__(self, tasmota_env):
        super().__init__()
        self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)
        self.devices = QSettings("{}/TDM/devices.cfg".format(QDir.homePath()), QSettings.IniFormat)
        self.tasmota_env = tasmota_env
        self.columns = []

        for d in self.tasmota_env.devices:
            d.property_changed = self.notify_change
            d.module_changed = self.module_change

    def setupColumns(self, columns):
        self.beginResetModel()
        self.columns = columns
        self.endResetModel()

    def deviceAtRow(self, row):
        return self.tasmota_env.devices[row]

    def notify_change(self, d, key):
        row = self.tasmota_env.devices.index(d)
        if key.startswith("POWER") and "Power" in self.columns:
            power_idx = self.columns.index("Power")
            idx = self.index(row, power_idx)
            self.dataChanged.emit(idx, idx)

        elif key in ("RSSI", "LWT"):
            fname_idx = self.columns.index("FriendlyName")
            idx = self.index(row, fname_idx)
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

                if col_name == "FriendlyName":
                    if val:
                        val = val[0]
                    else:
                        d.p['Topic']

                elif col_name == "Module":
                    if val == 0:
                        return d.p['Template'].get('NAME', "Fetching template name...")
                    else:
                        return d.module()

                elif col_name == "Version" and val:
                    return val.replace('(', ' (')

                elif col_name in ("Uptime", "Downtime") and val:
                    if val.startswith("0T"):
                        val = val.replace('0T', '')
                    val = val.replace('T', 'd ')

                elif col_name == "Core" and val:
                    return val.replace('_', '.')

                elif col_name == "Time" and val:
                    return val.replace('T', ' ')

                elif col_name == "Power":
                    return d.power()

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

                return val

            elif role == Qt.TextAlignmentRole:
                # Left-aligned columns
                if col_name in ("FriendlyName", "Module", "RestartReason", "OtaUrl", "Hostname", "Version") or col_name.endswith("Topic"):
                    return Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap

                # Right-aligned columns
                elif col_name in ("Uptime"):
                    return Qt.AlignRight | Qt.AlignVCenter

                else:
                    return Qt.AlignCenter

            elif role == Qt.DecorationRole and col_name == "FriendlyName":
                if d.p['LWT'] == "Online":
                    rssi = int(d.p.get("RSSI", 0))

                    if rssi > 0 and rssi < 50:
                        return QIcon("GUI/icons/status_low.png")

                    elif rssi < 75:
                        return QIcon("GUI/icons/status_medium.png")

                    elif rssi >= 75:
                        return QIcon("GUI/icons/status_high.png")

                return QIcon("GUI/icons/status_offline.png")

            elif role == Qt.BackgroundColorRole and col_name == "RSSI":
                rssi = int(d.p.get("RSSI", 0))
                if rssi > 0 and rssi < 50:
                    return QColor("#ef4522")
                elif rssi > 75:
                    return QColor("#7eca27")
                elif rssi > 0:
                    return QColor("#fcdd0f")

            elif role == Qt.ToolTipRole:
                if col_name == "Firmware":
                    return d.p.get('FriendlyName')

                elif col_name == "BSSId":
                    return d.p.get('BSSId')

                elif col_name == "FriendlyName":
                    fn = d.p['FriendlyName']
                    if len(fn) > 1:
                        return "\n".join(fn)

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
            # for r in range(rows):
            #     d = self._devices[pos][DevMdl.TOPIC]
            #     self.settings.beginGroup("Devices")
            #     if d in self.settings.childGroups():
            #         self.settings.remove(d)
            #     self.settings.endGroup()
            #     self._devices.pop(pos + r)
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

# class TasmotaDevicesTree(QAbstractItemModel):
#     def __init__(self, root=Node(""), parent=None):
#         super(TasmotaDevicesTree, self).__init__(parent)
#         self._rootNode = root
#
#         self.devices = {}
#
#         self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)
#         self.settings.beginGroup("Devices")
#
#         for d in self.settings.childGroups():
#             self.devices[d] = self.addDevice(TasmotaDevice, self.settings.value("{}/friendly_name".format(d), d))
#
#     def rowCount(self, parent=QModelIndex()):
#         if not parent.isValid():
#             parentNode = self._rootNode
#         else:
#             parentNode = parent.internalPointer()
#
#         return parentNode.childCount()
#
#     def columnCount(self, parent):
#         return 2
#
#     def data(self, index, role):
#
#         if not index.isValid():
#             return None
#
#         node = index.internalPointer()
#
#         if role == Qt.DisplayRole:
#             if index.column() == 0:
#                 return node.name()
#             elif index.column() == 1:
#                 return node.value()
#
#         elif role == Qt.DecorationRole:
#             if index.column() == 0:
#                 typeInfo = node.typeInfo()
#
#                 if typeInfo:
#                     return QIcon("GUI/icons/{}.png".format(typeInfo))
#
#         elif role == Qt.TextAlignmentRole:
#             if index.column() == 1:
#                 return Qt.AlignVCenter | Qt.AlignRight
#
#     def get_device_by_topic(self, topic):
#         for i in range(self._rootNode.childCount()):
#             d = self._rootNode.child(i)
#             if d.name() == topic:
#                 return self.index(d.row(), 0, QModelIndex())
#             return None
#
#     def setData(self, index, value, role=Qt.EditRole):
#
#         if index.isValid():
#             if role == Qt.EditRole:
#                 node = index.internalPointer()
#                 node.setValue(value)
#                 self.dataChanged.emit(index, index, [Qt.DisplayRole])
#                 return True
#         return False
#
#     def setDeviceFriendlyName(self, index, value, role=Qt.EditRole):
#         if index.isValid():
#             if role == Qt.EditRole:
#                 node = index.internalPointer()
#                 if value != node.friendlyName():
#                     node.setFriendlyName(value)
#                     self.dataChanged.emit(index, index, [Qt.DisplayRole])
#                     return True
#         return False
#
#     def setDeviceName(self, index, value, role=Qt.EditRole):
#         if index.isValid():
#             if role == Qt.EditRole:
#                 node = index.internalPointer()
#                 node.setName(value)
#                 self.dataChanged.emit(index, index, [Qt.DisplayRole])
#                 return True
#         return False
#
#     def headerData(self, section, orientation, role):
#         if role == Qt.DisplayRole:
#             if section == 0:
#                 return "Device"
#             else:
#                 return "Value"
#
#     def flags(self, index):
#         return Qt.ItemIsEnabled | Qt.ItemIsSelectable
#
#     def parent(self, index):
#
#         node = self.getNode(index)
#         parentNode = node.parent()
#
#         if parentNode == self._rootNode:
#             return QModelIndex()
#
#         return self.createIndex(parentNode.row(), 0, parentNode)
#
#     def index(self, row, column, parent):
#
#         parentNode = self.getNode(parent)
#
#         childItem = parentNode.child(row)
#
#         if childItem:
#             return self.createIndex(row, column, childItem)
#         else:
#             return QModelIndex()
#
#     def getNode(self, index):
#         if index.isValid():
#             node = index.internalPointer()
#             if node:
#                 return node
#
#         return self._rootNode
#
#     def insertRows(self, position, rows, parent=QModelIndex()):
#
#         parentNode = self.getNode(parent)
#
#         self.beginInsertRows(parent, position, position + rows - 1)
#
#         for row in range(rows):
#             childCount = parentNode.childCount()
#             childNode = Node("untitled" + str(childCount))
#             success = parentNode.insertChild(childCount, childNode)
#
#         self.endInsertRows()
#
#         return success
#
#     def addDevice(self, device_type, name, parent=QModelIndex()):
#         rc = self.rowCount(parent)
#         parentNode = self.getNode(parent)
#
#         device = device_type(name)
#         self.beginInsertRows(parent, rc, rc+1)
#         parentNode.insertChild(rc, device)
#         dev_idx = self.index(rc, 0, parent)
#         self.endInsertRows()
#
#         parentNode.devices()[name] = dev_idx
#
#         self.beginInsertRows(dev_idx, 0, len(device.provides()))
#         for p in device.provides().keys():
#             cc = device.childCount()
#             device.insertChild(cc, node_map[p](name=p))
#             device.provides()[p] = self.index(cc, 1, dev_idx)
#         self.endInsertRows()
#
#         return dev_idx
#
#     def removeRows(self, position, rows, parent=QModelIndex()):
#
#         parentNode = self.getNode(parent)
#         self.beginRemoveRows(parent, position, position + rows - 1)
#
#         for row in range(rows):
#             success = parentNode.removeChild(position)
#
#         self.endRemoveRows()
#
#         return success


class DeviceDelegate(QStyledItemDelegate):
    def __init__(self):
        super(DeviceDelegate, self).__init__()

    def sizeHint(self, option, index):
        col = index.column()
        col_name = index.model().sourceModel().columns[col]
        if col_name == "LWT":
            return QSize(16,1)

        elif col_name == "Power":
            if isinstance(index.data(), dict):
                num = len(index.data().keys())

                if num == 1:
                    w = 46

                elif num == 2:
                    w = 22

                elif num == 3:
                    w = 14

                else:
                    w = 10

                return QSize(20+num*(w+2), 1)

        return QStyledItemDelegate.sizeHint(self, option, index)

    def paint(self, p, option, index):
        col = index.column()
        col_name = index.model().sourceModel().columns[col]

        if col_name == "LWT":
            if option.state & QStyle.State_Selected:
                p.fillRect(option.rect, option.palette.highlight())

            px = self.icons.get(index.data().lower(), self.icons["undefined"])

            x = option.rect.center().x()+1 - px.rect().width() / 2
            y = option.rect.center().y() - px.rect().height() / 2

            p.drawPixmap(QRect(x, y, px.rect().width(), px.rect().height()), px)

        elif col_name == "Power":
            p.save()
            f = QFont(p.font())
            f.setPixelSize(6)
            p.setFont(f)

            if option.state & QStyle.State_Selected:
                p.fillRect(option.rect, option.palette.highlight())

            if isinstance(index.data(), dict):
                num = len(index.data().keys())

                r = option.rect.adjusted(2,2,-2,0)
                r.setHeight(24)

                if num == 1:
                    w = 46

                elif num == 2:
                    w = 22

                elif num == 3:
                    w = 14

                else:
                    w = 10

                for i,k in enumerate(index.data().keys()):
                    x = r.x() + (r.width() - (num * (w+2))) / 2 + 1
                    dip = QRectF(x + i*(w+2), r.y(), w, r.height())
                    p.fillRect(dip, QColor("white"))
                    p.setPen(QPen(QColor("darkgray")))
                    p.drawLine(dip.bottomLeft(), dip.bottomRight())
                    p.drawLine(dip.topRight(), dip.bottomRight())

                    p.setPen(QPen(QColor("black")))
                    p.drawLine(dip.topLeft(), dip.bottomLeft())
                    p.drawLine(dip.topLeft(), dip.topRight())

                    bar = QRect(QPoint(dip.center().x()-1, dip.center().y()-8), QPoint(dip.center().x()+1, dip.center().y()+8))
                    p.fillRect(bar, QColor("lightgrey").lighter(110))
                    p.drawRect(bar)

                    state = dip.adjusted(2, 2, 0, 0)
                    state.setHeight(8)
                    state.setWidth(w-4)

                    if index.data()[k] == "OFF":
                        state.moveTop(dip.y() + 14)
                        p.fillRect(state, QColor("lightgrey"))
                        p.drawText(state, Qt.AlignCenter, "OFF" if w > 15 else 'o')

                    else:
                        p.fillRect(state, QColor("lightgreen"))
                        p.drawText(state, Qt.AlignCenter, "ON" if w > 15 else 'I')

                    p.drawRect(state)

            p.restore()

        else:
            QStyledItemDelegate.paint(self, p, option, index)

