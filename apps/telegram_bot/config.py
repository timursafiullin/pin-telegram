from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TELEGRAM_BOT_API_KEY: str
    POSTGRES_LINK: str
    
    class Config:
        env_file = ".env"
        
settings = Settings()