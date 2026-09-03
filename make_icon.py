#!/usr/bin/env python3
"""Clean classic WhatsApp-style icon."""
import math
from PIL import Image, ImageDraw

S = 520
R = S / 2
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
GREEN = (37, 211, 102)
GREEN_D = (18, 120, 60)

# green circle
d.ellipse([8, 8, S - 8, S - 8], fill=GREEN, outline=GREEN_D, width=8)

cx, cy = R, R
# white speech bubble (filled rounded rect) with tail
bw, bh = R * 0.98, R * 1.14
bx0, by0 = cx - bw / 2, cy - bh * 0.68
bx1, by1 = cx + bw / 2, cy + bh * 0.46
d.rounded_rectangle([bx0, by0, bx1, by1], radius=R * 0.22, fill=(255, 255, 255))
# tail (bottom-left)
d.polygon([(bx0 + bw * 0.10, by1 - 2), (bx0 - bw * 0.06, by1 + bh * 0.40),
           (bx0 + bw * 0.40, by1 - 2)], fill=(255, 255, 255))

# green phone handset (curved) inside the bubble
hx, hy = cx, cy - bh * 0.08
hw = bw * 0.30
d.arc([hx - hw, hy - hw * 0.9, hx + hw, hy + hw * 0.9], start=30, end=150,
      fill=GREEN, width=int(S * 0.052))
for a in (40, 140):
    ax = hx + math.cos(math.radians(a)) * hw
    ay = hy + math.sin(math.radians(a)) * hw * 0.9
    d.ellipse([ax - 14, ay - 14, ax + 14, ay + 14], fill=GREEN)

img.save("video_assets/whatsapp.png")
print("whatsapp icon rebuilt", img.size)
