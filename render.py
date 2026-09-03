#!/usr/bin/env python3
"""Render the VISAGRU 10s promo (1080x1920, 30fps) and pipe to ffmpeg.
Also supports --sample to write a few PNG frames for inspection."""
import sys, subprocess, math, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
FPS = 30
DUR = 10.0
N = int(DUR * FPS)
A = "video_assets/"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

NAVY = (10, 27, 63)
NAVY_L = (28, 52, 110)
RED = (200, 16, 46)
GREEN = (0, 156, 59)
YELLOW = (255, 205, 0)
WHITE = (255, 255, 255)

def clamp(v, lo, hi): return max(lo, min(hi, v))
def smooth(t): t = clamp(t, 0, 1); return t * t * (3 - 2 * t)
def ease_t(t, a, b): return smooth((t - a) / (b - a))


def load_rgba(p):
    im = Image.open(A + p).convert("RGBA"); return im


# ---------- pre-rendered elements ----------
def make_mascot_card():
    im = Image.open(A + "mascote.png").convert("RGB")
    iw, ih = im.size                      # 900x1600
    cw, ch = 760, 980
    # scale by width, then crop a vertical window keeping the face
    scale = cw / iw
    nh = int(ih * scale)                  # 1351
    im2 = im.resize((cw, nh), Image.LANCZOS)
    # face is near 18%..40%; choose crop so we show face + torso
    top = int(nh * 0.14)
    bottom = top + ch
    if bottom > nh: bottom = nh
    top = max(0, bottom - ch)
    im2 = im2.crop((0, top, cw, top + ch))
    # rounded card with border
    rad = 40
    card = Image.new("RGBA", (cw + 40, ch + 40), (0, 0, 0, 0))
    mask = Image.new("L", (cw + 40, ch + 40), 0)
    ImageDraw.Draw(mask).rounded_rectangle([20, 20, cw + 20, ch + 20], radius=rad, fill=255)
    # soft shadow
    sh = Image.new("RGBA", (cw + 60, ch + 60), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([10, 14, cw + 46, ch + 50], radius=rad, fill=(0, 0, 0, 120))
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    card.alpha_composite(sh.crop((0, 0, cw + 40, ch + 40)))
    # photo
    photo = Image.new("RGBA", (cw + 40, ch + 40), (0, 0, 0, 0))
    photo.paste(im2, (20, 20))
    card.paste(photo, (0, 0), mask)
    # border
    ImageDraw.Draw(card).rounded_rectangle([20, 20, cw + 20, ch + 20], radius=rad,
                                           outline=NAVY_L, width=10)
    ImageDraw.Draw(card).rounded_rectangle([24, 24, cw + 16, ch + 16], radius=rad - 4,
                                           outline=(255, 205, 0, 255), width=4)
    # bottom gradient for legibility
    return card


def make_rounded(img, rad, border=None):
    w, h = img.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=rad, fill=255)
    out.paste(img, (0, 0), m)
    if border:
        ImageDraw.Draw(out).rounded_rectangle([0, 0, w - 1, h - 1], radius=rad, outline=border, width=8)
    return out


CARD = make_mascot_card()
PLANE = load_rgba("plane_visagru.png")
FLAG = load_rgba("flag_br_usa.png")
LOGO = load_rgba("visagru_logo_sem_fundo.png")
PBR = load_rgba("passport_br.png")
PUS = load_rgba("passport_usa.png")
WA = load_rgba("whatsapp.png")

# logo (transparent version) -> scale for end card
LOGO_BIG = LOGO.resize((int(LOGO.width * 1.05), int(LOGO.height * 1.05)), Image.LANCZOS)
FLAG_BACK = FLAG.resize((W, int(FLAG.height * W / FLAG.width)), Image.LANCZOS)
FLAG_BACK = FLAG_BACK.filter(ImageFilter.GaussianBlur(2))


def make_endcard():
    """One cohesive end card: dim flag background + centred logo, single gold frame."""
    fw, fh = 940, 960
    card = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    # navy rounded base
    ImageDraw.Draw(card).rounded_rectangle([0, 0, fw - 1, fh - 1], radius=46,
                                           fill=(4, 10, 26, 245))
    # flag as a dim blurred banner across the middle
    fb = FLAG_BACK.copy()
    fs = min(fw / fb.width, (fh * 0.62) / fb.height)
    fb = fb.resize((int(fb.width * fs), int(fb.height * fs)), Image.LANCZOS)
    fb = fb.filter(ImageFilter.GaussianBlur(3))
    # darken flag (keep it clearly readable)
    dark = Image.new("RGBA", fb.size, (6, 12, 30, 88))
    fb.alpha_composite(dark)
    mask = Image.new("L", (fw, fh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, fw - 1, fh - 1], radius=46, fill=255)
    fbx = int((fw - fb.width) // 2)
    fby = int((fh * 0.34) - fb.height // 2)
    card.paste(fb, (fbx, fby), mask.crop((fbx, fby, fbx + fb.width, fby + fb.height)))
    # logo centred
    lw = int(LOGO.width * 0.80); lh = int(LOGO.height * 0.80)
    lg = LOGO.resize((lw, lh), Image.LANCZOS)
    # subtle dark glow behind logo for contrast
    glow = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([fw/2 - lw*0.62, fh/2 - lh*0.62, fw/2 + lw*0.62, fh/2 + lh*0.62],
                                 fill=(0, 0, 0, 120))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    card.alpha_composite(glow)
    card.alpha_composite(lg, (int(fw/2 - lw/2), int(fh/2 - lh/2)))
    # single gold frame
    ImageDraw.Draw(card).rounded_rectangle([0, 0, fw - 1, fh - 1], radius=46, outline=YELLOW, width=7)
    return card


END_CARD = make_endcard()


def draw_background(d, t):
    # vertical gradient
    for y in range(H):
        f = y / H
        r = int(NAVY[0] + (8 - NAVY[0]) * f)
        g = int(NAVY[1] + (14 - NAVY[1]) * f)
        b = int(NAVY[2] + (40 - NAVY[2]) * f)
        d.line([(0, y), (W, y)], fill=(r, g, b))
    # soft radial glow upper-middle
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i in range(40, 0, -1):
        a = int(22 * (i / 40))
        gd.ellipse([540 - i * 14, 560 - i * 14, 540 + i * 14, 560 + i * 14], fill=(70, 120, 220, a))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    return glow


def text_layer(txt, size, fill, font=FONT_B, stroke=None, sw=0):
    f = ImageFont.truetype(font, size)
    bbox = f.getbbox(txt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 8
    im = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im)
    if stroke:
        dd.text((pad, pad - bbox[1]), txt, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)
    else:
        dd.text((pad, pad - bbox[1]), txt, font=f, fill=fill)
    return im


def paste_center(canvas, im, cx=None, cy=None, alpha=None):
    canvas = canvas  # helper returns new
    if alpha is not None:
        im = im.copy(); im.putalpha(im.split()[3].point(lambda a: int(a * alpha)))
    if cx is None: cx = W // 2
    if cy is None: cy = H // 2
    local = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    local.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)
    return local


def frame(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    glow = draw_background(d, t)
    img.alpha_composite(glow)

    # subtle drifting clouds
    for i in range(6):
        cx = int(((i * 320 + t * 18) % (W + 500)) - 250)
        cy = 120 + i * 300
        c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(c).ellipse([cx - 180, cy - 40, cx + 180, cy + 40], fill=(120, 160, 220, 26))
        img.alpha_composite(c)

    # -------- elements timeline --------
    # Mascot card: slide+fade in over 1.2s, gentle float, fade out before logo reveal
    fIn = ease_t(t, 0.05, 1.15)
    fOut = 1 - ease_t(t, 7.4, 8.2)
    cardA = fIn * fOut
    cardY = int(880 + (1 - fIn) * 90)
    cardX = 540
    float_ = math.sin(t * 1.5) * 6
    card = CARD.copy()
    # resize card slightly at intro
    sc = 0.94 + 0.06 * fIn
    card = card.resize((int(card.width * sc), int(card.height * sc)), Image.LANCZOS)
    if cardA > 0:
        aa = card.copy(); aa.putalpha(aa.split()[3].point(lambda a: int(a * cardA)))
        img.alpha_composite(aa, (int(cardX - aa.width / 2), int(cardY + float_ - aa.height / 2)))

    # -------- segment 2: plane + passports (1.3s–5.4s) --------
    if 1.1 <= t <= 5.6:
        # passports bob below card, tilt slightly
        po = math.sin(t * 2.2) * 10
        pbr = PBR.resize((int(PBR.width * 0.62), int(PBR.height * 0.62)), Image.LANCZOS)
        pus = PUS.resize((int(PUS.width * 0.62), int(PUS.height * 0.62)), Image.LANCZOS)
        # pulse passports when plane passes them
        planeMid = 0.5 * (1.1 + 5.6)
        prox = max(0, 1 - abs(t - 3.4) / 1.1)
        scp = 1 + 0.10 * prox
        pbr = pbr.resize((int(pbr.width * scp), int(pbr.height * scp)), Image.LANCZOS)
        pus = pus.resize((int(pus.width * scp), int(pus.height * scp)), Image.LANCZOS)
        pbr = pbr.rotate(-8 + po * 0.4, expand=True, resample=Image.BICUBIC)
        pus = pus.rotate(8 - po * 0.4, expand=True, resample=Image.BICUBIC)
        img.alpha_composite(pbr, (int(430 - pbr.width / 2), int(1330 + po - pbr.height / 2)))
        img.alpha_composite(pus, (int(650 - pus.width / 2), int(1330 - po - pus.height / 2)))

    # plane flies across in segment 2, dipping near passports (centered)
    if 1.2 <= t <= 5.5:
        seg_t = ease_t(t, 1.2, 5.5)
        px = -0.20 * W + seg_t * 1.55 * W      # center x
        base_y = 820
        dip = math.sin(seg_t * math.pi) * 150
        py = base_y + dip
        bob = math.sin(t * 6) * 10
        angle = -dip * 0.05 - 6 * math.cos(seg_t * math.pi)
        p = PLANE.copy()
        s = 0.55
        p = p.resize((int(p.width * s), int(p.height * s)), Image.LANCZOS)
        p = p.rotate(angle, expand=True, resample=Image.BICUBIC)
        img.alpha_composite(p, (int(px - p.width / 2), int(py + bob - p.height / 2)))

    # -------- headline text (top banner) --------
    def cap(txt, size, y, alpha, color=WHITE, stroke=NAVY, sw=6):
        tl = text_layer(txt, size, color, FONT_B, stroke, sw)
        if alpha > 0.01:
            tl2 = tl.copy(); tl2.putalpha(tl2.split()[3].point(lambda a: int(a * alpha)))
            img.alpha_composite(tl2, (W // 2 - tl2.width // 2, int(y)))

    # Segment 1 headline
    a1 = ease_t(t, 0.25, 0.9) * (1 - ease_t(t, 1.0, 1.35))
    cap("Pensou em tirar visto?", 74, 150, a1)
    # Segment 2 headline
    a2 = ease_t(t, 1.7, 2.4) * (1 - ease_t(t, 5.4, 5.9))
    cap("Vem para a VISAGRU!", 82, 172, a2, color=YELLOW)
    # Segment 3 headline (voiceover)
    a3 = ease_t(t, 5.8, 6.5) * (1 - ease_t(t, 8.3, 8.8))
    cap("Nos chame no WhatsApp!", 70, 172, a3, color=WHITE)

    # WhatsApp icon in segment 3
    if a3 > 0:
        ic = WA.resize((int(WA.width * 0.26), int(WA.height * 0.26)), Image.LANCZOS)
        ic2 = ic.copy(); ic2.putalpha(ic2.split()[3].point(lambda a: int(a * a3)))
        img.alpha_composite(ic2, (W // 2 - ic2.width // 2, 252))

    # -------- segment 4: logo reveal + flag + CTA (8.6s–10.0s) --------
    a4 = ease_t(t, 8.55, 9.15)
    if a4 > 0:
        lsc = 0.7 + 0.3 * ease_t(t, 8.6, 9.7)
        ec = END_CARD.resize((int(END_CARD.width * lsc), int(END_CARD.height * lsc)), Image.LANCZOS)
        ec2 = ec.copy(); ec2.putalpha(ec2.split()[3].point(lambda a: int(a * a4)))
        img.alpha_composite(ec2, (W // 2 - ec2.width // 2, int(H * 0.40) - int(ec2.height * 0.5)))

        # CTA text + whatsapp
        a5 = ease_t(t, 9.0, 9.6)
        cap("Chame no WhatsApp!", 64, int(H * 0.84), a5, color=WHITE)
        if a5 > 0:
            ic = WA.resize((int(WA.width * 0.28), int(WA.height * 0.28)), Image.LANCZOS)
            ic2 = ic.copy(); ic2.putalpha(ic2.split()[3].point(lambda a: int(a * a5)))
            img.alpha_composite(ic2, (W // 2 - ic2.width // 2, int(H * 0.93)))

    # bottom small brand watermark
    cap("VISAGRU", 46, H - 70, ease_t(t, 0.4, 1.0) * (1 - ease_t(t, 7.6, 8.4)), color=(200, 210, 235))

    # fade to black at the very end
    fo = ease_t(t, 9.6, 10.0)
    if fo > 0:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fo)))
        img.alpha_composite(ov)

    return img.convert("RGB")


if __name__ == "__main__":
    if "--sample" in sys.argv:
        os.makedirs("video_assets/samples", exist_ok=True)
        for ts in (0.6, 2.2, 3.4, 6.2, 9.2):
            frame(ts).save(f"video_assets/samples/f_{ts}.png")
        print("samples written")
        sys.exit(0)

    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-f", "rawvideo", "-v", "error",
         "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
         "-preset", "medium", "-movflags", "+faststart",
         "video_assets/visagru_video.mp4"],
        stdin=subprocess.PIPE)
    for i in range(N):
        t = i / FPS
        proc.stdin.write(frame(t).convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    print("encoded", proc.returncode)
