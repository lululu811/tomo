"""Tests for the LLM client."""

import json
from unittest.mock import MagicMock, patch

import pytest

from tomo.llm import LLMClient


class TestLLMClient:
    @pytest.fixture
    def client(self, default_config):
        return LLMClient(default_config)

    def test_init(self, client, default_config):
        assert client.config == default_config
        assert client.provider == "ollama"
        assert client.model == "qwen2.5:7b"

    def test_check_budget_no_limit(self, client):
        # daily_llm_limit=0 means unlimited
        client.config._data["pet"]["llm"]["call_budget"]["daily_limit"] = 0
        assert client._check_budget() is True

    def test_check_budget_within_limit(self, client):
        with patch.object(client, "_load_usage", return_value={"2025-01-01": 5}):
            client.config._data["pet"]["llm"]["call_budget"]["daily_limit"] = 20
            assert client._check_budget() is True

    def test_check_budget_exceeded(self, client):
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        with patch.object(client, "_load_usage", return_value={today: 25}):
            client.config._data["pet"]["llm"]["call_budget"]["daily_limit"] = 20
            assert client._check_budget() is False

    def test_generate_budget_exceeded(self, client):
        with patch.object(client, "_check_budget", return_value=False):
            result = client.generate(prompt="Hello")
            assert "休息" in result

    def test_generate_unknown_provider(self, client):
        client.provider = "unknown_provider"
        result = client.generate(prompt="Hello")
        assert "未知" in result

    def test_generate_ollama(self, client):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"message": {"content": "Hello from Ollama"}}
        ).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("tomo.llm._urlopen_with_retry", return_value=mock_response):
            result = client.generate(prompt="Hello")
            assert result == "Hello from Ollama"

    def test_generate_anthropic(self, client):
        client.provider = "anthropic"
        client.api_key = "test-key"
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"content": [{"type": "text", "text": "Hello from Claude"}]}
        ).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("tomo.llm._urlopen_with_retry", return_value=mock_response):
            result = client.generate(prompt="Hello")
            assert result == "Hello from Claude"

    def test_generate_openai_compatible(self, client):
        client.provider = "openai"
        client.api_key = "test-key"
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "Hello from OpenAI"}}]}
        ).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("tomo.llm._urlopen_with_retry", return_value=mock_response):
            result = client.generate(prompt="Hello")
            assert result == "Hello from OpenAI"

    def test_generate_http_error(self, client):
        from urllib.error import HTTPError

        err = HTTPError("url", 429, "Too Many Requests", {}, None)
        err.read = MagicMock(return_value=json.dumps({"error": {"message": "rate limit"}}).encode())

        with patch("tomo.llm._urlopen_with_retry", side_effect=err):
            result = client.generate(prompt="Hello")
            assert "出错" in result

    def test_generate_generic_error(self, client):
        with patch("tomo.llm._urlopen_with_retry", side_effect=ConnectionError("network down")):
            result = client.generate(prompt="Hello")
            assert "迷糊" in result

    def test_record_usage(self, client, tmp_path):
        with patch("tomo.llm.USAGE_FILE", tmp_path / "usage.json"):
            client._record_usage()
            usage = client._load_usage()
            assert isinstance(usage, dict)
