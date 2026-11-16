"""Unit tests for chat.llm — provider selection, grounding prompts, stub.

The stub provider is the documented no-network path for CI and `make demo`
(see chat/llm.py), so it can be asserted byte-for-byte. Real providers are
tested at the dispatch boundary only: we verify `answer()` routes to the
right adapter with the right prompt, then hand the test a canned response —
no API keys, no network.
"""
from __future__ import annotations

import pytest

from chat import llm
from chat.llm import LLMResponse, answer, get_model, get_provider


# ---------------------------------------------------------------------------
# provider/model selection
# ---------------------------------------------------------------------------


def test_default_provider_is_openai(monkeypatch):
    monkeypatch.delenv("DOCUBOT_LLM_PROVIDER", raising=False)
    assert get_provider() == "openai"


def test_provider_env_is_lowercased(monkeypatch):
    monkeypatch.setenv("DOCUBOT_LLM_PROVIDER", "OLLAMA")
    assert get_provider() == "ollama"


@pytest.mark.parametrize(
    ("provider", "expected"),
    [
        ("openai", "gpt-4o-mini"),
        ("anthropic", "claude-3-5-haiku-latest"),
        ("ollama", "llama3.1:8b"),
        ("stub", "stub"),
    ],
)
def test_model_defaults_per_provider(monkeypatch, provider, expected):
    monkeypatch.delenv("DOCUBOT_LLM_MODEL", raising=False)
    monkeypatch.setenv("DOCUBOT_LLM_PROVIDER", provider)
    assert get_model() == expected


def test_model_env_override_wins(monkeypatch):
    monkeypatch.setenv("DOCUBOT_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("DOCUBOT_LLM_MODEL", "qwen2.5:7b-instruct")
    assert get_model() == "qwen2.5:7b-instruct"


# ---------------------------------------------------------------------------
# prompt construction (grounding contract)
# ---------------------------------------------------------------------------


def test_grounded_prompt_numbers_passages_and_asks_for_citations(monkeypatch):
    monkeypatch.setenv("DOCUBOT_LLM_PROVIDER", "openai")
    captured = {}

    def fake_openai(system, user):
        captured["system"] = system
        captured["user"] = user
        return LLMResponse(text="[1] grounded", model="gpt-4o-mini")

    monkeypatch.setattr(llm, "_answer_openai", fake_openai)
    answer("what is docubot?", ["first passage", "second passage"])

    assert "[1] first passage" in captured["user"]
    assert "[2] second passage" in captured["user"]
    assert "Question: what is docubot?" in captured["user"]
    assert "ONLY the context" in captured["system"]
    assert "square brackets" in captured["system"]


def test_empty_context_prompt_admits_no_passages(monkeypatch):
    monkeypatch.setenv("DOCUBOT_LLM_PROVIDER", "openai")
    captured = {}

    def fake_openai(system, user):
        captured["system"] = system
        captured["user"] = user
        return LLMResponse(text="nothing found", model="gpt-4o-mini")

    monkeypatch.setattr(llm, "_answer_openai", fake_openai)
    answer("what is docubot?", [])

    assert "no relevant passages" in captured["system"]
    assert captured["user"] == "what is docubot?"


def test_answer_routes_to_anthropic(monkeypatch):
    routed = {}

    def fake_anthropic(system, user):
        routed["system"] = system
        return LLMResponse(text="ok", model="claude-3-5-haiku-latest")

    monkeypatch.setenv("DOCUBOT_LLM_PROVIDER", "anthropic")
    monkeypatch.setattr(llm, "_answer_anthropic", fake_anthropic)
    resp = answer("q", ["p"])
    assert resp.model == "claude-3-5-haiku-latest"
    assert "system" in routed


def test_answer_routes_to_ollama(monkeypatch):
    monkeypatch.setenv("DOCUBOT_LLM_PROVIDER", "ollama")
    monkeypatch.setattr(llm, "_answer_ollama", lambda s, u: LLMResponse(text="ok", model="m"))
    assert answer("q", ["p"]).text == "ok"


def test_answer_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("DOCUBOT_LLM_PROVIDER", "carrier-pigeon")
    with pytest.raises(NotImplementedError, match="carrier-pigeon"):
        answer("q", ["p"])


# ---------------------------------------------------------------------------
# stub provider (deterministic, used by CI + make demo)
# ---------------------------------------------------------------------------


def test_stub_cites_first_passage():
    resp = llm._answer_stub("what?", ["Neural nets need data.\nmore lines", "second"])
    assert "[1]" in resp.text
    assert "Neural nets need data." in resp.text
    assert resp.model == "stub"


def test_stub_without_passages_is_honest():
    resp = llm._answer_stub("what?", [])
    assert "could not find" in resp.text
    assert "[" not in resp.text


def test_stub_usage_is_populated():
    resp = llm._answer_stub("how long is a question", ["passage"])
    assert resp.usage["prompt_tokens"] > 0
    assert resp.usage["completion_tokens"] > 0


def test_answer_dispatches_stub_via_answer(monkeypatch):
    monkeypatch.setenv("DOCUBOT_LLM_PROVIDER", "stub")
    resp = answer("q", ["p"])
    assert resp.model == "stub"
