class Node(object):
    def __init__(self, name=None, parent=None):

        self._name = name
        self._value = ''
        self._children = []
        self._parent = parent
        self._devices = {}
        self._provides = {}

        if parent is not None:
            parent.addChild(self)

    def typeInfo(self):
        return "node"

    def provide(self, values):
        for v in values:
            self._provides[v] = None

    def provides(self):
        return self._provides

    def devices(self):
        return self._devices

    def addChild(self, child):
        self._children.append(child)
        child._parent = self
        return True

    def insertChild(self, position, child):

        if position < 0 or position > len(self._children):
            return False

        self._children.insert(position, child)
        child._parent = self
        return True

    def removeChild(self, position):

        if position < 0 or position > len(self._children):
            return False

        child = self._children.pop(position)
        child._parent = None

        return True

    def name(self):
        return self._name

    def setName(self, name):
        self._name = name

    def value(self):
        return self._value

    def setValue(self, value):
        self._value = value

    def child(self, row):
        if row < self.childCount():
            return self._children[row]

    def childCount(self):
        return len(self._children)

    def parent(self):
        return self._parent

    def row(self):
        if self._parent is not None:
            return self._parent._children.index(self)

    def __repr__(self):
        return "{}: {}".format(type(self), self.name())


class VCC(Node):
    def __init__(self, name=None, parent=None):
        super(VCC, self).__init__(name, parent)

    def typeInfo(self):
        return "vcc"


class Time(Node):
    def __init__(self, name=None, parent=None):
        super(Time, self).__init__(name, parent)

    def typeInfo(self):
        return "time"


class Temperature(Node):
    def __init__(self, name=None, parent=None):
        super(Temperature, self).__init__(name, parent)

    def typeInfo(self):
        return "temperature"

    def value(self):
        return "{} °{}".format(self._value, self._parent._temp_unit)


class Humidity(Node):
    def __init__(self, name=None, parent=None):
        super(Humidity, self).__init__(name, parent)

    def typeInfo(self):
        return "humidity"

    def value(self):
        return "{}%".format(self._value)


class Pressure(Node):
    def __init__(self, name=None, parent=None):
        super(Pressure, self).__init__(name, parent)

    def typeInfo(self):
        return "pressure"

    def value(self):
        return "{} {}".format(self._value, self._parent._pres_unit)


class SeaPressure(Pressure):
    def __init__(self, name=None, parent=None):
        super(SeaPressure, self).__init__(name, parent)


class ID(Node):
    def __init__(self, name=None, parent=None):
        super(ID, self).__init__(name, parent)

    def typeInfo(self):
        return "id"


class Illuminance(Node):
    def __init__(self, name=None, parent=None):
        super(Illuminance, self).__init__(name, parent)

    def typeInfo(self):
        return "illuminance"


class Molecule(Node):
    def __init__(self, name=None, parent=None):
        super(Molecule, self).__init__(name, parent)

    def typeInfo(self):
        return "molecule"


class UV(Node):
    def __init__(self, name=None, parent=None):
        super(UV, self).__init__(name, parent)

    def typeInfo(self):
        return "uv"


class Info(Node):
    def __init__(self, name=None, parent=None):
        super(Info, self).__init__(name, parent)

    def typeInfo(self):
        return "info"


class PowerFactor(Node):
    def __init__(self, name=None, parent=None):
        super(PowerFactor, self).__init__(name, parent)

    def typeInfo(self):
        return "powerfactor"


class Date(Node):
    def __init__(self, name=None, parent=None):
        super(Date, self).__init__(name, parent)

    def typeInfo(self):
        return "date"


class TotalKWh(Node):
    def __init__(self, name=None, parent=None):
        super(TotalKWh, self).__init__(name, parent)

    def typeInfo(self):
        return "total"

    def value(self):
        return "{} kWh".format(self._value)


class KWh(Node):
    def __init__(self, name=None, parent=None):
        super(KWh, self).__init__(name, parent)

    def typeInfo(self):
        return "kwh"

    def value(self):
        return "{} kWh".format(self._value if self._value else 0)


class Power(Node):
    def __init__(self, name=None, parent=None):
        super(Power, self).__init__(name, parent)

    def typeInfo(self):
        return "power"


class Voltage(Node):
    def __init__(self, name=None, parent=None):
        super(Voltage, self).__init__(name, parent)

    def typeInfo(self):
        return "voltage"


class Current(Node):
    def __init__(self, name=None, parent=None):
        super(Current, self).__init__(name, parent)

    def typeInfo(self):
        return "current"


class Error(Node):
    def __init__(self, name=None, parent=None):
        super(Error, self).__init__(name, parent)

    def typeInfo(self):
        return "error"


class Red(Node):
    def __init__(self, name=None, parent=None):
        super(Red, self).__init__(name, parent)

    def typeInfo(self):
        return "red"


class Green(Node):
    def __init__(self, name=None, parent=None):
        super(Green, self).__init__(name, parent)

    def typeInfo(self):
        return "green"


class Blue(Node):
    def __init__(self, name=None, parent=None):
        super(Blue, self).__init__(name, parent)

    def typeInfo(self):
        return "blue"


class Ambient(Node):
    def __init__(self, name=None, parent=None):
        super(Ambient, self).__init__(name, parent)

    def typeInfo(self):
        return "ambient"


class CCT(Node):
    def __init__(self, name=None, parent=None):
        super(CCT, self).__init__(name, parent)

    def typeInfo(self):
        return "cct"


class Proximity(Node):
    def __init__(self, name=None, parent=None):
        super(Proximity, self).__init__(name, parent)

    def typeInfo(self):
        return "proximity"


class Counter(Node):
    def __init__(self, name=None, parent=None):
        super(Counter, self).__init__(name, parent)

    def typeInfo(self):
        return "counter"


class Device(Node):
    def __init__(self, name=None, parent=None):
        super(Device, self).__init__(name, parent)

    def typeInfo(self):
        return "device"


class TelemetryDevice(Device):
    def __init__(self, name=None, parent=None):
        super(TelemetryDevice, self).__init__(name, parent)
        self.provide(['Time', 'Vcc'])
        self._friendly_name = ""

    def typeInfo(self):
        return "tasmotadevice"

    def setFriendlyName(self, fname):
        self._friendly_name = fname

    def friendlyName(self):
        return self._friendly_name

    def name(self):
        if self._friendly_name:
            return self._friendly_name
        return self._name


class Thermometer(Device):
    def __init__(self, name=None, parent=None):
        super(Thermometer, self).__init__(name, parent)
        self._temp_unit = "C"
        self.provide(['Temperature'])

    def setTempUnit(self, unit):
        self._temp_unit = unit


class ThermometerHumidity(Device):
    def __init__(self, name=None, parent=None):
        super(ThermometerHumidity, self).__init__(name, parent)
        self._temp_unit = "C"
        self.provide(['Temperature', 'Humidity'])

    def setTempUnit(self, unit):
        self._temp_unit = unit


class ThermometerHumidityPressure(Device):
    def __init__(self, name=None, parent=None):
        super(ThermometerHumidityPressure, self).__init__(name, parent)
        self._temp_unit = "C"
        self._pres_unit = "hPa"
        self.provide(['Temperature', 'Humidity', 'Pressure'])

    def setTempUnit(self, unit):
        self._temp_unit = unit

    def setPresUnit(self, unit):
        self._pres_unit = unit


class ThermometerPressure(Device):
    def __init__(self, name=None, parent=None):
        super(ThermometerPressure, self).__init__(name, parent)
        self._temp_unit = "C"
        self._pres_unit = "hPa"
        self.provide(['Temperature', 'Pressure'])

    def setTempUnit(self, unit):
        self._temp_unit = unit

    def setPresUnit(self, unit):
        self._pres_unit = unit


class BME280(ThermometerHumidityPressure):
    def __init__(self, name=None, parent=None):
        super(BME280, self).__init__(name, parent)
        self.provide(['Temperature', 'Humidity', 'Pressure', 'SeaPressure'])


class BME680(ThermometerHumidityPressure):
    def __init__(self, name=None, parent=None):
        super(BME680, self).__init__(name, parent)
        self.provide(['Temperature', 'Humidity', 'Pressure', 'Gas'])


class DS18x20(Thermometer):
    def __init__(self, name=None, parent=None):
        super(DS18x20, self).__init__(name, parent)
        self.provide(['Temperature', 'Id'])


class MHZ19B(Thermometer):
    def __init__(self, name=None, parent=None):
        super(MHZ19B, self).__init__(name, parent)
        self.provide(['Temperature', 'CarbonDioxide'])


class MAX31855(Device):
    def __init__(self, name=None, parent=None):
        super(MAX31855, self).__init__(name, parent)
        self._temp_unit = "C"
        self.provide(['ProbeTemperature', 'ReferenceTemperature', 'Error'])

    def setTempUnit(self, unit):
        self._temp_unit = unit


class MGS(Device):
    def __init__(self, name=None, parent=None):
        super(MGS, self).__init__(name, parent)
        self.provide(['C2H5OH', 'C3H8', 'C4H10', 'CH4', 'CO', 'H2', 'NH3', 'NO2'])


class CCS811(Device):
    def __init__(self, name=None, parent=None):
        super(CCS811, self).__init__(name, parent)
        self.provide(['eCO2', 'TVOC'])


class IlluminanceSns(Device):
    def __init__(self, name=None, parent=None):
        super(IlluminanceSns, self).__init__(name, parent)
        self.provide(['Illuminance'])


class VEML6070(Device):
    def __init__(self, name=None, parent=None):
        super(VEML6070, self).__init__(name, parent)
        self.provide(['UvIndex', 'UvIndexText', 'UvPower'])


class MHZ19B(Thermometer):
    def __init__(self, name=None, parent=None):
        super(MHZ19B, self).__init__(name, parent)
        self.provide(['CarbonDioxide'])


class APDS9960(Device):
    def __init__(self, name=None, parent=None):
        super(APDS9960, self).__init__(name, parent)
        self.provide(['Red', 'Green', 'Blue', 'Ambient', 'CCT', 'Proximity'])


class CounterSns(Device):
    def __init__(self, name=None, parent=None):
        super(CounterSns, self).__init__(name, parent)
        self.provide(['C1'])


class Energy(Device):
    def __init__(self, name=None, parent=None):
        super(Energy, self).__init__("Energy", parent)
        self.provide(['TotalStartTime', 'Total', 'Yesterday', 'Today', 'Period', 'Power', 'ApparentPower', 'ReactivePower', 'Factor', 'Voltage', 'Current'])


node_map = {
    'Vcc': VCC,
    'Time': Time,
    'Id': ID,
    'Temperature': Temperature,
    'Humidity': Humidity,
    'Pressure': Pressure,
    'SeaPressure': Pressure,
    'CarbonDioxide': Molecule,
    'Gas': Molecule,
    'NH3': Molecule,
    'CO': Molecule,
    'NO2': Molecule,
    'C3H8': Molecule,
    'C4H10': Molecule,
    'CH4': Molecule,
    'H2': Molecule,
    'C2H5OH': Molecule,
    'eCO2': Molecule,
    'TVOC': Molecule,
    'Illuminance': Illuminance,
    'UvIndex': UV,
    'UvIndexText': Info,
    'UvPower': UV,
    'ProbeTemperature': Temperature,
    'ReferenceTemperature': Temperature,
    'Error': Error,
    'C1': Counter,
    'C2': Counter,
    'C3': Counter,
    'C4': Counter,
    'TotalStartTime': Date,
    'Yesterday': KWh,
    'Today': KWh,
    'Period': KWh,
    'Total': TotalKWh,
    'Power': Power,
    'ApparentPower': Power,
    'ReactivePower': Power,
    'Factor': PowerFactor,
    'Voltage': Voltage,
    'Current': Current,
    'Red': Red,
    'Green': Green,
    'Blue': Blue,
    'Ambient': Ambient,
    'CCT': CCT,
    'Proximity': Proximity


}
sensor_map = {
    'AM2301': ThermometerHumidity,
    'BME280': BME280,
    'SHT3X-0x44': ThermometerHumidity,
    'SI7020': ThermometerHumidity,
    'BMP180': ThermometerPressure,
    'BMP280': ThermometerPressure,
    'LM75AD': Thermometer,
    'MHZ19B': MHZ19B,
    'BME680': BME680,
    'MGS': MGS,
    'CCS811': CCS811,
    'BH1750': Illuminance,
    'TSL2561': Illuminance,
    'VEML6070': VEML6070,
    'MAX31855': MAX31855,
    'COUNTER': CounterSns,
    'ENERGY': Energy,
    'APDS9960': APDS9960
}
