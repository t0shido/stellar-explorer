from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    SECRET_KEY: str
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str
    
    # Redis (optional - only needed if using Celery workers)
    REDIS_URL: Optional[str] = None
    
    # Celery (optional - only needed if using background workers)
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    # Stellar
    STELLAR_NETWORK: str = "testnet"
    STELLAR_HORIZON_URL: str = "https://horizon-testnet.stellar.org"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
