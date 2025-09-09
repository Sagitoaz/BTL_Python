from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

DEFAULT_STOPS = ["\n\n```", "\n\n##"]

class CompleteRequest(BaseModel):
    prefix: str = ""
    suffix: str = ""
    language: str = "python"
    max_tokens: int = Field(256, ge=1, le=512)
    temperature: float = Field(0.2, ge=0.0, le=1.0)
    stop: Optional[List[str]] = None

    @field_validator("language")
    @classmethod
    def normalize_lang(cls, v: str) -> str:
        return (v or "").strip().lower()

class CompleteResponse(BaseModel):
    request_id: str
    completion: str