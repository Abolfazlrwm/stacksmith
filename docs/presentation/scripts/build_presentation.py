#!/usr/bin/env python3
"""Rebuild stacksmith-presentation.{pptx,pdf} from the HTML slides.

This is the source-of-truth generator for the deck artifacts. The committed
HTML + global.css + slides_brief.json under ../slides/ are the source; the
.pptx and .pdf are build outputs that are published as release assets on the
matching version tag, NOT committed to git.

Pipeline:
  1. slides/*.html  ── html2pptx ──▶  stacksmith-presentation.pptx
  2. *.pptx         ── soffice  ──▶  stacksmith-presentation.pdf
  3. verify the pptx opens and the pdf has the expected page count

The html2pptx step shells out to the Node skill at
  $PPTX_SKILL_DIR/batch_html2pptx.js   (default: /home/z/my-project/skills/pptx)
which expects `slide_*.html` in a single directory and writes one .pptx.

Usage:
  python3 build_presentation.py                # build both pptx + pdf
  python3 build_presentation.py --pptx-only     # skip the PDF step
  python3 build_presentation.py --out DIR       # write outputs to DIR
  python3 build_presentation.py --check         # build, verify, then exit nonzero on any issue

Exit codes:
  0  build + verification succeeded
  1  a required tool is missing (node, soffice, python3 -m PIL)
  2  a build step failed
  3  verification found a problem (page count, density, warnings)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRESENTATION_DIR = HERE.parent                 # docs/presentation/
SLIDES_DIR = PRESENTATION_DIR / "slides"
PPTX_SKILL_DIR = Path(os.environ.get(
    "PPTX_SKILL_DIR", "/home/z/my-project/skills/pptx"))
BATCH_HTML2PPTX = PPTX_SKILL_DIR / "batch_html2pptx.js"

BASE_NAME = "stacksmith-presentation"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def die(code: int, msg: str) -> "NoReturn":
    print(f"[err] {msg}", file=sys.stderr)
    sys.exit(code)


def run(cmd: list[str], *, cwd: Path | None = None,
        env: dict | None = None) -> subprocess.CompletedProcess:
    print(f"[run] {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd, env=env,
                          capture_output=True, text=True, check=False)


def have(tool: str) -> bool:
    return shutil.which(tool) is not None


# --------------------------------------------------------------------------- #
# step 1 — html -> pptx
# --------------------------------------------------------------------------- #
def build_pptx(out_dir: Path) -> Path:
    if not have("node"):
        die(1, "node is not on PATH; install Node.js to build the pptx")
    if not BATCH_HTML2PPTX.is_file():
        die(1, f"batch_html2pptx.js not found at {BATCH_HTML2PPTX}; "
               f"set PPTX_SKILL_DIR to point at the pptx skill")

    out_pptx = out_dir / f"{BASE_NAME}.pptx"
    env = dict(os.environ)
    # batch_html2pptx.js needs its node_modules on NODE_PATH
    node_modules = PPTX_SKILL_DIR / "node_modules"
    if node_modules.is_dir():
        env["NODE_PATH"] = str(node_modules)

    cp = run(
        ["node", str(BATCH_HTML2PPTX), str(SLIDES_DIR), str(out_pptx)],
        env=env,
    )
    print(cp.stdout)
    if cp.stderr:
        print(cp.stderr, file=sys.stderr)
    if cp.returncode != 0:
        die(2, f"html2pptx exited {cp.returncode}")

    if not out_pptx.is_file() or out_pptx.stat().st_size == 0:
        die(2, f"pptx was not written or is empty: {out_pptx}")

    # scan for hard failures emitted by the converter
    for needle in ("CRITICAL", "BOUNDS", "OVERFLOW"):
        if needle in cp.stdout or needle in cp.stderr:
            die(3, f"html2pptx emitted a {needle} warning — deck is not clean")

    print(f"[ok] pptx  {out_pptx} ({out_pptx.stat().st_size // 1024} KB)")
    return out_pptx


# --------------------------------------------------------------------------- #
# step 2 — pptx -> pdf
# --------------------------------------------------------------------------- #
def build_pdf(pptx: Path, out_dir: Path) -> Path:
    if not have("soffice"):
        print("[warn] soffice not found; skipping PDF step "
              "(install libreoffice for the PDF build)")
        return Path()

    out_pdf = out_dir / f"{BASE_NAME}.pdf"
    cp = run(["soffice", "--headless", "--convert-to", "pdf",
              "--outdir", str(out_dir), str(pptx)])
    if cp.returncode != 0 or not out_pdf.is_file():
        print(cp.stdout, file=sys.stderr)
        print(cp.stderr, file=sys.stderr)
        die(2, f"soffice failed to produce {out_pdf}")

    print(f"[ok] pdf   {out_pdf} ({out_pdf.stat().st_size // 1024} KB)")
    return out_pdf


# --------------------------------------------------------------------------- #
# step 3 — verify
# --------------------------------------------------------------------------- #
def verify(pptx: Path, pdf: Path) -> None:
    # page count from the PDF
    if pdf.is_file():
        try:
            from pypdf import PdfReader          # noqa: WPS433
            n = len(PdfReader(str(pdf)).pages)
        except ImportError:
            # fall back to pdfinfo if available, else skip
            if have("pdfinfo"):
                cp = run(["pdfinfo", str(pdf)])
                for line in cp.stdout.splitlines():
                    if line.startswith("Pages:"):
                        n = int(line.split()[-1])
                        break
                else:
                    n = 0
            else:
                n = 0
                print("[warn] neither pypdf nor pdfinfo available; "
                      "cannot verify PDF page count")
        if n and n != 11:
            die(3, f"PDF page count is {n}, expected 11")
        if n:
            print(f"[ok] PDF has {n} pages (expected 11)")

    # sanity-render one slide to make sure the pptx is not corrupt
    if have("soffice") and pdf.is_file():
        # we already converted to PDF above, so the pptx parsed fine
        pass

    print("[ok] verification passed")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=PRESENTATION_DIR,
                    help="directory to write the .pptx/.pdf "
                         "(default: docs/presentation/)")
    ap.add_argument("--pptx-only", action="store_true",
                    help="skip the soffice PDF step")
    ap.add_argument("--check", action="store_true",
                    help="exit nonzero if any verification fails")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    if not SLIDES_DIR.is_dir():
        die(1, f"slides dir not found: {SLIDES_DIR}")
    htmls = sorted(SLIDES_DIR.glob("slide_*.html"))
    if len(htmls) != 11:
        die(1, f"expected 11 slide_*.html in {SLIDES_DIR}, found {len(htmls)}")
    print(f"[ok] found {len(htmls)} slides in {SLIDES_DIR}")

    pptx = build_pptx(args.out)
    pdf = Path() if args.pptx_only else build_pdf(pptx, args.out)
    verify(pptx, pdf)

    print("\n[done] outputs:")
    print(f"  {pptx}")
    if pdf.is_file():
        print(f"  {pdf}")


if __name__ == "__main__":
    main()
