from json import loads, JSONDecodeError

from PyQt5.QtCore import Qt, QSettings, QTimer, QDir, QTime, QTime, QSize, QDateTime, pyqtSlot
from PyQt5.QtWidgets import QWidget, QTabWidget, QLineEdit, QTabBar, QLabel, QComboBox, QPushButton, QFrame, \
    QTableWidget, QHeaderView, QSizePolicy, QGroupBox, QFormLayout, QSpacerItem, QTreeView, QCheckBox, QRadioButton, \
    QButtonGroup, QTimeEdit, QLabel, \
    QListWidget, QListWidgetItem, QApplication, QDockWidget, QTreeWidget, QTreeWidgetItem

from GUI import VLayout, HLayout, GroupBoxH, SpinBox, DetailLE, GroupBoxV, DeviceParam, DoubleSpinBox, \
    TimeItem, CounterItem

from pprint import pprint
T_NAME, T_VALUE = range(2)

class TelemetryWidget(QDockWidget):
    def __init__(self, device, *args, **kwargs):
        super(TelemetryWidget, self).__init__(*args, **kwargs)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setWindowTitle(device.p['FriendlyName'][0])

        self.tree_items = {}

        self.tree = QTreeWidget()
        self.setWidget(self.tree)
        self.tree.setColumnCount(2)
        self.tree.setHeaderHidden(True)

        device.update_telemetry.connect(self.update_telemetry)

        self.device = device

    def get_top_item(self, name):
        item = self.tree_items.get(name)
        if not item:
            item = QTreeWidgetItem()
            item.setText(0, name)
            self.tree.addTopLevelItem(item)
            self.tree_items[name] = item
        return item

    def get_nested_item(self, parent, name):
        nested_items = self.tree_items.get(parent)
        if nested_items:
            _top_item = nested_items["_top_item"]
            item = nested_items.get(name)
            if not item:
                item = QTreeWidgetItem()
                item.setText(0, name)
                _top_item.addChild(item)
                nested_items[name] = item
            return item
        else:
            _top_item = QTreeWidgetItem()
            _top_item.setText(0, parent)
            self.tree.addTopLevelItem(_top_item)
            self.tree_items[parent] = {"_top_item": _top_item}

            item = QTreeWidgetItem()
            item.setText(0, name)
            _top_item.addChild(item)
            self.tree_items[parent][name] = item
            return item


    @pyqtSlot()
    def update_telemetry(self):
        t = self.device.t
        time = t.pop('Time')

        time_item = self.get_top_item("Time")
        time_item.setText(1, time)

        for key in sorted(t.keys()):
            v = t[key]
            if isinstance(v, dict):
                for nested_key, nested_v in v.items():
                    nested_item = self.get_nested_item(key, nested_key)
                    nested_item.setText(1, str(nested_v))
            else:
                item = self.get_top_item(key)
                item.setText(1, str(v))

        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(1)


        # device = self.telemetry_model.devices.get(self.device_model.topic(index))
        # if device:
        #     node = self.telemetry_model.getNode(device)
        #     time = node.provides()['Time']
        #     if 'Time' in payload:
        #         self.telemetry_model.setData(time, )
        #
        #     temp_unit = "C"
        #     pres_unit = "hPa"
        #
        #     if 'TempUnit' in payload:
        #         temp_unit = payload.pop('TempUnit')
        #
        #     if 'PressureUnit' in payload:
        #         pres_unit = payload.pop('PressureUnit')
        #
        #     for sensor in sorted(payload.keys()):
        #         if sensor == 'DS18x20':
        #             for sns_name in payload[sensor].keys():
        #                 d = node.devices().get(sensor)
        #                 if not d:
        #                     d = self.telemetry_model.addDevice(DS18x20, payload[sensor][sns_name]['Type'], device)
        #                 self.telemetry_model.getNode(d).setTempUnit(temp_unit)
        #                 payload[sensor][sns_name]['Id'] = payload[sensor][sns_name].pop('Address')
        #
        #                 pr = self.telemetry_model.getNode(d).provides()
        #                 for pk in pr.keys():
        #                     self.telemetry_model.setData(pr[pk], payload[sensor][sns_name].get(pk))
        #                 self.tview.expand(d)
        #
        #         elif sensor.startswith('DS18B20'):
        #             d = node.devices().get(sensor)
        #             if not d:
        #                 d = self.telemetry_model.addDevice(DS18x20, sensor, device)
        #             self.telemetry_model.getNode(d).setTempUnit(temp_unit)
        #             pr = self.telemetry_model.getNode(d).provides()
        #             for pk in pr.keys():
        #                 self.telemetry_model.setData(pr[pk], payload[sensor].get(pk))
        #             self.tview.expand(d)
        #
        #         if sensor == 'COUNTER':
        #             d = node.devices().get(sensor)
        #             if not d:
        #                 d = self.telemetry_model.addDevice(CounterSns, "Counter", device)
        #             pr = self.telemetry_model.getNode(d).provides()
        #             for pk in pr.keys():
        #                 self.telemetry_model.setData(pr[pk], payload[sensor].get(pk))
        #             self.tview.expand(d)
        #
        #         else:
        #             d = node.devices().get(sensor)
        #             if not d:
        #                 d = self.telemetry_model.addDevice(sensor_map.get(sensor, Node), sensor, device)
        #             pr = self.telemetry_model.getNode(d).provides()
        #             if 'Temperature' in pr:
        #                 self.telemetry_model.getNode(d).setTempUnit(temp_unit)
        #             if 'Pressure' in pr or 'SeaPressure' in pr:
        #                 self.telemetry_model.getNode(d).setPresUnit(pres_unit)
        #             for pk in pr.keys():
        #                 self.telemetry_model.setData(pr[pk], payload[sensor].get(pk))
        #             self.tview.expand(d)
        # self.tview.resizeColumnToContents(0)