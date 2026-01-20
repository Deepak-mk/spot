from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # LLM
    groq_api_key: str
    llm_model: str = "llama-3.1-8b-instant"
    llm_temperature: float = 0.1
    
    # Database
    database_url: str = "sqlite:///data/analytics.db"
    
    # App
    app_env: str = "development"
    log_level: str = "INFO"
    debug: bool = False
    
    # Security
    secret_key: str = "dev-secret-key"
    session_timeout_minutes: int = 60
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 60
    
    # Monitoring
    sentry_dsn: Optional[str] = None
    datadog_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra env vars

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
