"""LLM adapters — one interface, three providers.

DOCUBOT_LLM_PROVIDER selects the backend:
  - openai    — OpenAI chat completions (gpt-4o-mini by default)
  - anthropic — Anthropic messages API (claude-3-5-haiku-latest by default)
  - ollama    — a local Ollama instance, no outbound traffic at all

The chat layer always passes the retrieved passages as context and asks the
model to cite them by index. Each adapter normalizes the response to a
``LLMResponse`` so the chat view does not care which provider is configured.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    text: str
    model: str
    usage: dict | None = None  # {"prompt_tokens":..., "completion_tokens":...}


def get_provider() -> str:
    return os.environ.get("DOCUBOT_LLM_PROVIDER", "openai").lower()


def get_model() -> str:
    """The default model for the configured provider."""
    provider = get_provider()
    defaults = {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-haiku-latest",
        "ollama": "llama3.1:8b",
        "stub": "stub",
    }
    return os.environ.get("DOCUBOT_LLM_MODEL", defaults.get(provider, "gpt-4o-mini"))


def answer(question: str, context_passages: list[str], *, owner: str = "") -> LLMResponse:
    """Answer `question` using the retrieved `context_passages`.

    The system prompt instructs the model to answer only from the context
    and to cite by [1], [2], ... — the chat view maps these back to the
    actual documents and returns structured citations.
    """
    provider = get_provider()
    if provider == "stub":
        return _answer_stub(question, context_passages)
    if not context_passages:
        # No context: the model should say it cannot answer, rather than
        # hallucinate. We still call the provider so the response is
        # consistent, but the prompt makes the absence explicit.
        system = (
            "You are docubot, a self-hosted document assistant. "
            "The user has no documents ingested that match this question. "
            "Politely explain that no relevant passages were found and "
            "suggest uploading documents first."
        )
        user_msg = question
    else:
        system = (
            "You are docubot, a self-hosted document assistant. "
            "Answer the user's question using ONLY the context passages "
            "below. If the answer is not in the context, say so explicitly. "
            "Cite passages by their number in square brackets, e.g. [1] or "
            "[2][3]. Keep answers concise and grounded."
        )
        parts = []
        for i, p in enumerate(context_passages, start=1):
            parts.append(f"[{i}] {p}")
        user_msg = (
            f"Context passages:\n\n" + "\n\n".join(parts)
            + f"\n\n---\n\nQuestion: {question}"
        )

    if provider == "openai":
        return _answer_openai(system, user_msg)
    if provider == "anthropic":
        return _answer_anthropic(system, user_msg)
    if provider == "ollama":
        return _answer_ollama(system, user_msg)
    raise NotImplementedError(f"unsupported LLM provider: {provider!r}")


def _answer_openai(system: str, user: str) -> LLMResponse:
    from openai import OpenAI
    client = OpenAI()
    resp = client.chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=float(os.environ.get("DOCUBOT_LLM_TEMPERATURE", "0.2")),
        max_tokens=int(os.environ.get("DOCUBOT_LLM_MAX_TOKENS", "800")),
    )
    choice = resp.choices[0]
    usage = None
    if resp.usage:
        usage = {
            "prompt_tokens": resp.usage.prompt_tokens,
            "completion_tokens": resp.usage.completion_tokens,
        }
    return LLMResponse(text=choice.message.content or "", model=resp.model, usage=usage)


def _answer_anthropic(system: str, user: str) -> LLMResponse:
    from anthropic import Anthropic
    client = Anthropic()
    resp = client.messages.create(
        model=get_model(),
        system=system,
        max_tokens=int(os.environ.get("DOCUBOT_LLM_MAX_TOKENS", "800")),
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in resp.content if hasattr(block, "text"))
    usage = {"prompt_tokens": resp.usage.input_tokens,
             "completion_tokens": resp.usage.output_tokens}
    return LLMResponse(text=text, model=resp.model, usage=usage)


def _answer_ollama(system: str, user: str) -> LLMResponse:
    """Ollama via its OpenAI-compatible endpoint — no SDK needed, just httpx.

    Set DOCUBOT_OLLAMA_URL to point at the local Ollama instance (default
    http://ollama:11434 — the service name in the compose stack).
    """
    import httpx
    base = os.environ.get("DOCUBOT_OLLAMA_URL", "http://ollama:11434")
    resp = httpx.post(
        f"{base}/v1/chat/completions",
        json={
            "model": get_model(),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": float(os.environ.get("DOCUBOT_LLM_TEMPERATURE", "0.2")),
            "max_tokens": int(os.environ.get("DOCUBOT_LLM_MAX_TOKENS", "800")),
        },
        timeout=120.0,
    )
    resp.raise_for_status()
    data = resp.json()
    choice = data["choices"][0]
    return LLMResponse(
        text=choice["message"]["content"],
        model=data.get("model", get_model()),
        usage=data.get("usage"),
    )


def _answer_stub(question: str, passages: list[str]) -> LLMResponse:
    """A no-op provider for tests and load drills.

    Returns a deterministic answer that cites the first passage, so the chat
    view's citation resolution path runs end-to-end without calling any
    external LLM. Use DOCUBOT_LLM_PROVIDER=stub in CI and in `make demo`
    when you want to exercise the product without an API key or a local
    model running.
    """
    if not passages:
        text = (
            "I could not find any documents matching your question. "
            "Upload a document and try again."
        )
    else:
        # Cite the top passage by [1]. The chat view resolves this back to
        # the actual chunk for the structured citation.
        snippet = passages[0].strip().split("\n")[0][:120]
        text = (
            f"Based on your documents, here is what I found [1]: "
            f"{snippet}…"
        )
    return LLMResponse(
        text=text,
        model="stub",
        usage={"prompt_tokens": len(question) // 4, "completion_tokens": len(text) // 4},
    )
