#!/usr/bin/env python3
"""demo.py — end-to-end demo of the docubot product.

Ingests the small sample corpus under tests/demo-corpus/, waits for the
documents to become ready, then asks a sample question through the chat
API and prints the answer with its citations.

This is what `make demo` runs. It exercises the same HTTP surface a real
user would, so it doubles as a smoke test for the product features.

Requires the prod stack (or any stack answering on the configured host)
to be up. Run `make up` first if it is not.

Usage:
  python3 scripts/demo.py                       # default question
  python3 scripts/demo.py "your question"      # custom question
  python3 scripts/demo.py --host http://localhost:8080
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "tests" / "demo-corpus"

DEFAULT_HOST = os.environ.get("DOCUBOT_HOST", "http://localhost:8080")
DEFAULT_OWNER = "demo"
DEFAULT_QUESTION = "What is docubot, and what does StackSmith include?"
# How long to wait for documents to ingest before giving up. Local
# embeddings on a fresh worker take ~30s to warm the model cache on the
# first run; allow generous slack.
INGEST_TIMEOUT_S = 180
INGEST_POLL_S = 3


def log(msg: str) -> None:
    print(f"[demo] {msg}", flush=True)


def upload(client: httpx.Client, host: str, owner: str, path: Path) -> dict:
    """Upload one document. Returns the created Document dict."""
    with path.open("rb") as fh:
        r = client.post(
            f"{host}/api/documents/",
            headers={"X-Docubot-Owner": owner},
            files={"file": (path.name, fh, "text/markdown")},
            data={"title": path.stem},
            timeout=60.0,
        )
    r.raise_for_status()
    return r.json()


def wait_ready(client: httpx.Client, host: str, owner: str,
               doc_ids: list[int]) -> None:
    """Poll the documents list until every id is ready or failed."""
    deadline = time.monotonic() + INGEST_TIMEOUT_S
    while time.monotonic() < deadline:
        r = client.get(
            f"{host}/api/documents/",
            headers={"X-Docubot-Owner": owner},
            timeout=10.0,
        )
        r.raise_for_status()
        docs = {d["id"]: d for d in r.json()}
        states = [docs[i]["status"] for i in doc_ids if i in docs]
        ready = sum(1 for s in states if s == "ready")
        failed = sum(1 for s in states if s == "failed")
        log(f"ingest status: {ready}/{len(doc_ids)} ready"
            f"{', ' + str(failed) + ' failed' if failed else ''}")
        if any(s == "failed" for s in states):
            failed_doc = next(docs[i] for i in doc_ids if docs[i]["status"] == "failed")
            raise RuntimeError(
                f"document {failed_doc['title']} failed to ingest: "
                f"{failed_doc.get('error', 'unknown error')}"
            )
        if all(s == "ready" for s in states):
            return
        time.sleep(INGEST_POLL_S)
    raise TimeoutError(
        f"documents not ready after {INGEST_TIMEOUT_S}s "
        f"(states={states})"
    )


def ask(client: httpx.Client, host: str, owner: str, question: str) -> dict:
    """Ask one question. Returns the chat API response dict."""
    r = client.post(
        f"{host}/api/chat/",
        headers={
            "X-Docubot-Owner": owner,
            "Content-Type": "application/json",
        },
        json={"question": question, "top_k": 5},
        timeout=120.0,  # LLM call can be slow on a cold worker
    )
    r.raise_for_status()
    return r.json()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    ap.add_argument("--host", default=DEFAULT_HOST,
                    help="base URL of the running docubot instance")
    ap.add_argument("--owner", default=DEFAULT_OWNER)
    args = ap.parse_args()

    corpus = sorted(CORPUS_DIR.glob("*.md"))
    if not corpus:
        print(f"[demo] no corpus files in {CORPUS_DIR}", file=sys.stderr)
        return 1
    log(f"host: {args.host}")
    log(f"owner: {args.owner}")
    log(f"corpus: {len(corpus)} documents in {CORPUS_DIR}")

    with httpx.Client() as client:
        # 1. Upload the corpus (dedup means a re-run is a no-op).
        log("uploading corpus...")
        doc_ids: list[int] = []
        for path in corpus:
            doc = upload(client, args.host, args.owner, path)
            log(f"  uploaded {path.name}: id={doc['id']} status={doc['status']}")
            doc_ids.append(doc["id"])

        # 2. Wait for ingestion to complete.
        log("waiting for ingestion...")
        wait_ready(client, args.host, args.owner, doc_ids)

        # 3. Ask the question.
        log(f"asking: {args.question}")
        resp = ask(client, args.host, args.owner, args.question)

    # 4. Print the answer and citations in a readable form.
    print()
    print("=" * 72)
    print("QUESTION")
    print("=" * 72)
    print(args.question)
    print()
    print("=" * 72)
    print("ANSWER")
    print("=" * 72)
    print(resp["answer"])
    print()
    print("=" * 72)
    print(f"CITATIONS ({len(resp['citations'])} of {resp['retrieved_count']} retrieved)")
    print("=" * 72)
    for i, c in enumerate(resp["citations"], start=1):
        print(f"[{i}] {c['document_title']} · chunk #{c['ordinal']} "
              f"· {c['score']*100:.0f}% match")
        # Indent the snippet for readability.
        for line in c["snippet"].splitlines():
            print(f"    {line}")
        print()
    print(f"model: {resp.get('model', '?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
