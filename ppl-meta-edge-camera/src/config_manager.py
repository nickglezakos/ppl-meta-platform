"""
Configuration Manager for Edge Camera.

Provides persistent storage for device UUID and other runtime configuration.
Stored separately from the main config.yaml to allow runtime updates.
"""

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages persistent configuration for edge camera."""
    
    # Singleton instance
    _instance: Optional['ConfigManager'] = None
    _config_path: Path
    _config_data: Dict[str, Any]
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Store runtime config in project root (persists across deploys)
        base_dir = Path(__file__).parent.parent
        self._config_path = base_dir / "runtime_config.json"
        self._config_data = self._load_config()
        self._initialized = True
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        if self._config_path.exists():
            try:
                with open(self._config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load runtime config: {e}")
                return {}
        return {}
    
    def _save_config(self):
        """Save configuration to JSON file."""
        try:
            with open(self._config_path, 'w') as f:
                json.dump(self._config_data, f, indent=2)
            logger.info(f"Saved runtime config to {self._config_path}")
        except Exception as e:
            logger.error(f"Failed to save runtime config: {e}")
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get current configuration dictionary."""
        instance = cls()
        return instance._config_data.copy()
    
    @classmethod
    def set_value(cls, key: str, value: Any):
        """Set a configuration value."""
        instance = cls()
        instance._config_data[key] = value
        instance._save_config()
    
    @classmethod
    def get_value(cls, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        instance = cls()
        return instance._config_data.get(key, default)
    
    @classmethod
    def save_config(cls, config_dict: Dict[str, Any]):
        """Save entire configuration dictionary."""
        instance = cls()
        instance._config_data = config_dict.copy()
        instance._save_config()
