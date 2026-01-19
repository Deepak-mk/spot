import yaml
import os
from typing import Optional, Dict
from threading import Lock

class PromptManager:
    """
    Manages loading and saving of prompts from configuration.
    Allows for dynamic prompt engineering via the UI.
    """
    def __init__(self, config_path: str = "config/prompts.yaml"):
        self.config_path = config_path
        self._prompts: Dict[str, str] = {}
        self._lock = Lock()
        self._load()

    def get_system_prompt(self) -> str:
        """Get the current analytics system prompt."""
        with self._lock:
            return self._prompts.get("analytics_system_prompt", "System prompt not loaded.")

    def update_system_prompt(self, new_prompt: str) -> None:
        """Update and save the system prompt."""
        with self._lock:
            self._prompts["analytics_system_prompt"] = new_prompt
            self._save()
    
    def _load(self):
        """Load prompts from YAML."""
        if not os.path.exists(self.config_path):
            # Fallback if file missing
            self._prompts["analytics_system_prompt"] = "You are an AI assistant."
            return

        try:
            with open(self.config_path, "r") as f:
                self._prompts = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading prompts: {e}")

    def _save(self):
        """Save prompts to YAML."""
        try:
            with open(self.config_path, "w") as f:
                yaml.dump(self._prompts, f, default_flow_style=False)
        except Exception as e:
            print(f"Error saving prompts: {e}")

# Singleton
_prompt_manager: Optional[PromptManager] = None

def get_prompt_manager() -> PromptManager:
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
