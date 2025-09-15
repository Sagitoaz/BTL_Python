from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    
    OLLAMA_URL: str = "http://127.0.0.1:11434"
    
    MODEL: str = "qwen2.5-coder:7b"
    API_KEY: str = "5conmeo"
    TIMEOUT_SECONDS: int = 120
    ALLOW_ORIGINS: str = "*"
    HEADERS_MIDDLEWARE: str = "X-Request-ID"
    REQUEST_ID : str = "request_id"
    POSTPROCESS_ENABLED: bool = True # hậu thêm vào
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()




settings = Settings()