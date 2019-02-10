from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt, QAbstractTableModel, QSettings
from PyQt5.QtGui import QIcon, QColor

from GUI import columns
from Util import DevMdl
from Util.libtasmota import modules
from Util.nodes import *


class TasmotaDevicesModel(QAbstractTableModel):
    def __init__(self, *args, **kwargs):
        super(TasmotaDevicesModel, self).__init__(*args, **kwargs)
        self.settings = QSettings()
        self.settings.beginGroup("Devices")
        self.__devices = []

        for d in self.settings.childGroups():
            self.loadDevice(d, self.settings.value("{}/full_topic".format(d)), self.settings.value("{}/friendly_name".format(d)))

    def addDevice(self, topic, full_topic, friendly_name="", lwt="undefined"):
        rc = self.rowCount()
        self.beginInsertRows(QModelIndex(), rc, rc)
        self.__devices.append([lwt, topic, full_topic, friendly_name if friendly_name else topic] + ([''] * (len(columns) - 4)))
        self.settings.setValue("{}/full_topic".format(topic), full_topic)
        self.settings.setValue("{}/friendly_name".format(topic), friendly_name)
        self.endInsertRows()
        return True

    def loadDevice(self, topic, full_topic, friendly_name="", lwt="undefined"):
        rc = self.rowCount()
        self.beginInsertRows(QModelIndex(), rc, rc)
        self.__devices.append([lwt, topic, full_topic, friendly_name if friendly_name else topic] + ([''] * (len(columns) - 4)))
        self.endInsertRows()
        return True

    def get_device_by_topic(self, topic):
        device = [i for i,x in enumerate(self.__devices) if x[DevMdl.TOPIC] == topic]
        return device[0] if device else -1

    def columnCount(self, parent=None):
        return len(columns)

    def rowCount(self, parent=None):
        return len(self.__devices)

    def insertRows(self, pos, rows, parent=QModelIndex()):
        self.beginInsertRows(parent, pos, pos + rows -1)
        for i in range(rows):
            self.__devices.append(['undefined'] + ([''] * (len(columns)-1)))
        self.endInsertRows()
        return True

    def removeRows(self, pos, rows, parent=QModelIndex()):
        if pos + rows <= self.rowCount():
            self.beginRemoveRows(parent, pos, pos + rows -1)
            for r in range(rows):
                d = self.__devices[pos][DevMdl.TOPIC]
                if d in self.settings.childGroups():
                    self.settings.remove(d)
                self.__devices.pop(pos + r)
            self.endRemoveRows()
            return True
        return False

    def headerData(self, col, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role==Qt.DisplayRole:
            if col <= len(columns):
                return columns[col][0]
            else:
                return ''

    def data(self, idx, role=Qt.DisplayRole):
        if idx.isValid():
            row = idx.row()
            col = idx.column()

            if role in (Qt.DisplayRole, Qt.EditRole):
                val = self.__devices[row][col]
                if val and col == DevMdl.UPTIME:
                    return val.replace('0T', '').replace('T', 'd ')

                elif val and col == DevMdl.MODULE:
                    return modules.get(val, 'Unknown')

                elif col == DevMdl.LOADAVG:
                    if val:
                        return val
                    return "n/a" if self.__devices[row][DevMdl.LWT] == 'online' else ''

                return self.__devices[row][col]

            elif role == Qt.TextAlignmentRole:
                if col in (DevMdl.RSSI, DevMdl.POWER, DevMdl.LOADAVG):
                    return Qt.AlignCenter

                elif col == DevMdl.UPTIME:
                    return Qt.AlignRight | Qt.AlignVCenter

            elif role == Qt.BackgroundColorRole and col == DevMdl.RSSI:
                rssi = self.__devices[row][DevMdl.RSSI]
                if rssi:
                    rssi = int(rssi)
                    if rssi < 50:
                        return QColor("#ef4522")
                    elif rssi > 75:
                        return QColor("#7eca27")
                    else:
                        return QColor("#fcdd0f")

            elif role == Qt.DecorationRole:
                if col == DevMdl.FRIENDLY_NAME:
                    return QIcon("./GUI/icons/{}.png".format(self.__devices[row][DevMdl.LWT].lower()))

            elif role == Qt.ToolTipRole:
                if col == DevMdl.FIRMWARE:
                    return self.__devices[row][DevMdl.FIRMWARE]

                elif col == DevMdl.FRIENDLY_NAME:
                    return "Topic: {}\nFull topic: {}".format(self.__devices[row][DevMdl.TOPIC], self.__devices[row][DevMdl.FULL_TOPIC])

    def setData(self, idx, val, role=Qt.EditRole):
        row = idx.row()
        col = idx.column()

        if role == Qt.EditRole:
            dev = self.__devices[row][DevMdl.TOPIC]
            d = dev if dev else val

            if col == DevMdl.FRIENDLY_NAME:
                self.settings.setValue("{}/friendly_name".format(d), val)

            elif col == DevMdl.FULL_TOPIC:
                self.settings.setValue("{}/full_topic".format(d), val)

            elif col == DevMdl.TOPIC:
                self.settings.setValue("{}/full_topic".format(val), self.__devices[row][DevMdl.FULL_TOPIC])
                self.settings.setValue("{}/friendly_name".format(val), self.__devices[row][DevMdl.FRIENDLY_NAME])
                self.settings.remove(d)

            self.__devices[row][col] = val
            self.dataChanged.emit(idx, idx)
            self.settings.sync()
            return True
        return False

    def flags(self, idx):
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

class TasmotaDevicesTree(QAbstractItemModel):
    """INPUTS: Node, QObject"""

    def __init__(self, root=Node(""), parent=None):
        super(TasmotaDevicesTree, self).__init__(parent)
        self._rootNode = root

        self.devices = {}

        self.settings = QSettings()
        self.settings.beginGroup("Devices")

        for d in self.settings.childGroups():
            self.devices[d] = self.addDevice(TasmotaDevice, self.settings.value("{}/friendly_name".format(d), d))

    """INPUTS: QModelIndex"""
    """OUTPUT: int"""

    def rowCount(self, parent=QModelIndex()):
        if not parent.isValid():
            parentNode = self._rootNode
        else:
            parentNode = parent.internalPointer()

        return parentNode.childCount()

    """INPUTS: QModelIndex"""
    """OUTPUT: int"""

    def columnCount(self, parent):
        return 2

    """INPUTS: QModelIndex, int"""
    """OUTPUT: QVariant, strings are cast to QString which is a QVariant"""

    def data(self, index, role):

        if not index.isValid():
            return None

        node = index.internalPointer()

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return node.name()
            elif index.column() == 1:
                return node.value()

        elif role == Qt.DecorationRole:
            if index.column() == 0:
                typeInfo = node.typeInfo()

                if typeInfo:
                    return QIcon("GUI/icons/{}.png".format(typeInfo))

        elif role == Qt.TextAlignmentRole:
            if index.column() == 1:
                return Qt.AlignVCenter | Qt.AlignRight


    def get_device_by_topic(self, topic):
        for i in range(self._rootNode.childCount()):
            d = self._rootNode.child(i)
            if d.name() == topic:
                return self.index(d.row(), 0, QModelIndex())
            return None


    """INPUTS: QModelIndex, QVariant, int (flag)"""

    def setData(self, index, value, role=Qt.EditRole):

        if index.isValid():
            if role == Qt.EditRole:
                node = index.internalPointer()
                node.setValue(value)
                self.dataChanged.emit(index, index, [Qt.DisplayRole])
                return True
        return False

    def setDeviceFriendlyName(self, index, value, role=Qt.EditRole):
        if index.isValid():
            if role == Qt.EditRole:
                node = index.internalPointer()
                node.setFriendlyName(value)
                self.dataChanged.emit(index, index, [Qt.DisplayRole])
                return True
        return False

    """INPUTS: int, Qt::Orientation, int"""
    """OUTPUT: QVariant, strings are cast to QString which is a QVariant"""

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if section == 0:
                return "Device"
            else:
                return "Value"

    """INPUTS: QModelIndex"""
    """OUTPUT: int (flag)"""

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    """INPUTS: QModelIndex"""
    """OUTPUT: QModelIndex"""
    """Should return the parent of the node with the given QModelIndex"""

    def parent(self, index):

        node = self.getNode(index)
        parentNode = node.parent()

        if parentNode == self._rootNode:
            return QModelIndex()

        return self.createIndex(parentNode.row(), 0, parentNode)

    """INPUTS: int, int, QModelIndex"""
    """OUTPUT: QModelIndex"""
    """Should return a QModelIndex that corresponds to the given row, column and parent node"""

    def index(self, row, column, parent):

        parentNode = self.getNode(parent)

        childItem = parentNode.child(row)

        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    """CUSTOM"""
    """INPUTS: QModelIndex"""

    def getNode(self, index):
        if index.isValid():
            node = index.internalPointer()
            if node:
                return node

        return self._rootNode

    """INPUTS: int, int, QModelIndex"""

    def insertRows(self, position, rows, parent=QModelIndex()):

        parentNode = self.getNode(parent)

        self.beginInsertRows(parent, position, position + rows - 1)

        for row in range(rows):
            childCount = parentNode.childCount()
            childNode = Node("untitled" + str(childCount))
            success = parentNode.insertChild(childCount, childNode)

        self.endInsertRows()

        return success


    def addDevice(self, device_type, name, parent=QModelIndex()):
        rc = self.rowCount(parent)
        parentNode = self.getNode(parent)

        device = device_type(name)
        self.beginInsertRows(parent, rc, rc+1)
        parentNode.insertChild(rc, device)
        dev_idx = self.index(rc, 0, parent)
        self.endInsertRows()

        parentNode.devices()[name] = dev_idx

        self.beginInsertRows(dev_idx, 0, len(device.provides()))
        for p in device.provides().keys():
            cc = device.childCount()
            device.insertChild(cc, node_map[p](name=p))
            device.provides()[p] = self.index(cc, 1, dev_idx)
        self.endInsertRows()

        return dev_idx

    """INPUTS: int, int, QModelIndex"""

    def removeRows(self, position, rows, parent=QModelIndex()):

        parentNode = self.getNode(parent)
        self.beginRemoveRows(parent, position, position + rows - 1)

        for row in range(rows):
            success = parentNode.removeChild(position)

        self.endRemoveRows()

        return success