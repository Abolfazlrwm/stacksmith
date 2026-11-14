# StackSmith + docubot — Product Presentation

Editable source for the 11-slide product deck. The slides themselves (HTML +
CSS + the brief) live in this directory; the `.pptx` and `.pdf` artifacts are
**build outputs** published as release assets on the matching version tag, not
committed to git.

| Asset | Where to get it |
| --- | --- |
| `stacksmith-presentation.pptx` | [Release assets on the latest `v1.1.x` tag](https://github.com/Abolfazlrwm/stacksmith/releases) |
| `stacksmith-presentation.pdf` | [Release assets on the latest `v1.1.x` tag](https://github.com/Abolfazlrwm/stacksmith/releases) |
| Editable HTML source | `slides/` in this directory |

## Layout

```
docs/presentation/
├── README.md                          # this file
├── slides/                            # source-of-truth
│   ├── global.css                     # ops-console dark theme tokens
│   ├── slides_brief.json              # the per-slide spec (paths relative)
│   └── slide_01.html .. slide_11.html  # one file per slide, 1280×720 canvas
└── scripts/
    ├── build_presentation.py          # rebuild pptx + pdf from the HTML
    └── relativize_brief_paths.py      # keep slides_brief.json paths portable
```

## Rebuild from source

The generator shells out to the `pptx` skill's `batch_html2pptx.js` converter
(located at `skills/pptx/batch_html2pptx.js` in the agent sandbox; point
`PPTX_SKILL_DIR` at it if your environment differs), then `soffice` for the
PDF pass.

### Prerequisites

- **Node.js** 18+ (for `batch_html2pptx.js`)
- **LibreOffice** (`soffice` on PATH, for the PDF step)
- **Python 3.10+** with `pypdf` (optional — only for page-count verification;
  falls back to `pdfinfo`)

### Build

```bash
# from the repo root
python3 docs/presentation/scripts/build_presentation.py
# → writes docs/presentation/stacksmith-presentation.{pptx,pdf}
```

Useful flags:

```bash
--out DIR        # write outputs to DIR instead of docs/presentation/
--pptx-only      # skip the soffice PDF step
--check          # exit nonzero if any verification fails (for CI)
```

### CI integration

The `--check` flag is designed for a GitHub Actions workflow that rebuilds
the deck on every push to `slides/` or `scripts/`, verifies page count and
density, and re-uploads the artifacts to the release on tag builds. Wire it
into a job like:

```yaml
- run: python3 docs/presentation/scripts/build_presentation.py --check
```

## Editing a slide

1. Edit the matching `slides/slide_*.html`. Every slide is a self-contained
   1280×720 page that pulls tokens from `global.css`. Keep `padding` and the
   `position:absolute` footer (`bottom:20px; left:56px; right:56px`) consistent
   across slides — the deck was deliberately standardized.
2. If the per-slide spec changes, update `slides/slides_brief.json` too so the
   brief stays the source of truth.
3. Rebuild locally with the script above and eyeball the PDF before opening a
   pull request.

## Design tokens

The deck uses one dark theme, defined in `slides/global.css`:

| Token | Value | Use |
| --- | --- | --- |
| `--bg` | `#0B1220` | slide canvas |
| `--primary` | `#38BDF8` | sky-blue accents, primary numbers |
| `--accent` | `#F59E0B` | amber highlights, version tags |
| `--font-heading` | Space Grotesk | H1 / H2 |
| `--font-body` | Inter | paragraphs |
| `--font-num` | JetBrains Mono | eyebrow, footer, numerics |

Fonts are loaded from Google Fonts in `global.css`; no local font install
needed for the HTML preview. The `pptx` converter renders the same fonts via
its bundled font stack.

## Versioning

The deck tracks `VERSION` at the repo root. When `VERSION` bumps, update the
`v1.1.4 · stable` tags on slide 01 and the cover/release chips on slide 11,
then cut a release with the rebuilt artifacts attached.
