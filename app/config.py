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

    # MPLADS
    DEFAULT_MPLADS_BUDGET: int = 50000000  # ₹5 Crore per MP per year

    # Cloud Storage
    GCS_BUCKET: str = "pp26-501410-uploads"

    # CORS — space-separated list of allowed origins
    # e.g. "https://frontend-xyz-uc.a.run.app http://localhost:5173"
    CORS_ORIGINS: str = "https://frontend-186301339803.asia-south1.run.app https://scheduler-186301339803.asia-south1.run.app http://localhost:5173 http://localhost:3000"

    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000


def get_current_financial_year() -> str:
    """Returns Indian financial year string based on current date (April-March)."""
    from datetime import date
    today = date.today()
    if today.month >= 4:
        return f"{today.year}-{str(today.year + 1)[2:]}"
    else:
        return f"{today.year - 1}-{str(today.year)[2:]}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
