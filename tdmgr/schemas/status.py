from typing import List, Optional, Union

from pydantic import BaseModel, create_model


class StatusSchema(BaseModel):
    Module: int
    DeviceName: Optional[str] = None
    FriendlyName: List[str]
    Topic: str
    ButtonTopic: str
    Power: int
    PowerOnState: int
    LedState: int
    LedMask: Optional[str] = None
    SaveData: int
    SaveState: int
    SwitchTopic: str
    SwitchMode: List[int]
    ButtonRetain: int
    SwitchRetain: int
    SensorRetain: int
    PowerRetain: int


class StatusPRMSchema(BaseModel):
    Baudrate: int
    GroupTopic: str
    OtaUrl: str
    RestartReason: str
    Uptime: str
    StartupUTC: str
    Sleep: int
    CfgHolder: Optional[int] = None
    BootCount: int
    SaveCount: int
    SaveAddress: Optional[str] = None


class StatusFWRSchema(BaseModel):
    Version: str
    BuildDateTime: str
    Boot: Optional[int] = None
    Core: Optional[str] = None
    SDK: str
    Hardware: Optional[str] = None


class StatusLOGSchema(BaseModel):
    SerialLog: int
    WebLog: int
    MqttLog: int
    SysLog: int
    LogHost: str
    LogPort: int
    SSId: List[str]
    TelePeriod: int
    Resolution: str
    SetOption: List[str]


class StatusMEMSchema(BaseModel):
    ProgramSize: int
    Free: int
    Heap: int
    ProgramFlashSize: int
    FlashSize: int
    FlashChipId: str
    FlashMode: Optional[Union[int, str]] = None
    Features: List[str]
    Drivers: str
    Sensors: str


class StatusNETSchema(BaseModel):
    Hostname: str
    IPAddress: str
    Gateway: str
    Subnetmask: str
    DNSServer: Optional[str] = None
    Mac: str
    Webserver: int
    WifiConfig: int


class StatusMQTSchema(BaseModel):
    MqttHost: str
    MqttPort: int
    MqttClientMask: str
    MqttClient: str
    MqttUser: str
    MqttCount: int
    MAX_PACKET_SIZE: int
    KEEPALIVE: int


class StatusPTHSchema(BaseModel):
    PowerDelta: Union[int, List[int]]
    PowerLow: Union[int, List[int]]
    PowerHigh: Union[int, List[int]]
    VoltageLow: Union[int, List[int]]
    CurrentLow: Union[int, List[int]]
    CurrentHigh: Union[int, List[int]]


class StatusSTKSchema(BaseModel):
    Exception: int
    Reason: str
    EPC: List[str]
    EXCVADDR: str
    DEPC: str
    CallChain: List[str]


class StatusTIMSchema(BaseModel):
    UTC: str
    Local: str
    StartDST: str
    EndDST: str
    Timezone: Union[str, int]
    Sunrise: Optional[str] = None
    Sunset: Optional[str] = None


class WifiSchema(BaseModel):
    AP: int
    SSId: str
    BSSId: str
    Channel: Union[int, List[int]]
    RSSI: int
    Signal: Optional[int] = None
    LinkCount: int
    Downtime: str


class BerrySchema(BaseModel):
    HeapUsed: int
    Objects: int


class StateSTSBaseSchema(BaseModel):
    Time: str
    Uptime: str
    UptimeSec: int
    Heap: int
    SleepMode: str
    Sleep: int
    LoadAvg: int
    MqttCount: int
    Wifi: WifiSchema


class StateBaseSchema(StateSTSBaseSchema):
    Vcc: Optional[float] = None
    Dimmer: Optional[int] = None
    Color: Optional[str] = None
    HSBColor: Optional[str] = None
    Channel: Optional[Union[int, List[int]]] = None
    Scheme: Optional[int] = None
    Fade: Optional[str] = None
    Speed: Optional[int] = None
    LedTable: Optional[str] = None
    Berry: Optional[BerrySchema] = None


StateSchema = create_model(
    'StateSchema',
    __base__=StateBaseSchema,
    **{f"POWER{idx}": (Optional[str], None) for idx in list(map(str, range(1, 33))) + [""]},
)

StatusSTSSchema = create_model(
    'StatusSTSSchema',
    __base__=StateSTSBaseSchema,
    **{f"POWER{idx}": (Optional[str], None) for idx in list(map(str, range(1, 33))) + [""]},
)


class StatusResponseSchema(BaseModel):
    Status: StatusSchema


class Status1ResponseSchema(BaseModel):
    StatusPRM: StatusPRMSchema


class Status2ResponseSchema(BaseModel):
    StatusFWR: StatusFWRSchema


class Status3ResponseSchema(BaseModel):
    StatusLOG: StatusLOGSchema


class Status4ResponseSchema(BaseModel):
    StatusMEM: StatusMEMSchema


class Status5ResponseSchema(BaseModel):
    StatusNET: StatusNETSchema


class Status6ResponseSchema(BaseModel):
    StatusMQT: StatusMQTSchema


class Status7ResponseSchema(BaseModel):
    StatusTIM: StatusTIMSchema


class Status9ResponseSchema(BaseModel):
    StatusPTH: StatusPTHSchema


class Status11ResponseSchema(BaseModel):
    StatusSTS: StatusSTSSchema


class Status12ResponseSchema(BaseModel):
    StatusSTK: StatusSTKSchema


class Status0ResponseSchema(StatusResponseSchema):
    StatusPRM: StatusPRMSchema
    StatusFWR: StatusFWRSchema
    StatusLOG: StatusLOGSchema
    StatusMEM: StatusMEMSchema
    StatusNET: StatusNETSchema
    StatusMQT: Optional[StatusMQTSchema]
    # StatusSNS: Optional[Status10ResponseSchema]
    # StatusSTS: Optional[Json]


STATUS_SCHEMA_MAP: [str, BaseModel] = {
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
    'STATUS11': Status11ResponseSchema,
    'STATUS12': Status12ResponseSchema,
}

StatusSchemaType = STATUS_SCHEMA_MAP.values()
