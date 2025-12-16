"""
Docstring for src.utils.config
Updated for GitMentor branding and workspace pathing.
"""
import yaml
import os
from typing import Dict, Any

class Config:
    _instance = None
    _config_data = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_path = os.getenv("CONFIG_PATH", "config.yaml")
        
        # Internal Defaults (Fallback if yaml is missing or incomplete)
        self._defaults = {
            "project": {
                "name": "GitMentor",
                "version": "1.0.0"
            },
            "paths": {
                "workspace": ".gitmentor_workspace",
                "repo_root": os.getcwd()
            }
        }

        if not os.path.exists(config_path):
            # If no config.yaml exists, we use the defaults
            self._config_data = self._defaults
        else:
            with open(config_path, "r") as f:
                self._config_data = yaml.safe_load(f) or {}

    def get(self, path: str, default: Any = None) -> Any:
        """
        Access config using dot notation, e.g., config.get('project.name')
        """
        keys = path.split(".")
        
        # First try to get from the loaded yaml data
        value = self._config_data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                # If not found in yaml, try to get from internal defaults
                return self._get_default(path, default)
        return value

    def _get_default(self, path: str, final_default: Any) -> Any:
        keys = path.split(".")
        value = self._defaults
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return final_default
        return value

# Global instance for easy import
cfg = Config()