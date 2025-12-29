"""
Configuration management for Agentic Analytics Platform.
Centralized settings with environment variable support.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class LLMConfig:
    """LLM-related configuration."""
    model_name: str = "gpt-3.5-turbo"
    max_tokens_per_request: int = 4096
    max_completion_tokens: int = 1024
    temperature: float = 0.1
    token_budget_per_query: int = 8000
    cost_per_1k_prompt_tokens: float = 0.0015
    cost_per_1k_completion_tokens: float = 0.002


@dataclass
class AgentConfig:
    """Agent runtime configuration."""
    max_loops: int = 10
    max_retries: int = 3
    timeout_seconds: int = 60
    allowed_tools: List[str] = field(default_factory=lambda: [
        "sql_query", "metadata_lookup", "semantic_search"
    ])
    blocked_query_patterns: List[str] = field(default_factory=lambda: [
        "DROP", "DELETE", "TRUNCATE", "ALTER"
    ])


@dataclass 
class ObservabilityConfig:
    """Observability and logging configuration."""
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"
    trace_output_dir: str = "./traces"
    enable_cost_tracking: bool = True
    enable_latency_tracking: bool = True
    cost_warning_threshold: float = 0.80  # 80% of budget
    cost_error_threshold: float = 1.00    # 100% of budget


@dataclass
class DataConfig:
    """Data layer configuration."""
    semantic_data_dir: str = "./src/data/semantic"
    metadata_file: str = "metadata.json"
    vector_store_path: str = "./data/vector_store"
    embedding_model: str = "all-MiniLM-L6-v2"


@dataclass
class ControlPlaneConfig:
    """Control plane configuration."""
    kill_switch_enabled: bool = False
    kill_switch_reason: Optional[str] = None
    policy_file: Optional[str] = None
    enable_permissions: bool = True
    default_permission_level: str = "read"


@dataclass
class Settings:
    """
    Master settings container for the entire platform.
    Loads from environment variables with sensible defaults.
    """
    # Sub-configurations
    llm: LLMConfig = field(default_factory=LLMConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    data: DataConfig = field(default_factory=DataConfig)
    control_plane: ControlPlaneConfig = field(default_factory=ControlPlaneConfig)
    
    # Global settings
    environment: str = "development"
    debug: bool = False
    app_name: str = "agentic-analytics-platform"
    version: str = "0.1.0"
    
    def __post_init__(self):
        """Load overrides from environment variables."""
        self._load_from_env()
        self._ensure_directories()
    
    def _load_from_env(self):
        """Override settings from environment variables."""
        # Environment
        self.environment = os.getenv("APP_ENV", self.environment)
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # LLM
        self.llm.model_name = os.getenv("LLM_MODEL", self.llm.model_name)
        self.llm.max_tokens_per_request = int(os.getenv(
            "LLM_MAX_TOKENS", str(self.llm.max_tokens_per_request)
        ))
        
        # Observability
        self.observability.log_level = os.getenv(
            "LOG_LEVEL", self.observability.log_level
        )
        self.observability.trace_output_dir = os.getenv(
            "TRACE_OUTPUT_DIR", self.observability.trace_output_dir
        )
        
        # Control Plane
        self.control_plane.kill_switch_enabled = os.getenv(
            "KILL_SWITCH", "false"
        ).lower() == "true"
        
        # Data
        self.data.semantic_data_dir = os.getenv(
            "SEMANTIC_DATA_DIR", self.data.semantic_data_dir
        )
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        Path(self.observability.trace_output_dir).mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> dict:
        """Export settings as dictionary for logging."""
        return {
            "environment": self.environment,
            "debug": self.debug,
            "app_name": self.app_name,
            "version": self.version,
            "llm": {
                "model_name": self.llm.model_name,
                "max_tokens_per_request": self.llm.max_tokens_per_request,
            },
            "control_plane": {
                "kill_switch_enabled": self.control_plane.kill_switch_enabled,
            },
            "observability": {
                "log_level": self.observability.log_level,
            }
        }


# Global settings instance (singleton pattern)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Force reload settings from environment."""
    global _settings
    _settings = Settings()
    return _settings
