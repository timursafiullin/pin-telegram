from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LLM_API_URL: str
    LLM_MODEL: str
    POSTGRES_URL: str
    DATABASE_ECHO: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
