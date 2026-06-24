"""Server configuration for MathAssistant backend.

Follows the same layered-loading pattern as the main Config:
  1. server.yaml          — shared, committed settings
  2. server.local.yaml    — gitignored, for secrets (JWT secret key)
  3. environment variables — highest precedence (MATH_ASSISTANT_SERVER_*)
"""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    url: str = "sqlite:///./math_assistant.db"


class AuthConfig(BaseModel):
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    database: DatabaseConfig = DatabaseConfig()
    auth: AuthConfig = AuthConfig()
    cors_origins: list[str] = ["*"]
    log_level: str = "info"

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "ServerConfig":
        """Load server configuration from YAML and environment variables.

        Args:
            config_path: Path to YAML config file. If None, looks for
                         server.yaml in the project root.
        """
        if config_path is None:
            this_file = Path(__file__).resolve()
            project_root = this_file.parent.parent.parent.parent
            config_path = str(project_root / "server.yaml")

        config_path_obj = Path(config_path).resolve()
        config_dir = config_path_obj.parent
        config_name = config_path_obj.stem

        # Layer 1: main config file
        yaml_data = {}
        if config_path_obj.exists():
            with open(config_path_obj, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f) or {}

        # Layer 2: local override file (gitignored, for secrets)
        local_path = config_dir / f"{config_name}.local.yaml"
        local_data = {}
        if local_path.exists():
            with open(local_path, "r", encoding="utf-8") as f:
                local_data = yaml.safe_load(f) or {}

        def _deep_merge(base: dict, override: dict) -> dict:
            for key, value in override.items():
                if (
                    key in base
                    and isinstance(base[key], dict)
                    and isinstance(value, dict)
                ):
                    _deep_merge(base[key], value)
                else:
                    base[key] = value
            return base

        config_data = _deep_merge(yaml_data, local_data)

        # Extract sections
        config_dict = {}
        for section in ("database", "auth", "cors_origins"):
            if section in config_data:
                config_dict[section] = config_data[section]

        # Host and port at top level
        for key in ("host", "port", "log_level"):
            if key in config_data:
                config_dict[key] = config_data[key]

        # Environment variable overrides
        env_overrides = {
            "MATH_ASSISTANT_SERVER_HOST": "host",
            "MATH_ASSISTANT_SERVER_PORT": "port",
            "MATH_ASSISTANT_DB_URL": "database.url",
            "MATH_ASSISTANT_SECRET_KEY": "auth.secret_key",
            "MATH_ASSISTANT_TOKEN_EXPIRE_MINUTES": "auth.access_token_expire_minutes",
        }

        def _set_nested(d: dict, key_path: str, value: str):
            keys = key_path.split(".")
            for k in keys[:-1]:
                if k not in d:
                    d[k] = {}
                d = d[k]
            target_key = keys[-1]
            existing = d.get(target_key)
            if isinstance(existing, bool):
                d[target_key] = value.lower() in ("true", "1", "yes")
            elif isinstance(existing, int):
                d[target_key] = int(value)
            elif isinstance(existing, float):
                d[target_key] = float(value)
            else:
                d[target_key] = value

        for env_var, config_path_str in env_overrides.items():
            env_value = os.environ.get(env_var)
            if env_value:
                _set_nested(config_dict, config_path_str, env_value)

        return cls(**config_dict)
