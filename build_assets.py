#!/usr/bin/env python3
"""Generate branded assets: combined Brazil+USA flag and a VISAGRU-coloured
stylized airplane (transparent PNG)."""
from PIL import Image, ImageDraw, ImageColor

# ---- Brand colours (from the VISAGRU logo) ----
NAVY = (0, 48, 135)
RED = (200, 16, 46)
GREEN = (0, 156, 59)
YELLOW = (255, 205, 0)
BLUE_BR = (0, 39, 118)      # Brazil blue globe
GREEN_BR = (0, 156, 59)
YELLOW_BR = (255, 223, 0)
USA_RED = (178, 34, 52)
USA_BLUE = (60, 59, 110)
WHITE = (255, 255, 255)


def draw_brazil(d, x0, y0, w, h):
    d.rectangle([x0, y0, x0 + w, y0 + h], fill=GREEN_BR)
    ct = (x0 + w / 2, y0 + h / 2)
    # yellow rhombus
    d.polygon([(ct[0], y0 + h * 0.12), (x0 + w * 0.92, ct[1]),
               (ct[0], y0 + h * 0.88), (x0 + w * 0.08, ct[1])], fill=YELLOW_BR)
    r = h * 0.30
    # blue globe
    d.ellipse([ct[0] - r, ct[1] - r * 0.82, ct[0] + r, ct[1] + r * 0.82], fill=BLUE_BR)
    # white band (diagonal)
    band = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    bd.polygon([(ct[0] - r * 0.95, ct[1] + r * 0.42),
                (ct[0] + r * 0.95, ct[1] - r * 0.42),
                (ct[0] + r * 0.95, ct[1] - r * 0.05),
                (ct[0] - r * 0.95, ct[1] + r * 0.80)], fill=WHITE)
    d.bitmap((x0, y0), band, fill=WHITE)
    # stars (a few dots)
    for i in range(6):
        ang = 3.14 * 2 * i / 6
        sx = ct[0] + 0.62 * r * min(1, (1.0 if i % 2 else 0.72)) * 0
        # place dots along band
        d.ellipse([ct[0] - 2 + 8 * (i - 3), ct[1] - 2 + (8 if i % 2 else -8),
                   ct[0] + 2 + 8 * (i - 3), ct[1] + 2 + (8 if i % 2 else -8)], fill=WHITE)


def draw_usa(d, x0, y0, w, h):
    stripes = 13
    sh = h / stripes
    for i in range(stripes):
        col = USA_RED if i % 2 == 0 else WHITE
        d.rectangle([x0, y0 + i * sh, x0 + w, y0 + (i + 1) * sh], fill=col)
    cw = w * 0.40
    ch = sh * 7
    d.rectangle([x0, y0, x0 + cw, y0 + ch], fill=USA_BLUE)
    # stars grid
    import math
    for row in range(5):
        for col in range(6):
            sx = x0 + cw * (col + 1) / 7
            sy = y0 + ch * (row + 1) / 6
            r = min(cw, ch) / 18
            for k in range(5):
                ang = math.pi / 2 + k * 2 * math.pi / 5
                # simple 5-point star
                d.ellipse([sx - r / 1.6, sy - r / 1.6, sx + r / 1.6, sy + r / 1.6], fill=WHITE)


def make_flag():
    # Combined flag: Brazil (left) + USA (right), 16:9-ish
    FW, FH = 1600, 900
    img = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    draw_brazil(d, 0, 0, FW // 2, FH)
    draw_usa(d, FW // 2, 0, FW // 2, FH)
    img.save("video_assets/flag_br_usa.png")
    print("flag", img.size)


def draw_plane():
    # Stylized commercial jet pointing RIGHT, VISAGRU logo colours, transparent.
    W, H = 1000, 400
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    top, bot = 180, 238            # fuselage top/bottom (a smooth capsule)
    nose_r = 26

    # ---- fuselage: capsule (rounded ends) ----
    d.rounded_rectangle([82, top, 900, bot], radius=nose_r,
                        fill=WHITE, outline=(20, 30, 60), width=3)

    # ---- colour bands along the fuselage (clip to body) ----
    # green (tail) | red (middle) | blue (nose)
    bands = [
        (82, 300, GREEN), (300, 560, RED), (560, 900, NAVY),
    ]
    for x0, x1, col in bands:
        d.polygon([(x0, top), (x1, top), (x1, bot), (x0, bot)], fill=col)
    # re-stroke body outline on top of bands
    d.rounded_rectangle([82, top, 900, bot], radius=nose_r, outline=(20, 30, 60), width=3)
    # yellow pinstripe along the body
    d.line([(120, top + 7), (880, top + 7)], fill=YELLOW, width=4)

    # ---- swept wing (red, yellow accent) pointing back-down ----
    d.polygon([(478, 205), (588, 212), (400, 360), (368, 320)],
              fill=RED, outline=(20, 30, 60), width=2)
    d.polygon([(492, 222), (560, 226), (432, 330), (408, 306)],
              fill=YELLOW, outline=(20, 30, 60), width=1)

    # ---- tail fin (green + yellow) ----
    d.polygon([(150, 192), (238, 192), (162, 70)], fill=GREEN, outline=(20, 30, 60), width=2)
    d.polygon([(168, 188), (216, 188), (170, 108)], fill=YELLOW, outline=(20, 30, 60), width=1)

    # ---- engine pod (blue) + cockpit ----
    d.rounded_rectangle([452, 250, 570, 300], radius=10, fill=NAVY, outline=(20, 30, 60), width=2)
    d.ellipse([790, 192, 872, 226], fill=(150, 190, 240, 255), outline=(20, 30, 60), width=1)

    img = img.crop((70, 40, 930, 390))
    img.save("video_assets/plane_visagru.png")
    print("plane", img.size)


if __name__ == "__main__":
    make_flag()
    draw_plane()
