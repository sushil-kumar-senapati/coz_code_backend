from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "peoples_priorities"

    # JWT
    JWT_SECRET: str = "pp-hackathon-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

    # File uploads
    UPLOAD_DIR: str = "./uploads"

    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000


@lru_cache()
def get_settings() -> Settings:
    return Settings()
