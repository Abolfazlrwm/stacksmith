"""Generate a GitHub social preview image (1280x640 PNG).

GitHub's social preview is what shows when someone links the repo on
Twitter, LinkedIn, or in GitHub's own discovery surfaces. It must be
1280x640 PNG. We compose:
  - the app's dark navy gradient background
  - the docubot logo (left)
  - the product name + tagline (center)
  - a row of feature pills (right/bottom)
"""
import matplotlib.font_manager as fm
fm.fontManager.addfont('/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf')
fm.fontManager.addfont('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

plt.rcParams['font.sans-serif'] = ['Noto Sans SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(figsize=(12.8, 6.4), dpi=100)
ax.set_xlim(0, 1280)
ax.set_ylim(0, 640)
ax.invert_yaxis()
ax.axis('off')

# --- background gradient (navy) ---
grad = np.zeros((640, 1280, 3))
for y in range(640):
    t = y / 640
    # top: #0B1220, bottom: #131C2E
    grad[y, :, 0] = 0x0B/255 + t * (0x13 - 0x0B)/255
    grad[y, :, 1] = 0x12/255 + t * (0x1C - 0x12)/255
    grad[y, :, 2] = 0x20/255 + t * (0x2E - 0x20)/255
# radial glow top-right (sky blue)
yy, xx = np.mgrid[0:640, 0:1280]
glow = np.exp(-((xx-1050)**2 + (yy-150)**2) / (2*350**2))
grad[..., 0] += glow * 0.05
grad[..., 1] += glow * 0.08
grad[..., 2] += glow * 0.10
grad = np.clip(grad, 0, 1)
ax.imshow(grad, extent=[0, 1280, 640, 0], aspect='auto', zorder=0)

# --- logo (recreate the SVG shape with patches) ---
# document body
doc = FancyBboxPatch((110, 180), 180, 230, boxstyle="round,pad=0,rounding_size=8",
                     facecolor='#18233A', edgecolor='#334155', linewidth=2, zorder=2)
ax.add_patch(doc)
# folded corner
ax.fill([250, 290, 290], [180, 180, 220], color='#334155', zorder=3)
# text lines on document
for i, w in enumerate([100, 130, 75]):
    y = 230 + i * 32
    color = '#38BDF8' if i == 0 else '#64748B'
    ax.add_patch(mpatches.Rectangle((135, y), w, 6, facecolor=color, zorder=3))
# chat bubble
bubble = FancyBboxPatch((250, 320), 130, 110, boxstyle="round,pad=0,rounding_size=30",
                        facecolor='#38BDF8', edgecolor='none', zorder=3)
ax.add_patch(bubble)
ax.plot([250, 235, 250], [350, 380, 370], color='#38BDF8', linewidth=4, zorder=3, solid_capstyle='round')
for dx in [0, 25, 50]:
    ax.add_patch(mpatches.Circle((275+dx, 375), 5, facecolor='#0B1220', zorder=4))
# live dot
ax.add_patch(mpatches.Circle((310, 195), 12, facecolor='#34D399', zorder=5))
ax.add_patch(mpatches.Circle((310, 195), 18, facecolor='none', edgecolor='#34D399', linewidth=1.5, alpha=0.4, zorder=5))

# --- text (right of logo) ---
ax.text(360, 240, 'docubot', fontsize=72, color='#E2E8F0', weight='bold',
        family='DejaVu Sans', zorder=5, va='center')
ax.text(365, 320, 'Self-hosted document chat with RAG over pgvector',
        fontsize=22, color='#38BDF8', family='DejaVu Sans', zorder=5, va='center')
ax.text(365, 360, 'One VPS · no Kubernetes · no cloud lock-in',
        fontsize=18, color='#94A3B8', family='DejaVu Sans', zorder=5, va='center')

# --- feature pills (bottom) ---
pills = ['PDF · Markdown · .txt', 'pgvector + HNSW', 'blue-green deploy',
         'cosign signed', 'encrypted backups', '119 unit tests']
pill_y = 510
pill_x = 110
pill_h = 42
pill_pad = 12
ax_font = fm.FontProperties(family='DejaVu Sans', size=13)
for i, p in enumerate(pills):
    w = len(p) * 8.5 + 40
    if pill_x + w > 1170:
        pill_x = 110
        pill_y += 60
    pill = FancyBboxPatch((pill_x, pill_y), w, pill_h,
                          boxstyle="round,pad=0,rounding_size=21",
                          facecolor='#18233A', edgecolor='#334155', linewidth=1.5, zorder=4)
    ax.add_patch(pill)
    ax.text(pill_x + w/2, pill_y + pill_h/2, p, color='#E2E8F0',
            fontproperties=ax_font, ha='center', va='center', zorder=5)
    pill_x += w + pill_pad

# --- top-right: StackSmith badge ---
badge = FancyBboxPatch((1000, 70), 170, 50, boxstyle="round,pad=0,rounding_size=25",
                       facecolor='#0EA5E9', edgecolor='none', zorder=5)
ax.add_patch(badge)
ax.text(1085, 95, 'StackSmith v1.2.6', color='#0B1220', fontsize=15, weight='bold',
        family='DejaVu Sans', ha='center', va='center', zorder=6)

plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
fig.savefig('/home/z/my-project/download/social-preview.png', dpi=100,
            facecolor='#0B1220', bbox_inches='tight', pad_inches=0)
print("saved /home/z/my-project/download/social-preview.png")
import os
print(f"size: {os.path.getsize('/home/z/my-project/download/social-preview.png')//1024} KB")
