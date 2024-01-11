from enum import Enum, auto

from PyQt5.QtCore import Qt


class DeviceRoles(int, Enum):
    LWTRole = Qt.UserRole
    RestartReasonRole = auto()
    RSSIRole = auto()
    FirmwareRole = auto()
    PowerRole = auto()
    ShuttersRole = auto()
    ShutterPositionsRole = auto()
    ColorRole = auto()
    ModuleRole = auto()
    HardwareRole = auto()
