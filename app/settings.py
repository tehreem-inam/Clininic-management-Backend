# app/settings.py
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import Optional
import os

load_dotenv()

class Settings(BaseSettings):
    APP_NAME: str = "Clinic Management Backend"
    DATABASE_URL: str = os.getenv("DATABASE_URL")
   # JWT Configuration
    JWT_SECRET_KEY: str = "your-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440   # 1 day
   # CORS Configuration
    cors_origins: Optional[str] = None
    
    
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Allow extra fields for forward compatibility
        extra = "ignore"
settings = Settings()

