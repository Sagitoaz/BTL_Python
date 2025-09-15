from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Literal

DEFAULT_STOPS_PY = ["\n\n```", "\n\n##", "\n\n# ", "\n\n\"\"\"", "\n\n'''"]  
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 256
MAX_SIDE_CHARS = 4000

class CompleteRequest(BaseModel):
    prefix: str = Field("", description="Code before cursor")
    suffix: str = Field("", description="Code after cursor")
    language: Literal["python"] = "python"
    max_tokens: int = Field(DEFAULT_MAX_TOKENS, ge=1, le=512)
    temperature: float = Field(DEFAULT_TEMPERATURE, ge=0.0, le=1.0)
    stop: Optional[List[str]] = None

    code_only: bool = True
    allow_comments: bool = False

    @field_validator("stop", mode="before")
    @classmethod
    def sanitize_stops(cls, v: Optional[List[str]]):
        # Phân biệt None vs [] nếu sau này bạn muốn tắt stop hoàn toàn
        if v is None:
            return None
        if isinstance(v, list) and len(v) == 0:
            return []  # giữ nguyên: cố ý không có stop
        seen, out = set(), []
        for s in (s.strip() for s in v if s is not None):
            if s and s not in seen:
                seen.add(s)
                out.append(s)
        return out or []

    @model_validator(mode="after")
    def apply_defaults_and_trim(self):
        # Chỉ gán default khi client không gửi (None); nếu gửi [] thì tôn trọng
        if self.stop is None:
            self.stop = DEFAULT_STOPS_PY.copy()

        # self.prefix = _smart_trim_prefix(self.prefix, MAX_SIDE_CHARS)
        # self.suffix = _smart_trim_suffix(self.suffix, MAX_SIDE_CHARS)
        return self

class CompleteResponse(BaseModel):
    request_id: str
    completion: str
    # (meta có thể mở lại sau này)
    # model: Optional[str] = None
    # tokens_in: Optional[int] = None
    # tokens_out: Optional[int] = None
    # latency_ms: Optional[float] = None
