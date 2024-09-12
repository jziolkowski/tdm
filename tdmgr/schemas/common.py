import logging
from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator


class OnOffEnum(str, Enum):
    ON = "ON"
    OFF = "OFF"


class TDMBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def log_extra_fields(cls, values):
        if cls.__name__ != "StatusSNSSchema" and values.model_extra:
            logging.warning("%s has extra fields: %s", cls.__name__, values.model_extra)
        return values
