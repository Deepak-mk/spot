from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # LLM
    groq_api_key: str
    # LLM
    groq_api_key: str
    llm_model: str = "llama-3.1-8b-instant"
    llm_temperature: float = 0.1
    embedding_model: str = "all-MiniLM-L6-v2"
    
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # Data Paths
    semantic_data_dir: str = "data/semantic"
    vector_store_path: str = "data/vector_store"
    
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
    
    # Observability
    trace_output_dir: str = "traces"
    cost_warning_threshold: float = 0.5
    cost_error_threshold: float = 1.0
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Monitoring
    sentry_dsn: Optional[str] = None
    datadog_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra env vars

@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Automatically loads from Streamlit secrets if available.
    """
    import os
    import streamlit as st
    
    # Try to load from Streamlit secrets if running in Streamlit
    try:
        if st.secrets:
            # Inject streamlit secrets into os.environ for Pydantic to pick up
            # This is safer than manually constructing Settings because Pydantic handles validation
            for key, value in st.secrets.items():
                if isinstance(value, str):
                    os.environ[key.upper()] = value
                elif isinstance(value, dict):
                    # Handle nested secrets (e.g. [connections.snowflake])
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, str):
                            os.environ[f"{key.upper()}_{subkey.upper()}"] = subvalue
    except (FileNotFoundError, ImportError, AttributeError):
        # Not running in Streamlit or no secrets found
        pass
        
    return Settings()
