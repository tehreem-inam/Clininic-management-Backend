# app/settings.py
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings loaded from environment or `.env`.

    Keep names compatible with existing code (uppercase attributes
    like `DATABASE_URL`, `AUTO_CREATE_TABLES`) while adding a few
    explicit production-friendly fields.
    """

    # App identity / runtime
    APP_NAME: str = "Clinic Management Backend"
    APP_PORT: int = 8000
    # lowercase alias used elsewhere in code
    app_port: int = 8000

    # Database
    DATABASE_URL: Optional[str] = None

    # When true, the app will call `Base.metadata.create_all()` on startup.
    # Keep False in environments where Alembic is used.
    AUTO_CREATE_TABLES: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"

    # JWT Configuration
    JWT_SECRET_KEY: str = "your-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440   # 1 day

    # CORS Configuration (comma-separated string of origins)
    cors_origins: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    def get_cors_origins_list(self) -> List[str]:
        """Return `cors_origins` as a cleaned list of origins."""
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

