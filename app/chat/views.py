"""Chat API — POST a question, get an answer grounded in your documents.

Flow:
  1. Receive {question, conversation_id?, top_k?}
  2. Retrieve top_k chunks for the question (RAG over pgvector)
  3. Pass context to the LLM adapter (OpenAI / Anthropic / Ollama)
  4. Persist the user message and the assistant answer (with citations)
  5. Return {answer, citations, conversation_id, message_id, model}

The owner is taken from the request — for v1.2 we use a simple header
(X-Docubot-Owner) set by the reverse proxy after auth. A future phase can
swap this for a real session/JWT without changing this view.
"""
from __future__ import annotations

import logging
import re

from django.db import transaction
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from rag.retrieval import retrieve

from .llm import answer as llm_answer
from .models import Conversation, Message
from .serializers import ChatRequestSerializer, ChatResponseSerializer

log = logging.getLogger(__name__)

CITATION_RE = re.compile(r"\[(\d+)\]")


def _owner_from_request(request: HttpRequest) -> str:
    """Resolve the owner string for this request.

    v1.2: trust an X-Docubot-Owner header set by the reverse proxy. This is
    deliberately simple — it lets us ship multi-user isolation without a
    full auth system, and the README documents that the operator must set
    the header in nginx after performing their own auth.
    """
    return request.headers.get("X-Docubot-Owner", "anonymous")


class ChatView(APIView):
    """POST /api/chat/ — ask docubot a question."""

    def post(self, request: HttpRequest) -> Response:
        # Owner scoping — never mix users' corpora.
        owner = _owner_from_request(request)

        ser = ChatRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        question = ser.validated_data["question"]
        top_k = ser.validated_data["top_k"]
        conversation_id = ser.validated_data.get("conversation_id")

        # 1. Retrieve the most relevant chunks for this owner's corpus.
        hits = retrieve(question, owner=owner, top_k=top_k)

        # 2. Ask the LLM, grounded in the retrieved passages.
        passages = [h.text for h in hits]
        llm_resp = llm_answer(question, passages, owner=owner)

        # 3. Map [1]/[2]/... back to the actual chunks for structured citations.
        citations = _resolve_citations(llm_resp.text, hits)

        # 4. Persist the conversation turn.
        with transaction.atomic():
            if conversation_id:
                conv = Conversation.objects.filter(
                    id=conversation_id, owner=owner,
                ).first()
                if conv is None:
                    return Response(
                        {"detail": "conversation not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                conv = Conversation.objects.create(
                    owner=owner,
                    title=question[:80],
                )
            Message.objects.create(
                conversation=conv, role=Message.Role.USER, content=question,
            )
            assistant_msg = Message.objects.create(
                conversation=conv,
                role=Message.Role.ASSISTANT,
                content=llm_resp.text,
                citations=citations,
                retrieved_count=len(hits),
                model=llm_resp.model,
                usage=llm_resp.usage or {},
            )

        # 5. Shape the response.
        resp_data = {
            "answer": llm_resp.text,
            "conversation_id": conv.id,
            "message_id": assistant_msg.id,
            "citations": citations,
            "retrieved_count": len(hits),
            "model": llm_resp.model,
        }
        return Response(ChatResponseSerializer(resp_data).data,
                        status=status.HTTP_200_OK)


def _resolve_citations(text: str, hits) -> list[dict]:
    """Parse [1], [2], ... markers from `text` and map to actual chunks.

    Returns a deduplicated list of citation dicts, ordered by first
    appearance in the answer. If the model did not cite anything (no
    markers), we return all retrieved hits ranked by score so the UI can
    still show sources.
    """
    cited_indices: list[int] = []
    seen: set[int] = set()
    for m in CITATION_RE.finditer(text):
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(hits) and idx not in seen:
            cited_indices.append(idx)
            seen.add(idx)

    if not cited_indices:
        # No explicit citations — return all hits, sorted by score.
        ordered = sorted(range(len(hits)), key=lambda i: hits[i].score, reverse=True)
        cited_indices = ordered

    out = []
    for i in cited_indices:
        h = hits[i]
        out.append({
            "chunk_id": h.chunk_id,
            "document_id": h.document_id,
            "document_title": h.document_title,
            "ordinal": h.ordinal,
            "score": round(h.score, 4),
            "snippet": h.text[:300] + ("..." if len(h.text) > 300 else ""),
        })
    return out
