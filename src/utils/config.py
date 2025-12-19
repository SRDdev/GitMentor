"""
Docstring for src.utils.config
Updated for GitMentor branding and workspace pathing.
"""
import yaml
import os
from pathlib import Path
from typing import Any


class Config:
    _instance = None
    _config_data = None
    _defaults = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """
        Load configuration from config.yaml.

        Resolution order:
        1. CONFIG_PATH environment variable (absolute or relative)
        2. Project-root-relative config.yaml (CLI safe)
        3. Internal defaults
        """
        # Internal Defaults (safe fallback)
        self._defaults = {
            "project": {
                "name": "GitMentor",
                "version": "1.0.0",
            },
            "paths": {
                "workspace": ".gitmentor_workspace",
                "repo_root": os.getcwd(),
            },
            "llm": {
                "provider": "google",
                "default": {
                    "model": "gemini-2.0-flash",
                    "temperature": 0.1,
                    "max_tokens": 8192,
                    "top_p": 0.95,
                    "top_k": 64,
                },
            },
        }

        # Resolve config path
        env_path = os.getenv("CONFIG_PATH")

        if env_path:
            config_path = Path(env_path).expanduser().resolve()
        else:
            # Resolve config.yaml relative to project root
            # src/utils/config.py -> project root
            config_path = (
                Path(__file__)
                .resolve()
                .parents[2]   # adjust if directory depth changes
                / "config.yaml"
            )

        # Load config
        if not config_path.exists():
            self._config_data = self._defaults
        else:
            with open(config_path, "r") as f:
                self._config_data = yaml.safe_load(f) or {}

    def get(self, path: str, default: Any = None) -> Any:
        """
        Access config using dot notation.

        Example:
            cfg.get("llm.provider")
            cfg.get("llm.default.model")
        """
        keys = path.split(".")

        # First try loaded YAML
        value = self._config_data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
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


# Global singleton instance
cfg = Config()
