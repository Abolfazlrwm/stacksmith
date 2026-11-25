"""Compress and crop screenshots for README.

The agent-browser screenshots are 1280px wide full-page PNGs at ~900KB
each — too big and too tall to embed in a README. We:
  - hero (showcase-top.png): keep as-is, it's already viewport-sized.
  - chat crop: the live chat pane after a question was asked.
  - arch crop: the architecture section.
"""
from PIL import Image
import os

SRC = "docs/screenshots"
OUT = "docs/screenshots"


def compress(im: Image.Image, max_w: int = 1100, quality: int = 78) -> Image.Image:
    """Resize to max_w (preserving aspect) and re-encode."""
    if im.width > max_w:
        h = int(im.height * max_w / im.width)
        im = im.resize((max_w, h), Image.LANCZOS)
    return im


# 1. hero (top viewport) — already small, just compress to jpeg
hero = Image.open(f"{SRC}/showcase-top.png").convert("RGB")
hero = compress(hero, max_w=1100)
hero.save(f"{OUT}/hero.jpg", quality=80, optimize=True)
print(f"hero.jpg: {hero.size} {os.path.getsize(f'{OUT}/hero.jpg')//1024}KB")

# 2. chat crop — from the full-page (post-click) image, crop the product section
#    The hero is ~577px tall; the product section (chat + code side by side)
#    runs roughly from y=580 to y=1700.
full = Image.open(f"{SRC}/showcase-chat.png").convert("RGB")
chat_crop = full.crop((0, 580, 1280, 1720))
chat_crop = compress(chat_crop, max_w=1100)
chat_crop.save(f"{OUT}/chat-and-code.jpg", quality=78, optimize=True)
print(f"chat-and-code.jpg: {chat_crop.size} {os.path.getsize(f'{OUT}/chat-and-code.jpg')//1024}KB")

# 3. arch crop — find the architecture section. It's ~mid-page.
#    From the full image, the arch section starts around y=3800.
arch_crop = full.crop((0, 3700, 1280, 4600))
arch_crop = compress(arch_crop, max_w=1100)
arch_crop.save(f"{OUT}/architecture.jpg", quality=78, optimize=True)
print(f"architecture.jpg: {arch_crop.size} {os.path.getsize(f'{OUT}/architecture.jpg')//1024}KB")

# 4. security crop — the upload validation demo + checklist
sec_crop = full.crop((0, 2400, 1280, 3500))
sec_crop = compress(sec_crop, max_w=1100)
sec_crop.save(f"{OUT}/security.jpg", quality=78, optimize=True)
print(f"security.jpg: {sec_crop.size} {os.path.getsize(f'{OUT}/security.jpg')//1024}KB")

# cleanup the big raw files
for raw in ["showcase-full.png", "showcase-chat.png", "showcase-top.png"]:
    p = f"{SRC}/{raw}"
    if os.path.exists(p):
        os.remove(p)
        print(f"removed {raw}")
