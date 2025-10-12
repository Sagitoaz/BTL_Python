from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

DEFAULT_STOPS_PY = ["\n\n```", "\n\n##", "\n\n# ", '\n\n"""', "\n\n'''"]
DEFAULT_MAX_TOKENS = 128
DEFAULT_TEMPERATURE = 0.2


class CompleteRequest(BaseModel):
    prefix: str = ""
    suffix: str = ""
    language: Literal[
        "python", "javascript", "typescript", "java", "c", "cpp", "c++", "go", "rust", "kotlin", ""
    ] = "python"
    max_tokens: int = Field(DEFAULT_MAX_TOKENS, ge=1, le=512)
    temperature: float = Field(DEFAULT_TEMPERATURE, ge=0.0, le=1.0)
    stop: list[str] | None = None

    code_only: bool = True

    @field_validator("stop", mode="before")
    @classmethod
    def sanitize_stops(cls, v: list[str] | None):
        if v is None:
            return None
        return [s for s in v if isinstance(s, str) and s]

    @model_validator(mode="after")
    def normalize_language(self):
        if self.language:
            self.language = self.language.lower()
        return self


class CompleteResponse(BaseModel):
    request_id: str
    completion: str
