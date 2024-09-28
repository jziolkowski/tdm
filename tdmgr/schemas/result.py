from typing import List, Optional

from pydantic import BaseModel, create_model


class TemplateResultSchema(BaseModel):
    NAME: str
    GPIO: List[int]
    FLAG: int
    BASE: int


class PulseTimeLegacySchema(BaseModel):
    Set: int
    Remaining: int


class PulseTimeLegacyResultSchema(BaseModel):
    PulseTime1: PulseTimeLegacySchema
    PulseTime2: PulseTimeLegacySchema
    PulseTime3: PulseTimeLegacySchema
    PulseTime4: PulseTimeLegacySchema
    PulseTime5: PulseTimeLegacySchema
    PulseTime6: PulseTimeLegacySchema
    PulseTime7: PulseTimeLegacySchema
    PulseTime8: PulseTimeLegacySchema


class PulseTimeSchema(BaseModel):
    Set: List[int]
    Remaining: List[int]


class PulseTimeResultSchema(BaseModel):
    PulseTime: PulseTimeSchema


class ShutterSchema(BaseModel):
    Position: int
    Direction: int
    Target: int
    Tilt: int


ShutterResultSchema = create_model(
    "ShutterResultSchema",
    __base__=BaseModel,
    **{f"Shutter{idx}": (Optional[ShutterSchema], None) for idx in range(1, 9)},
)
