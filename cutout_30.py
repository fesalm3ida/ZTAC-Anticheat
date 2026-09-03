#!/usr/bin/env python3
"""Cut the mascot out of the street background using border-seeded region growing."""
import sys
from collections import deque
import numpy as np
from PIL import Image, ImageFilter, ImageOps

SRC = "video_assets/mascote.png"
OUT = "video_assets/mascote_cut_30.png"

img = Image.open(SRC).convert("RGB")
W, H = img.size
print("source", W, H)

# Work at a reduced resolution for the mask, then upscale.
MW = 360
scale = MW / float(W)
MH = int(round(H * scale))
small = img.resize((MW, MH), Image.LANCZOS)
a = np.asarray(small).astype(np.int16)

h, w, _ = a.shape

def colordist(px, p):
    return abs(int(px[0]) - int(p[0])) + abs(int(px[1]) - int(p[1])) + abs(int(px[2]) - int(p[2]))

# Foreground = subject. We grow the BACKGROUND from all border pixels,
# allowing expansion to neighbours whose colour is within TOL of the
# *current* pixel (region growing by local similarity). This handles a
# non-uniform background while stopping at the subject's strong outline.
TOL = int(sys.argv[1]) if len(sys.argv) > 1 else 42

# A pixel is a valid background-candidate if it is NOT obviously foreground.
# We only flood through low-contrast/bright background; but to be safe we let
# the similarity rule decide. Seed = all border pixels.
visited = np.zeros((h, w), dtype=bool)
q = deque()

for x in range(w):
    for y in (0, h - 1):
        if not visited[y, x]:
            visited[y, x] = True
            q.append((x, y))
for y in range(h):
    for x in (0, w - 1):
        if not visited[y, x]:
            visited[y, x] = True
            q.append((x, y))

# Also seed the four corners' surrounding region to help kick off.
while q:
    x, y = q.popleft()
    cx, cy, cz = int(a[y, x, 0]), int(a[y, x, 1]), int(a[y, x, 2])
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h and not visited[ny, nx]:
            nx_, ny_, nz_ = int(a[ny, nx, 0]), int(a[ny, nx, 1]), int(a[ny, nx, 2])
            if (abs(cx - nx_) + abs(cy - ny_) + abs(cz - nz_)) <= TOL:
                visited[ny, nx] = True
                q.append((nx, ny))

# mask: background=True (to be removed). Convert to PIL at reduced size.
mask = Image.fromarray((visited * 255).astype('uint8'), 'L')
# Clean up: remove tiny specks of background that stay, dilate background a
# little to eat the outline, then blur (feather).
mask = mask.filter(ImageFilter.MaxFilter(3))   # grow background / smooth
mask = mask.filter(ImageFilter.MinFilter(3))   # remove noise islands
mask = mask.filter(ImageFilter.GaussianBlur(2.0))

# Upscale mask to full size, feather.
mask = mask.resize((W, H), Image.LANCZOS)
mask = mask.filter(ImageFilter.GaussianBlur(1.5))

# Composite: where mask is bright -> background transparent.
bg = np.asarray(mask).astype(np.float32) / 255.0  # 1 = background
alpha = (1.0 - bg)
rgba = img.convert("RGBA")
ra = np.asarray(rgba).copy()
ra[:, :, 3] = (np.asarray(img.convert("RGBA"))[:, :, 3] * alpha).astype('uint8')
Image.fromarray(ra, 'RGBA').save(OUT)
print("saved", OUT, "tol", TOL)

# Quick stats
fg = (alpha > 0.6).mean()
print("fg fraction:", round(float(fg), 3))
