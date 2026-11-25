"""Generate a GitHub social preview image (1280x640 PNG) — v1.2.7 palette.

Warm ink background (purple-black, not Tailwind navy) + a single earthy
ochre accent. Square corners (no rounded pills), no glow, no gradient
on the bubble. IBM Plex type. Matches the app identity in demo.html.
"""
import matplotlib.font_manager as fm
fm.fontManager.addfont('/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf')
fm.fontManager.addfont('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np

plt.rcParams['font.sans-serif'] = ['Noto Sans SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# --- palette (mirrors demo.html :root) ---
BG       = '#171421'   # warm ink
BG_ELEV  = '#1d1928'
BG_CARD  = '#211e2b'
LINE     = '#322e3d'
LINE_2   = '#423d4f'
PRIMARY  = '#d4a055'   # ochre
PRIMARY2 = '#b88842'
OK       = '#7fa67e'   # moss
TEXT     = '#e8e4dc'   # paper
TEXT_DIM = '#9c968a'
TEXT_MUTE= '#6e6a62'

fig, ax = plt.subplots(figsize=(12.8, 6.4), dpi=100)
ax.set_xlim(0, 1280)
ax.set_ylim(0, 640)
ax.invert_yaxis()
ax.axis('off')

# --- background: solid warm ink, no gradient glow ---
ax.add_patch(Rectangle((0, 0), 1280, 640, facecolor=BG, zorder=0))

# --- top border accent (ochre, 3px) ---
ax.add_patch(Rectangle((0, 0), 1280, 3, facecolor=PRIMARY, zorder=1))

# --- logo (recreate the new SVG: square corners, flat ochre bubble) ---
# document body — square corners
ax.add_patch(Rectangle((110, 180), 180, 230,
                       facecolor=BG_CARD, edgecolor=LINE_2, linewidth=2, zorder=2))
# folded corner (top-right of doc)
ax.fill([250, 290, 290], [180, 180, 220], color=LINE_2, zorder=3)
# text lines on document
for i, w in enumerate([100, 130, 75]):
    y = 230 + i * 32
    color = PRIMARY if i == 0 else TEXT_MUTE
    ax.add_patch(Rectangle((135, y), w, 5, facecolor=color, zorder=3))
# chat bubble — flat ochre, slight rounding only on the bubble
bubble = FancyBboxPatch((250, 320), 130, 110, boxstyle="round,pad=0,rounding_size=18",
                        facecolor=PRIMARY, edgecolor='none', zorder=3)
ax.add_patch(bubble)
# bubble tail (flat triangle, no round cap)
ax.fill([250, 235, 250], [350, 380, 370], color=PRIMARY, zorder=3)
# bubble dots (ink, not navy)
for dx in [0, 25, 50]:
    ax.add_patch(mpatches.Circle((275+dx, 375), 5, facecolor=BG, zorder=4))

# --- text (right of logo) ---
ax.text(360, 235, 'docubot', fontsize=68, color=TEXT, weight='bold',
        family='DejaVu Sans', zorder=5, va='center')
ax.text(365, 315, 'Self-hosted document chat with RAG over pgvector',
        fontsize=21, color=PRIMARY, family='DejaVu Sans', zorder=5, va='center')
ax.text(365, 355, 'One VPS · no Kubernetes · no cloud lock-in',
        fontsize=17, color=TEXT_DIM, family='DejaVu Sans', zorder=5, va='center')

# --- feature markers (bottom) — square-cornered, mono-styled, no rounded pills ---
markers = [
    ('PDF · Markdown · .txt', PRIMARY),
    ('pgvector + HNSW', OK),
    ('blue-green deploy', PRIMARY),
    ('cosign signed', OK),
    ('encrypted backups', PRIMARY),
    ('119 unit tests', OK),
]
marker_y = 500
marker_x = 110
marker_h = 36
marker_gap = 10
ax_font = fm.FontProperties(family='DejaVu Sans', size=12)
for i, (label, accent) in enumerate(markers):
    w = len(label) * 8.0 + 50
    if marker_x + w > 1170:
        marker_x = 110
        marker_y += 56
    # left accent bar (2px), square body
    ax.add_patch(Rectangle((marker_x, marker_y), 2, marker_h,
                           facecolor=accent, zorder=4))
    ax.add_patch(Rectangle((marker_x+2, marker_y), w-2, marker_h,
                           facecolor=BG_CARD, edgecolor=LINE, linewidth=1, zorder=4))
    ax.text(marker_x + w/2 + 1, marker_y + marker_h/2, label, color=TEXT,
            fontproperties=ax_font, ha='center', va='center', zorder=5)
    marker_x += w + marker_gap

# --- top-right: version badge (square, not pill) ---
badge_w = 180
ax.add_patch(Rectangle((1000, 70), badge_w, 50,
                       facecolor=PRIMARY, edgecolor='none', zorder=5))
ax.text(1000 + badge_w/2, 95, 'StackSmith v1.2.7', color=BG, fontsize=15, weight='bold',
        family='DejaVu Sans', ha='center', va='center', zorder=6)

plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
out = '/home/z/my-project/download/social-preview.png'
fig.savefig(out, dpi=100, facecolor=BG, bbox_inches='tight', pad_inches=0)
print(f"saved {out}")
import os
print(f"size: {os.path.getsize(out)//1024} KB")
