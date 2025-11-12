from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Groq Cloud API - Get your key from console.groq.com
    GROQ_API_KEY: str = ""
    # Recommended models (updated Nov 2025):
    # - llama-3.3-70b-versatile (newest, best quality)
    # - llama-3.1-8b-instant (fastest)
    # - mixtral-8x7b-32768 (large context)
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 9000

    # Internal server API key (for protecting this FastAPI server)
    API_KEY: str = "5conmeo"

    # LLM / request tuning
    NUM_CTX: int = 4096
    TIMEOUT_SECONDS: int = 120

    # CORS and middleware
    ALLOW_ORIGINS: str = "*"
    HEADERS_MIDDLEWARE: str = "X-Request-ID"
    REQUEST_ID: str = "request_id"
    POSTPROCESS_ENABLED: bool = True
    AUTO_FORMAT: bool = True  # Auto-format completions with black/autopep8

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore old OLLAMA_URL, MODEL env vars during migration


settings = Settings()
