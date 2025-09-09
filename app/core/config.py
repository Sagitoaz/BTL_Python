from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OLLAMA_URL: str = "http://127.0.0.1:11434"
    MODEL: str = "starcoder2:3b"
    API_KEY: str = ""
    TIMEOUT_SECONDS: int = 300
    ALLOW_ORIGINS: str = "*"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()