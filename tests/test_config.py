"""Tests for configuration system."""

import os
from pathlib import Path

import pytest
import yaml

from tomo.config import Config, ensure_default_config, load_config, merge_dicts, validate_config
from tomo.exceptions import ConfigError, ValidationError


class TestConfig:
    def test_pet_name(self):
        config = Config({"pet": {"name": "Test"}})
        assert config.pet_name == "Test"

    def test_default_pet_name(self):
        config = Config({})
        assert config.pet_name == "Tomo"

    def test_llm_api_key_plain(self):
        config = Config({"pet": {"llm": {"api_key": "secret123"}}})
        assert config.llm_api_key == "secret123"

    def test_llm_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("MY_TOKEN", "from_env")
        config = Config({"pet": {"llm": {"api_key": "env:MY_TOKEN"}}})
        assert config.llm_api_key == "from_env"

    def test_llm_api_key_env_missing(self):
        config = Config({"pet": {"llm": {"api_key": "env:NONEXISTENT_VAR"}}})
        assert config.llm_api_key is None

    def test_daily_llm_limit(self):
        config = Config({"pet": {"llm": {"call_budget": {"daily_limit": 50}}}})
        assert config.daily_llm_limit == 50


class TestLoadConfig:
    def test_load_existing_file(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("pet:\n  name: Custom\n")
        config = load_config(config_path)
        assert config.pet_name == "Custom"

    def test_load_nonexistent_returns_default(self, tmp_path):
        config = load_config(tmp_path / "nonexistent.yaml")
        assert config.pet_name == "Tomo"

    def test_load_invalid_yaml_raises(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("{ invalid yaml")
        with pytest.raises(ConfigError):
            load_config(config_path)

    def test_load_non_dict_raises(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("- item1\n- item2\n")
        with pytest.raises(ConfigError):
            load_config(config_path)


class TestMergeDicts:
    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = merge_dicts(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"pet": {"name": "Tomo", "traits": {"a": 1}}}
        override = {"pet": {"traits": {"b": 2}}}
        result = merge_dicts(base, override)
        assert result["pet"]["name"] == "Tomo"
        assert result["pet"]["traits"] == {"a": 1, "b": 2}

    def test_does_not_mutate_base(self):
        base = {"a": 1}
        override = {"b": 2}
        merge_dicts(base, override)
        assert base == {"a": 1}


class TestValidateConfig:
    def test_valid_config(self):
        data = {"pet": {"name": "Tomo", "llm": {"provider": "ollama"}}}
        validate_config(data)  # Should not raise

    def test_invalid_provider(self):
        data = {"pet": {"llm": {"provider": "invalid_provider"}}}
        with pytest.raises(ValidationError):
            validate_config(data)

    def test_invalid_trait_value(self):
        data = {"pet": {"personality": {"traits": {"curiosity": 1.5}}}}
        with pytest.raises(ValidationError):
            validate_config(data)

    def test_empty_name(self):
        data = {"pet": {"name": ""}}
        with pytest.raises(ValidationError):
            validate_config(data)

    def test_invalid_daily_limit(self):
        data = {"pet": {"llm": {"call_budget": {"daily_limit": 0}}}}
        with pytest.raises(ValidationError):
            validate_config(data)


class TestEnsureDefaultConfig:
    def test_creates_default_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        config_path = ensure_default_config()
        assert config_path.exists()
        data = yaml.safe_load(config_path.read_text())
        assert data["pet"]["name"] == "Tomo"
