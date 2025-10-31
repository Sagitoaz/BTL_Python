from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Groq Cloud API - Get your key from console.groq.com
    GROQ_API_KEY: str = ""
    # Recommended models: llama-3.1-70b-versatile (fast), codellama-34b-instruct (code-focused)
    GROQ_MODEL: str = "llama-3.1-70b-versatile"

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

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
