from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    DATABASE_URL: str = "postgresql://stellar_user:stellar_password@postgres:5432/stellar_explorer"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    
    # Stellar Network
    STELLAR_NETWORK: str = "testnet"
    STELLAR_HORIZON_URL: str = "https://horizon-testnet.stellar.org"
    
    # Rule Engine Configuration
    RULE_ENGINE_ENABLED: bool = True
    RULE_ENGINE_DRY_RUN: bool = False
    RULE_ENGINE_INTERVAL_MINUTES: int = 5
    
    # Rule 1: Large Transfer
    RULE_LARGE_TRANSFER_ENABLED: bool = True
    RULE_LARGE_TRANSFER_THRESHOLD: float = 10000.0
    RULE_LARGE_TRANSFER_SEVERITY: str = "medium"
    
    # Rule 2: New Counterparty
    RULE_NEW_COUNTERPARTY_ENABLED: bool = True
    RULE_NEW_COUNTERPARTY_THRESHOLD: float = 5000.0
    RULE_NEW_COUNTERPARTY_SEVERITY: str = "medium"
    
    # Rule 3: Dormant Account Reactivation
    RULE_DORMANT_REACTIVATION_ENABLED: bool = True
    RULE_DORMANT_DAYS_THRESHOLD: int = 30
    RULE_DORMANT_AMOUNT_THRESHOLD: float = 1000.0
    RULE_DORMANT_REACTIVATION_SEVERITY: str = "high"
    
    # Rule 4: Rapid Outflow Burst
    RULE_RAPID_OUTFLOW_ENABLED: bool = True
    RULE_RAPID_OUTFLOW_TX_COUNT: int = 10
    RULE_RAPID_OUTFLOW_MINUTES: int = 60
    RULE_RAPID_OUTFLOW_SEVERITY: str = "high"
    
    # Rule 5: Asset Concentration
    RULE_ASSET_CONCENTRATION_ENABLED: bool = True
    RULE_ASSET_CONCENTRATION_PERCENT: float = 80.0
    RULE_ASSET_CONCENTRATION_SEVERITY: str = "low"
    
    # Alert Deduplication
    ALERT_DEDUP_WINDOW_HOURS: int = 24
    
    class Config:
        env_file = ".env"


settings = Settings()
