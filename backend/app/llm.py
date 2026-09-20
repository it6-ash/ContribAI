"""LLM provider abstraction.

Two rules the rest of the app depends on:
  1. Every call can return None. Callers MUST have a heuristic fallback, so the
     product works with no API key and never dies mid-demo.
  2. The LLM only interprets data we already gathered. It is never the source of
     a fact about GitHub.

ponytail: no vendor SDK. Groq serves the OpenAI chat-completions wire format, so
the whole provider is one httpx POST. Any OpenAI-compatible host (Together,
OpenRouter, a local vLLM) works by changing GROQ_BASE_URL.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Protocol

import httpx

from .config import get_settings

log = logging.getLogger("contribai.llm")


class LLMProvider(Protocol):
    name: str

    def available(self) -> bool: ...

    def complete(
        self, system: str, prompt: str, *, max_tokens: int = 1200, json_mode: bool = False
    ) -> str | None: ...


class GroqProvider:
    name = "groq"

    def __init__(self, api_key: str, model: str, base_url: str, reasoning_effort: str):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._reasoning_effort = reasoning_effort

    def available(self) -> bool:
        return bool(self._api_key)

    def complete(
        self, system: str, prompt: str, *, max_tokens: int = 1200, json_mode: bool = False
    ) -> str | None:
        payload = {
            "model": self._model,
            "max_completion_tokens": max_tokens,
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        if self._model.startswith("openai/gpt-oss"):
            payload["reasoning_effort"] = self._reasoning_effort
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        started = time.perf_counter()
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
            if resp.status_code == 429:
                log.warning("groq rate limited, retry after %s", resp.headers.get("retry-after"))
                return None
            resp.raise_for_status()
            data = resp.json()
            text = (data["choices"][0]["message"].get("content") or "").strip()
            log.info(
                "llm ok model=%s ms=%d tokens=%s",
                self._model,
                (time.perf_counter() - started) * 1000,
                (data.get("usage") or {}).get("total_tokens"),
            )
            return text or None
        except Exception as exc:  # network, auth, overload — never fatal
            log.warning("llm failed (%s): %s", type(exc).__name__, exc)
            return None


class NullProvider:
    """No credentials configured. Every call declines so heuristics take over."""

    name = "heuristic"

    def available(self) -> bool:
        return False

    def complete(
        self, system: str, prompt: str, *, max_tokens: int = 1200, json_mode: bool = False
    ) -> str | None:
        return None


_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        settings = get_settings()
        if settings.groq_api_key:
            _provider = GroqProvider(
                settings.groq_api_key,
                settings.groq_model,
                settings.groq_base_url,
                settings.groq_reasoning_effort,
            )
        else:
            _provider = NullProvider()
        log.info("llm provider: %s", _provider.name)
    return _provider


def set_provider(provider: LLMProvider | None) -> None:
    """Test/DI hook. Pass None to re-read settings on the next call."""
    global _provider
    _provider = provider


def complete_json(system: str, prompt: str, *, max_tokens: int = 1200) -> dict | None:
    """Ask for JSON, return the parsed object, or None if unavailable/unparseable."""
    provider = get_provider()
    if not provider.available():
        return None
    raw = provider.complete(
        system + "\n\nRespond with a single JSON object and nothing else.",
        prompt,
        max_tokens=max_tokens,
        json_mode=True,
    )
    if not raw:
        return None
    return _extract_json(raw)


def complete_text(system: str, prompt: str, *, max_tokens: int = 800) -> str | None:
    provider = get_provider()
    if not provider.available():
        return None
    return provider.complete(system, prompt, max_tokens=max_tokens)


def _extract_json(raw: str) -> dict | None:
    raw = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.+?)```", raw, re.S)
    if fenced:
        raw = fenced.group(1).strip()
    try:
        value = json.loads(raw)
    except ValueError:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            value = json.loads(raw[start : end + 1])
        except ValueError:
            return None
    return value if isinstance(value, dict) else None
