
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, Dict, Any
import json

class _testRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    test: str
    model: Optional[Dict[str, str]] = {
        "test": "_test",
    }
    file: Optional[Dict[str, Any]] = None

    @field_validator("model", mode="before")
    @classmethod
    def parse_model(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("model must be valid JSON string")
        return v