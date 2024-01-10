from typing import List

from pydantic import BaseModel


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
