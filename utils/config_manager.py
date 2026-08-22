"""
Configuration manager for EasySpeak.
Handles loading/saving JSON config and .env API keys.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """Manages application configuration from JSON and environment variables."""

    def __init__(self, config_path: Optional[str] = None, env_path: Optional[str] = None):
        """
        Initialize the config manager.

        Args:
            config_path: Path to config.json file
            env_path: Path to .env file
        """
        self.config_path = Path(config_path) if config_path else Path(__file__).parent.parent / "config.json"
        self.env_path = Path(env_path) if env_path else Path(__file__).parent.parent / ".env"

        self._config: Dict[str, Any] = {}
        self._load_config()
        self._load_env()

    def _load_config(self) -> None:
        """Load configuration from JSON file."""
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        else:
            self._config = self._get_default_config()
            self.save_config()

    def _load_env(self) -> None:
        """Load environment variables from .env file."""
        if self.env_path.exists():
            with open(self.env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "hotkey": {
                "key": "Key.caps_lock",
                "double_tap_threshold_ms": 300
            },
            "transcription": {
                "mode": "local",
                "local_model": "base",
                "api_provider": "groq"
            },
            "llm": {
                "enabled": True,
                "provider": "groq",
                "model": "llama3-8b-8192",
                "prompt": "You are a dictation assistant. Clean up this transcript: - Remove filler words (um, uh, like, you know) - Add proper punctuation - Fix capitalization for proper nouns - Keep the natural flow of speech - Don't change the meaning or add words"
            },
            "clipboard": {
                "restore_previous": True,
                "restore_delay_seconds": 2.0
            },
            "audio": {
                "input_device": None,
                "gain": 20.0
            },
            "auto_stop_minutes": 5,
            "launch_at_login": False
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key: Dot-separated key path (e.g., "hotkey.key")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.

        Args:
            key: Dot-separated key path (e.g., "hotkey.key")
            value: Value to set
        """
        keys = key.split(".")
        target = self._config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

    def save_config(self) -> None:
        """Save configuration to JSON file."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2)

    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a provider from environment variables.

        Args:
            provider: Provider name (groq, openai, anthropic)

        Returns:
            API key or None if not found
        """
        env_var = f"{provider.upper()}_API_KEY"
        return os.environ.get(env_var)

    @property
    def config(self) -> Dict[str, Any]:
        """Get the full configuration dictionary."""
        return self._config.copy()


# Global config instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Get the global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager