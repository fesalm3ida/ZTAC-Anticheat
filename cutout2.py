#!/usr/bin/env python3
"""Cut the mascot out with FOREGROUND seeded from the body (center) and grown
by local colour similarity. Keeps head+torso and stops at the background."""
import sys
from collections import deque
import numpy as np
from PIL import Image, ImageFilter

SRC = "video_assets/mascote.png"
OUT = "video_assets/mascote_cut.png"

img = Image.open(SRC).convert("RGB")
W, H = img.size

MW = 300
scale = MW / float(W)
MH = int(round(H * scale))
small = img.resize((MW, MH), Image.LANCZOS)
a = np.asarray(small).astype(np.int16)
h, w, _ = a.shape

TOL = int(sys.argv[1]) if len(sys.argv) > 1 else 40

# Foreground seeds: a vertical run down the centre through the body.
seeds = []
for fy in np.linspace(0.15, 0.92, 40):        # 15%..92% height
    y = int(fy * (h - 1))
    for fx in np.linspace(0.30, 0.70, 7):     # central horizontal band
        x = int(fx * (w - 1))
        if 0 <= y < h and 0 <= x < w:
            seeds.append((x, y))

fg = np.zeros((h, w), dtype=bool)
q = deque()
for (x, y) in seeds:
    if not fg[y, x]:
        fg[y, x] = True
        q.append((x, y))

while q:
    x, y = q.popleft()
    cx, cy, cz = int(a[y, x, 0]), int(a[y, x, 1]), int(a[y, x, 2])
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h and not fg[ny, nx]:
            nx_, ny_, nz_ = int(a[ny, nx, 0]), int(a[ny, nx, 1]), int(a[ny, nx, 2])
            if (abs(cx - nx_) + abs(cy - ny_) + abs(cz - nz_)) <= TOL:
                fg[ny, nx] = True
                q.append((nx, ny))

mask = Image.fromarray((fg * 255).astype('uint8'), 'L')
mask = mask.filter(ImageFilter.MaxFilter(3))
mask = mask.filter(ImageFilter.MinFilter(3))
mask = mask.filter(ImageFilter.GaussianBlur(1.5))
mask = mask.resize((W, H), Image.LANCZOS)
mask = mask.filter(ImageFilter.GaussianBlur(1.2))

bg = np.asarray(mask).astype(np.float32) / 255.0
rgba = np.asarray(img.convert("RGBA")).copy()
rgba[:, :, 3] = (rgba[:, :, 3].astype(np.float32) * bg).astype('uint8')
Image.fromarray(rgba, 'RGBA').save(OUT)
print("saved", OUT, "tol", TOL, "fg frac", round(float((bg > 0.6).mean()), 3))
