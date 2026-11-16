"""Unit tests for chat.serializers — the API's input contract.

Pure validation: no database access anywhere in this module.
"""
from __future__ import annotations

import pytest

from chat.serializers import (
    ChatRequestSerializer,
    CitationSerializer,
    ChatResponseSerializer,
)


def _ser(data):
    s = ChatRequestSerializer(data=data)
    valid = s.is_valid()
    return s, valid


def test_chat_request_minimal_payload_is_valid():
    s, valid = _ser({"question": "what is in my documents?"})
    assert valid, s.errors
    # top_k default is 5, matching the documented retrieval behavior.
    assert s.validated_data["top_k"] == 5


def test_chat_request_question_is_required():
    s, valid = _ser({})
    assert not valid
    assert "question" in s.errors


def test_chat_request_question_max_length_4000():
    s, valid = _ser({"question": "x" * 4001})
    assert not valid
    s2, valid2 = _ser({"question": "x" * 4000})
    assert valid2, s2.errors


def test_chat_request_top_k_bounds():
    s, valid = _ser({"question": "q", "top_k": 0})
    assert not valid
    s2, valid2 = _ser({"question": "q", "top_k": 21})
    assert not valid2
    s3, valid3 = _ser({"question": "q", "top_k": 20})
    assert valid3, s3.errors


def test_chat_request_conversation_id_optional_and_nullable():
    s, valid = _ser({"question": "q", "conversation_id": None})
    assert valid, s.errors
    assert s.validated_data.get("conversation_id") is None
    s2, valid2 = _ser({"question": "q", "conversation_id": 7})
    assert valid2, s2.errors
    assert s2.validated_data["conversation_id"] == 7


def test_chat_response_roundtrip_with_citations():
    payload = {
        "answer": "grounded answer [1]",
        "conversation_id": 1,
        "message_id": 2,
        "citations": [
            {
                "chunk_id": 3,
                "document_id": 4,
                "document_title": "handbook.md",
                "ordinal": 0,
                "score": 0.87,
                "snippet": "retrieved text...",
            }
        ],
        "retrieved_count": 1,
        "model": "gpt-4o-mini",
    }
    s = ChatResponseSerializer(data=payload)
    assert s.is_valid(), s.errors
    assert s.validated_data["citations"][0]["document_title"] == "handbook.md"


def test_citation_serializer_requires_all_fields():
    s = CitationSerializer(data={"chunk_id": 1})
    assert not s.is_valid()
    assert set(s.errors) >= {
        "document_id",
        "document_title",
        "ordinal",
        "score",
        "snippet",
    }
