from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        case_sensitive = False
    OLLAMA_URL: str = "http://127.0.0.1:11434"
    MODEL: str = "qwen2.5-coder:7b"
    API_KEY: str = ""
    TIMEOUT_SECONDS: int = 300
    ALLOW_ORIGINS: str = "*"

    


settings = Settings()

print("Loaded API_KEY:", repr(settings.OLLAMA_URL))

