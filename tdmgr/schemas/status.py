from typing import List, Optional, Union

from pydantic import create_model

from tdmgr.schemas.common import TDMBaseModel


class StatusSchema(TDMBaseModel):
    ButtonRetain: int
    ButtonTopic: str
    DeviceName: Optional[str] = None
    FriendlyName: List[str]
    InfoRetain: Optional[int] = None
    LedMask: Optional[str] = None
    LedState: int
    Module: int
    Power: int
    PowerLock: Optional[str] = None
    PowerOnState: int
    PowerRetain: int
    SaveData: int
    SaveState: int
    SensorRetain: int
    StateRetain: Optional[int] = None
    StatusRetain: Optional[int] = None
    SwitchMode: List[int]
    SwitchRetain: int
    SwitchTopic: str
    Topic: str


class StatusPRMSchema(TDMBaseModel):
    BCResetTime: Optional[str] = None
    Baudrate: int
    BootCount: int
    CfgHolder: Optional[int] = None
    GroupTopic: str
    OtaUrl: str
    RestartReason: str
    SaveAddress: Optional[str] = None
    SaveCount: int
    SerialConfig: Optional[str] = None
    Sleep: int
    StartupUTC: str
    Uptime: str


class StatusFWRSchema(TDMBaseModel):
    Boot: Optional[int] = None
    BuildDateTime: str
    CR: Optional[str] = None
    Core: Optional[str] = None
    CpuFrequency: Optional[int] = None
    Hardware: Optional[str] = None
    SDK: str
    Version: str


class StatusLOGSchema(TDMBaseModel):
    LogHost: str
    LogPort: int
    MqttLog: Optional[int] = None
    Resolution: Optional[str] = None
    SSId: List[str]
    SerialLog: int
    SetOption: List[str]
    SysLog: int
    TelePeriod: int
    WebLog: int


class StatusMEMSchema(TDMBaseModel):
    Drivers: Optional[str] = None
    Features: List[str]
    FlashChipId: str
    FlashFrequency: Optional[int] = None
    FlashMode: Optional[Union[int, str]] = None
    FlashSize: int
    Free: int
    Heap: int
    I2CDriver: Optional[str] = None
    ProgramFlashSize: int
    ProgramSize: int
    PsrFree: Optional[int] = None
    PsrMax: Optional[int] = None
    Sensors: Optional[str] = None
    StackLowMark: Optional[int] = None


class BaseNETSchema(TDMBaseModel):
    DNSServer1: Optional[str] = None
    DNSServer2: Optional[str] = None
    DNSServer: Optional[str] = None
    Gateway: str
    HTTP_API: Optional[int] = None
    Hostname: str
    IP6Global: Optional[str] = None
    IP6Local: Optional[str] = None
    IPAddress: str
    Mac: str
    Subnetmask: str


class StatusNETSchema(BaseNETSchema):
    Ethernet: Optional[BaseNETSchema] = None
    Webserver: int
    WifiConfig: int
    WifiPower: Optional[int] = None


class StatusMQTSchema(TDMBaseModel):
    KEEPALIVE: int
    MAX_PACKET_SIZE: int
    MqttClient: str
    MqttClientMask: str
    MqttCount: Optional[int] = None
    MqttHost: str
    MqttPort: int
    MqttType: Optional[int] = None
    MqttUser: str
    SOCKET_TIMEOUT: Optional[int] = None


class StatusPTHSchema(TDMBaseModel):
    CurrentHigh: Union[int, List[int]]
    CurrentLow: Union[int, List[int]]
    MaxEnergy: Optional[int] = None
    MaxEnergyStart: Optional[int] = None
    MaxPower: Optional[int] = None
    MaxPowerHold: Optional[int] = None
    MaxPowerWindow: Optional[int] = None
    PowerDelta: Union[int, List[int]]
    PowerHigh: Union[int, List[int]]
    PowerLow: Union[int, List[int]]
    VoltageHigh: Optional[int] = None
    VoltageLow: Union[int, List[int]]


class StatusSTKSchema(TDMBaseModel):
    CallChain: List[str]
    DEPC: str
    EPC: List[str]
    EXCVADDR: str
    Exception: int
    Reason: str


class StatusSNSSchema(TDMBaseModel):
    TempUnit: Optional[str] = None
    Time: str


class StatusTIMSchema(TDMBaseModel):
    EndDST: str
    Local: str
    StartDST: str
    Sunrise: Optional[str] = None
    Sunset: Optional[str] = None
    Timezone: Union[str, int]
    UTC: str


class WifiSchema(TDMBaseModel):
    AP: int
    BSSId: str
    Channel: Union[int, List[int]]
    Downtime: Optional[str] = None
    LinkCount: Optional[int] = None
    Mode: Optional[str] = None
    RSSI: int
    SSId: str
    Signal: Optional[int] = None


class BerrySchema(TDMBaseModel):
    HeapUsed: int
    Objects: int


class StateSTSBaseSchema(TDMBaseModel):
    Berry: Optional[BerrySchema] = None
    Channel: Optional[List[int]] = None
    Color: Optional[str] = None
    Fade: Optional[str] = None
    HSBColor: Optional[str] = None
    Heap: Optional[int] = None
    LedTable: Optional[str] = None
    LoadAvg: Optional[int] = None
    MqttCount: Optional[int] = None
    Scheme: Optional[int] = None
    Sleep: Optional[int] = None
    SleepMode: Optional[str] = None
    Speed: Optional[int] = None
    Time: str
    Uptime: str
    UptimeSec: Optional[int] = None
    Vcc: Optional[float] = None
    White: Optional[int] = None
    Wifi: WifiSchema


class StateBaseSchema(StateSTSBaseSchema):
    Dimmer: Optional[int] = None


StateSchema = create_model(
    'StateSchema',
    __base__=StateBaseSchema,
    **{f"POWER{idx}": (Optional[str], None) for idx in list(map(str, range(1, 33))) + [""]},
)

_power_dict = {f"POWER{idx}": (Optional[str], None) for idx in list(map(str, range(1, 33))) + [""]}
_dimmer_dict = {f"Dimmer{idx}": (Optional[int], None) for idx in list(map(str, range(1, 6))) + [""]}
_channel_dict = {f"Channel{idx}": (Optional[int], None) for idx in list(map(str, range(1, 6)))}

StatusSTSSchema = create_model(
    'StatusSTSSchema',
    __base__=StateSTSBaseSchema,
    **{
        **_power_dict,
        **_dimmer_dict,
        **_channel_dict
    },
)


class StatusResponseSchema(TDMBaseModel):
    Status: StatusSchema


class Status1ResponseSchema(TDMBaseModel):
    StatusPRM: StatusPRMSchema


class Status2ResponseSchema(TDMBaseModel):
    StatusFWR: StatusFWRSchema


class Status3ResponseSchema(TDMBaseModel):
    StatusLOG: StatusLOGSchema


class Status4ResponseSchema(TDMBaseModel):
    StatusMEM: StatusMEMSchema


class Status5ResponseSchema(TDMBaseModel):
    StatusNET: StatusNETSchema


class Status6ResponseSchema(TDMBaseModel):
    StatusMQT: StatusMQTSchema


class Status7ResponseSchema(TDMBaseModel):
    StatusTIM: StatusTIMSchema


class Status9ResponseSchema(TDMBaseModel):
    StatusPTH: StatusPTHSchema

class Status10ResponseSchema(TDMBaseModel):
    StatusSNS: StatusSNSSchema


class Status11ResponseSchema(TDMBaseModel):
    StatusSTS: StatusSTSSchema


class Status12ResponseSchema(TDMBaseModel):
    StatusSTK: StatusSTKSchema


class Status0ResponseSchema(StatusResponseSchema):
    # StatusSTS: Optional[Json]
    StatusFWR: StatusFWRSchema
    StatusLOG: StatusLOGSchema
    StatusMEM: StatusMEMSchema
    StatusMQT: Optional[StatusMQTSchema]
    StatusNET: StatusNETSchema
    StatusPRM: StatusPRMSchema
    StatusSNS: Optional[Status10ResponseSchema]


STATUS_SCHEMA_MAP: [str, TDMBaseModel] = {
    'STATE': StateSchema,
    'STATUS': StatusResponseSchema,
    'STATUS0': Status0ResponseSchema,
    'STATUS1': Status1ResponseSchema,
    'STATUS2': Status2ResponseSchema,
    'STATUS3': Status3ResponseSchema,
    'STATUS4': Status4ResponseSchema,
    'STATUS5': Status5ResponseSchema,
    'STATUS6': Status6ResponseSchema,
    'STATUS7': Status7ResponseSchema,
    'STATUS9': Status9ResponseSchema,
    'STATUS10': Status10ResponseSchema,
    'STATUS11': Status11ResponseSchema,
    'STATUS12': Status12ResponseSchema,
}

StatusSchemaType = STATUS_SCHEMA_MAP.values()
