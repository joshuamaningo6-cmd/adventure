"""'What if you could walk on clouds?' — bright anime-adventure test scene.
Hero: Tavi, a young sky-explorer (goggles, red scarf, mustard jacket, satchel).
Sidekick: Puff, a tiny cloud creature.
"""
import math, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DUR = 1280, 720, 30, 16.4
SS = 2
BEAT = 60 / 125
random.seed(11)
NAVY = (34, 44, 82, 255)          # anime outline colour
FONT_B = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"

# ======================================================================= helpers
def ease(u):
    u = min(max(u, 0.0), 1.0); return u * u * (3 - 2 * u)

def to_img(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def down(img):
    return img.resize((img.width // SS, img.height // SS), Image.LANCZOS)

def cumulus(d, x, y, w, h, k=1.0, shade=(198, 226, 247, 255), light=(255, 255, 255, 255), seed=0):
    """Puffy anime cloud: shaded underside + bright top puffs. Coordinates already scaled."""
    r = random.Random(seed)
    puffs = []
    n = max(4, int(w / (h * 0.55)))
    for i in range(n):
        u = i / (n - 1)
        px = x - w / 2 + u * w
        bump = math.sin(u * math.pi)
        pr = h * (0.35 + 0.45 * bump) * r.uniform(0.85, 1.15)
        py = y - bump * h * 0.35 + r.uniform(-h * 0.06, h * 0.06)
        puffs.append((px, py, pr))
    for px, py, pr in puffs:                 # shade layer
        d.ellipse([px - pr, py - pr + pr * 0.18, px + pr, py + pr + pr * 0.18], fill=shade)
    d.rectangle([x - w / 2, y - h * 0.05, x + w / 2, y + h * 0.32], fill=shade)
    for px, py, pr in puffs:                 # light layer
        d.ellipse([px - pr * 0.92, py - pr * 0.95, px + pr * 0.92, py + pr * 0.75], fill=light)

def island(d, x, y, w, depth, grass=(110, 200, 90, 255), grass_dark=(70, 160, 70, 255),
           rock=(120, 130, 140, 255), rock_dark=(85, 92, 110, 255), seed=0, tufts=True):
    """Floating island: grassy cap and a jagged rocky cone below."""
    r = random.Random(seed)
    pts = [(x - w / 2, y)]
    steps = 9
    for i in range(1, steps):
        u = i / steps
        px = x - w / 2 + u * w
        taper = math.sin(u * math.pi)
        pts.append((px + r.uniform(-w * 0.03, w * 0.03), y + depth * taper ** 1.4 * r.uniform(0.75, 1.1)))
    pts.append((x + w / 2, y))
    d.polygon(pts, fill=rock)
    # darker right-hand rock faces
    for i in range(1, steps - 1):
        a, b = pts[i], pts[i + 1]
        if i >= steps // 2 - 1:
            d.polygon([(a[0], y + 6), a, b, (b[0], y + 6)], fill=rock_dark)
    d.ellipse([x - w / 2 - w * 0.02, y - depth * 0.09, x + w / 2 + w * 0.02, y + depth * 0.11], fill=grass_dark)
    d.ellipse([x - w / 2, y - depth * 0.12, x + w / 2, y + depth * 0.06], fill=grass)
    if tufts:  # grass drips over the edge
        for i in range(int(w / 14)):
            gx = x - w / 2 + r.uniform(0, w)
            d.polygon([(gx - 5, y + depth * 0.04), (gx + 5, y + depth * 0.04), (gx + r.uniform(-2, 2), y + depth * 0.04 + r.uniform(6, 16))],
                      fill=grass_dark)

def tree(d, x, y, k, seed=0, leaf=(96, 196, 72, 255), leaf_dark=(58, 150, 62, 255), leaf_light=(170, 230, 110, 255)):
    r = random.Random(seed)
    trunk = (124, 86, 60, 255)
    d.polygon([(x - 18 * k, y), (x + 18 * k, y), (x + 9 * k, y - 120 * k), (x - 9 * k, y - 120 * k)], fill=trunk)
    d.line([(x, y - 100 * k), (x + 50 * k, y - 150 * k)], fill=trunk, width=int(10 * k))
    d.line([(x, y - 90 * k), (x - 46 * k, y - 140 * k)], fill=trunk, width=int(9 * k))
    blobs = [(r.uniform(-90, 90) * k, r.uniform(-230, -120) * k, r.uniform(40, 62) * k) for _ in range(14)]
    for bx, by, br in blobs:
        d.ellipse([x + bx - br, y + by - br + 10 * k, x + bx + br, y + by + br + 10 * k], fill=leaf_dark)
    for bx, by, br in blobs:
        d.ellipse([x + bx - br * 0.9, y + by - br, x + bx + br * 0.9, y + by + br * 0.8], fill=leaf)
    for bx, by, br in blobs[:7]:
        d.ellipse([x + bx - br * 0.45 - 8 * k, y + by - br * 0.75, x + bx + br * 0.25 - 8 * k, y + by - br * 0.2], fill=leaf_light)

# ======================================================================= layers
SKY_TOP, SKY_BOT = np.array([26, 120, 214]), np.array([150, 228, 246])

def build_sky():
    y = np.linspace(0, 1, H)[:, None, None]
    arr = SKY_TOP + (SKY_BOT - SKY_TOP) * (y ** 1.3)
    arr = np.repeat(arr, W, axis=1).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt((xx - 170) ** 2 + (yy - 90) ** 2)
    arr += (np.clip(1 - d / 520, 0, 1) ** 2.2)[..., None] * np.array([120, 110, 40])
    arr += (np.clip(1 - d / 70, 0, 1) ** 0.8)[..., None] * np.array([140, 140, 140])
    return to_img(arr).convert("RGBA")

def build_rays():
    img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = 170 * SS, 90 * SS
    r = random.Random(4)
    for i in range(11):
        a = math.radians(-10 + i * 11 + r.uniform(-3, 3)); spread = math.radians(r.uniform(1.2, 3.0))
        L = 1700 * SS
        d.polygon([(cx, cy), (cx + math.cos(a - spread) * L, cy + math.sin(a - spread) * L),
                   (cx + math.cos(a + spread) * L, cy + math.sin(a + spread) * L)], fill=(255, 250, 200, r.randint(26, 52)))
    img = img.filter(ImageFilter.GaussianBlur(6 * SS))
    return down(img)

def build_far():
    w = 1500
    img = Image.new("RGBA", (w * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = SS
    horizon = 585
    # land far below, hazy
    d.rectangle([0, horizon * s, w * s, H * s], fill=(120, 196, 150, 255))
    r = random.Random(5)
    for i in range(40):
        x = r.uniform(0, w); y = r.uniform(horizon + 8, H); rw = r.uniform(40, 160)
        d.ellipse([(x - rw) * s, (y - rw * 0.12) * s, (x + rw) * s, (y + rw * 0.12) * s],
                  fill=r.choice([(98, 176, 120, 255), (140, 206, 140, 255), (165, 214, 160, 255)]))
    for i in range(9):  # hazy mountains on the horizon
        x = r.uniform(0, w); hh = r.uniform(25, 60); ww = r.uniform(70, 150)
        d.polygon([((x - ww) * s, horizon * s), (x * s, (horizon - hh) * s), ((x + ww) * s, horizon * s)], fill=(120, 170, 175, 255))
    # tiny floating islands
    for i in range(10):
        x = r.uniform(40, w - 40); y = r.uniform(470, 560); ww = r.uniform(26, 70)
        island(d, x * s, y * s, ww * s, ww * 0.9 * s, grass=(130, 200, 150, 255), grass_dark=(105, 175, 140, 255),
               rock=(130, 160, 180, 255), rock_dark=(110, 140, 165, 255), seed=i, tufts=False)
    # cloud banks along horizon
    for i in range(12):
        x = r.uniform(0, w); y = r.uniform(560, 600)
        cumulus(d, x * s, y * s, r.uniform(160, 300) * s, r.uniform(40, 70) * s, seed=i,
                shade=(205, 232, 246, 255), light=(246, 252, 255, 255))
    img = img.filter(ImageFilter.GaussianBlur(1.6 * SS))
    img = down(img)
    # atmospheric haze toward sky colour
    a = np.array(img).astype(np.float32)
    haze = np.array([170, 222, 240])
    a[..., :3] = a[..., :3] * 0.72 + haze * 0.28
    return Image.fromarray(a.astype(np.uint8))

def build_mid():
    w = 1800
    img = Image.new("RGBA", (w * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = SS
    r = random.Random(8)
    for i, (x, y, cw, ch) in enumerate([(300, 200, 360, 110), (900, 150, 420, 130), (1450, 230, 380, 100), (1700, 120, 300, 90)]):
        cumulus(d, x * s, y * s, cw * s, ch * s, seed=20 + i)
    isl = [(560, 430, 180, 150, True), (1060, 360, 240, 200, True), (1520, 420, 150, 120, False), (180, 470, 120, 100, False)]
    for i, (x, y, ww, dp, has_tree) in enumerate(isl):
        if i == 1:  # waterfall off the big one
            d.rectangle([(x + 60) * s, (y + 4) * s, (x + 76) * s, (y + 250) * s], fill=(210, 240, 255, 230))
            d.rectangle([(x + 64) * s, (y + 4) * s, (x + 68) * s, (y + 250) * s], fill=(255, 255, 255, 255))
        island(d, x * s, y * s, ww * s, dp * s, seed=40 + i)
        if has_tree:
            tree(d, (x - ww * 0.18) * s, (y - 2) * s, 0.42 * s, seed=i)
    img = img.filter(ImageFilter.GaussianBlur(0.7 * SS))
    img = down(img)
    a = np.array(img).astype(np.float32)
    a[..., :3] = a[..., :3] * 0.88 + np.array([170, 222, 240]) * 0.12
    return Image.fromarray(a.astype(np.uint8))

CLIFF_TOP, CLIFF_EDGE = 470, 575

def build_fg():
    w = 2500
    img = Image.new("RGBA", (w * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = SS
    # big cliff island on the left
    top = CLIFF_TOP
    pts = [(-40, top), (CLIFF_EDGE, top), (CLIFF_EDGE + 10, top + 40), (CLIFF_EDGE - 20, top + 120), (CLIFF_EDGE + 5, top + 200),
           (CLIFF_EDGE - 60, H + 40), (-40, H + 40)]
    d.polygon([(px * s, py * s) for px, py in pts], fill=(132, 128, 142, 255))
    d.polygon([((CLIFF_EDGE - 70) * s, top * s), (CLIFF_EDGE * s, top * s), ((CLIFF_EDGE + 10) * s, (top + 40) * s),
               ((CLIFF_EDGE - 20) * s, (top + 120) * s), ((CLIFF_EDGE + 5) * s, (top + 200) * s), ((CLIFF_EDGE - 60) * s, (H + 40) * s),
               ((CLIFF_EDGE - 110) * s, (H + 40) * s)], fill=(100, 98, 120, 255))
    for i in range(14):  # rock cracks
        x = random.uniform(40, CLIFF_EDGE - 40); y = random.uniform(top + 40, H)
        d.line([(x * s, y * s), ((x + random.uniform(-20, 20)) * s, (y + random.uniform(20, 50)) * s)], fill=(90, 88, 108, 255), width=2 * s)
    # grass cap with lip and drips
    d.rounded_rectangle([-40 * s, (top - 16) * s, (CLIFF_EDGE + 12) * s, (top + 14) * s], 14 * s, fill=(70, 162, 66, 255))
    d.rounded_rectangle([-40 * s, (top - 20) * s, (CLIFF_EDGE + 6) * s, (top + 6) * s], 12 * s, fill=(118, 206, 86, 255))
    r = random.Random(9)
    for i in range(70):
        gx = r.uniform(-30, CLIFF_EDGE + 6)
        d.polygon([((gx - 4) * s, (top - 16) * s), ((gx + 4) * s, (top - 16) * s), ((gx + r.uniform(-4, 4)) * s, (top - 16 - r.uniform(6, 14)) * s)],
                  fill=(150, 222, 100, 255))
    for i in range(30):
        gx = r.uniform(-20, CLIFF_EDGE)
        d.polygon([((gx - 6) * s, (top + 10) * s), ((gx + 6) * s, (top + 10) * s), ((gx + r.uniform(-3, 3)) * s, (top + 10 + r.uniform(8, 26)) * s)],
                  fill=(70, 162, 66, 255))
    for i in range(6):  # pebbles + flowers
        fx = r.uniform(40, CLIFF_EDGE - 60)
        d.ellipse([(fx - 9) * s, (top - 22) * s, (fx + 9) * s, (top - 10) * s], fill=(190, 192, 200, 255))
    for i in range(18):
        fx = r.uniform(0, CLIFF_EDGE - 30); fy = top - 18 - r.uniform(0, 4)
        c = r.choice([(255, 255, 255, 255), (255, 214, 90, 255), (255, 150, 180, 255)])
        d.ellipse([(fx - 3) * s, (fy - 3) * s, (fx + 3) * s, (fy + 3) * s], fill=c)
    tree(d, 150 * s, (top - 12) * s, 1.15 * s, seed=3)
    return down(img)

# ======================================================================= characters
SKIN, SKIN_SH = (255, 224, 196, 255), (240, 190, 160, 255)
HAIR, HAIR_SH, HAIR_HI = (226, 118, 58, 255), (186, 82, 44, 255), (255, 170, 100, 255)
JACKET, JACKET_SH = (245, 184, 62, 255), (214, 140, 40, 255)
SHORTS = (52, 140, 170, 255)
SCARF, SCARF_SH = (232, 66, 64, 255), (186, 40, 52, 255)
BOOT = (120, 72, 48, 255)
BRASS, LENS = (214, 170, 80, 255), (90, 210, 220, 255)

def seg(d, a, b, col, w, outline=True):
    if outline:
        d.line([a, b], fill=NAVY, width=int(w + 4 * SS))
        for p in (a, b):
            rr = (w + 4 * SS) / 2; d.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr], fill=NAVY)
    d.line([a, b], fill=col, width=int(w))
    for p in (a, b):
        rr = w / 2; d.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr], fill=col)

def tavi(d, x, gy, t, run=0.0, phase=0.0, crouch=0.0, arms_up=0.0, air=0.0, squash=0.0, blink=False, cheer=0.0, sc=1.3):
    """Draws Tavi facing right with feet at (x, gy). All inputs in output px; drawn at SS."""
    k = SS * sc
    X = lambda v: x * SS + v * k
    Y = lambda v: gy * SS + v * k
    sq = 1 - 0.12 * squash          # vertical squash on landing
    cr = crouch * 14 + squash * 6
    bob = abs(math.sin(phase)) * 5 * run
    hip_y = -52 * sq + cr - bob * 0.5
    sho_y = -94 * sq + cr - bob
    lean = 6 * run + 4 * air
    hip = (X(0), Y(hip_y)); sho = (X(lean), Y(sho_y))

    def leg(side):
        p = phase + (0 if side > 0 else math.pi)
        if air > 0:
            a1, a2 = (0.9 if side > 0 else -0.2) * air, (-1.3 if side > 0 else -0.6) * air
        else:
            a1 = math.sin(p) * 0.75 * run + side * 0.10 * (1 - run) + crouch * 0.5
            a2 = a1 - (max(0, math.sin(p + 1.3)) * 1.1 * run) - crouch * 1.1 - squash * 0.4
        L1, L2 = 26 * sq, 26 * sq
        knee = (hip[0] + math.sin(a1) * L1 * k, hip[1] + math.cos(a1) * L1 * k)
        foot = (knee[0] + math.sin(a2) * L2 * k, knee[1] + math.cos(a2) * L2 * k)
        if air == 0: foot = (foot[0], min(foot[1], Y(0) - 4 * k))
        return knee, foot

    def arm(side):
        p = phase + (math.pi if side > 0 else 0)
        swing = math.sin(p) * 0.9 * run
        up = min(1.0, arms_up + cheer * (0.88 + 0.12 * math.sin(t * 14 + side)))
        a1 = swing * (1 - up) + up * (math.pi * (0.6 if side > 0 else 0.95))
        a2 = a1 + 0.5 * (1 - up) + (0.4 if side < 0 else 0.6) * up
        el = (sho[0] + math.sin(a1) * 22 * k, sho[1] + math.cos(a1) * 22 * k)
        hand = (el[0] + math.sin(a2) * 20 * k, el[1] + math.cos(a2) * 20 * k)
        return el, hand

    # ---- scarf tails (behind everything)
    neck = (sho[0] - 2 * k, sho[1] - 4 * k)
    wind = 1.0 + 0.8 * run + 1.2 * air
    for j, (off, col) in enumerate([(0, SCARF_SH), (7, SCARF)]):
        pts = []
        for i in range(9):
            u = i / 8
            px = neck[0] - (u * 40 * wind + 4) * k
            py = neck[1] + (u * 20 * (1.2 - 0.6 * min(wind, 1.6)) + math.sin(t * 9 + u * 4 + j) * 7 * u + off * u) * k
            pts.append((px, py))
        upper = [(px, py - (5 - 2 * i / 8) * k) for i, (px, py) in enumerate(pts)]
        lower = [(px, py + (5 - 2 * i / 8) * k) for i, (px, py) in enumerate(pts)]
        poly = upper + lower[::-1]
        d.polygon(poly, fill=NAVY)
        d.polygon([(px + 1.5 * k, py) for px, py in upper] + [(px + 1.5 * k, py - 1.5 * k) for px, py in lower[::-1]], fill=col)

    # ---- back limbs
    kb, fb = leg(-1); eb, hb = arm(-1)
    seg(d, hip, kb, (40, 112, 140, 255), 13 * k); seg(d, kb, fb, SKIN_SH, 9 * k)
    d.ellipse([fb[0] - 9 * k, fb[1] - 5 * k, fb[0] + 11 * k, fb[1] + 6 * k], fill=NAVY)
    d.ellipse([fb[0] - 7 * k, fb[1] - 3 * k, fb[0] + 9 * k, fb[1] + 4 * k], fill=(96, 56, 38, 255))
    seg(d, sho, eb, JACKET_SH, 11 * k); seg(d, eb, hb, SKIN_SH, 8 * k)

    # ---- satchel (back hip)
    sx, sy = hip[0] - 16 * k, hip[1] - 14 * k
    d.rounded_rectangle([sx - 13 * k, sy - 10 * k, sx + 9 * k, sy + 12 * k], 5 * k, fill=NAVY)
    d.rounded_rectangle([sx - 11 * k, sy - 8 * k, sx + 7 * k, sy + 10 * k], 4 * k, fill=(150, 98, 60, 255))
    d.rectangle([sx - 11 * k, sy - 8 * k, sx + 7 * k, sy - 1 * k], fill=(122, 76, 46, 255))

    # ---- torso (jacket)
    tw = 17 * k
    body = [(hip[0] - tw, hip[1] + 4 * k), (hip[0] + tw, hip[1] + 4 * k), (sho[0] + tw * 0.85, sho[1]), (sho[0] - tw * 0.85, sho[1])]
    d.polygon([(px + (2 * k if i in (1, 2) else -2 * k), py + (2 * k if i < 2 else -2 * k)) for i, (px, py) in enumerate(body)], fill=NAVY)
    d.polygon(body, fill=JACKET)
    d.polygon([body[1], body[2], (body[2][0] - 8 * k, body[2][1]), (body[1][0] - 8 * k, body[1][1])], fill=JACKET_SH)
    d.polygon([(sho[0] + 1 * k, sho[1]), (sho[0] + 9 * k, sho[1]), (sho[0] + 3 * k, sho[1] + 16 * k)], fill=(255, 255, 255, 255))  # shirt V
    d.rectangle([hip[0] - tw, hip[1] - 4 * k, hip[0] + tw, hip[1] + 1 * k], fill=(110, 66, 44, 255))  # belt
    d.rectangle([hip[0] + 2 * k, hip[1] - 5 * k, hip[0] + 8 * k, hip[1] + 2 * k], fill=BRASS)
    d.line([(sho[0] + 10 * k, sho[1] + 2 * k), (hip[0] - 14 * k, hip[1] - 8 * k)], fill=(122, 76, 46, 255), width=int(4 * k))  # strap

    # ---- front leg
    kf, ff = leg(1)
    seg(d, hip, kf, SHORTS, 13 * k); seg(d, kf, ff, SKIN, 9 * k)
    d.ellipse([ff[0] - 9 * k, ff[1] - 6 * k, ff[0] + 12 * k, ff[1] + 6 * k], fill=NAVY)
    d.ellipse([ff[0] - 7 * k, ff[1] - 4 * k, ff[0] + 10 * k, ff[1] + 4 * k], fill=BOOT)

    # ---- scarf wrap at neck
    d.rounded_rectangle([sho[0] - 14 * k, sho[1] - 9 * k, sho[0] + 14 * k, sho[1] + 4 * k], 6 * k, fill=NAVY)
    d.rounded_rectangle([sho[0] - 12 * k, sho[1] - 7 * k, sho[0] + 12 * k, sho[1] + 2 * k], 5 * k, fill=SCARF)

    # ---- head
    hx, hy = sho[0] + 3 * k, sho[1] - 30 * k
    R = 27 * k
    # back hair
    spikes = [(-1.0, 1.2), (-0.55, 1.35), (-0.15, 1.3), (0.3, 1.18)]
    d.ellipse([hx - R - 3 * k, hy - R - 3 * k, hx + R + 3 * k, hy + R + 3 * k], fill=NAVY)
    for ang, ln in spikes + [(-1.5, 1.15), (-1.95, 1.05)]:
        a = ang - math.pi / 2
        tip = (hx + math.cos(a) * R * ln * 1.08, hy + math.sin(a) * R * ln * 1.08 - 2 * k)
        b1 = (hx + math.cos(a - 0.35) * R * 0.8, hy + math.sin(a - 0.35) * R * 0.8)
        b2 = (hx + math.cos(a + 0.35) * R * 0.8, hy + math.sin(a + 0.35) * R * 0.8)
        d.polygon([b1, tip, b2], fill=NAVY)
    d.ellipse([hx - R, hy - R, hx + R, hy + R], fill=SKIN)
    # hair cap
    d.chord([hx - R - 1 * k, hy - R - 1 * k, hx + R + 1 * k, hy + R + 1 * k], 160, 345, fill=HAIR)
    d.pieslice([hx - R, hy - R, hx + R, hy + R], 95, 200, fill=HAIR)       # back of head
    for ang, ln in spikes + [(-1.5, 1.15), (-1.95, 1.05)]:
        a = ang - math.pi / 2
        tip = (hx + math.cos(a) * R * ln, hy + math.sin(a) * R * ln)
        b1 = (hx + math.cos(a - 0.32) * R * 0.78, hy + math.sin(a - 0.32) * R * 0.78)
        b2 = (hx + math.cos(a + 0.32) * R * 0.78, hy + math.sin(a + 0.32) * R * 0.78)
        d.polygon([b1, tip, b2], fill=HAIR)
    # ahoge (cowlick) that bounces
    bounce = math.sin(t * 10) * 3 * (run + air + 0.3)
    d.line([(hx - 2 * k, hy - R + 2 * k), (hx + 4 * k, hy - R - 14 * k), (hx + 14 * k + bounce * k, hy - R - 16 * k)],
           fill=HAIR_SH, width=int(4 * k), joint="curve")
    # fringe over forehead (right side, facing)
    for fx in (0.15, 0.45, 0.72):
        d.polygon([(hx + R * (fx - 0.2), hy - R * 0.72), (hx + R * (fx + 0.22), hy - R * 0.66), (hx + R * (fx + 0.05), hy - R * 0.18)], fill=HAIR)
    d.arc([hx - R * 0.6, hy - R * 0.9, hx + R * 0.2, hy - R * 0.2], 200, 290, fill=HAIR_HI, width=int(3 * k))
    # goggles on forehead
    gy_ = hy - R * 0.55
    d.line([(hx - R * 0.95, gy_ + 4 * k), (hx + R * 0.55, gy_)], fill=(90, 60, 40, 255), width=int(5 * k))
    for gx_, gr in ((hx + R * 0.25, 8.5), (hx + R * 0.72, 7.5)):
        d.ellipse([gx_ - (gr + 2) * k, gy_ - (gr + 2) * k, gx_ + (gr + 2) * k, gy_ + (gr + 2) * k], fill=NAVY)
        d.ellipse([gx_ - gr * k, gy_ - gr * k, gx_ + gr * k, gy_ + gr * k], fill=BRASS)
        d.ellipse([gx_ - (gr - 3) * k, gy_ - (gr - 3) * k, gx_ + (gr - 3) * k, gy_ + (gr - 3) * k], fill=LENS)
        d.ellipse([gx_ - (gr - 4) * k, gy_ - (gr - 4) * k, gx_ - (gr - 7) * k, gy_ - (gr - 7) * k], fill=(255, 255, 255, 255))
    # ear
    d.ellipse([hx - R * 0.25, hy - 2 * k, hx - R * 0.25 + 10 * k, hy + 12 * k], fill=SKIN_SH)
    # face: eye, brow, blush, mouth (looking right)
    ex, ey = hx + R * 0.55, hy + 2 * k
    if blink:
        d.arc([ex - 6 * k, ey - 4 * k, ex + 6 * k, ey + 6 * k], 200, 340, fill=NAVY, width=int(3 * k))
    else:
        d.ellipse([ex - 6.5 * k, ey - 10 * k, ex + 6.5 * k, ey + 10 * k], fill=NAVY)
        d.ellipse([ex - 5 * k, ey - 8 * k, ex + 5 * k, ey + 8 * k], fill=(70, 120, 200, 255))
        d.ellipse([ex - 4 * k, ey - 1 * k, ex + 4 * k, ey + 7 * k], fill=(40, 70, 150, 255))
        d.ellipse([ex - 4 * k, ey - 8 * k, ex + 1.5 * k, ey - 2 * k], fill=(255, 255, 255, 255))
        d.ellipse([ex + 1 * k, ey + 3 * k, ex + 3.5 * k, ey + 5.5 * k], fill=(255, 255, 255, 255))
    d.line([(ex - 6 * k, ey - 15 * k), (ex + 5 * k, ey - 17 * k)], fill=HAIR_SH, width=int(3 * k))
    d.ellipse([ex - 4 * k, ey + 10 * k, ex + 9 * k, ey + 16 * k], fill=(255, 160, 160, 200))
    open_mouth = cheer > 0.1 or air > 0.3
    if open_mouth:
        d.chord([hx + R * 0.62, hy + 13 * k, hx + R * 0.98, hy + 24 * k], 0, 180, fill=(170, 50, 60, 255))
    else:
        d.arc([hx + R * 0.6, hy + 9 * k, hx + R * 0.95, hy + 19 * k], 10, 140, fill=NAVY, width=int(2 * k))

    # ---- front arm (over body)
    ef, hf = arm(1)
    seg(d, sho, ef, JACKET, 11 * k); seg(d, ef, hf, SKIN, 8 * k)
    d.ellipse([hf[0] - 6 * k, hf[1] - 6 * k, hf[0] + 6 * k, hf[1] + 6 * k], fill=NAVY)
    d.ellipse([hf[0] - 4.5 * k, hf[1] - 4.5 * k, hf[0] + 4.5 * k, hf[1] + 4.5 * k], fill=SKIN)

def puff(d, x, y, t, happy=0.0, k=SS):
    """Puff the cloud sprite."""
    X, Y = x * k, y * k
    spin = math.sin(t * 3) * 2
    blobs = [(-14, 4, 12), (0, -4, 16), (14, 3, 12), (-6, 8, 11), (8, 9, 11)]
    for bx, by, br in blobs:
        d.ellipse([X + (bx - br - 2) * k, Y + (by - br - 2) * k, X + (bx + br + 2) * k, Y + (by + br + 2) * k], fill=NAVY)
    for bx, by, br in blobs:
        d.ellipse([X + (bx - br) * k, Y + (by - br + 3) * k, X + (bx + br) * k, Y + (by + br + 3) * k], fill=(196, 226, 250, 255))
    for bx, by, br in blobs:
        d.ellipse([X + (bx - br) * k, Y + (by - br) * k, X + (bx + br) * k, Y + (by + br - 3) * k], fill=(255, 255, 255, 255))
    ex = X + (4 + spin) * k
    if happy > 0.5:   # ^ ^ eyes
        for dx in (-6, 6):
            d.arc([ex + (dx - 4) * k, Y - 4 * k, ex + (dx + 4) * k, Y + 4 * k], 200, 340, fill=NAVY, width=int(2 * k))
    else:
        for dx in (-6, 6):
            d.ellipse([ex + (dx - 2.5) * k, Y - 4 * k, ex + (dx + 2.5) * k, Y + 2 * k], fill=NAVY)
            d.ellipse([ex + (dx - 1.5) * k, Y - 3.5 * k, ex + (dx + 0) * k, Y - 1.5 * k], fill=(255, 255, 255, 255))
    for dx in (-11, 11):
        d.ellipse([ex + (dx - 4) * k, Y + 3 * k, ex + (dx + 4) * k, Y + 7 * k], fill=(255, 170, 190, 255))
    d.arc([ex - 3 * k, Y + 1 * k, ex + 3 * k, Y + 6 * k], 20, 160, fill=NAVY, width=int(2 * k))

# ======================================================================= choreography
CLOUDS = [(860, 560, 150), (1110, 525, 130), (1360, 492, 130), (1640, 462, 190)]  # x, top-y, width (world)
def cloud_top(i, t):
    x, y, w = CLOUDS[i]
    return y + math.sin(t * 1.6 + i) * 4

def hero_state(t):
    """Returns world x, ground y, and pose dict."""
    st = dict(run=0.0, phase=0.0, crouch=0.0, arms_up=0.0, air=0.0, squash=0.0, cheer=0.0, on=None)
    if t < 3.3:
        x = 40 + 140 * t; st.update(run=1.0, phase=t * 11); return x, CLIFF_TOP - 8, st
    if t < 3.7:  # skid to a stop
        u = (t - 3.3) / 0.4; x = 502 + 18 * ease(u); st.update(run=1 - u, phase=3.3 * 11 + u * 3); return x, CLIFF_TOP - 8, st
    x0, g0 = 520, CLIFF_TOP - 8
    if t < 5.5:
        st.update(cheer=ease((t - 4.4) / 0.3) * (1 - ease((t - 5.2) / 0.3))); return x0, g0, st
    if t < 5.95:
        st.update(crouch=ease((t - 5.5) / 0.3)); return x0, g0, st
    # hops: (start t, end t, from (x, ground), to cloud index)
    hops = [(5.95, 6.85, (x0, g0), 0), (7.45, 8.15, None, 1), (8.6, 9.3, None, 2), (9.75, 10.55, None, 3)]
    prev = (x0, g0)
    for hi, (ta, tb, frm, ci) in enumerate(hops):
        if frm is None:
            frm = (CLOUDS[hops[hi - 1][3]][0] + 10, cloud_top(hops[hi - 1][3], ta))
        to = (CLOUDS[ci][0] - (20 if ci < 3 else 50), cloud_top(ci, tb))
        if t < ta:
            # standing on previous cloud, small crouch before the hop
            cx, cy = prev
            st.update(crouch=ease((t - (ta - 0.25)) / 0.25) * 0.7, squash=max(0, 1 - (t - (ta - 0.6)) / 0.3) if hi > 0 else 0, on=hops[hi - 1][3] if hi else None)
            return cx, cy, st
        if t < tb:
            u = (t - ta) / (tb - ta)
            x = frm[0] + (to[0] - frm[0]) * u
            y = frm[1] + (to[1] - frm[1]) * u - math.sin(u * math.pi) * (150 if hi == 0 else 95)
            st.update(air=1.0, arms_up=0.8 if hi == 0 else 0.5); return x, y, st
        prev = (to[0], cloud_top(ci, t))
    # final cloud: land, then cheer
    cx, _ = prev
    st.update(squash=max(0, 1 - (t - 10.55) / 0.3), cheer=ease((t - 11.0) / 0.4), on=3)
    return cx, cloud_top(3, t), st

def cloud_squish(i, t):
    lands = {0: 6.85, 1: 8.15, 2: 9.3, 3: 10.55}
    dt = t - lands[i]
    return math.exp(-dt * 6) * math.cos(dt * 22) if dt > 0 else 0.0

SUBS = [(0.35, 3.3, "What if you could walk on clouds?"),
        (3.6, 5.7, "Not fly... just walk. Anywhere the sky goes."),
        (5.95, 7.9, "One step off the edge..."),
        (8.2, 12.6, "...and the whole sky becomes your playground!")]
TITLE_T = 13.44   # lands on the final musical hit

def text_layer(txt, size, fill, stroke=6):
    f = ImageFont.truetype(FONT_B, size * SS)
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bb = tmp.textbbox((0, 0), txt, font=f, stroke_width=stroke * SS)
    img = Image.new("RGBA", (bb[2] - bb[0] + 20 * SS, bb[3] - bb[1] + 20 * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((10 * SS - bb[0], 10 * SS - bb[1]), txt, font=f, fill=fill, stroke_width=stroke * SS, stroke_fill=NAVY)
    return down(img)

# ======================================================================= render
def render(out, only=None):
    sky = build_sky(); rays = build_rays(); far = build_far(); mid = build_mid(); fg = build_fg()
    rays_a = np.array(rays)[..., 3].astype(np.float32)
    sub_imgs = {txt: text_layer(txt, 30, (255, 255, 255, 255), 4) for _, _, txt in SUBS}
    t1 = text_layer("WHAT IF YOU COULD", 34, (255, 255, 255, 255), 5)
    t2 = text_layer("WALK ON CLOUDS?", 78, (255, 214, 64, 255), 8)
    motes = [[random.uniform(0, W), random.uniform(0, H), random.uniform(0.6, 1.6), random.uniform(0, 6)] for _ in range(45)]
    birds = [[random.uniform(200, 1400), random.uniform(160, 300), random.uniform(25, 45), random.uniform(0, 6)] for _ in range(5)]
    n = int(DUR * FPS)
    frames = set(only) if only is not None else None
    ff = None
    if only is None:
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", out],
                              stdin=subprocess.PIPE)
    cam = 640.0
    puff_pos = np.array([0.0, 380.0])
    for i in range(n):
        t = i / FPS
        hx, hy, st = hero_state(t)
        target = min(max(hx + 130, 640), 1700)
        cam += (target - cam) * (0.08 if i else 1)
        # Puff follows a point above-behind Tavi, with lag
        ahead = ease((t - 3.8) / 0.5) * (1 - ease((t - 5.4) / 0.5))
        goal = np.array([hx - 70 + 150 * ahead, hy - 225 + 40 * ahead + math.sin(t * 3.2) * 8])
        puff_pos = goal if i == 0 else puff_pos + (goal - puff_pos) * 0.09
        if frames is not None and i not in frames:
            continue
        off = cam - 640
        frame = sky.copy()
        ra = rays.copy(); ra.putalpha(Image.fromarray((rays_a * (0.85 + 0.15 * math.sin(t * 1.3))).astype(np.uint8)))
        frame.alpha_composite(ra)
        frame.alpha_composite(far.crop((int(off * 0.15), 0, int(off * 0.15) + W, H)))
        # birds (mid-depth)
        bl = ImageDraw.Draw(frame)
        for b in birds:
            bx = (b[0] + t * b[2] - off * 0.45) % (W + 100) - 50; by = b[1] + math.sin(t * 2 + b[3]) * 6
            flap = math.sin(t * 9 + b[3]) * 5
            bl.line([(bx - 9, by - flap), (bx, by), (bx + 9, by - flap)], fill=(60, 90, 130, 255), width=2)
        frame.alpha_composite(mid.crop((int(off * 0.45), 0, int(off * 0.45) + W, H)))
        frame.alpha_composite(fg.crop((int(off), 0, int(off) + W, H)))

        # dynamic layer at SS: step clouds, hero, Puff
        dyn = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(dyn)
        for ci, (cx, cy, cw) in enumerate(CLOUDS):
            sx = cx - off
            if -200 < sx < W + 200:
                q = cloud_squish(ci, t)
                top = cloud_top(ci, t) + q * 8
                hh = 46 * (1 - 0.15 * q)
                cumulus(d, sx * SS, (top + hh * 0.42) * SS, cw * (1 + 0.08 * q) * SS, hh * SS, seed=60 + ci)
        # contact shadow
        sx = hx - off
        if st["air"] == 0:
            d.ellipse([(sx - 30) * SS, (hy - 4) * SS, (sx + 30) * SS, (hy + 6) * SS], fill=(40, 80, 60, 70) if st['on'] is None and t < 6 else (120, 160, 210, 110))
        blink = (t % 3.1) < 0.12
        tavi(d, sx, hy, t, run=st["run"], phase=st["phase"], crouch=st["crouch"], arms_up=st["arms_up"],
             air=st["air"], squash=st["squash"], blink=blink, cheer=st["cheer"])
        puff(d, puff_pos[0] - off, puff_pos[1], t, happy=1.0 if (4.4 < t < 5.5 or t > 10.8) else 0.0)
        # landing sparkles
        for land_t, ci in ((6.85, 0), (8.15, 1), (9.3, 2), (10.55, 3)):
            dt = t - land_t
            if 0 < dt < 0.6:
                lx = CLOUDS[ci][0] - (20 if ci < 3 else 50) - off; ly = cloud_top(ci, t)
                for j in range(8):
                    a = j / 8 * math.pi * 2; rr = 20 + dt * 90; al = int(255 * (1 - dt / 0.6))
                    px, py = lx + math.cos(a) * rr, ly - 10 + math.sin(a) * rr * 0.5
                    sz = 5 * (1 - dt / 0.6) + 1
                    d.polygon([((px) * SS, (py - sz) * SS), ((px + sz * 0.35) * SS, py * SS), (px * SS, (py + sz) * SS), ((px - sz * 0.35) * SS, py * SS)],
                              fill=(255, 250, 200, al))
        frame.alpha_composite(down(dyn))

        # floating light motes
        md = ImageDraw.Draw(frame)
        for m in motes:
            mx = (m[0] - off * 0.7 + math.sin(t + m[3]) * 10) % W; my = (m[1] - t * 12 * m[2]) % H
            a = int(140 + 110 * math.sin(t * 3 + m[3]))
            md.ellipse([mx - m[2], my - m[2], mx + m[2], my + m[2]], fill=(255, 255, 220, max(0, a)))

        # subtitles
        for a, b, txt in SUBS:
            if a <= t <= b:
                op = min(1, (t - a) / 0.2, (b - t) / 0.2)
                im = sub_imgs[txt]
                if op < 1:
                    arr = np.array(im); arr[..., 3] = (arr[..., 3] * op).astype(np.uint8); im = Image.fromarray(arr)
                frame.alpha_composite(im, ((W - im.width) // 2, H - 92))
        # title card
        if t >= TITLE_T:
            u = t - TITLE_T
            sc = 1 + 0.25 * math.exp(-u * 7) * math.cos(u * 18)  # springy pop
            op = min(1, u / 0.12)
            for img, cy, delay in ((t1, 120, 0.0), (t2, 200, 0.08)):
                if u < delay: continue
                s2 = sc if u > delay else 1
                im = img.resize((max(1, int(img.width * s2)), max(1, int(img.height * s2))), Image.LANCZOS)
                if op < 1:
                    arr = np.array(im); arr[..., 3] = (arr[..., 3] * op).astype(np.uint8); im = Image.fromarray(arr)
                frame.alpha_composite(im, ((W - im.width) // 2, cy - im.height // 2))
        # gentle bloom + warm grade
        rgb = frame.convert("RGB")
        if ff:
            ff.stdin.write(rgb.tobytes())
        else:
            rgb.save(f"{out}_{i:03d}.png")
    if ff:
        ff.stdin.close(); sys.exit(ff.wait())

if __name__ == "__main__":
    if sys.argv[1] == "preview":
        render("sp", only=[int(float(v) * FPS) for v in sys.argv[2:]])
    else:
        render(sys.argv[1])
