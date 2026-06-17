"""Configuration management for MathAssistant.

Loads config from config.yaml, then overrides with environment variables.
Environment variables take precedence over YAML values.
"""

import os
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field


class SearchConfig(BaseModel):
    provider: str = "duckduckgo"


class PythonExecutorConfig(BaseModel):
    timeout_seconds: int = Field(default=30, gt=0, le=120)
    allowed_imports: list[str] = Field(
        default=["sympy", "numpy", "matplotlib.pyplot", "math", "json", "fractions", "decimal", "itertools", "collections", "random"]
    )


class AgentConfig(BaseModel):
    max_tool_calls: int = Field(default=20, gt=0, le=100)


class ModelConfig(BaseModel):
    provider: str = "deepseek"
    name: str = "deepseek-chat"
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)


class ApiConfig(BaseModel):
    base_url: str = "https://api.deepseek.com"
    api_key: Optional[str] = None


class OutputConfig(BaseModel):
    image_dir: str = "./images"


class Config(BaseModel):
    model: ModelConfig = ModelConfig()
    api: ApiConfig = ApiConfig()
    search: SearchConfig = SearchConfig()
    python_executor: PythonExecutorConfig = PythonExecutorConfig()
    agent: AgentConfig = AgentConfig()
    output: OutputConfig = OutputConfig()

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """Load configuration from YAML file and environment variables.

        Args:
            config_path: Path to YAML config file. If None, looks for config.yaml
                         in project root (parent of src/math_assistant).
        """
        if config_path is None:
            # Default: look for config.yaml in project root
            this_file = Path(__file__).resolve()
            project_root = this_file.parent.parent.parent
            config_path = str(project_root / "config.yaml")

        # Start with YAML
        yaml_data = {}
        if Path(config_path).exists():
            with open(config_path, "r") as f:
                yaml_data = yaml.safe_load(f) or {}

        # Merge YAML data into config dict
        config_dict = {}
        if "model" in yaml_data:
            config_dict["model"] = yaml_data["model"]
        if "api" in yaml_data:
            config_dict["api"] = yaml_data["api"]
        if "search" in yaml_data:
            config_dict["search"] = yaml_data["search"]
        if "python_executor" in yaml_data:
            config_dict["python_executor"] = yaml_data["python_executor"]
        if "agent" in yaml_data:
            config_dict["agent"] = yaml_data["agent"]
        if "output" in yaml_data:
            config_dict["output"] = yaml_data["output"]

        # Override with environment variables
        env_overrides = {
            "MATH_ASSISTANT_API_KEY": "api.api_key",
            "DEEPSEEK_API_KEY": "api.api_key",
            "OPENAI_API_KEY": "api.api_key",
            "MATH_ASSISTANT_BASE_URL": "api.base_url",
            "MATH_ASSISTANT_MODEL": "model.name",
            "MATH_ASSISTANT_TEMPERATURE": "model.temperature",
            "MATH_ASSISTANT_SEARCH_PROVIDER": "search.provider",
            "MATH_ASSISTANT_PYTHON_TIMEOUT": "python_executor.timeout_seconds",
            "MATH_ASSISTANT_MAX_TOOL_CALLS": "agent.max_tool_calls",
            "MATH_ASSISTANT_IMAGE_DIR": "output.image_dir",
        }

        def _set_nested(d: dict, key_path: str, value: str):
            keys = key_path.split(".")
            for k in keys[:-1]:
                if k not in d:
                    d[k] = {}
                d = d[k]
            # Type conversion
            target_key = keys[-1]
            existing = d.get(target_key)
            if isinstance(existing, bool) or target_key == "temperature":
                d[target_key] = float(value)
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

    def get_api_key(self) -> str:
        """Get the API key, raising a clear error if not set."""
        if self.api.api_key:
            return self.api.api_key
        raise ValueError(
            "API key not configured. Set DEEPSEEK_API_KEY, MATH_ASSISTANT_API_KEY, "
            "or OPENAI_API_KEY environment variable."
        )
