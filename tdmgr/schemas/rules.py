from typing import Dict

from pydantic import BaseModel, Json, RootModel

from tdmgr.schemas.common import OnOffEnum


class RuleSchema(BaseModel):
    State: OnOffEnum
    Once: OnOffEnum
    StopOnError: OnOffEnum
    Length: int
    Free: int
    Rules: Json


RuleResponseSchema = RootModel[Dict[str, RuleSchema]]
