"""Model client adapters.

Tier 0 uses a deterministic heuristic client so the pipeline can run without
local vLLM or API credentials. Real vLLM/API clients should implement the same
`complete(system, user, options)` method.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv


class HeuristicProposerClient:
    """Cheap stand-in for a Proposer model during architecture validation."""

    model_id = "heuristic-proposer-v0"

    def complete(self, system: str, user: str, options: list[str]) -> str:
        text = user.lower()
        choice = self._choose(text, options)
        return f"{choice}: Tier 0 heuristic selected this option from surface cues."

    def _choose(self, text: str, options: list[str]) -> str:
        if options == ["case_1", "case_2"]:
            if "case 1" in text and "case 2" in text:
                return self._stable_hash_choice(text, options)
        if "unreasonable" in options and "reasonable" in options:
            negative_cues = ["no excuse", "lied", "steal", "harm", "hurt"]
            return "unreasonable" if any(cue in text for cue in negative_cues) else "reasonable"
        if "unjustified" in options and "justified" in options:
            weak_cues = ["wanted", "prefer", "felt like", "because i want"]
            return "unjustified" if any(cue in text for cue in weak_cues) else "justified"
        if "author_wrong" in options and "other_wrong" in options:
            author_cues = ["i lied", "i stole", "i yelled", "i refused", "i called"]
            return "author_wrong" if any(cue in text for cue in author_cues) else "other_wrong"
        return self._stable_hash_choice(text, options)

    def _stable_hash_choice(self, text: str, options: list[str]) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return options[int(digest[:8], 16) % len(options)]


class OllamaProposerClient:
    """Local Proposer client using Ollama's HTTP API."""

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        timeout_seconds: int | None = None,
    ):
        load_dotenv()
        self.model_id = model or os.getenv("OLLAMA_PROPOSER_MODEL", "llama3.1:8b")
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.temperature = (
            temperature
            if temperature is not None
            else float(os.getenv("PROPOSER_TEMPERATURE", "0.2"))
        )
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))
        )

    def complete(self, system: str, user: str, options: list[str]) -> str:
        payload = {
            "model": self.model_id,
            "stream": False,
            "messages": [
                {"role": "system", "content": self._system(system, options)},
                {"role": "user", "content": user},
            ],
            "options": {
                "temperature": self.temperature,
                "num_predict": 256,
            },
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not reach Ollama at {self.base_url}. Start Ollama and pull {self.model_id!r}."
            ) from exc

        message = data.get("message") or {}
        content = message.get("content")
        if not content:
            raise RuntimeError(f"Ollama returned no message content: {data}")
        return content

    def _system(self, system: str, options: list[str]) -> str:
        return (
            f"{system}\n\n"
            f"You must begin your answer with exactly one of these option labels: {', '.join(options)}.\n"
            "After the label, add a colon and one brief sentence of reasoning."
        )


class OpenAIProposerClient:
    """Hosted Proposer client using the OpenAI Responses API."""

    def __init__(
        self,
        model: str | None = None,
        max_output_tokens: int | None = None,
        reasoning_effort: str | None = None,
    ):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing. Copy .env.sample to .env and set a real key.")

        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model_id = model or os.getenv("OPENAI_PROPOSER_MODEL", "gpt-5-mini")
        self.max_output_tokens = max_output_tokens or int(os.getenv("PROPOSER_MAX_OUTPUT_TOKENS", "512"))
        self.reasoning_effort = reasoning_effort or os.getenv("OPENAI_PROPOSER_REASONING_EFFORT", "minimal")
        self.last_usage: dict = {}
        self._scenario_usage = _empty_usage()

    def reset_usage(self) -> None:
        self.last_usage = {}
        self._scenario_usage = _empty_usage()

    def usage_summary(self) -> dict:
        if not self._scenario_usage["requests"]:
            return {}
        return dict(self._scenario_usage)

    def complete(self, system: str, user: str, options: list[str]) -> str:
        payload = {
            "model": self.model_id,
            "input": [
                {"role": "system", "content": self._system(system, options)},
                {"role": "user", "content": user},
            ],
            "max_output_tokens": self.max_output_tokens,
        }
        if self._supports_reasoning_controls():
            payload["reasoning"] = {"effort": self.reasoning_effort}
            payload["text"] = {"verbosity": "low"}
        response = self.client.responses.create(**payload)
        self.last_usage = _openai_response_usage(response)
        _accumulate_usage(self._scenario_usage, self.last_usage)
        content = getattr(response, "output_text", None)
        if not content:
            raise RuntimeError(f"OpenAI Proposer returned no output_text: {response}")
        return content

    def _system(self, system: str, options: list[str]) -> str:
        return (
            f"{system}\n\n"
            f"You must begin your answer with exactly one of these option labels: {', '.join(options)}.\n"
            "After the label, add a colon and one brief sentence of reasoning. "
            "Do not include markdown or extra headings."
        )

    def _supports_reasoning_controls(self) -> bool:
        return self.model_id.startswith(("gpt-5", "o1", "o3", "o4"))


class AnthropicProposerClient:
    """Hosted Proposer client using Anthropic's Messages API."""

    def __init__(
        self,
        model: str | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
        timeout_seconds: int | None = None,
    ):
        load_dotenv()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is missing. Add it to .env before running Claude Proposer tests.")

        self.api_key = api_key
        self.model_id = model or os.getenv("ANTHROPIC_PROPOSER_MODEL", "claude-haiku-4-5")
        self.max_output_tokens = max_output_tokens or int(os.getenv("PROPOSER_MAX_OUTPUT_TOKENS", "512"))
        self.temperature = (
            temperature
            if temperature is not None
            else float(os.getenv("PROPOSER_TEMPERATURE", "0.2"))
        )
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else int(os.getenv("ANTHROPIC_TIMEOUT_SECONDS", "180"))
        )
        self.last_usage: dict = {}
        self._scenario_usage = _empty_usage()

    def reset_usage(self) -> None:
        self.last_usage = {}
        self._scenario_usage = _empty_usage()

    def usage_summary(self) -> dict:
        if not self._scenario_usage["requests"]:
            return {}
        return dict(self._scenario_usage)

    def complete(self, system: str, user: str, options: list[str]) -> str:
        payload = {
            "model": self.model_id,
            "max_tokens": self.max_output_tokens,
            "temperature": self.temperature,
            "system": self._system(system, options),
            "messages": [{"role": "user", "content": user}],
        }
        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic Proposer request failed with HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("Could not reach Anthropic Messages API.") from exc

        self.last_usage = self._anthropic_usage(data)
        _accumulate_usage(self._scenario_usage, self.last_usage)
        content_blocks = data.get("content") or []
        text_parts = [
            block.get("text", "")
            for block in content_blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        content = "\n".join(part.strip() for part in text_parts if part.strip())
        if not content:
            raise RuntimeError(f"Anthropic Proposer returned no text content: {data}")
        return content

    def _system(self, system: str, options: list[str]) -> str:
        return (
            f"{system}\n\n"
            f"You must begin your answer with exactly one of these option labels: {', '.join(options)}.\n"
            "After the label, add a colon and one brief sentence of reasoning. "
            "Do not include markdown or extra headings."
        )

    def _anthropic_usage(self, data: dict) -> dict:
        usage = data.get("usage") or {}
        input_tokens = int(usage.get("input_tokens", 0) or 0)
        output_tokens = int(usage.get("output_tokens", 0) or 0)
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }


def _empty_usage() -> dict:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "requests": 0,
    }


def _accumulate_usage(total: dict, usage: dict) -> None:
    total["requests"] += int(usage.get("requests", 1) or 1)
    token_source = usage.get("cumulative") or usage
    for key in ["input_tokens", "output_tokens", "total_tokens"]:
        total[key] += int(token_source.get(key, 0) or 0)


def _openai_response_usage(response) -> dict:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if isinstance(usage, dict):
        return usage
    return {
        key: getattr(usage, key)
        for key in ["input_tokens", "output_tokens", "total_tokens"]
        if hasattr(usage, key)
    }
