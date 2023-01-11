import json
import re
from dataclasses import dataclass
from enum import Enum, auto

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QLineEdit,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from GUI.dialogs.modbus.common import commands, datatypes, RX_INT_OR_HEX
from GUI.widgets import DictComboBox, GroupBoxH, GroupBoxV, HLayout, SpinBox, VLayout

builtin_fields = [
    "Voltage",
    "Current",
    "Power",
    "ApparentPower",
    "ReactivePower",
    "Factor",
    "Frequency",
    "Total",
    "ExportActive",
]

modifiers = {
    -4: '/ 10000',
    -3: '/ 1000',
    -2: '/ 100',
    -1: '/ 10',
    0: 'no action',
    1: '* 10',
    2: '* 100',
    3: '* 1000',
    4: '* 10000',
}



class ListTooLong(ValueError):
    pass


class NoMatchError(ValueError):
    pass


class FieldColumnEnum(int, Enum):
    FieldName = 0
    Register = auto()
    Datatype = auto()
    Modifier = auto()


class UserFieldColumnEnum(int, Enum):
    JSONName = 0
    Register = auto()
    Datatype = auto()
    Modifier = auto()
    Name = auto()
    Unit = auto()
    Precision = auto()


@dataclass
class Column:
    name: str
    idx: int
    resize_mode: QHeaderView.ResizeMode


class ModbusEnergyEditorDialog(QWidget):
    def __init__(self, *args, **kwargs):
        super(ModbusEnergyEditorDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle("Modbus Energy rule editor")
        self.setupUI()

    def setupUI(self):
        # self.setMinimumSize(QSize(480, 480))
        layout = VLayout()

        gbSerialSettings = QGroupBox("Connection settings")
        gbSerialSettings.setMaximumWidth(250)

        flSerialSettings = QFormLayout()
        flSerialSettings.setSpacing(3)
        gbSerialSettings.setLayout(flSerialSettings)

        self.leRuleName = QLineEdit()
        self.leRuleName.textChanged.connect(self.input_changed)
        self.leRuleName.textChanged.connect(self.update_title)

        self.ecbBaudRate = QComboBox()
        self.ecbBaudRate.addItems(['9600', '115200'])
        self.ecbBaudRate.currentTextChanged.connect(self.input_changed)

        self.ecbConfig = QComboBox()
        self.ecbConfig.setEditable(True)
        self.ecbConfig.addItems(['8N1'])
        self.ecbConfig.currentTextChanged.connect(self.input_changed)

        self.sbPolling = SpinBox(minimum=200, maximum=9999999, singleStep=100)
        self.sbPolling.setSuffix(' ms')
        self.sbPolling.valueChanged.connect(self.input_changed)

        self.leAddress = QLineEdit("1")
        self.leAddress.textChanged.connect(self.input_changed)

        self.cbxFunction = DictComboBox(commands)
        self.cbxFunction.setCurrentIndex(1)
        self.cbxFunction.currentTextChanged.connect(self.input_changed)

        flSerialSettings.addRow("Name", self.leRuleName)
        flSerialSettings.addRow("Baud rate", self.ecbBaudRate)
        flSerialSettings.addRow("Config", self.ecbConfig)
        flSerialSettings.addRow("Polling [ms]", self.sbPolling)
        flSerialSettings.addRow("Address", self.leAddress)
        flSerialSettings.addRow("Function", self.cbxFunction)

        gbFields = GroupBoxV("Predefined fields")
        gbFields.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        fields_columns = [
            Column("Field name", FieldColumnEnum.FieldName, QHeaderView.Stretch),
            Column("Register", FieldColumnEnum.Register, QHeaderView.Stretch),
            Column("Datatype", FieldColumnEnum.Datatype, QHeaderView.ResizeToContents),
            Column("Modifier", FieldColumnEnum.Modifier, QHeaderView.Fixed),
        ]

        self.twFields = QTableWidget(0, 4)
        self.twFields.verticalHeader().setVisible(False)
        self.twFields.setSelectionBehavior(QTableWidget.SelectRows)
        self.twFields.setRowCount(len(builtin_fields))

        self.twFields.horizontalHeader().setHighlightSections(False)
        self.twFields.horizontalHeader().setAlternatingRowColors(True)
        self.twFields.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        for field in fields_columns:
            self.twFields.setHorizontalHeaderItem(field.idx, QTableWidgetItem(field.name))
            self.twFields.horizontalHeader().setSectionResizeMode(field.idx, field.resize_mode)

        for row, field in enumerate(builtin_fields):
            name = QTableWidgetItem(field)
            name.setCheckState(Qt.Unchecked)
            name.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)

            self.twFields.setItem(row, FieldColumnEnum.FieldName, name)
            self.twFields.setCellWidget(row, FieldColumnEnum.Datatype, self.get_datatype_cbx())
            self.twFields.setCellWidget(row, FieldColumnEnum.Modifier, self.get_modifier_cbx())

        gbFields.addElements(self.twFields)
        self.twFields.itemChanged.connect(self.input_changed)

        user_fields_columns = [
            Column("JSON name", UserFieldColumnEnum.JSONName, QHeaderView.Stretch),
            Column("Register", UserFieldColumnEnum.Register, QHeaderView.Stretch),
            Column("Datatype", UserFieldColumnEnum.Datatype, QHeaderView.Stretch),
            Column("Modifier", UserFieldColumnEnum.Modifier, QHeaderView.Fixed),
            Column("GUI name", UserFieldColumnEnum.Name, QHeaderView.Stretch),
            Column("GUI unit", UserFieldColumnEnum.Unit, QHeaderView.ResizeToContents),
            Column("GUI precision", UserFieldColumnEnum.Precision, QHeaderView.Fixed),
        ]

        gbUserFields = GroupBoxH("User-defined fields")
        self.twUserFields = QTableWidget(0, 7)
        self.twUserFields.setSelectionBehavior(QTableWidget.SelectRows)
        self.twUserFields.verticalHeader().setVisible(False)

        self.twUserFields.horizontalHeader().setHighlightSections(False)
        self.twUserFields.horizontalHeader().setAlternatingRowColors(True)
        self.twUserFields.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        for field in user_fields_columns:
            self.twUserFields.setHorizontalHeaderItem(field.idx, QTableWidgetItem(field.name))
            self.twUserFields.horizontalHeader().setSectionResizeMode(field.idx, field.resize_mode)

        bbUserFieldsBtns = QDialogButtonBox(Qt.Vertical)
        btnAddRow = bbUserFieldsBtns.addButton("Add row", QDialogButtonBox.ActionRole)
        btnDelRow = bbUserFieldsBtns.addButton("Delete row", QDialogButtonBox.ActionRole)

        btnAddRow.clicked.connect(self.add_user_row)

        self.twUserFields.itemChanged.connect(self.input_changed)
        gbUserFields.addElements(self.twUserFields, bbUserFieldsBtns)

        self.leResult = QLineEdit()
        self.leResult.setReadOnly(True)

        hl = HLayout(0)
        hl.addElements(gbSerialSettings, gbFields)
        layout.addElements(hl, gbUserFields, self.leResult)

        self.setLayout(layout)

    def update_title(self, title: str):
        self.setWindowTitle(f"Modbus Energy rule editor [{title}]")

    def add_user_row(self):
        row = self.twUserFields.rowCount()
        self.twUserFields.insertRow(row)

        json_name = QTableWidgetItem()
        json_name.setFlags(json_name.flags() | Qt.ItemIsUserCheckable)
        json_name.setCheckState(Qt.Unchecked)

        self.twUserFields.setItem(row, UserFieldColumnEnum.JSONName, json_name)
        self.twUserFields.setCellWidget(row, UserFieldColumnEnum.Datatype, self.get_datatype_cbx())
        self.twUserFields.setCellWidget(row, UserFieldColumnEnum.Modifier, self.get_modifier_cbx())
        self.twUserFields.setCellWidget(row, UserFieldColumnEnum.Precision, self.get_precision_sb())

    def get_datatype_cbx(self):
        dcbDatatype = DictComboBox(datatypes)
        dcbDatatype.currentTextChanged.connect(self.input_changed)
        return dcbDatatype

    def get_modifier_cbx(self):
        dcbModifier = DictComboBox(modifiers)
        dcbModifier.setCurrentIndex(4)
        dcbModifier.currentTextChanged.connect(self.input_changed)
        return dcbModifier

    def get_precision_sb(self):
        sbPrecision = SpinBox(minimum=0, maximum=29)
        sbPrecision.setFrame(False)
        sbPrecision.valueChanged.connect(self.input_changed)
        return sbPrecision

    def input_changed(self):
        self.leResult.setText(self.generate())

    @staticmethod
    def parse_int_hex(value: str):
        items = list(value.replace(' ', '').rstrip(',').split(','))

        for i, item in enumerate(list(items)):
            if i > 2:
                raise ListTooLong
            if match := re.match(RX_INT_OR_HEX, item):
                val = match.string
                try:
                    items[i] = int(val)
                except ValueError:
                    items[i] = val
            else:
                items.remove(item)

        if len(items) == 1:
            return items[0]
        if len(items) == 0:
            raise NoMatchError
        return items

    def generate(self):
        if not (name := self.leRuleName.text()):
            return "Rule name is missing"

        if not (config := self.ecbConfig.currentText()):
            return "Config is missing"

        if not (address := self.leAddress.text()):
            return "Address is missing"

        try:
            address = self.parse_int_hex(address)
        except ListTooLong:
            return "Up to 3 addresses allowed"
        except NoMatchError:
            return "Address must be either integer or hex"

        result = {
            "Name": name,
            "Baud": int(self.ecbBaudRate.currentText()),
            "Config": config,
            "Function": self.cbxFunction.currentData(Qt.UserRole),
            "Address": address,
        }

        poll = self.sbPolling.value()
        if poll != 200:
            result.update({"Poll": poll})

        fields = dict()
        for row in range(self.twFields.rowCount()):
            name_item = self.twFields.item(row, FieldColumnEnum.FieldName)
            if name_item.checkState() == Qt.Checked:
                name = name_item.text()
                if (register := self.twFields.item(row, FieldColumnEnum.Register)) is None:
                    return f"{name}: Register is missing"

                try:
                    register = self.parse_int_hex(register.text())
                except ListTooLong:
                    return f"{name}: Up to 3 registers allowed"
                except NoMatchError:
                    return f"{name}: Register must be either integer or hex"

                field = {"R": register}
                datatype = self.twFields.cellWidget(row, FieldColumnEnum.Datatype).currentData(Qt.UserRole)
                if datatype != 0:
                    field["T"] = datatype

                modifier = self.twFields.cellWidget(row, FieldColumnEnum.Modifier).currentData(Qt.UserRole)
                if modifier != 0:
                    field["F"] = modifier
                fields[name] = field

        user_fields = []
        for row in range(self.twUserFields.rowCount()):
            json_name_item = self.twUserFields.item(row, UserFieldColumnEnum.JSONName)

            if json_name_item.checkState() == Qt.Checked:
                json_name = json_name_item.text()
                if not json_name:
                    return f"User field #{row}: JSON name missing"

                if (register := self.twUserFields.item(row, FieldColumnEnum.Register)) is None:
                    return f"{json_name}: Register missing"

                field = {"J": json_name}

                try:
                    register = self.parse_int_hex(register.text())
                except ListTooLong:
                    return f"{json_name}: Up to 3 registers allowed"
                except NoMatchError:
                    return f"{json_name}: Register must be either integer or hex"

                field["R"] = register
                datatype = self.twUserFields.cellWidget(row, FieldColumnEnum.Datatype).currentData(Qt.UserRole)
                if datatype != 0:
                    field["T"] = datatype

                modifier = self.twUserFields.cellWidget(row, FieldColumnEnum.Modifier).currentData(Qt.UserRole)
                if modifier != 0:
                    field["F"] = modifier

                if (name_item := self.twUserFields.item(row, UserFieldColumnEnum.Name)) is not None:
                    if name_item_text := name_item.text():
                        field["G"] = name_item_text

                        if (unit_item := self.twUserFields.item(row, UserFieldColumnEnum.Unit)) is not None:
                            if unit_item_text := unit_item.text():
                                field["U"] = unit_item_text

                        precision_item = self.twUserFields.cellWidget(row, UserFieldColumnEnum.Precision)
                        field["D"] = precision_item.value()
                user_fields.append(field)

        if not (fields or user_fields):
            return "No default fields or user fields configured"

        result.update(fields)
        if user_fields:
            result.update({"User": user_fields})
        return json.dumps(result, separators=(',', ':'))
