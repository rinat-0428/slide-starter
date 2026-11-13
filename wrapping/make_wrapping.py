#!/usr/bin/env python3
"""Chammi オリジナル包装紙 v2

- モチーフはピッチ資料表紙(cover-01.png)の線画を再現
- Poisson-disk(ブルーノイズ)配置で格子感をなくす
- 四六判 788x545mm / 300dpi の入稿データ(A案・B案)、シームレスタイル、
  メッセージカード(100x148mm)、包装モックアップを出力

usage: python3 make_wrapping.py            # 全部
       python3 make_wrapping.py preview    # 低解像度プレビューのみ
"""
import math, os, random, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FONT = os.path.join(HERE, "fonts", "montserrat-latin-800-normal.woff")
FONT_SUB = os.path.join(HERE, "fonts", "montserrat-latin-700-normal.woff")

DPI = 300
MM = DPI / 25.4                       # px per mm
BG = (250, 226, 229)                  # #FAE2E5
LINE = (231, 171, 184)                # #E7ABB8
LOGO_A = (35, 32, 33)                 # #232021
LOGO_B = (216, 130, 148)              # #D88294
SS = 3                                # supersampling for sprites

# ---------------------------------------------------------------- geometry
def bez(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        t = i / n; u = 1 - t
        out.append((u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0],
                    u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1]))
    return out

def ellipse_pts(cx, cy, rx, ry, a0=0, a1=2*math.pi, n=48):
    return [(cx + rx*math.cos(a0 + (a1-a0)*i/n), cy + ry*math.sin(a0 + (a1-a0)*i/n)) for i in range(n + 1)]

def rrect(x0, y0, x1, y1, r):
    p = []
    p += ellipse_pts(x1 - r, y0 + r, r, r, -math.pi/2, 0, 8)
    p += ellipse_pts(x1 - r, y1 - r, r, r, 0, math.pi/2, 8)
    p += ellipse_pts(x0 + r, y1 - r, r, r, math.pi/2, math.pi, 8)
    p += ellipse_pts(x0 + r, y0 + r, r, r, math.pi, 1.5*math.pi, 8)
    return p + [p[0]]

def rot(pts, ang, cx=0, cy=0):
    c, s = math.cos(ang), math.sin(ang)
    return [(cx + (x-cx)*c - (y-cy)*s, cy + (x-cx)*s + (y-cy)*c) for x, y in pts]

# Each motif returns a list of polylines in unit space [-1, 1]
def m_heart():
    p = []
    for i in range(73):
        t = i / 72 * 2 * math.pi
        x = 16 * math.sin(t)**3
        y = 13*math.cos(t) - 5*math.cos(2*t) - 2*math.cos(3*t) - math.cos(4*t)
        p.append((x / 18, -y / 18 + 0.05))
    return [p]

def m_sparkle():
    p = []; n = 0.62
    for i in range(121):
        t = i / 120 * 2 * math.pi
        c, s = math.cos(t), math.sin(t)
        x = math.copysign(abs(c) ** (2/n), c) * 0.78
        y = math.copysign(abs(s) ** (2/n), s) * 0.95
        p.append((x, y))
    return [p]

def m_star():
    p = []
    for i in range(10):
        a = -math.pi/2 + i * math.pi / 5
        r = 0.95 if i % 2 == 0 else 0.42
        p.append((r*math.cos(a), r*math.sin(a) + 0.08))
    # soften tips a bit by small bezier rounding
    out = []
    for i in range(10):
        a, b, c = p[i-1], p[i], p[(i+1) % 10]
        if i % 2 == 0:
            k = 0.12
            q0 = (b[0] + (a[0]-b[0])*k, b[1] + (a[1]-b[1])*k)
            q1 = (b[0] + (c[0]-b[0])*k, b[1] + (c[1]-b[1])*k)
            out += bez(q0, b, b, q1, 6)
        else:
            out.append(b)
    return [out + [out[0]]]

def m_crown():
    base = [(-0.72, 0.55), (-0.82, -0.25), (-0.38, 0.10), (0.0, -0.45),
            (0.38, 0.10), (0.82, -0.25), (0.72, 0.55)]
    body = base + [base[0]]
    band = [(-0.74, 0.32), (0.74, 0.32)]
    balls = [ellipse_pts(x, y - 0.13, 0.11, 0.11) for x, y in [(-0.82, -0.25), (0.0, -0.45), (0.82, -0.25)]]
    return [body, band] + balls

def m_flower():
    p = []
    for i in range(181):
        t = i / 180 * 2 * math.pi
        r = 0.55 + 0.38 * abs(math.cos(2.5 * (t + math.pi/2))) ** 0.6
        p.append((r * math.cos(t), r * math.sin(t)))
    return [p, ellipse_pts(0, 0, 0.22, 0.22)]

def m_bubble():
    body = ellipse_pts(0, -0.08, 0.92, 0.70, math.radians(118), math.radians(118 + 335), 60)
    tail = [body[-1], (-0.62, 0.78), body[0]]
    return [body, tail]

def m_bow():
    L = bez((-0.10, -0.02), (-0.45, -0.80), (-1.05, -0.60), (-0.95, -0.05), 22) + \
        bez((-0.95, -0.05), (-0.88, 0.32), (-0.45, 0.28), (-0.10, 0.06), 18)
    R = [(-x, y) for x, y in L]
    knot = rrect(-0.13, -0.15, 0.13, 0.17, 0.08)
    tl = [(-0.08, 0.17), (-0.42, 0.88), (-0.28, 0.80), (-0.20, 0.92), (0.02, 0.17)]
    tr = [(0.08, 0.17), (0.40, 0.86), (0.26, 0.80), (0.20, 0.92), (-0.02, 0.17)]
    return [L, R, knot, tl, tr]

def m_clapper():
    body = rrect(-0.80, -0.20, 0.80, 0.78, 0.08)
    bar = [(-0.80, -0.20), (-0.80, -0.42), (0.80, -0.42), (0.80, -0.20)]
    top = rot([(-0.80, -0.48), (-0.80, -0.70), (0.80, -0.70), (0.80, -0.48), (-0.80, -0.48)],
              math.radians(-16), -0.80, -0.45)
    stripes = []
    for i in range(4):
        x = -0.55 + i * 0.38
        stripes.append([(x, -0.20), (x + 0.20, -0.42)])
        s = rot([(x + 0.05, -0.48), (x + 0.25, -0.70)], math.radians(-16), -0.80, -0.45)
        stripes.append(s)
    lines = [[(-0.55, 0.15), (0.55, 0.15)], [(-0.55, 0.42), (0.35, 0.42)]]
    return [body, bar, top] + stripes + lines

def m_film():
    out = [rrect(-0.92, -0.62, 0.92, 0.62, 0.08), [(-0.55, -0.62), (-0.55, 0.62)], [(0.55, -0.62), (0.55, 0.62)]]
    for x in (-0.735, 0.735):
        for y in (-0.36, 0.0, 0.36):
            out.append(ellipse_pts(x, y, 0.075, 0.075, n=16))
    return out

def m_penlight():
    tube = rrect(-0.16, -0.62, 0.16, 0.30, 0.10)
    grip = rrect(-0.13, 0.30, 0.13, 0.92, 0.07)
    btn = [(0.0, 0.48), (0.0, 0.62)]
    rays = [[(0, -0.78), (0, -0.98)], [(-0.24, -0.72), (-0.38, -0.90)], [(0.24, -0.72), (0.38, -0.90)]]
    parts = [tube, grip, btn] + rays
    return [rot(p, math.radians(22)) for p in parts]

def m_lipstick():
    tip = [(-0.22, -0.10), (-0.22, -0.55), (0.22, -0.80), (0.22, -0.10)]
    sleeve = rrect(-0.30, -0.10, 0.30, 0.15, 0.04)
    case = rrect(-0.32, 0.15, 0.32, 0.92, 0.06)
    return [tip, sleeve, case]

MOTIFS = {
    "heart": m_heart, "sparkle": m_sparkle, "star": m_star, "crown": m_crown,
    "flower": m_flower, "bubble": m_bubble, "bow": m_bow, "clapper": m_clapper,
    "film": m_film, "penlight": m_penlight, "lipstick": m_lipstick,
}
# relative frequency (sparkles are the "filler" like the cover)
WEIGHTS = {"sparkle": 3, "heart": 2, "star": 1.4, "crown": 1, "flower": 1, "bubble": 1,
           "bow": 1, "clapper": 1, "film": 1, "penlight": 1, "lipstick": 0.6}
SIZE_MM = {"sparkle": (9, 14), "heart": (11, 15), "star": (12, 16)}   # others: default
DEFAULT_SIZE_MM = (15, 20)

_cache = {}
def sprite(name, size_px, angle_deg, color=LINE, line_ratio=0.052):
    key = (name, size_px, round(angle_deg, 1), color)
    if key in _cache:
        return _cache[key]
    S = size_px * SS
    pad = int(S * 0.15)
    img = Image.new("L", (S + 2*pad, S + 2*pad), 0)
    d = ImageDraw.Draw(img)
    w = max(2, int(size_px * line_ratio * SS))
    half = S / 2
    for poly in MOTIFS[name]():
        pts = [(pad + half + x * half * 0.92, pad + half + y * half * 0.92) for x, y in poly]
        d.line(pts, fill=255, width=w, joint="curve")
        r = w / 2
        for x, y in (pts[0], pts[-1]):          # round caps
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    img = img.rotate(angle_deg, resample=Image.BICUBIC, expand=True)
    img = img.resize((img.width // SS, img.height // SS), Image.LANCZOS)
    out = Image.new("RGBA", img.size, color + (0,))
    out.putalpha(img)
    _cache[key] = out
    return out

def wordmark(width_px, color, font=FONT, text="CHAMMI", tracking=0.02):
    f = ImageFont.truetype(font, 400)
    # render each letter with small tracking
    adv = [f.getlength(ch) for ch in text]
    track = 400 * tracking
    total = sum(adv) + track * (len(text) - 1)
    asc, desc = f.getmetrics()
    img = Image.new("L", (int(total) + 40, asc + desc + 40), 0)
    d = ImageDraw.Draw(img)
    x = 20
    for ch, a in zip(text, adv):
        d.text((x, 20), ch, font=f, fill=255)
        x += a + track
    img = img.crop(img.getbbox())
    h = int(img.height * width_px / img.width)
    img = img.resize((width_px, h), Image.LANCZOS)
    out = Image.new("RGBA", img.size, color + (0,))
    out.putalpha(img)
    return out

# ---------------------------------------------------------------- layout
def poisson(w, h, rmin, rnd, wrap, existing=(), k=30, max_pts=100000):
    """Bridson Poisson-disk sampling. existing: list of (x, y, r) obstacles."""
    cell = rmin / math.sqrt(2)
    gw, gh = int(math.ceil(w / cell)), int(math.ceil(h / cell))
    grid = {}
    pts = []
    def dist2(a, b):
        dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
        if wrap:
            dx, dy = min(dx, w - dx), min(dy, h - dy)
        return dx*dx + dy*dy
    def blocked(p):
        for ox, oy, orad in existing:
            if dist2(p, (ox, oy)) < orad * orad:
                return True
        return False
    def ok(p):
        if not wrap and not (0 <= p[0] < w and 0 <= p[1] < h):
            return False
        gx, gy = int(p[0] / cell), int(p[1] / cell)
        for ix in range(gx - 2, gx + 3):
            for iy in range(gy - 2, gy + 3):
                jx, jy = ix, iy
                if wrap:
                    jx %= gw; jy %= gh
                q = grid.get((jx, jy))
                if q is not None and dist2(p, q) < rmin * rmin:
                    return False
        return not blocked(p)
    def add(p):
        if wrap:
            p = (p[0] % w, p[1] % h)
        grid[(int(p[0] / cell) % gw if wrap else int(p[0] / cell),
              int(p[1] / cell) % gh if wrap else int(p[1] / cell))] = p
        pts.append(p); active.append(p)
    active = []
    for _ in range(200):
        p = (rnd.uniform(0, w), rnd.uniform(0, h))
        if ok(p):
            add(p); break
    while active and len(pts) < max_pts:
        i = rnd.randrange(len(active)); base = active[i]
        for _ in range(k):
            a = rnd.uniform(0, 2*math.pi); r = rnd.uniform(rmin, 2*rmin)
            p = (base[0] + r*math.cos(a), base[1] + r*math.sin(a))
            if wrap:
                p = (p[0] % w, p[1] % h)
            if ok(p):
                add(p); break
        else:
            active.pop(i)
    return pts

class Bag:
    """weighted shuffle-bag so the same motif doesn't cluster"""
    def __init__(self, rnd):
        self.rnd = rnd; self.items = []
    def next(self, avoid=()):
        if not self.items:
            pool = []
            for k, wgt in WEIGHTS.items():
                pool += [k] * int(round(wgt * 5))
            self.rnd.shuffle(pool); self.items = pool
        for i, it in enumerate(self.items):
            if it not in avoid:
                return self.items.pop(i)
        return self.items.pop()

def layout(w, h, seed, wrap, logo_w_mm=56, logo_gap_mm=118, motif_gap_mm=29):
    rnd = random.Random(seed)
    lw = logo_w_mm * MM
    # logos: Poisson with anisotropic distance (squash x so rows don't line up)
    lp = poisson(w / 1.25, h, logo_gap_mm * MM / 1.12, rnd, wrap)
    logos = [(x * 1.25, y) for x, y in lp]
    obstacles = []
    for x, y in logos:  # approximate logo rectangle with 3 circles
        for dx in (-0.36, -0.12, 0.12, 0.36):
            obstacles.append((x + dx * lw, y, lw * 0.30))
    pts = poisson(w, h, motif_gap_mm * MM, rnd, wrap, existing=obstacles)
    bag = Bag(rnd); motifs = []
    for x, y in pts:
        name = bag.next()
        lo, hi = SIZE_MM.get(name, DEFAULT_SIZE_MM)
        size = int(rnd.uniform(lo, hi) * MM)
        ang = rnd.uniform(-22, 22)
        motifs.append((name, x, y, size, ang))
    return logos, motifs

def render(w, h, logo_color, seed, wrap=False, logo=True, scale=1.0, **kw):
    """scale<1 renders a low-res preview of the same layout."""
    logos, motifs = layout(w, h, seed, wrap, **kw)
    W, H = int(w * scale), int(h * scale)
    img = Image.new("RGBA", (W, H), BG + (255,))
    def paste(spr, cx, cy):
        offs = [(0, 0)]
        if wrap:
            offs = [(dx, dy) for dx in (-W, 0, W) for dy in (-H, 0, H)]
        for dx, dy in offs:
            x0 = int(cx * scale + dx - spr.width / 2); y0 = int(cy * scale + dy - spr.height / 2)
            if x0 > W or y0 > H or x0 + spr.width < 0 or y0 + spr.height < 0:
                continue
            img.alpha_composite(spr, (x0, y0)) if (x0 >= 0 and y0 >= 0 and x0 + spr.width <= W and y0 + spr.height <= H) \
                else img.paste(spr, (x0, y0), spr)
    for name, x, y, size, ang in motifs:
        paste(sprite(name, max(8, int(size * scale)), round(ang)), x, y)
    if logo:
        lm = wordmark(int(kw.get("logo_w_mm", 56) * MM * scale), logo_color)
        for x, y in logos:
            paste(lm, x, y)
    return img.convert("RGB")

# ---------------------------------------------------------------- outputs
def save_pdf(img, path, w_mm, h_mm):
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    c = canvas.Canvas(path, pagesize=(w_mm * mm, h_mm * mm))
    c.drawImage(ImageReader(img), 0, 0, w_mm * mm, h_mm * mm)
    c.showPage(); c.save()

def sheet(variant, scale=1.0):
    color = LOGO_A if variant == "a" else LOGO_B
    seed = 2026 if variant == "a" else 1125
    bleed = 3
    W, H = 788 + 2*bleed, 545 + 2*bleed
    return render(W * MM, H * MM, color, seed, scale=scale), bleed

def card(variant):
    color = LOGO_A if variant == "a" else LOGO_B
    bleed = 3
    W, H = (100 + 2*bleed) * MM, (148 + 2*bleed) * MM
    # front: pattern without repeated logos + one centered logo on a clear zone
    logo_w = 62 * MM
    cx, cy = W / 2, H / 2
    rnd = random.Random(7 if variant == "a" else 8)
    obstacles = [(cx + dx * logo_w, cy, logo_w * 0.30) for dx in (-0.36, -0.12, 0.12, 0.36)]
    obstacles.append((cx, cy + 14 * MM, 14 * MM))
    pts = poisson(W, H, 22 * MM, rnd, False, existing=obstacles)
    front = Image.new("RGBA", (int(W), int(H)), BG + (255,))
    bag = Bag(rnd)
    for x, y in pts:
        name = bag.next()
        lo, hi = SIZE_MM.get(name, DEFAULT_SIZE_MM)
        spr = sprite(name, int(rnd.uniform(lo, hi) * MM * 0.85), round(rnd.uniform(-22, 22)))
        front.paste(spr, (int(x - spr.width/2), int(y - spr.height/2)), spr)
    lm = wordmark(int(logo_w), color)
    front.alpha_composite(lm, (int(cx - lm.width/2), int(cy - lm.height/2)))
    sub = wordmark(int(30 * MM), color if variant == "b" else (120, 110, 112), font=FONT_SUB,
                   text="THANK YOU 2026", tracking=0.18)
    front.alpha_composite(sub, (int(cx - sub.width/2), int(cy + lm.height/2 + 6 * MM)))
    # back: white, ruled lines, tiny motifs
    back = Image.new("RGBA", (int(W), int(H)), (255, 255, 255, 255))
    d = ImageDraw.Draw(back)
    m = (bleed + 12) * MM
    to = wordmark(int(9 * MM), LOGO_B, font=FONT_SUB, text="TO", tracking=0.1)
    back.alpha_composite(to, (int(m), int((bleed + 16) * MM)))
    y = (bleed + 32) * MM
    while y < H - (bleed + 30) * MM:
        d.line([(m, y), (W - m, y)], fill=LINE, width=max(2, int(0.25 * MM)))
        y += 10 * MM
    fr = wordmark(int(15 * MM), LOGO_B, font=FONT_SUB, text="FROM", tracking=0.1)
    fy = H - (bleed + 18) * MM
    back.alpha_composite(fr, (int(W / 2 - 4 * MM), int(fy - fr.height)))
    d.line([(W / 2 + 13 * MM, fy), (W - m, fy)], fill=LINE, width=max(2, int(0.25 * MM)))
    for name, x, yy, s in [("sparkle", W - m + 2 * MM, (bleed + 17) * MM, 8), ("heart", W - m - 8 * MM, (bleed + 20) * MM, 7)]:
        spr = sprite(name, int(s * MM), 10)
        back.paste(spr, (int(x - spr.width/2), int(yy - spr.height/2)), spr)
    return front.convert("RGB"), back.convert("RGB"), bleed

def crop_bleed(img, bleed):
    b = int(round(bleed * MM))
    return img.crop((b, b, img.width - b, img.height - b))

# ---------------------------------------------------------------- mockup
def perspective_coeffs(dst, src):
    """coeffs mapping output(dst) -> input(src) for Image.transform PERSPECTIVE"""
    import numpy as np
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u*x, -u*y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v*x, -v*y]); B.append(v)
    return list(np.linalg.solve(np.array(A, float), np.array(B, float)))

def warp_face(canvas, tex, quad, shade=1.0):
    W, H = canvas.size
    src = [(0, 0), (tex.width, 0), (tex.width, tex.height), (0, tex.height)]
    co = perspective_coeffs(quad, src)
    face = tex.transform((W, H), Image.PERSPECTIVE, co, Image.BICUBIC)
    if shade != 1.0:
        face = Image.eval(face, lambda v: int(min(255, v * shade)))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(quad, fill=255)
    canvas.paste(face, (0, 0), mask)

def mockup(sheet_img, card_front, out_path):
    W, H = 2400, 1600
    cv = Image.new("RGB", (W, H), (244, 240, 236))
    # subtle table gradient
    g = Image.linear_gradient("L").resize((W, H)).point(lambda v: int(v * 0.10))
    cv = Image.composite(Image.new("RGB", (W, H), (226, 220, 214)), cv, g)
    # box: 300 x 220 x 100 mm, oblique projection
    px = 3.1                                   # px per mm in mockup
    bw, bd, bh = 300, 220, 100
    ox, oy = 560, 640
    ang = math.radians(28)
    dx, dy = math.cos(ang) * bd * px * 0.62, -math.sin(ang) * bd * px * 0.62
    A = (ox, oy); B = (ox + bw * px, oy); C = (B[0], oy + bh * px); D = (ox, oy + bh * px)
    A2 = (A[0] + dx, A[1] + dy); B2 = (B[0] + dx, B[1] + dy); C2 = (C[0] + dx, C[1] + dy)
    tex_px = 300 / 25.4                        # sheet px per mm
    def tex(x0_mm, y0_mm, w_mm, h_mm):
        return sheet_img.crop((int(x0_mm * tex_px), int(y0_mm * tex_px),
                               int((x0_mm + w_mm) * tex_px), int((y0_mm + h_mm) * tex_px))).resize(
            (int(w_mm * 4), int(h_mm * 4)), Image.LANCZOS)
    # shadow
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).polygon([(D[0] - 10, D[1] + 8), (C[0] + 20, C[1] + 8), (C2[0] + 60, C2[1] + 20),
                                (B2[0] + 60, B2[1] + 40)], fill=110)
    sh = sh.filter(ImageFilter.GaussianBlur(40))
    cv = Image.composite(Image.new("RGB", (W, H), (150, 138, 132)), cv, sh)
    warp_face(cv, tex(120, 80, bw, bd), [A2, B2, B, A], 1.03)          # top
    warp_face(cv, tex(120, 300, bw, bh), [A, B, C, D], 0.97)            # front
    warp_face(cv, tex(420, 300, bd, bh), [B, B2, C2, C], 0.88)          # side
    d = ImageDraw.Draw(cv, "RGBA")
    # edges (paper fold highlights)
    d.line([A, B], fill=(255, 255, 255, 120), width=3)
    d.line([B, B2], fill=(255, 255, 255, 90), width=3)
    d.line([B, C], fill=(150, 110, 120, 60), width=2)
    # satin ribbon (white) crossing top + front + side
    rib = 16 * px
    def lerp(p, q, t): return (p[0] + (q[0]-p[0]) * t, p[1] + (q[1]-p[1]) * t)
    t0, t1 = 0.5 - rib / (2 * bw * px), 0.5 + rib / (2 * bw * px)
    for (p1, p2, p3, p4, sh_) in [
        (lerp(A2, B2, t0), lerp(A2, B2, t1), lerp(A, B, t1), lerp(A, B, t0), 255),
        (lerp(A, B, t0), lerp(A, B, t1), lerp(D, C, t1), lerp(D, C, t0), 240)]:
        d.polygon([p1, p2, p3, p4], fill=(sh_, sh_ - 2, sh_ - 4, 255))
    s0, s1 = 0.5 - rib / (2 * bd * px * 0.62 * 1.0) * 0.62, 0.5 + rib / (2 * bd * px * 0.62) * 0.62
    s0, s1 = 0.5 - 0.06, 0.5 + 0.06
    d.polygon([lerp(A, A2, s0), lerp(A, A2, s1), lerp(B, B2, s1), lerp(B, B2, s0)], fill=(252, 250, 248, 255))
    d.polygon([lerp(B, B2, s0), lerp(B, B2, s1), lerp(C, C2, s1), lerp(C, C2, s0)], fill=(222, 218, 214, 255))
    # bow on top centre
    top_c = lerp(lerp(A, B, 0.5), lerp(A2, B2, 0.5), 0.5)
    L, R, knot, tl, tr = m_bow()
    k = 150
    def tp(poly, ox=0, oy=0):
        return [(top_c[0] + x * k + ox, top_c[1] + y * k * 0.8 - 40 + oy) for x, y in poly]
    for poly in (tl, tr, L, R, knot):
        d.polygon(tp(poly, 6, 10), fill=(160, 140, 140, 70))
    for poly, col in ((tl, (238, 234, 230)), (tr, (238, 234, 230)), (L, (252, 250, 248)), (R, (248, 246, 244)), (knot, (240, 236, 232))):
        d.polygon(tp(poly), fill=col + (255,), outline=(205, 195, 195, 255))
        d.line(tp(poly), fill=(205, 195, 195, 255), width=3, joint="curve")
    # inner loop crease
    for poly in (L, R):
        inner = [(x * 0.55, y * 0.55 + 0.02) for x, y in poly]
        d.line(tp(inner), fill=(225, 218, 216, 255), width=3, joint="curve")
    # message card leaning in front-right
    cw = 100 * px * 1.05
    ci = card_front.resize((int(cw), int(cw * 148 / 100)), Image.LANCZOS).convert("RGBA")
    ci = ci.rotate(-9, resample=Image.BICUBIC, expand=True)
    cx0, cy0 = int(C2[0] + 70), int(C[1] - ci.height + 60)
    shadow = Image.new("RGBA", ci.size, (0, 0, 0, 0))
    shadow.putalpha(ci.getchannel("A").point(lambda v: int(v * 0.35)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    cv.paste((120, 100, 100), (cx0 + 18, cy0 + 22), shadow)
    cv.paste(ci, (cx0, cy0), ci)
    bb = (ox - 140, int(B2[1]) - 260, min(W, cx0 + ci.width + 140), int(C[1]) + 200)
    cv.crop(bb).save(out_path, quality=92)

# ---------------------------------------------------------------- main
def main():
    preview_only = len(sys.argv) > 1 and sys.argv[1] == "preview"
    os.makedirs(OUT, exist_ok=True)
    for v in ("a", "b"):
        tag = v.upper()
        if preview_only:
            img, _ = sheet(v, scale=0.12)
            img.save(f"{OUT}/preview_sheet_{v}.jpg", quality=88)
            continue
        full, bleed = sheet(v)
        full.save(f"{OUT}/print_{tag}_shiroku_788x545mm_bleed3mm_300dpi.png", dpi=(DPI, DPI), optimize=True)
        trim = crop_bleed(full, bleed)
        save_pdf(full, f"{OUT}/print_{tag}_shiroku_788x545mm_bleed3mm.pdf", 794, 551)
        trim.resize((trim.width // 6, trim.height // 6), Image.LANCZOS).save(f"{OUT}/preview_sheet_{v}.jpg", quality=88)
        # seamless tile 200mm
        T = 200 * MM
        tile = render(T, T, LOGO_A if v == "a" else LOGO_B, 77 if v == "a" else 78, wrap=True)
        tile.save(f"{OUT}/tile_{v}_200mm_300dpi.png", dpi=(DPI, DPI), optimize=True)
        cf, cb, cbl = card(v)
        cf.save(f"{OUT}/card_{tag}_front_100x148mm_bleed3mm_300dpi.png", dpi=(DPI, DPI))
        cb.save(f"{OUT}/card_{tag}_back_100x148mm_bleed3mm_300dpi.png", dpi=(DPI, DPI))
        from reportlab.pdfgen import canvas as rc
        from reportlab.lib.units import mm
        from reportlab.lib.utils import ImageReader
        c = rc.Canvas(f"{OUT}/card_{tag}_100x148mm_bleed3mm.pdf", pagesize=(106 * mm, 154 * mm))
        for im in (cf, cb):
            c.drawImage(ImageReader(im), 0, 0, 106 * mm, 154 * mm); c.showPage()
        c.save()
        mockup(trim, crop_bleed(cf, cbl), f"{OUT}/mockup_{v}.jpg")
        print("done", tag)

if __name__ == "__main__":
    main()
