"""Configuration system for Tomo."""

import os
from pathlib import Path
from typing import Any

import yaml

from tomo.exceptions import ConfigError, ValidationError

DEFAULT_CONFIG = {
    "pet": {
        "name": "Tomo",
        "avatar": "🦊",
        "species": "fox",
        "personality": {
            "description": "A curious fox companion.",
            "traits": {
                "curiosity": 0.8,
                "clinginess": 0.6,
                "wisdom": 0.4,
            },
            "style": "encourager",
            "speech": {
                "style": "casual, short (under 20 chars), uses emoji",
                "tone": "warm, healing, slightly playful",
                "forbidden": [
                    "no lecturing",
                    "no criticizing work style",
                    "no asking for sensitive info",
                ],
            },
            "preferences": {
                "favorite_topics": [],
                "disliked_topics": [],
            },
            "evolution_path": "knowledge",
        },
        "llm": {
            "provider": "ollama",
            "model": "qwen2.5:7b",
            "api_key": None,
            "base_url": None,
            "system_prompt": None,
            "call_budget": {
                "daily_limit": 20,
                "important_only": True,
            },
        },
    }
}


class Config:
    """Tomo configuration wrapper."""

    def __init__(self, data: dict[str, Any]):
        self._data = data

    @property
    def pet_name(self) -> str:
        return self._data.get("pet", {}).get("name", "Tomo")

    @property
    def pet_avatar(self) -> str:
        return self._data.get("pet", {}).get("avatar", "🦊")

    @property
    def species(self) -> str:
        return self._data.get("pet", {}).get("species", "fox")

    @property
    def personality(self) -> dict[str, Any]:
        return self._data.get("pet", {}).get("personality", {})

    @property
    def chat_style(self) -> str:
        return self._data.get("pet", {}).get("personality", {}).get("style", "encourager")

    @property
    def llm_provider(self) -> str:
        return self._data.get("pet", {}).get("llm", {}).get("provider", "ollama")

    @property
    def llm_model(self) -> str:
        return self._data.get("pet", {}).get("llm", {}).get("model", "qwen2.5:7b")

    @property
    def llm_api_key(self) -> str | None:
        raw = self._data.get("pet", {}).get("llm", {}).get("api_key")
        if raw and raw.startswith("env:"):
            return os.environ.get(raw[4:].strip())
        return raw

    @property
    def llm_base_url(self) -> str | None:
        return self._data.get("pet", {}).get("llm", {}).get("base_url")

    @property
    def daily_llm_limit(self) -> int:
        return (
            self._data.get("pet", {}).get("llm", {}).get("call_budget", {}).get("daily_limit", 20)
        )

    @property
    def llm_important_only(self) -> bool:
        return (
            self._data.get("pet", {})
            .get("llm", {})
            .get("call_budget", {})
            .get("important_only", True)
        )

    def to_yaml(self) -> str:
        return yaml.dump(self._data, default_flow_style=False, allow_unicode=True)


def load_config(path: str | Path | None = None) -> Config:
    """Load configuration from YAML file."""
    path = Path.home() / ".tomo" / "config.yaml" if path is None else Path(path)

    if not path.exists():
        return Config(DEFAULT_CONFIG.copy())

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in config file: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Cannot read config file: {exc}") from exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigError(
            f"Config file must contain a YAML mapping (got {type(data).__name__})",
            details={"path": str(path)},
        )

    merged = merge_dicts(DEFAULT_CONFIG, data)
    validate_config(merged)
    return Config(merged)


def merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


VALID_PROVIDERS = {"ollama", "anthropic", "openai", "siliconflow", "deepseek", "minimax"}
VALID_TRAITS = {"curiosity", "clinginess", "wisdom", "playfulness", "bravery"}


def validate_config(data: dict[str, Any]) -> None:
    """Validate configuration structure and values.

    Raises:
        ValidationError: If config is invalid.
    """
    pet = data.get("pet", {})

    # Validate pet name
    name = pet.get("name", "")
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("pet.name must be a non-empty string")

    # Validate avatar
    avatar = pet.get("avatar", "")
    if not isinstance(avatar, str):
        raise ValidationError("pet.avatar must be a string")

    # Validate traits
    traits = pet.get("personality", {}).get("traits", {})
    for trait, value in traits.items():
        if not isinstance(value, (int, float)):
            raise ValidationError(
                f"Trait '{trait}' must be a number",
                details={"trait": trait, "value": value},
            )
        if not 0.0 <= float(value) <= 1.0:
            raise ValidationError(
                f"Trait '{trait}' must be between 0.0 and 1.0",
                details={"trait": trait, "value": value},
            )

    # Validate LLM provider
    provider = pet.get("llm", {}).get("provider", "ollama")
    if provider not in VALID_PROVIDERS:
        raise ValidationError(
            f"Unknown LLM provider: '{provider}'",
            details={"valid_providers": sorted(VALID_PROVIDERS)},
        )

    # Validate call budget
    budget = pet.get("llm", {}).get("call_budget", {})
    daily_limit = budget.get("daily_limit", 20)
    if not isinstance(daily_limit, int) or daily_limit < 0:
        raise ValidationError(
            "llm.call_budget.daily_limit must be non-negative (0 = unlimited)"
        )


def ensure_default_config() -> Path:
    """Ensure default config file exists at ~/.tomo/config.yaml."""
    config_dir = Path.home() / ".tomo"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"
    if not config_path.exists():
        config = Config(DEFAULT_CONFIG.copy())
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config.to_yaml())
    return config_path
