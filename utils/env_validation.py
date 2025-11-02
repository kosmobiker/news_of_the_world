from pydantic import BaseSettings, Field, ValidationError


class Settings(BaseSettings):
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    TG_API_KEY: str = Field(..., env="TG_API_KEY")
    CHAT_ID: str = Field(..., env="CHAT_ID")
    XAI_API_KEY: str = Field(..., env="XAI_API_KEY")

    class Config:
        env_file = ".env"


try:
    settings = Settings()
except ValidationError as e:
    print("Environment validation error:", e)
    raise
