#!/usr/bin/env python3
"""Make slides_brief.json paths relative to the docs/presentation/ root.

Replaces every absolute /home/z/my-project/download/slides/... reference
with a relative path so the brief is portable inside the repo.
"""
import json
import re
import sys
from pathlib import Path

BRIEF = Path(__file__).resolve().parent.parent / "slides" / "slides_brief.json"
ABS_PREFIX = "/home/z/my-project/download/slides/"

text = BRIEF.read_text(encoding="utf-8")

# Count occurrences before reporting
before = text.count(ABS_PREFIX)
if before == 0:
    print(f"[ok] no absolute paths found in {BRIEF.name} — nothing to do")
    sys.exit(0)

# Replace the prefix wherever it appears inside JSON string values.
# slides_brief.json stores paths like:
#   "global_css_path": "/home/z/my-project/download/slides/global.css",
#   "slides_dir":      "/home/z/my-project/download/slides",       # no trailing slash
#   "output_path":     "/home/z/my-project/download/slides/slide_01.html"
# Target forms after rewrite (relative to docs/presentation/):
#   "slides/global.css", "slides", "slides/slide_01.html"
# Replace the prefix WITHOUT the trailing slash first, so that
# "/home/z/my-project/download/slides" (no trailing slash) becomes "slides",
# then the prefix WITH the trailing slash handles the rest.
ABS_PREFIX_NO_SLASH = "/home/z/my-project/download/slides"
ABS_PREFIX = ABS_PREFIX_NO_SLASH + "/"

new_text = text.replace(ABS_PREFIX_NO_SLASH, "slides")

# Validate the result still parses as JSON
try:
    data = json.loads(new_text)
except json.JSONDecodeError as e:
    print(f"[err] rewrite produced invalid JSON: {e}", file=sys.stderr)
    sys.exit(1)

BRIEF.write_text(new_text, encoding="utf-8")
print(f"[ok] rewrote {before} absolute path(s) → relative in {BRIEF.name}")

# Sanity-report the keys we expect to now be relative
for key in ("global_css_path", "slides_dir"):
    if key in data:
        print(f"     {key} = {data[key]!r}")
for s in data.get("slides", [])[:3]:
    if "output_path" in s:
        print(f"     output_path = {s['output_path']!r}")
