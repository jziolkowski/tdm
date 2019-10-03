from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDockWidget, QTreeWidget, QTreeWidgetItem

# TODO: merge get_top_item() and get_nested_item() to a recursive generator

item_icons = {
    "Time": "time.png",
}

item_units = {
    # ENERGY units
    "Voltage": "V",
    "Current": "A",
    "Power": "W",
    "ApparentPower": "VA",
    "ReactivePower": "VAR",
    "Frequency": "Hz",
    "Total": "kWh",
    "Yesterday": "kWh",
    "Today": "kWh",
}

class TelemetryWidget(QDockWidget):
    def __init__(self, device, *args, **kwargs):
        super(TelemetryWidget, self).__init__(*args, **kwargs)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setWindowTitle(device.p['FriendlyName1'])

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
            item.setIcon(0, QIcon("GUI/icons/{}".format(item_icons.get(name, ""))))
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
                item.setIcon(0, QIcon("GUI/icons/{}".format(item_icons.get(name, ""))))
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

        time = t.get("Time")

        time_item = self.get_top_item("Time")
        time_item.setText(1, time.replace("T", " "))

        for key in sorted(t.keys()):
            if key != "Time":
                v = t[key]
                if isinstance(v, dict):
                    for nested_key, nested_v in v.items():
                        nested_item = self.get_nested_item(key, nested_key)
                        nested_item.setText(1, "{} {}".format(nested_v, item_units.get(nested_key, "")))

                else:
                    item = self.get_top_item(key)
                    item.setText(1, "{}".format(v))

        self.tree.expandAll()
        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(1)
