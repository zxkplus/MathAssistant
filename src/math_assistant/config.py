"""Configuration management for MathAssistant.

Layered loading (later sources override earlier ones):
  1. config.yaml          — shared, committed settings
  2. config.local.yaml    — gitignored, for secrets (API keys)
  3. environment variables — highest precedence (MATH_ASSISTANT_*)

LLM Profile Pattern — each "role" (main, vision, future sub-agents)
  gets its own self-contained LLMProfile with independent model, api_key,
  and base_url. No cross-role fallbacks.  Adding a new role is just adding
  a new top-level section in config.yaml.

  Example for a future tagging agent:
    # config.yaml
    tagging:
      model: qwen-plus
      base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # config.local.yaml
    tagging:
      api_key: "sk-qwen-xxx"
"""

import os
from pathlib import Path
from typing import Literal, Optional

import yaml
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


# ── LLM Profile — unified model + auth + endpoint per role ──────────────

class LLMProfile(BaseModel):
    """Self-contained LLM connection config for one role.

    Each role (main agent, vision, future sub-agents) owns one profile.
    Profiles are independent: no API key fallback across roles.
    """

    model: str
    api_key: Optional[str] = None
    base_url: str
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)

    def get_api_key(self, role_name: str = "") -> str:
        """Resolve the API key for this profile, raising if not set.

        Checks in order: explicit field → environment variables.
        No cross-profile fallback — each role stands alone.
        """
        if self.api_key:
            return self.api_key

        # Provider-agnostic env vars (highest to lowest priority)
        env_candidates = [
            "MATH_ASSISTANT_API_KEY",
            "DEEPSEEK_API_KEY",
            "OPENAI_API_KEY",
            "KIMI_API_KEY",
            "MOONSHOT_API_KEY",
        ]
        for var in env_candidates:
            val = os.environ.get(var)
            if val:
                return val

        label = f" ({role_name})" if role_name else ""
        raise ValueError(
            f"API key not configured for LLM profile{label}.\n"
            f"Set it in config.local.yaml under the profile section:\n"
            f"  {role_name or '<role>'}:\n"
            f"    api_key: \"sk-xxx\"\n"
            f"Or via environment variable: MATH_ASSISTANT_API_KEY / DEEPSEEK_API_KEY / etc."
        )

    def create_chat_openai(self, role_name: str = "") -> ChatOpenAI:
        """Create a ChatOpenAI instance from this profile.

        Args:
            role_name: Optional label for error messages (e.g. "main", "vision").

        Returns:
            Configured ChatOpenAI LLM.
        """
        return ChatOpenAI(
            model=self.model,
            api_key=self.get_api_key(role_name),
            base_url=self.base_url,
            temperature=self.temperature,
        )


# ── Other config sections ───────────────────────────────────────────────

class SearchConfig(BaseModel):
    provider: str = "duckduckgo"


class PythonExecutorConfig(BaseModel):
    timeout_seconds: int = Field(default=30, gt=0, le=120)
    allowed_imports: list[str] = Field(
        default=[
            "sympy", "numpy", "matplotlib.pyplot", "math", "json",
            "fractions", "decimal", "itertools", "collections", "random",
        ]
    )


class AgentConfig(BaseModel):
    max_tool_calls: int = Field(default=20, gt=0, le=100)


class OutputConfig(BaseModel):
    image_dir: str = "./images"
    save_mode: Literal["session", "turn", "manual"] = "session"
    save_dir: str = "./sessions"
    html_export: bool = True
    embed_images: bool = True


# ── Top-level Config ────────────────────────────────────────────────────

class Config(BaseModel):
    """Application configuration.

    LLM roles are top-level LLMProfile instances.  The reserved role names
    are ``main`` (primary agent) and ``vision`` (image-to-text OCR).
    Additional roles can be added by the user — they are parsed as extra
    fields via the ``extra`` Pydantic config.
    """

    main: LLMProfile = LLMProfile(
        model="deepseek-chat",
        base_url="https://api.deepseek.com",
    )
    vision: LLMProfile = LLMProfile(
        model="gpt-4o",
        base_url="https://api.openai.com/v1",
    )
    search: SearchConfig = SearchConfig()
    python_executor: PythonExecutorConfig = PythonExecutorConfig()
    agent: AgentConfig = AgentConfig()
    output: OutputConfig = OutputConfig()

    class Config:
        # Allow extra fields so users can add new LLM roles (e.g. "tagging")
        # without modifying the Config model.
        extra = "allow"

    # ── Legacy compatibility ───────────────────────────────────────────

    def get_api_key(self) -> str:
        """Legacy method — returns the main profile's API key.

        Kept for backward compatibility with any code that still calls
        ``config.get_api_key()``. Prefer ``config.main.get_api_key("main")``.
        """
        return self.main.get_api_key("main")

    # ── Loading ────────────────────────────────────────────────────────

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """Load configuration from YAML file, local overrides, and env vars.

        Args:
            config_path: Path to YAML config file. If None, looks for
                         config.yaml in project root.
        """
        if config_path is None:
            this_file = Path(__file__).resolve()
            project_root = this_file.parent.parent.parent
            config_path = str(project_root / "config.yaml")

        config_path_obj = Path(config_path).resolve()
        config_dir = config_path_obj.parent

        # Layer 1: main config file (config.yaml)
        yaml_data = {}
        if config_path_obj.exists():
            with open(config_path_obj, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f) or {}

        # Layer 2: local override file (config.local.yaml)
        local_path = config_dir / "config.local.yaml"
        local_data = {}
        if local_path.exists():
            with open(local_path, "r", encoding="utf-8") as f:
                local_data = yaml.safe_load(f) or {}

        # Deep-merge local into main
        config_data = _deep_merge(yaml_data, local_data)

        # ── Legacy compatibility: map old model/api/vision sections ────
        # If the user still has the old format, migrate on-the-fly.
        config_data = _migrate_legacy_config(config_data)

        # ── Extract known sections ──────────────────────────────────────
        config_dict: dict = {}
        for section in ("main", "vision", "search", "python_executor", "agent", "output"):
            if section in config_data:
                config_dict[section] = config_data[section]

        # Apply environment variable overrides
        _apply_env_overrides(config_dict)

        return cls(**config_dict)


# ── Helpers ──────────────────────────────────────────────────────────────

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base dict."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _migrate_legacy_config(data: dict) -> dict:
    """On-the-fly migration from old model/api/vision format to unified LLMProfile.

    Old format:
        model: {provider, name, temperature}
        api: {base_url, api_key}
        vision: {provider, model, api_key, base_url}

    New format:
        main: {model, base_url, temperature, api_key}
        vision: {model, base_url, api_key}
    """
    # Migrate old model+api → main
    if "main" not in data:
        old_model = data.pop("model", {})
        old_api = data.pop("api", {})
        if old_model or old_api:
            data["main"] = {
                "model": old_model.get("name", "deepseek-chat"),
                "base_url": old_api.get("base_url", "https://api.deepseek.com"),
                "temperature": old_model.get("temperature", 0.0),
            }
            if old_api.get("api_key"):
                data["main"]["api_key"] = old_api["api_key"]

    # Migrate old vision → new vision (LLMProfile format)
    if "vision" in data and "provider" in data["vision"]:
        old_vision = data["vision"]
        # Old VisionConfig has: provider, model, api_key, base_url
        # New LLMProfile has: model, api_key, base_url (no provider)
        migrated = {
            "model": old_vision.get("model", "gpt-4o"),
            "base_url": old_vision.get("base_url", "https://api.openai.com/v1"),
        }
        if old_vision.get("api_key"):
            migrated["api_key"] = old_vision["api_key"]
        data["vision"] = migrated

    return data


def _apply_env_overrides(config_dict: dict) -> None:
    """Apply environment variable overrides to config_dict (mutated in place)."""
    env_overrides = {
        # Main LLM profile
        "MATH_ASSISTANT_API_KEY": "main.api_key",
        "DEEPSEEK_API_KEY": "main.api_key",
        "OPENAI_API_KEY": "main.api_key",
        "MATH_ASSISTANT_BASE_URL": "main.base_url",
        "MATH_ASSISTANT_MODEL": "main.model",
        "MATH_ASSISTANT_TEMPERATURE": "main.temperature",
        # Vision LLM profile
        "KIMI_API_KEY": "vision.api_key",
        "MOONSHOT_API_KEY": "vision.api_key",
        "MATH_ASSISTANT_VISION_MODEL": "vision.model",
        "MATH_ASSISTANT_VISION_API_KEY": "vision.api_key",
        "MATH_ASSISTANT_VISION_BASE_URL": "vision.base_url",
        # Other sections
        "MATH_ASSISTANT_SEARCH_PROVIDER": "search.provider",
        "MATH_ASSISTANT_PYTHON_TIMEOUT": "python_executor.timeout_seconds",
        "MATH_ASSISTANT_MAX_TOOL_CALLS": "agent.max_tool_calls",
        "MATH_ASSISTANT_IMAGE_DIR": "output.image_dir",
        "MATH_ASSISTANT_SAVE_MODE": "output.save_mode",
        "MATH_ASSISTANT_SAVE_DIR": "output.save_dir",
        "MATH_ASSISTANT_HTML_EXPORT": "output.html_export",
        "MATH_ASSISTANT_EMBED_IMAGES": "output.embed_images",
    }

    for env_var, config_path_str in env_overrides.items():
        env_value = os.environ.get(env_var)
        if env_value:
            _set_nested(config_dict, config_path_str, env_value)


def _set_nested(d: dict, key_path: str, value: str) -> None:
    """Set a nested dict value by dot-separated path, with type coercion."""
    keys = key_path.split(".")
    for k in keys[:-1]:
        if k not in d:
            d[k] = {}
        d = d[k]
    target_key = keys[-1]
    existing = d.get(target_key)

    if isinstance(existing, bool):
        d[target_key] = value.lower() in ("true", "1", "yes")
    elif isinstance(existing, float):
        d[target_key] = float(value)
    elif isinstance(existing, int):
        d[target_key] = int(value)
    else:
        d[target_key] = value
