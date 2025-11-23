from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Saving Advisor System"
    ENVIRONMENT: str = "development"  # development, production
    DEBUG: bool = True
    SERVER_PORT: int = 50051  # gRPC server port (standard gRPC port)
    GATEWAY_PORT: int = 8080  # REST gateway port (HTTP port)
    
    # Security
    SECRET_KEY: str = "change-this-to-a-random-secret-key-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    
    # Database Configuration
    DB_DRIVER: str = "sqlite"  # sqlite or postgres
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "saving_advisor"
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"
    
    # Feature Flags
    ENABLE_ANALYTICS: bool = True
    ENABLE_ANALYTICS_SYNC: bool = True
    INITIAL_SYNC_ON_STARTUP: bool = False
    SYNC_BATCH_SIZE: int = 100
    CACHE_TTL_HOURS: int = 2
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Monitoring Configuration
    ENABLE_MONITORING: bool = True
    ENABLE_SSE_MONITORING: bool = True
    MONITORING_LITE_MODE: bool = False
    
    # Flower Monitoring
    FLOWER_USER: str = "admin"
    FLOWER_PASSWORD: str = "admin"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()