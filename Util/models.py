import re

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt, QAbstractTableModel, QSettings, QSize, QRect, QDateTime, \
    QDir, QRectF, QPoint
from PyQt5.QtGui import QIcon, QColor, QPixmap, QFont, QPen
from PyQt5.QtWidgets import QStyledItemDelegate, QStyle

from Util import found_obj
from Util.nodes import *


# class TasmotaDevicesModel(QAbstractTableModel):
#     def __init__(self, *args, **kwargs):
#         super(TasmotaDevicesModel, self).__init__(*args, **kwargs)
#         self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)
#         self.settings.beginGroup("Devices")
#         self._devices = []
#
#         for d in self.settings.childGroups():
#             self.loadDevice(d, self.settings.value("{}/full_topic".format(d)), self.settings.value("{}/friendly_name".format(d)))
#
#         self.settings.endGroup()
#
#     def addDevice(self, topic, full_topic, lwt="undefined"):
#         rc = self.rowCount()
#         self.beginInsertRows(QModelIndex(), rc, rc)
#         self._devices.append([lwt, topic, full_topic, topic] + ([''] * (len(columns) - 4)))
#         self.settings.beginGroup("Devices")
#         self.settings.setValue("{}/full_topic".format(topic), full_topic)
#         self.settings.setValue("{}/friendly_name".format(topic), full_topic)
#         self.settings.endGroup()
#         self.endInsertRows()
#         return self.index(rc, 0)
#
#     def loadDevice(self, topic, full_topic, friendly_name="", lwt="undefined"):
#         rc = self.rowCount()
#         self.beginInsertRows(QModelIndex(), rc, rc)
#         self._devices.append([lwt, topic, full_topic, friendly_name if friendly_name else topic] + ([''] * (len(columns) - 4)))
#         self.endInsertRows()
#         return True
#
#     def findDevice(self, topic):
#         split_topic = topic.split('/')
#         possible_topic = split_topic[1]
#
#         if possible_topic in ('tele', 'stat'):
#             possible_topic = split_topic[0]
#
#         for i, d in enumerate(self._devices):
#             match = match_topic(d[DevMdl.FULL_TOPIC], topic)
#
#             if match:
#                 found = match.groupdict()
#                 if found['topic'] == d[DevMdl.TOPIC]:
#                     found.update({'index': self.index(i, DevMdl.LWT)})
#                     return found_obj(found)
#
#         return found_obj({'index': QModelIndex(), 'topic': possible_topic, 'reply': split_topic[-1]})
#
#     def columnCount(self, parent=None):
#         return len(columns)
#
#     def rowCount(self, parent=None):
#         return len(self._devices)
#
#     def insertRows(self, pos, rows, parent=QModelIndex()):
#         self.beginInsertRows(parent, pos, pos + rows -1)
#         for i in range(rows):
#             self._devices.append(['undefined'] + ([''] * (len(columns)-1)))
#         self.endInsertRows()
#         return True
#
#     def removeRows(self, pos, rows, parent=QModelIndex()):
#         if pos + rows <= self.rowCount():
#             self.beginRemoveRows(parent, pos, pos + rows -1)
#             for r in range(rows):
#                 d = self._devices[pos][DevMdl.TOPIC]
#                 self.settings.beginGroup("Devices")
#                 if d in self.settings.childGroups():
#                     self.settings.remove(d)
#                 self.settings.endGroup()
#                 self._devices.pop(pos + r)
#             self.endRemoveRows()
#             return True
#         return False
#
#     def headerData(self, col, orientation, role=Qt.DisplayRole):
#         if orientation == Qt.Horizontal and role==Qt.DisplayRole:
#             if col <= len(columns):
#                 return columns[col][0]
#             else:
#                 return ''
#
#     def data(self, idx, role=Qt.DisplayRole):
#         if idx.isValid():
#             row = idx.row()
#             col = idx.column()
#
#             if role in [Qt.DisplayRole, Qt.EditRole]:
#                 val = self._devices[row][col]
#                 if val and col == DevMdl.UPTIME:
#                     val = str(val)
#                     if val.startswith("0T"):
#                         val = val.replace('0T', '')
#                     return val.replace('T', 'd ')
#
#                 elif val and col == DevMdl.FIRMWARE:
#                     return val.replace('(', ' (')
#
#                 elif col == DevMdl.LOADAVG:
#                     if val:
#                         return val
#                     return "n/a" if self._devices[row][DevMdl.LWT] == 'online' else ''
#
#                 elif col == DevMdl.BSSID:
#                     alias = self.settings.value("BSSID/{}".format(val))
#                     if alias:
#                         return alias
#
#                 return self._devices[row][col]
#
#             elif role == Qt.TextAlignmentRole:
#                 if col in (DevMdl.RSSI, DevMdl.MAC, DevMdl.IP, DevMdl.SSID, DevMdl.BSSID, DevMdl.CHANNEL, DevMdl.POWER, DevMdl.LOADAVG, DevMdl.CORE, DevMdl.TELEPERIOD):
#                     return Qt.AlignCenter
#
#                 elif col == DevMdl.UPTIME:
#                     return Qt.AlignRight | Qt.AlignVCenter
#
#                 elif col == DevMdl.RESTART_REASON:
#                     return Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap
#
#             elif role == Qt.BackgroundColorRole and col == DevMdl.RSSI:
#                 rssi = self._devices[row][DevMdl.RSSI]
#                 if rssi:
#                     rssi = int(rssi)
#                     if rssi < 50:
#                         return QColor("#ef4522")
#                     elif rssi > 75:
#                         return QColor("#7eca27")
#                     else:
#                         return QColor("#fcdd0f")
#
#             elif role == Qt.ToolTipRole:
#                 if col == DevMdl.FIRMWARE:
#                     return self._devices[row][DevMdl.FIRMWARE]
#
#                 elif col == DevMdl.BSSID:
#                     return self._devices[row][DevMdl.BSSID]
#
#                 elif col == DevMdl.FRIENDLY_NAME:
#                     return "Topic: {}\nFull topic: {}".format(self._devices[row][DevMdl.TOPIC], self._devices[row][DevMdl.FULL_TOPIC])
#
#                 elif col == DevMdl.POWER:
#                     return "\n".join(["{} is {}".format(k, v) for k, v in self._devices[row][DevMdl.POWER].items()])
#
#     def setData(self, idx, val, role=Qt.EditRole):
#         row = idx.row()
#         col = idx.column()
#
#         if role == Qt.EditRole:
#             dev = self._devices[row][DevMdl.TOPIC]
#             old_val = self._devices[row][col]
#             if val != old_val:
#                 self.settings.beginGroup("Devices")
#                 if col == DevMdl.FRIENDLY_NAME:
#                     self.settings.setValue("{}/friendly_name".format(dev), val)
#                 elif col == DevMdl.FULL_TOPIC:
#                     self.settings.setValue("{}/full_topic".format(dev), val)
#                 self.settings.endGroup()
#                 self._devices[row][col] = val
#                 self.dataChanged.emit(idx, idx)
#                 self.settings.sync()
#                 return True
#         return False
#
#     def flags(self, idx):
#         return Qt.ItemIsSelectable | Qt.ItemIsEnabled
#
#     def updateValue(self, idx, column, val):
#         if idx.isValid():
#             row = idx.row()
#             idx = self.index(row, column)
#             self.setData(idx, val)
#
#     def topic(self, idx):
#         if idx and idx.isValid():
#             row = idx.row()
#             return self._devices[row][DevMdl.TOPIC]
#         return None
#
#     def fullTopic(self, idx):
#         if idx and idx.isValid():
#             row = idx.row()
#             return self._devices[row][DevMdl.FULL_TOPIC]
#         return None
#
#     def module(self, idx):
#         if idx.isValid():
#             row = idx.row()
#             return self._devices[row][DevMdl.MODULE]
#         return None
#
#     def firmware(self, idx):
#         if idx.isValid():
#             row = idx.row()
#             return self._devices[row][DevMdl.FIRMWARE]
#         return None
#
#     def core(self, idx):
#         if idx.isValid():
#             row = idx.row()
#             return self._devices[row][DevMdl.CORE]
#         return None
#
#     def friendly_name(self, idx):
#         if idx.isValid():
#             row = idx.row()
#             return self._devices[row][DevMdl.FRIENDLY_NAME]
#         return ""
#
#     def commandTopic(self, idx):
#         if idx.isValid():
#             row = idx.row()
#             return self._devices[row][DevMdl.FULL_TOPIC].replace("%prefix%", "cmnd").replace("%topic%", self._devices[row][DevMdl.TOPIC])
#         return None
#
#     def statTopic(self, idx):
#         if idx.isValid():
#             row = idx.row()
#             return self._devices[row][DevMdl.FULL_TOPIC].replace("%prefix%", "stat").replace("%topic%", self._devices[row][DevMdl.TOPIC])
#         return None
#
#     def teleTopic(self, idx):
#         if idx.isValid():
#             row = idx.row()
#             return self._devices[row][DevMdl.FULL_TOPIC].replace("%prefix%", "tele").replace("%topic%", self._devices[row][DevMdl.TOPIC])
#         return None
#
#     def isDefaultTemplate(self, idx):
#         if idx.isValid():
#             return self._devices[idx.row()][DevMdl.FULL_TOPIC] in ["%prefix%/%topic%/", "%topic%/%prefix%/"]
#
#     def bssid(self, idx):
#         if idx.isValid():
#             row = idx.row()
#             return self._devices[row][DevMdl.BSSID]
#         return None
#
#     def power(self, idx):
#         if idx.isValid():
#             row = idx.row()
#             return self._devices[row][DevMdl.POWER]
#         return None
#
#     def ip(self, idx):
#         if idx.isValid():
#             row = idx.row()
#             return self._devices[row][DevMdl.IP]
#         return None
#
#     def mac(self, idx):
#         if idx.isValid():
#             row = idx.row()
#             return self._devices[row][DevMdl.MAC]
#         return None
#
#     def refreshBSSID(self):
#         first = self.index(0, DevMdl.BSSID)
#         last = self.index(self.rowCount(), DevMdl.BSSID)
#         self.dataChanged.emit(first, last)


class TasmotaDevicesModel2(QAbstractTableModel):
    def __init__(self, tasmota_env):
        super().__init__()
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

        if key in self.columns:
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

                if col_name == "FriendlyName" and val:
                    val = val[0]

                elif col_name == "Module":
                    if val == 0:
                        return d.p['Template'].get('NAME', "Fetching template name...")
                    else:
                        return d.module()

                elif col_name == "Version" and val:
                    return val.replace('(', ' (')

                elif col_name == "Uptime" and val:
                    if val.startswith("0T"):
                        val = val.replace('0T', '')
                    val = val.replace('T', 'd ')

                elif col_name == "Core" and val:
                    return val.replace('_', '.')

                elif col_name == "Time" and val:
                    return val.replace('T', ' ')

                elif col_name == "Power":
                    return d.power()

                return val



            #
            #     elif col == DevMdl.BSSID:
            #         alias = self.settings.value("BSSID/{}".format(val))
            #         if alias:
            #             return alias
            #
            #     return self._devices[row][col]
            #
            elif role == Qt.TextAlignmentRole:
                # Left-aligned columns
                if col_name in ("FriendlyName", "Topic", "FullTopic", "Module", "RestartReason", "OtaUrl", "Hostname", "Version"):
                    return Qt.AlignLeft | Qt.AlignVCenter

                # Right-aligned columns
                elif col_name in ("Uptime"):
                    return Qt.AlignRight | Qt.AlignVCenter

                # elif col == DevMdl.RESTART_REASON:
                #     return Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap

                else:
                    return Qt.AlignCenter

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

                # elif col_name == "BSSID":
                #     return self._devices[row][DevMdl.BSSID]

                elif col_name == "FriendlyName":
                    fn = d.p['FriendlyName']
                    if len(fn) > 1:
                        return "\n".join(fn)
            #
            #     elif col == DevMdl.POWER:
            #         return "\n".join(["{} is {}".format(k, v) for k, v in self._devices[row][DevMdl.POWER].items()])

    def addDevice(self, device):
        self.beginInsertRows(QModelIndex(), 0, 0)
        device.property_changed = self.notify_change
        device.module_changed = self.module_change
        self.endInsertRows()

    def columnIndex(self, column):
        return self.columns.index(column)

# class ConsoleModel(QAbstractTableModel):
#     def __init__(self, *args, **kwargs):
#         super(ConsoleModel, self).__init__(*args, **kwargs)
#         self._entries = []
#
#     def addEntry(self, topic, device, description, payload, known=True):
#         self.beginInsertRows(QModelIndex(), 0, 0)
#         self._entries.insert(0, [QDateTime.currentDateTime(), topic, device, description, payload, known])
#         self.endInsertRows()
#
#     def columnCount(self, parent=None):
#         return len(columns_console)
#
#     def rowCount(self, parent=None):
#         return len(self._entries)
#
#     def headerData(self, col, orientation, role=Qt.DisplayRole):
#         if orientation == Qt.Horizontal and role==Qt.DisplayRole:
#             if col <= len(columns_console):
#                 return columns_console[col][0]
#             else:
#                 return ''
#
#     def data(self, idx, role=Qt.DisplayRole):
#         if idx.isValid():
#             row = idx.row()
#             col = idx.column()
#
#             if role == Qt.DisplayRole:
#                 if col == CnsMdl.TIMESTAMP:
#                     return self._entries[row][col].toString("yyyy-MM-dd hh:mm:ss")
#
#                 return self._entries[row][col]
#
#             elif role == Qt.BackgroundColorRole:
#                 if not self._entries[row][CnsMdl.KNOWN]:
#                     return QColor("yellow")
#                 elif self._entries[row][CnsMdl.PAYLOAD] == "":
#                     return QColor("red")
#
#
#     def flags(self, idx):
#         return Qt.ItemIsSelectable | Qt.ItemIsEnabled


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
        self.icons = {
            'online': QPixmap("./GUI/icons/online.png"),
            'offline': QPixmap("./GUI/icons/offline.png"),
            'undefined': QPixmap("./GUI/icons/undefined.png"),
            'on': QPixmap("./GUI/icons/on.png"),
            'off': QPixmap("./GUI/icons/off.png"),
        }

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

