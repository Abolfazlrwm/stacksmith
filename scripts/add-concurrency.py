"""Add a concurrency: block to every GitHub Actions workflow.

The block cancels in-progress runs of the same workflow + branch when
a new commit lands. Without it, a fast push cadence queues 30 stale
runs (one per workflow) that finish minutes after the developer has
already moved on — wasting CI minutes and slowing feedback.

The group key is `{{ github.workflow }}-{{ github.ref }}` so:
- runs on different branches do NOT cancel each other
- runs on the same branch DO cancel the previous run
- pull_request runs are scoped to the PR's ref

`cancel-in-progress: true` is the standard for a single-maintainer
project. The only workflows this is wrong for are scheduled/cron ones
(stale.yml, codeql weekly) — for those, cancelling a half-finished run
mid-backup or mid-scan would leave state inconsistent. We skip those by
checking the `on:` trigger for `schedule:`.

Usage:
    python3 scripts/add-concurrency.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

WORKFLOW_DIR = Path(__file__).resolve().parent.parent / ".github" / "workflows"

# The block to insert. Indented to sit at top level (col 0).
CONCURRENCY_BLOCK = """
concurrency:
  # Cancel in-progress runs of this workflow on the same ref when a new
  # commit lands. A fast push cadence otherwise queues stale runs that
  # finish minutes after the developer moved on — wasting CI minutes.
  # Different branches / different PRs get their own group, so they do
  # not interfere with each other.
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
"""


def has_schedule(content: str) -> bool:
    """True if the workflow runs on a cron schedule.

    Scheduled workflows must NOT cancel-in-progress: a half-finished
    backup, scan, or stale-sweep interrupted mid-run leaves inconsistent
    state. We let those overlap instead.
    """
    # Look for `schedule:` under `on:` — tolerate both flow and mapping
    # forms. The mapping form is `on:\n  schedule:`; the flow form is
    # `on: schedule:` (rare). We check both.
    return bool(re.search(r"^on:.*\bschedule\b|^\s+schedule:", content, re.MULTILINE))


def already_has_concurrency(content: str) -> bool:
    return bool(re.search(r"^concurrency:", content, re.MULTILINE))


def add_concurrency(path: Path) -> str:
    """Insert the concurrency block after `permissions:` (top-level).

    Returns a status string for logging.
    """
    content = path.read_text()

    if already_has_concurrency(content):
        return "skip (already has concurrency)"
    if has_schedule(content):
        return "skip (scheduled — must not cancel mid-run)"

    # Insert right after the permissions: block. The permissions block
    # is a single-line `permissions: read` OR a multi-line mapping:
    #   permissions:
    #     contents: read
    #     issues: write
    # We match the top-level `permissions:` line and then everything up
    # to the next top-level key (a line starting at col 0, non-space).
    m = re.search(r"^permissions:.*?(?=^\S)", content, re.MULTILINE | re.DOTALL)
    if not m:
        return "skip (no top-level permissions: block found)"

    insert_at = m.end()
    new = content[:insert_at] + CONCURRENCY_BLOCK + content[insert_at:]
    path.write_text(new)
    return "added"


def main() -> int:
    if not WORKFLOW_DIR.is_dir():
        print(f"ERR: {WORKFLOW_DIR} not found", file=sys.stderr)
        return 1

    workflows = sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))
    if not workflows:
        print("ERR: no workflow files found", file=sys.stderr)
        return 1

    counts = {"added": 0, "skip": 0}
    for p in workflows:
        status = add_concurrency(p)
        counts[status.split()[0]] = counts.get(status.split()[0], 0) + 1
        print(f"  {status:35s}  {p.relative_to(WORKFLOW_DIR.parent.parent)}")

    print(f"\n  added: {counts.get('added', 0)}  skipped: {counts.get('skip', 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
