from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Ollama endpoint (can be local or remote). Examples:
    # - Local Ollama: http://127.0.0.1:11434
    # - Remote/Cloud: https://ollama.example.com
    OLLAMA_URL: str = "http://127.0.0.1:11434"
    # API key to authenticate against Ollama Cloud (if required). Leave blank for local Ollama.
    OLLAMA_API_KEY: str = ""
    # Which model to use on the Ollama server
    MODEL: str = "qwen2.5-coder:7b"

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
