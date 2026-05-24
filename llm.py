"""LLM client for Tomo."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tomo.config import Config

logger = logging.getLogger(__name__)

USAGE_FILE = Path.home() / ".tomo" / "llm_usage.json"

DEFAULT_TIMEOUT = 60
MAX_RETRIES = 3


def _urlopen_with_retry(req: Request, timeout: int) -> Any:
    """Open URL with exponential backoff retry.

    Retries on transient errors (5xx, network issues, timeouts).
    Does not retry on 4xx client errors.
    """
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            return urlopen(req, timeout=timeout)
        except HTTPError as exc:
            last_exc = exc
            if 400 <= exc.code < 500:
                raise  # Client error, don't retry
            if attempt < MAX_RETRIES - 1:
                wait = 2**attempt
                logger.debug("HTTP %s, retrying in %ds...", exc.code, wait)
                time.sleep(wait)
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                wait = 2**attempt
                logger.debug("Request failed (%s), retrying in %ds...", exc, wait)
                time.sleep(wait)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Request failed after retries")


class LLMClient:
    """Unified LLM client supporting multiple providers."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.provider = config.llm_provider
        self.model = config.llm_model
        self.api_key = config.llm_api_key
        self.base_url = config.llm_base_url

    def generate(
        self,
        prompt: str | None = None,
        system_prompt: str | None = None,
        messages: list[dict[str, Any]] | None = None,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: Single user prompt (used when messages is None).
            system_prompt: Optional system instruction.
            messages: Full conversation history in OpenAI/Anthropic format.

        Returns a fallback message if budget is exceeded or generation fails.
        """
        if not self._check_budget():
            return "今天聊太多了，让我休息一下吧~ 🦊"

        try:
            if self.provider == "ollama":
                response = self._generate_ollama(prompt, system_prompt, messages)
            elif self.provider in ("anthropic", "minimax"):
                response = self._generate_anthropic(prompt, system_prompt, messages)
            elif self.provider in ("openai", "siliconflow", "deepseek"):
                response = self._generate_openai_compatible(prompt, system_prompt, messages)
            else:
                return f"未知的 LLM provider: {self.provider}"

            self._record_usage()
            return response
        except HTTPError as exc:
            logger.warning("LLM HTTP error: %s %s", exc.code, exc.reason)
            try:
                body = json.loads(exc.read().decode("utf-8"))
                detail = body.get("error", {}).get("message", str(exc.reason))
            except Exception:
                detail = str(exc.reason)
            return f"嗯... 我出错了 ({detail})，稍后再聊吧~ 😴"
        except Exception as exc:
            logger.warning("LLM generation failed: %s", exc)
            return "嗯... 我现在有点迷糊，稍后再聊吧~ 😴"

    # ------------------------------------------------------------------ #
    # Budget control
    # ------------------------------------------------------------------ #

    def _check_budget(self) -> bool:
        """Check if we are within the daily call budget."""
        limit = self.config.daily_llm_limit
        if limit <= 0:
            return True
        usage = self._load_usage()
        today = datetime.now().strftime("%Y-%m-%d")
        return usage.get(today, 0) < limit

    def _record_usage(self) -> None:
        """Record one LLM call in usage file."""
        usage = self._load_usage()
        today = datetime.now().strftime("%Y-%m-%d")
        usage[today] = usage.get(today, 0) + 1
        self._save_usage(usage)

    def _load_usage(self) -> dict[str, Any]:
        if not USAGE_FILE.exists():
            return {}
        try:
            with open(USAGE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_usage(self, usage: dict[str, Any]) -> None:
        try:
            USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(USAGE_FILE, "w", encoding="utf-8") as f:
                json.dump(usage, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            logger.warning("Failed to save LLM usage: %s", exc)

    # ------------------------------------------------------------------ #
    # Provider implementations
    # ------------------------------------------------------------------ #

    def _generate_ollama(
        self,
        prompt: str | None,
        system_prompt: str | None,
        messages: list[dict[str, Any]] | None,
    ) -> str:
        url = self.base_url or "http://localhost:11434"
        url = url.rstrip("/") + "/api/chat"

        if messages:
            msgs = list(messages)
            if system_prompt:
                msgs.insert(0, {"role": "system", "content": system_prompt})
        else:
            msgs = []
            if system_prompt:
                msgs.append({"role": "system", "content": system_prompt})
            if prompt:
                msgs.append({"role": "user", "content": prompt})

        data = {
            "model": self.model,
            "messages": msgs,
            "stream": False,
        }

        req = Request(
            url,
            data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with _urlopen_with_retry(req, DEFAULT_TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["message"]["content"]

    def _generate_anthropic(
        self,
        prompt: str | None,
        system_prompt: str | None,
        messages: list[dict[str, Any]] | None,
    ) -> str:
        if not self.api_key:
            raise ValueError("Anthropic API key is required")

        url = self.base_url or "https://api.anthropic.com/v1/messages"
        if not url.endswith("/v1/messages"):
            url = url.rstrip("/") + "/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        data: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 1024,
        }
        if messages:
            data["messages"] = messages
        elif prompt:
            data["messages"] = [{"role": "user", "content": prompt}]
        if system_prompt:
            data["system"] = system_prompt

        req = Request(
            url,
            data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            headers=headers,
        )
        with _urlopen_with_retry(req, DEFAULT_TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))
            for block in result.get("content", []):
                if block.get("type") == "text" and "text" in block:
                    return block["text"]
            # Fallback: try legacy format
            return result["content"][0]["text"]

    def _generate_openai_compatible(
        self,
        prompt: str | None,
        system_prompt: str | None,
        messages: list[dict[str, Any]] | None,
    ) -> str:
        url = self._resolve_openai_url()

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        if messages:
            msgs = list(messages)
            if system_prompt:
                msgs.insert(0, {"role": "system", "content": system_prompt})
        else:
            msgs = []
            if system_prompt:
                msgs.append({"role": "system", "content": system_prompt})
            if prompt:
                msgs.append({"role": "user", "content": prompt})

        data = {
            "model": self.model,
            "messages": msgs,
        }

        req = Request(
            url,
            data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            headers=headers,
        )
        with _urlopen_with_retry(req, DEFAULT_TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]

    def _resolve_openai_url(self) -> str:
        """Resolve the API endpoint for OpenAI-compatible providers."""
        if self.base_url:
            base = self.base_url.rstrip("/")
            if base.endswith("/v1/chat/completions"):
                return base
            return base + "/v1/chat/completions"

        urls = {
            "openai": "https://api.openai.com/v1/chat/completions",
            "siliconflow": "https://api.siliconflow.cn/v1/chat/completions",
            "deepseek": "https://api.deepseek.com/v1/chat/completions",
        }
        return urls.get(self.provider, urls["openai"])
