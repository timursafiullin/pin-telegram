from pydantic_settings import BaseSettings
from datetime import datetime

class Settings(BaseSettings):
    TELEGRAM_BOT_API_KEY: str
    
    DEFAULT_TIMEZONE: str = "Europe/Moscow"
    
    LOG_VERBOSE_BOT_PAYLOAD: bool = True
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = f"logs/api-{datetime.now().strftime('%d-%m-%Y-%H-%M-%S')}.log"
    
    class Config:
        env_file = ".env"
        extra = "ignore"
        
settings = Settings()
