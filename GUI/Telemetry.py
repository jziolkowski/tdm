from json import loads, JSONDecodeError

from PyQt5.QtCore import Qt, QSettings, QTimer, QDir, QTime, QTime, QSize, QDateTime, pyqtSlot
from PyQt5.QtWidgets import QWidget, QTabWidget, QLineEdit, QTabBar, QLabel, QComboBox, QPushButton, QFrame, \
    QTableWidget, QHeaderView, QSizePolicy, QGroupBox, QFormLayout, QSpacerItem, QTreeView, QCheckBox, QRadioButton, \
    QButtonGroup, QTimeEdit, QLabel, \
    QListWidget, QListWidgetItem, QApplication, QDockWidget, QTreeWidget

from GUI import VLayout, HLayout, GroupBoxH, SpinBox, DetailLE, GroupBoxV, DeviceParam, DoubleSpinBox, \
    TimeItem, CounterItem
from Util.mqtt import MqttClient
from pprint import pprint
T_NAME, T_VALUE = range(2)

class TelemetryWidget(QDockWidget):
    def __init__(self, fname, topic, tele_topic, stat_topic, *args, **kwargs):
        super(TelemetryWidget, self).__init__(*args, **kwargs)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setWindowTitle(fname)

        # self.settings = QSettings("{}/TDM/tdm.cfg".format(QDir.homePath()), QSettings.IniFormat)
        # self.broker_hostname = self.settings.value('hostname', 'localhost')
        # self.broker_port = self.settings.value('port', 1883, int)
        # self.broker_username = self.settings.value('username')
        # self.broker_password = self.settings.value('password')

        # self.topic = topic
        # self.tele_topic = tele_topic
        # self.stat_topic = stat_topic

        self.tree = QTreeWidget()
        self.setWidget(self.tree)
        self.tree.setColumnCount(2)
        self.tree.setHeaderHidden(True)

        # self.setup_mqtt()
        self.tree_items = {}

    def setup_mqtt(self):
        self.mqtt = MqttClient()
        self.mqtt.connecting.connect(self.mqtt_connecting)
        self.mqtt.connected.connect(self.mqtt_connected)
        self.mqtt.disconnected.connect(self.mqtt_disconnected)
        self.mqtt.connectError.connect(self.mqtt_connectError)
        self.mqtt.messageSignal.connect(self.mqtt_message)

        self.mqtt.hostname = self.broker_hostname
        self.mqtt.port = self.broker_port

        if self.broker_username:
            self.mqtt.setAuth(self.broker_username, self.broker_password)

        self.mqtt.connectToHost()

    def mqtt_connecting(self):
        pass

    def mqtt_connected(self):
        self.mqtt.subscribe(self.tele_topic + "+")
        self.mqtt.subscribe(self.stat_topic + "+")

    def mqtt_disconnected(self):
        self.close()

    def mqtt_connectError(self, rc):
        pass

    def mqtt_message(self, topic, msg):
        reply = topic.split("/")[-1]
        ok = False
        try:
            if msg.startswith("{"):
                payload = loads(msg)
            else:
                payload = msg
            ok = True
        except JSONDecodeError as e:
            with open("{}/TDM/error.log".format(QDir.homePath()), "a+") as l:
                l.write("{}\t{}\t{}\t{}\n".format(
                    QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss"),
                    topic, msg, e.msg))
        if ok:
            try:
                if reply in ('SENSOR', 'STATUS8'):
                    if reply == 'STATUS8':
                        payload = payload['StatusSNS']
                        self.parse_telemetry(payload)

                elif reply == 'STATUS':
                    payload = payload['Status']
                    self.setWindowTitle(payload['FriendlyName'][0])

            except KeyError as k:
                pass

    @pyqtSlot(str, str)
    def parse_telemetry(self, topic, payload):
        if 'Time' in payload:
            time_item = self.tree_items.get('time')
            if not time_item:
                time_item = TimeItem()
                self.tree_items['time'] = time_item
                self.tree.addTopLevelItem(time_item)
            time_item.setData(T_VALUE, Qt.DisplayRole, payload.pop('Time'))

        if 'COUNTER' in payload:
            cnt_item = self.tree_items.get('counter')
            if not cnt_item:
                cnt_item = CounterItem()
                self.tree_items['counter'] = cnt_item
                self.tree.addTopLevelItem(cnt_item)
            cnt_item.setValues(payload.pop('COUNTER'))

        pprint(payload)

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

    def closeEvent(self, e):
        self.mqtt.disconnectFromHost()
        e.accept()
#
# pte_payload = QPlainTextEdit()
#         pte_payload.setFont(fnt_mono)
#         pte_payload.setMinimumHeight(400)
#         pte_payload.setReadOnly(True)
#         if payload:
#             payload = str(payload)
#             if payload.startswith("{") or payload.startswith("["):
#                 pte_payload.setPlainText(dumps(loads(payload), indent=2))
#             else:
#                 pte_payload.setPlainText(payload)
#         else:
#             pte_payload.setPlainText("(empty)")