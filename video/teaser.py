"""10-second stand-alone teaser for Episode 1: "What If You Had 10 Hours to Build a Zombie-Proof Home?"

One script, two native formats (nothing is cropped or letterboxed):
    python3 teaser.py yt   out_16x9.mp4      # 1920x1080, YouTube
    python3 teaser.py reel out_9x16.mp4      # 1080x1920, Shorts / Reels / TikTok, full bleed
    python3 teaser.py reel preview 1.0 4.5   # PNG stills of chosen seconds (quick look)

Beat sheet (10 s):
  0.0-2.2  Night. The Scarf sprints, shadow zombies burst from the bushes, one leaps at the camera.
  2.2-3.2  Freeze, tape-rewind back across the meadow, navy sky flips to day. "10 HOURS EARLIER".
  3.2-7.3  Sped-up build: stone axe -> foundation -> walls -> roof -> spike wall -> torches.
           Sun timer counts 10:00 -> 0:00, colour script runs day -> gold -> dusk.
  7.3-8.5  Night falls. One pair of eyes in the bushes, then ten, then dozens. Hero on the roof, crystal spear.
  8.5-10   Title card + "What would you build first?" (comment prompt, the loop ends on a question).

Pillow + NumPy frames piped to ffmpeg. Audio is fully synthesised here (plus code/music.py for the day theme),
so nothing costs money. Everything is drawn at 2x and box-reduced for anti-aliasing.
"""
import math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FMT = sys.argv[1] if len(sys.argv) > 1 else "yt"
FPS, DUR = 30, 10.0
NF = int(FPS * DUR)
SS = 2
FONT_DIR = "/usr/share/fonts/opentype/inter/"

if FMT == "yt":
    W, H = 1920, 1080
    GY = 842            # ground line (feet)
    HERO = 235          # hero height px
    CAB_X, CAB_W = 1250, 360
    HERO_X = 0.56       # hero screen x during the chase (fraction of W)
    YH = GY - 205       # horizon
    CAP_Y, CAP_X, CAP_SIZE = 0.895 * H, 0.5 * W, 88
    TIMER = (56, 44, 1.0)
elif FMT in ("banner", "avatar"):   # channel art (see make_channel_art)
    W, H = 2560, 1440
    GY = 935
    HERO = 290
    CAB_X, CAB_W = 2230, 400
    HERO_X = 0.66
    YH = GY - 250
    CAP_Y, CAP_X, CAP_SIZE = 0, 0, 10
    TIMER = (0, 0, 1)
else:
    W, H = 1080, 1920
    GY = 1300
    HERO = 330
    CAB_X, CAB_W = 560, 470
    HERO_X = 0.64
    YH = GY - 330
    CAP_Y, CAP_X, CAP_SIZE = 0.215 * H, 0.46 * W, 112   # above middle, clear of right 15% / top 10% / bottom 20%
    TIMER = (60, 226, 1.3)
K = HERO / 235.0                     # decoration scale
RUN_V = 2.6 * HERO                   # px/s the camera travels in the chase
O0 = 1.25 * W                        # chase happens this far right of the build site
OMAX = O0 + RUN_V * 2.2
RNG = np.random.default_rng(5)


def S(v):
    return v * SS


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return a + (b - a) * u


def lerpc(a, b, u):
    return tuple(int(round(a[i] + (b[i] - a[i]) * u)) for i in range(len(a)))


_fonts = {}


def font(size, w="Black"):
    key = (int(size), w)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_DIR + f"Inter-{w}.otf", int(size))
    return _fonts[key]


# =========================================================================== timeline
def tod(t):
    """(day, gold, night) weights."""
    D, G, Nn = (1, 0, 0), (0, 1, 0), (0, 0, 1)
    def mix(a, b, u): return tuple(lerp(a[i], b[i], u) for i in range(3))
    if t < 2.4: return Nn
    if t < 3.2: return mix(Nn, D, ease((t - 2.4) / 0.8))
    if t < 5.0: return D
    if t < 6.4: return mix(D, G, ease((t - 5.0) / 1.4))
    if t < 7.6: return mix(G, Nn, ease((t - 6.4) / 1.2))
    return Nn


def rewind_u(t):
    return ease((t - 2.4) / 0.8) if t > 2.4 else 0.0


def camera_o(t):
    if t < 2.2: return O0 + RUN_V * t
    if t < 2.4: return OMAX
    if t < 3.2: return OMAX * (1 - rewind_u(t))
    return 0.0


def chase_tc(t):
    """Time inside the chase (runs backwards during the rewind)."""
    if t < 2.2: return t
    if t < 2.4: return 2.2
    return 2.2 * (1 - rewind_u(t))


# Hero build schedule: (t0, t1, action, x in cabin widths, on_roof, dir)
SCHED = [
    (3.20, 3.55, "idle", -1.00, False, 1),
    (3.55, 3.66, "dash", -1.32, False, -1),
    (3.66, 4.05, "chop", -1.32, False, -1),
    (4.05, 4.16, "dash", -0.72, False, 1),
    (4.16, 4.55, "hammer", -0.72, False, 1),
    (4.55, 4.66, "dash", 0.74, False, -1),
    (4.66, 5.05, "hammer", 0.74, False, -1),
    (5.05, 5.16, "dash", -0.74, False, 1),
    (5.16, 5.55, "hammer", -0.74, False, 1),
    (5.55, 5.66, "dash", 0.76, False, -1),
    (5.66, 5.98, "hammer", 0.76, False, -1),
    (5.98, 6.10, "jump", -0.05, True, 1),
    (6.10, 6.38, "hammer", -0.05, True, 1),
    (6.38, 6.50, "jump", 0.98, False, -1),
    (6.50, 6.88, "hammer", 0.98, False, -1),
    (6.88, 7.18, "idle", 0.98, False, -1),
    (7.18, 7.48, "jump", 0.12, True, -1),
    (7.48, 7.95, "spear", 0.12, True, -1),
    (7.95, 10.1, "spear", 0.12, True, 1),
]
SWING_T = 0.195


def hammer_hits():
    hits = []
    for t0, t1, act, *_ in SCHED:
        if act in ("hammer", "chop"):
            k = 0
            while t0 + SWING_T * (k + 0.93) < t1:
                hits.append(t0 + SWING_T * (k + 0.93)); k += 1
    return hits


def cabin_p(t):
    if t < 2.2: return 1.0
    if t < 3.2: return 1.0 - rewind_u(t)
    keys = [(4.10, 0.0), (4.55, 0.15), (4.66, 0.15), (5.05, 0.30), (5.16, 0.30), (5.98, 0.60),
            (6.10, 0.60), (6.38, 0.75), (6.50, 0.75), (6.88, 0.95), (7.05, 0.95), (7.25, 1.0)]
    if t <= keys[0][0]: return 0.0
    for (a, pa), (b, pb) in zip(keys, keys[1:]):
        if t <= b: return lerp(pa, pb, (t - a) / (b - a))
    return 1.0


ICONS = [(3.80, "STONE AXE", "axe"), (6.38, "CABIN", "cabin"), (6.88, "SPIKE WALL", "spikes")]
CAPTIONS = [(2.32, 3.15, "LET'S BACK UP"), (3.22, 4.05, "10 HOURS EARLIER"), (4.10, 4.90, "ZOMBIES COME"),
            (4.92, 5.70, "AT SUNSET."), (5.72, 6.50, "SO YOU BUILD."), (6.52, 7.25, "FAST."),
            (7.62, 8.45, "THEY'RE HERE.")]


def ground_y(wx):
    d = (wx - CAB_X) / (1.25 * CAB_W)
    return GY - (0.06 * CAB_W * math.cos(d * math.pi / 2) ** 2 if abs(d) < 1 else 0)


# =========================================================================== static layers
def cumulus(d, x, y, w, h, shade, light, seed=0):
    r = random.Random(seed)
    n = max(4, int(w / (h * 0.55)))
    puffs = []
    for i in range(n):
        u = i / (n - 1)
        bump = math.sin(u * math.pi)
        pr = h * (0.35 + 0.45 * bump) * r.uniform(0.85, 1.15)
        puffs.append((x - w / 2 + u * w, y - bump * h * 0.35 + r.uniform(-h * 0.06, h * 0.06), pr))
    for px, py, pr in puffs:
        d.ellipse([px - pr, py - pr * 0.82, px + pr, py + pr * 1.18], fill=shade)
    d.rectangle([x - w / 2, y - h * 0.05, x + w / 2, y + h * 0.32], fill=shade)
    for px, py, pr in puffs:
        d.ellipse([px - pr * 0.92, py - pr * 0.95, px + pr * 0.92, py + pr * 0.75], fill=light)


def float_island(d, x, y, w, col, col2, seed):
    r = random.Random(seed)
    pts = [(x - w / 2, y)]
    for i in range(1, 8):
        u = i / 8
        pts.append((x - w / 2 + u * w + r.uniform(-w * .03, w * .03), y + w * 0.9 * math.sin(u * math.pi) ** 1.5 * r.uniform(0.7, 1.1)))
    pts.append((x + w / 2, y))
    d.polygon(pts, fill=col)
    d.ellipse([x - w * 0.55, y - w * 0.12, x + w * 0.55, y + w * 0.1], fill=col2)
    for i in range(3):  # little trees
        tx = x + r.uniform(-w * .35, w * .35); tr = w * r.uniform(.12, .2)
        d.ellipse([tx - tr, y - tr * 2.2, tx + tr, y - tr * 0.2], fill=col2)
    for i in range(4):  # dangling vines
        vx = x + r.uniform(-w * .3, w * .3)
        d.line([vx, y, vx + r.uniform(-4, 4) * SS, y + w * r.uniform(0.3, 0.7)], fill=col2, width=int(S(2 * K)))


def bush(d, x, y, w, h, seed, dark=(36, 112, 58), mid=(68, 160, 72), light=(132, 208, 92), hi=(196, 236, 128)):
    """Painterly bush: dark base blobs, mid blobs, sunlit tops (light from upper right)."""
    r = random.Random(seed)
    blobs = []
    n = max(5, int(w / (h * 0.4)))
    for i in range(n):
        u = i / (n - 1)
        bump = math.sin(u * math.pi) ** 0.7
        br = h * (0.3 + 0.35 * bump) * r.uniform(0.8, 1.2)
        blobs.append((x - w / 2 + u * w + r.uniform(-br * .3, br * .3), y - bump * h * 0.55 + r.uniform(-h * .05, h * .05), br))
    for bx, by, br in blobs:
        d.ellipse([bx - br, by - br, bx + br, by + br * 1.3], fill=dark)
    for bx, by, br in blobs:
        d.ellipse([bx - br * 0.85, by - br * 0.95, bx + br * 0.8, by + br * 0.7], fill=mid)
    for bx, by, br in blobs:
        d.ellipse([bx - br * 0.35, by - br * 0.88, bx + br * 0.72, by + br * 0.05], fill=light)
    for bx, by, br in blobs[1::2]:
        d.ellipse([bx + br * 0.1, by - br * 0.8, bx + br * 0.5, by - br * 0.45], fill=hi)


def big_tree(d, x, gy, h, seed):
    r = random.Random(seed)
    trunk, trunk_d = (112, 82, 62), (80, 58, 48)
    tw = h * 0.07
    d.polygon([(x - tw, gy), (x + tw, gy), (x + tw * 0.55, gy - h * 0.62), (x - tw * 0.55, gy - h * 0.62)], fill=trunk)
    d.polygon([(x + tw * 0.15, gy), (x + tw, gy), (x + tw * 0.55, gy - h * 0.62), (x + tw * 0.1, gy - h * 0.62)], fill=trunk_d)
    d.line([(x, gy - h * 0.5), (x + h * 0.2, gy - h * 0.72)], fill=trunk, width=int(tw * 0.6))
    d.line([(x, gy - h * 0.45), (x - h * 0.18, gy - h * 0.66)], fill=trunk, width=int(tw * 0.5))
    for k in range(3):
        cy = gy - h * (0.62 + 0.13 * k)
        cw = h * (0.62 - 0.12 * k)
        bush(d, x + r.uniform(-h * .05, h * .05), cy + cw * 0.25, cw, cw * 0.55, seed * 10 + k)


def boulder(d, x, gy, w, h, seed):
    r = random.Random(seed)
    d.ellipse([x - w / 2, gy - h, x + w / 2, gy + h * 0.18], fill=(104, 108, 112))
    d.ellipse([x - w / 2 + w * .04, gy - h, x + w / 2 - w * .12, gy + h * 0.02], fill=(146, 150, 148))
    d.ellipse([x - w * 0.2, gy - h * 0.9, x + w * 0.25, gy - h * 0.5], fill=(176, 180, 172))
    # moss cap
    d.chord([x - w * 0.46, gy - h * 1.02, x + w * 0.44, gy - h * 0.25], 180, 360, fill=(92, 156, 66))
    for i in range(7):
        mx = x + r.uniform(-w * .4, w * .38)
        d.ellipse([mx - w * .07, gy - h * 0.72, mx + w * .07, gy - h * 0.52], fill=(92, 156, 66))
    d.chord([x - w * 0.3, gy - h * 1.0, x + w * 0.3, gy - h * 0.62], 190, 350, fill=(140, 200, 90))


def vgrad(h, stops):
    """stops: [(pos 0..1, (r,g,b)), ...] -> float32 (h,1,3)."""
    y = np.linspace(0, 1, h)
    out = np.zeros((h, 1, 3), np.float32)
    ps = [p for p, _ in stops]
    for c in range(3):
        out[:, 0, c] = np.interp(y, ps, [col[c] for _, col in stops])
    return out


def to_layer(img2x):
    img = img2x.reduce(SS)
    a = np.asarray(img, dtype=np.float32)
    alpha = a[..., 3:4] / 255.0
    return {"rgb": a[..., :3] * alpha, "a": alpha}


def build_sky():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    def sky(stops):
        g = vgrad(H, [(min(p, 1), c) for p, c in stops])
        return np.repeat(g, W, axis=1)
    hz = YH / H
    day = sky([(0, (34, 118, 214)), (hz * 0.7, (110, 190, 238)), (hz + 0.06, (196, 236, 248)), (1, (196, 236, 248))])
    gold = sky([(0, (64, 92, 176)), (hz * 0.55, (214, 140, 120)), (hz, (255, 196, 120)), (1, (255, 210, 140))])
    night = sky([(0, (6, 10, 32)), (hz * 0.8, (20, 30, 74)), (hz + 0.05, (44, 54, 104)), (1, (44, 54, 104))])
    r = np.random.default_rng(2)
    for _ in range(int(W * H / 5200)):  # stars
        x, y = r.integers(0, W), r.integers(0, int(YH * 0.95))
        b = r.uniform(80, 255)
        night[y, x] = np.minimum(255, night[y, x] + b)
        if b > 220 and 0 < x < W - 1 and 0 < y < H - 1:
            night[y - 1:y + 2, x] += b * 0.3; night[y, x - 1:x + 2] += b * 0.3
    # god rays from the day sun
    rays = Image.new("L", (W, H), 0)
    rd = ImageDraw.Draw(rays)
    sx, sy = SUN_DAY
    rr = random.Random(4)
    for i in range(13):
        a = math.radians(95 + i * 11 + rr.uniform(-3, 3)); sp = math.radians(rr.uniform(1.0, 2.6)); L = 2.5 * max(W, H)
        rd.polygon([(sx, sy), (sx + math.cos(a - sp) * L, sy + math.sin(a - sp) * L),
                    (sx + math.cos(a + sp) * L, sy + math.sin(a + sp) * L)], fill=rr.randint(30, 60))
    rays = np.asarray(rays.filter(ImageFilter.GaussianBlur(10)), np.float32)[..., None] / 255.0
    return day, gold, np.clip(night, 0, 255), rays * np.array([255, 246, 200], np.float32)


SUN_DAY = (0.80 * W, 0.12 * H)
SUN_SET = (0.88 * W, YH + 6)
MOON = (0.20 * W, 0.13 * H if FMT == "yt" else 0.16 * H)


def layer_w(f):
    return int(W + OMAX * f + 40)


def build_far():
    LW = layer_w(0.12)
    img = Image.new("RGBA", (S(LW), S(H)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = random.Random(1)
    sky_top = 0.08 * H if FMT == "yt" else 0.18 * H
    ncl = int(LW / (380 if FMT == "yt" else 300)) + 3
    for i in range(ncl):
        x = r.uniform(-100, LW + 100); y = r.uniform(sky_top, YH - 90 * K)
        w = r.uniform(260, 560) * K * (0.6 + 0.6 * y / YH)
        cumulus(d, S(x), S(y), S(w), S(w * 0.3), (205, 228, 244, 255), (252, 254, 255, 255), seed=i)
    for i in range(int(LW / 520) + 2):  # far floating islands (the world's signature)
        x = r.uniform(0, LW); y = r.uniform(sky_top + 40 * K, YH - 160 * K); w = r.uniform(50, 120) * K
        float_island(d, S(x), S(y), S(w), (118, 150, 168, 255), (122, 168, 150, 255), seed=i)
    # two rows of hazy hills
    for row, (col, base, amp) in enumerate([((150, 200, 186, 255), YH - 34 * K, 40 * K), ((112, 184, 132, 255), YH + 10 * K, 30 * K)]):
        pts = [(0, S(H))]
        ph = r.uniform(0, 6)
        for xx in range(0, LW + 40, 20):
            y = base - amp * (0.6 * math.sin(xx / (260 * K) + ph) + 0.4 * math.sin(xx / (97 * K) + ph * 2))
            pts.append((S(xx), S(y)))
        pts.append((S(LW + 40), S(H)))
        d.polygon(pts, fill=col)
    img = img.filter(ImageFilter.GaussianBlur(S(1.3)))
    return to_layer(img)


def build_mid():
    LW = layer_w(0.45)
    img = Image.new("RGBA", (S(LW), S(H)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = random.Random(3)
    # soft back tree line
    x = -60
    while x < LW + 60:
        w = r.uniform(140, 260) * K
        bush(d, S(x), S(YH + 70 * K), S(w), S(w * 0.55), seed=1000 + int(x),
             dark=(58, 126, 92), mid=(84, 160, 104), light=(130, 198, 120), hi=(170, 220, 140))
        x += w * 0.6
    # tall trees (portrait gets taller ones so the frame is filled top to bottom)
    th = (0.62 if FMT == "yt" else 0.55) * H
    x = r.uniform(0, 200)
    while x < LW:
        big_tree(d, S(x), S(GY + 10), S(th * r.uniform(0.75, 1.05)), seed=int(x))
        x += r.uniform(700, 1100) * K
    # bushes along the ground line
    x = -80
    while x < LW + 80:
        w = r.uniform(170, 330) * K
        bush(d, S(x), S(GY + 6), S(w), S(w * r.uniform(0.5, 0.75)), seed=int(x * 7))
        x += w * r.uniform(0.55, 0.8)
    img = img.filter(ImageFilter.GaussianBlur(S(0.5)))
    return to_layer(img)


def build_ground():
    LW = layer_w(1.0)
    surf = np.zeros((H, LW, 4), np.float32)
    g = vgrad(H - YH, [(0, (150, 214, 84)), (0.02, (118, 196, 72)), (0.25, (84, 162, 60)), (1, (34, 96, 44))])
    xs = np.arange(LW)
    gy = np.array([ground_y(x) for x in xs], np.float32)
    rows = np.arange(YH, H)[:, None]
    mask = (rows >= gy[None, :] - 1).astype(np.float32)
    surf[YH:, :, :3] = np.repeat(g, LW, axis=1)
    surf[YH:, :, 3] = mask * 255
    img = Image.fromarray(surf.astype(np.uint8), "RGBA").resize((S(LW), S(H)), Image.BILINEAR)
    d = ImageDraw.Draw(img)
    r = random.Random(7)
    # boulders behind and around the build site ("giant boulders at your back")
    boulder(d, S(CAB_X + 0.62 * CAB_W), S(ground_y(CAB_X + 0.62 * CAB_W) + 4), S(0.95 * CAB_W), S(0.62 * CAB_W), 1)
    boulder(d, S(CAB_X + 1.25 * CAB_W), S(GY + 6), S(0.6 * CAB_W), S(0.38 * CAB_W), 2)
    boulder(d, S(CAB_X - 1.75 * CAB_W), S(GY + 8), S(0.5 * CAB_W), S(0.3 * CAB_W), 3)
    for i in range(int(LW / 900)):
        bx = r.uniform(CAB_X + 2.5 * CAB_W, LW)
        boulder(d, S(bx), S(GY + 6), S(r.uniform(90, 190) * K), S(r.uniform(60, 110) * K), 10 + i)
    # grass tufts along the lip
    for i in range(int(LW / 9)):
        gx = r.uniform(0, LW); gyy = ground_y(gx) + r.uniform(0, 6)
        hh = r.uniform(6, 18) * K
        d.polygon([(S(gx - 4 * K), S(gyy + 2)), (S(gx + 4 * K), S(gyy + 2)), (S(gx + r.uniform(-5, 5) * K), S(gyy - hh))],
                  fill=r.choice([(160, 222, 92), (132, 204, 78), (110, 186, 70)]))
    # meadow texture: blades, flowers, pebbles (fills the lower part of the portrait frame)
    for i in range(int(LW * (H - GY) / 900)):
        gx = r.uniform(0, LW); gyy = r.uniform(GY + 14, H)
        depth = (gyy - GY) / (H - GY)
        hh = (10 + 40 * depth) * K
        c = lerpc((120, 196, 76), (30, 82, 40), depth * r.uniform(0.7, 1.1))
        d.polygon([(S(gx - 3 * K), S(gyy)), (S(gx + 3 * K), S(gyy)), (S(gx + r.uniform(-12, 12) * K), S(gyy - hh))], fill=c)
    for i in range(int(LW * (H - GY) / 9000)):
        fx = r.uniform(0, LW); fy = r.uniform(GY + 20, H * 0.97)
        fr = (2.5 + 6 * (fy - GY) / (H - GY)) * K
        col = r.choice([(255, 255, 240), (255, 220, 90), (255, 170, 190), (190, 210, 255)])
        d.ellipse([S(fx - fr), S(fy - fr), S(fx + fr), S(fy + fr)], fill=col)
        d.ellipse([S(fx - fr * .35), S(fy - fr * .35), S(fx + fr * .35), S(fy + fr * .35)], fill=(255, 200, 60))
    return to_layer(img)


def build_fg():
    LW = layer_w(1.3)
    img = Image.new("RGBA", (S(LW), S(H)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = random.Random(9)
    cols = [(14, 34, 24, 255), (20, 46, 30, 255), (26, 58, 36, 255)]
    bh = (0.14 if FMT == "yt" else 0.11) * H
    for i in range(int(LW / 7)):
        x = r.uniform(-20, LW + 20); hh = bh * r.uniform(0.25, 1.0) * (1.2 if r.random() < 0.08 else 1)
        lean = r.uniform(-0.5, 0.5) * hh
        w = r.uniform(5, 12) * K
        d.polygon([(S(x - w), S(H + 5)), (S(x + w), S(H + 5)), (S(x + w * 0.4 + lean * 0.6), S(H - hh * 0.6)),
                   (S(x + lean), S(H - hh))], fill=r.choice(cols))
    x = r.uniform(0, 300)
    while x < LW:  # broad leaves
        for k in range(r.randint(2, 4)):
            L = r.uniform(80, 170) * K; a = math.radians(r.uniform(-150, -30))
            cx, cy = x + math.cos(a) * L * 0.5, H - 10 + math.sin(a) * L * 0.5
            pts = []
            for j in range(13):
                u = j / 12; ww = math.sin(u * math.pi) * L * 0.22
                px, py = x + math.cos(a) * L * u, H - 10 + math.sin(a) * L * u
                pts.append((px - math.sin(a) * ww, py + math.cos(a) * ww))
            for j in range(12, -1, -1):
                u = j / 12; ww = math.sin(u * math.pi) * L * 0.22
                px, py = x + math.cos(a) * L * u, H - 10 + math.sin(a) * L * u
                pts.append((px + math.sin(a) * ww, py - math.cos(a) * ww))
            d.polygon([(S(px), S(py)) for px, py in pts], fill=r.choice(cols))
        x += r.uniform(380, 700) * K
    return to_layer(img)


# =========================================================================== characters
INK = (14, 13, 20, 255)
SCARF = (226, 38, 40, 255)
SCARF_D = (150, 18, 28, 255)


def limb(d, pts, w, col=INK):
    d.line([(S(x), S(y)) for x, y in pts], fill=col, width=max(1, int(S(w))), joint="curve")
    for x, y in pts:
        d.ellipse([S(x - w / 2), S(y - w / 2), S(x + w / 2), S(y + w / 2)], fill=col)


def hero(d, e, glows, x, y, h, pose, dir, t, ph=0.0, swing=0.0, tool=None, night=0.0, flow=None):
    """Red-scarf stick hero. y = feet. d = lit canvas, e = emissive canvas (may be None)."""
    run = pose in ("run", "dash")
    lean = 0.32 if run else (0.12 if pose in ("hammer", "chop") else 0.03)
    bob = -abs(math.sin(ph)) * 0.04 * h if run else (math.sin(t * 3) * 0.006 * h)
    hip = (x, y - 0.43 * h + bob)
    if pose == "jump": hip = (x, y - 0.40 * h)
    sho = (hip[0] + math.sin(lean) * 0.27 * h * dir, hip[1] - math.cos(lean) * 0.27 * h)
    head = (sho[0] + math.sin(lean) * 0.165 * h * dir, sho[1] - math.cos(lean) * 0.165 * h)
    neck = (sho[0] + math.sin(lean) * 0.03 * h * dir, sho[1] - 0.03 * h)
    Lt, Ls, Lu, Lf = 0.22 * h, 0.215 * h, 0.15 * h, 0.14 * h
    lw = 0.058 * h

    def leg(a, b):
        kn = (hip[0] + dir * math.sin(a) * Lt, hip[1] + math.cos(a) * Lt)
        ft = (kn[0] + dir * math.sin(a - b) * Ls, kn[1] + math.cos(a - b) * Ls)
        return [hip, kn, ft]

    def arm(a, el):
        eb = (sho[0] + dir * math.sin(a) * Lu, sho[1] + math.cos(a) * Lu)
        hd = (eb[0] + dir * math.sin(a + el) * Lf, eb[1] + math.cos(a + el) * Lf)
        return [sho, eb, hd]

    if run:
        legs = [leg(0.9 * math.sin(ph + k), 0.2 + 1.5 * max(0, math.cos(ph + k))) for k in (math.pi, 0)]
        arms = [arm(-0.95 * math.sin(ph + k), 1.4) for k in (0, math.pi)]
    elif pose == "jump":
        legs = [leg(-0.3, 1.2), leg(0.7, 1.6)]
        arms = [arm(-2.4, 0.4), arm(2.6, 0.3)]
    else:
        legs = [leg(-0.16, 0.06), leg(0.16, 0.1)]
        if pose in ("hammer", "chop"):
            s = swing % 1.0
            a = lerp(0.9, -2.7, ease(s / 0.6)) if s < 0.6 else lerp(-2.7, 1.0, ((s - 0.6) / 0.4) ** 1.6)
            arms = [arm(0.5, 0.7), arm(a, 0.25)]
        elif pose == "spear":
            arms = [arm(0.25, 0.5), arm(0.75, -1.65)]
        else:
            arms = [arm(0.18, 0.25), arm(-0.12, 0.35)]

    # scarf tails (behind body)
    flow = flow if flow is not None else (1.0 if run or pose == "jump" else 0.35)
    nx, ny = neck[0] - dir * 0.04 * h, neck[1] + 0.01 * h
    sc_c = e if (e is not None and night > 0.5) else d
    cS, cD = (lerpc(SCARF, (150, 26, 40, 255), night), lerpc(SCARF_D, (96, 14, 30, 255), night)) if sc_c is e else (SCARF, SCARF_D)
    for k, col, Lk in ((1, cD, 0.82), (0, cS, 1.0)):
        L = h * (0.42 + 0.36 * flow) * Lk
        droop = 0.12 + 0.6 * (1 - flow)
        top, bot = [], []
        for j in range(15):
            s = j / 14
            cx = nx - dir * s * L * math.cos(droop * 0.9)
            cy = ny + s * L * droop * 0.85 + math.sin(s * 6.5 - t * (9 + 9 * flow) + k * 1.4) * 0.05 * h * s * (0.4 + flow) + k * 0.02 * h
            wd = 0.036 * h * (1 - 0.55 * s)
            top.append((S(cx), S(cy - wd))); bot.append((S(cx), S(cy + wd)))
        sc_c.polygon(top + bot[::-1], fill=col)
    limb(d, legs[0], lw); limb(d, arms[0], lw * 0.9)
    limb(d, [hip, sho], lw * 1.15)
    limb(d, legs[1], lw)
    # scarf knot
    sc_c.rounded_rectangle([S(neck[0] - 0.075 * h), S(neck[1] - 0.03 * h), S(neck[0] + 0.075 * h), S(neck[1] + 0.035 * h)],
                        radius=S(0.03 * h), fill=cS)
    if sc_c is e:  # re-draw the head over the emissive knot
        r = 0.128 * h
        e.ellipse([S(head[0] - r), S(head[1] - r), S(head[0] + r), S(head[1] + r)], fill=INK)
        for i in (0, 1):
            ex = head[0] + dir * (0.03 + 0.052 * i) * h; ey = head[1] - 0.004 * h
            e.ellipse([S(ex - 0.018 * h), S(ey - 0.032 * h), S(ex + 0.018 * h), S(ey + 0.032 * h)], fill=(250, 250, 245, 255))
    r = 0.128 * h
    d.ellipse([S(head[0] - r), S(head[1] - r), S(head[0] + r), S(head[1] + r)], fill=INK)
    for i in (0, 1):  # two white eye glints
        ex = head[0] + dir * (0.03 + 0.052 * i) * h; ey = head[1] - 0.004 * h
        d.ellipse([S(ex - 0.018 * h), S(ey - 0.032 * h), S(ex + 0.018 * h), S(ey + 0.032 * h)], fill=(250, 250, 245, 255))
    hand = arms[1][2]
    if tool in ("hammer", "axe"):
        a = math.atan2(arms[1][2][1] - arms[1][1][1], arms[1][2][0] - arms[1][1][0])
        tip = (hand[0] + math.cos(a) * 0.2 * h, hand[1] + math.sin(a) * 0.2 * h)
        d.line([S(hand[0]), S(hand[1]), S(tip[0]), S(tip[1])], fill=(122, 82, 50, 255), width=int(S(0.03 * h)))
        px, py = -math.sin(a), math.cos(a)
        hw = 0.07 * h
        col = (150, 152, 160, 255) if tool == "axe" else (110, 78, 52, 255)
        d.polygon([(S(tip[0] - px * hw * .4 - math.cos(a) * 0.03 * h), S(tip[1] - py * hw * .4 - math.sin(a) * 0.03 * h)),
                   (S(tip[0] + px * hw), S(tip[1] + py * hw)),
                   (S(tip[0] + px * hw + math.cos(a) * 0.05 * h), S(tip[1] + py * hw + math.sin(a) * 0.05 * h)),
                   (S(tip[0] - px * hw * .4 + math.cos(a) * 0.04 * h), S(tip[1] - py * hw * .4 + math.sin(a) * 0.04 * h))], fill=col)
    limb(d, arms[1], lw * 0.9)
    if tool == "spear":
        top_y, bot_y = hand[1] - 0.62 * h, hand[1] + 0.34 * h
        d.line([S(hand[0]), S(bot_y), S(hand[0]), S(top_y)], fill=(122, 82, 50, 255), width=int(S(0.028 * h)))
        tip = [(hand[0], top_y - 0.13 * h), (hand[0] + 0.035 * h, top_y - 0.03 * h), (hand[0], top_y + 0.02 * h), (hand[0] - 0.035 * h, top_y - 0.03 * h)]
        (e or d).polygon([(S(a), S(b)) for a, b in tip], fill=(150, 246, 255, 255))
        glows.append((hand[0], top_y - 0.05 * h, 0.22 * h, (90, 220, 255), 0.9 + 0.1 * math.sin(t * 9)))
    return head


def zombie(d, e, glows, x, y, h, ph, dir, seed, pose="run", eye_glow=1.0):
    r = random.Random(seed)
    col = (8, 6, 12, 255)
    lean = 0.62 if pose == "run" else 0.95
    hip = (x, y - 0.40 * h)
    sho = (hip[0] + dir * math.sin(lean) * 0.27 * h, hip[1] - math.cos(lean) * 0.27 * h)
    head = (sho[0] + dir * 0.10 * h, sho[1] - 0.07 * h)
    lw = 0.06 * h
    Lt = Ls = 0.215 * h

    def leg(a, b):
        kn = (hip[0] + dir * math.sin(a) * Lt, hip[1] + math.cos(a) * Lt)
        return [hip, kn, (kn[0] + dir * math.sin(a - b) * Ls, kn[1] + math.cos(a - b) * Ls)]

    if pose == "run":
        legs = [leg(0.8 * math.sin(ph + k), 0.3 + 1.2 * max(0, math.cos(ph + k))) for k in (0, math.pi)]
        arm_a = [1.45 + 0.25 * math.sin(ph), 1.25 + 0.25 * math.sin(ph + 2)]
    else:
        legs = [leg(-0.9, 0.9), leg(-0.5, 1.3)]
        arm_a = [2.1, 1.7]
    for lg in legs: limb(d, lg, lw, col)
    # ragged torso
    pts = []
    for j in range(10):
        u = j / 9
        cx, cy = lerp(hip[0], sho[0], u), lerp(hip[1], sho[1], u)
        pts.append((cx - dir * 0.07 * h * math.cos(lean) + r.uniform(-1, 1) * 0.02 * h, cy - 0.07 * h * math.sin(lean) * dir * 0))
    body = [(hip[0] - 0.09 * h, hip[1] + 0.06 * h)]
    for j in range(7):  # rag hem
        body.append((hip[0] - 0.09 * h + j * 0.03 * h, hip[1] + (0.11 if j % 2 else 0.03) * h + r.uniform(0, .03) * h))
    body += [(hip[0] + 0.1 * h, hip[1]), (sho[0] + dir * 0.07 * h, sho[1] - 0.02 * h), (sho[0] - dir * 0.06 * h, sho[1] - 0.06 * h)]
    d.polygon([(S(a), S(b)) for a, b in body], fill=col)
    limb(d, [hip, sho], lw * 1.6, col)
    for a in arm_a:
        eb = (sho[0] + dir * math.sin(a) * 0.17 * h, sho[1] + math.cos(a) * 0.17 * h)
        hd = (eb[0] + dir * math.sin(a + 0.15) * 0.17 * h, eb[1] + math.cos(a + 0.15) * 0.17 * h)
        limb(d, [sho, eb, hd], lw * 0.8, col)
        for c in (-0.5, 0, 0.5):  # claws
            d.line([S(hd[0]), S(hd[1]), S(hd[0] + dir * math.sin(a + c) * 0.06 * h), S(hd[1] + math.cos(a + c) * 0.06 * h)],
                   fill=col, width=max(1, int(S(lw * 0.3))))
    hr = 0.105 * h
    d.ellipse([S(head[0] - hr), S(head[1] - hr), S(head[0] + hr), S(head[1] + hr * 1.05)], fill=col)
    for k in range(4):  # lumpy, messy hair
        a = math.radians(200 + k * 35)
        d.polygon([(S(head[0] + math.cos(a) * hr * .8), S(head[1] + math.sin(a) * hr * .8)),
                   (S(head[0] + math.cos(a) * hr * 1.45), S(head[1] + math.sin(a) * hr * 1.45 + r.uniform(-3, 3))),
                   (S(head[0] + math.cos(a + .4) * hr * .8), S(head[1] + math.sin(a + .4) * hr * .8))], fill=col)
    eyes(e or d, glows, head[0] + dir * 0.045 * h, head[1] - 0.005 * h, 0.034 * h, dir, eye_glow)


def eyes(e, glows, x, y, s, dir=1, amt=1.0, open_=1.0):
    if amt <= 0.01 or open_ <= 0.02: return
    c = (255, 168, 50, 255)
    for i in (-1, 1):
        ex = x + i * s * 0.95
        tilt = i * dir * 0.35 * s
        e.polygon([(S(ex - s * 0.7), S(y - tilt - s * 0.25 * open_)), (S(ex + s * 0.7), S(y + tilt - s * 0.45 * open_)),
                   (S(ex + s * 0.5), S(y + tilt + s * 0.35 * open_)), (S(ex - s * 0.6), S(y - tilt + s * 0.4 * open_))], fill=c)
    glows.append((x, y, s * 4.0, (255, 120, 20), 0.75 * amt * open_))


def cabin(d, e, glows, cx, gy, CW, p, t, night):
    if p <= 0.001: return
    WH = 0.56 * CW
    fh = 0.1 * CW
    def seg(a, b): return min(max((p - a) / (b - a), 0.0), 1.0)
    u_sp = seg(0.75, 0.95)
    nsp = 15
    spx = [cx + (-0.95 + 1.9 * i / (nsp - 1)) * CW for i in range(nsp)]
    def spike(x, base, h, a, col):
        dx = math.sin(a) * h
        d.polygon([(S(x - 0.028 * CW), S(base)), (S(x + 0.028 * CW), S(base)),
                   (S(x + dx + 0.025 * CW * 0.6), S(base - h * 0.85)), (S(x + dx), S(base - h)), (S(x + dx - 0.025 * CW * 0.6), S(base - h * 0.85))], fill=col)
    # back row of spikes (behind the cabin)
    for i, x in enumerate(spx):
        k = min(max(u_sp * nsp * 1.0 - i, 0), 1)
        if k > 0: spike(x + 0.03 * CW, gy - 0.05 * CW, 0.24 * CW * ease(k), (x - cx) / CW * 0.35, (96, 64, 42, 255))
    # foundation
    u = seg(0.0, 0.15)
    ns = 7
    for i in range(int(math.ceil(u * ns))):
        x0 = cx - 0.58 * CW + i * (1.16 * CW / ns)
        d.rounded_rectangle([S(x0), S(gy - fh), S(x0 + 1.16 * CW / ns - 2), S(gy + 0.01 * CW)], radius=S(0.025 * CW), fill=(118, 120, 128, 255))
        d.rounded_rectangle([S(x0 + 3), S(gy - fh + 2), S(x0 + 1.16 * CW / ns - 6), S(gy - fh * 0.45)], radius=S(0.02 * CW), fill=(162, 164, 170, 255))
    base = gy - fh
    # walls (logs)
    u = seg(0.30, 0.60)
    nl = 7
    lh = WH / nl
    for i in range(nl):
        k = min(max(u * nl - i, 0), 1)
        if k <= 0: break
        drop = (1 - ease(k)) * 0.25 * CW
        y1 = base - (i + 1) * lh - drop
        col = (156, 104, 62, 255) if i % 2 else (140, 92, 54, 255)
        d.rounded_rectangle([S(cx - 0.52 * CW), S(y1), S(cx + 0.52 * CW), S(y1 + lh)], radius=S(lh * 0.45), fill=col)
        d.line([S(cx - 0.48 * CW), S(y1 + lh * 0.3), S(cx + 0.48 * CW), S(y1 + lh * 0.3)], fill=(184, 134, 84, 255), width=int(S(lh * 0.12)))
        for sx in (-0.53, 0.53):
            d.ellipse([S(cx + sx * CW - lh * 0.5), S(y1), S(cx + sx * CW + lh * 0.5), S(y1 + lh)], fill=(200, 160, 108, 255))
            d.ellipse([S(cx + sx * CW - lh * 0.2), S(y1 + lh * 0.3), S(cx + sx * CW + lh * 0.2), S(y1 + lh * 0.7)], fill=(150, 108, 66, 255))
    if u > 0.5:  # door
        dh = WH * 0.62 * min(1, (u - 0.5) * 4)
        d.rounded_rectangle([S(cx - 0.13 * CW), S(base - dh), S(cx + 0.13 * CW), S(base)], radius=S(0.05 * CW), fill=(70, 44, 30, 255))
        for k in (-0.045, 0.045):
            d.line([S(cx + k * CW), S(base - dh + 6), S(cx + k * CW), S(base)], fill=(52, 32, 22, 255), width=int(S(0.01 * CW)))
    if u >= 1:  # window, warm at night
        wx, wy, ws = cx + 0.32 * CW, base - WH * 0.62, 0.075 * CW
        lit = night > 0.3
        d.rectangle([S(wx - ws), S(wy - ws), S(wx + ws), S(wy + ws)], fill=(60, 40, 28, 255))
        (e if (lit and e) else d).rectangle([S(wx - ws * .75), S(wy - ws * .75), S(wx + ws * .75), S(wy + ws * .75)],
                                            fill=(255, 196, 96, 255) if lit else (40, 30, 30, 255))
        d.line([S(wx), S(wy - ws), S(wx), S(wy + ws)], fill=(60, 40, 28, 255), width=int(S(0.012 * CW)))
        d.line([S(wx - ws), S(wy), S(wx + ws), S(wy)], fill=(60, 40, 28, 255), width=int(S(0.012 * CW)))
        if lit: glows.append((wx, wy, 0.25 * CW, (255, 170, 70), 0.6 * night))
    # corner posts
    u = seg(0.15, 0.30)
    if u > 0:
        for sx in (-0.56, 0.56):
            ph_ = base - (WH + 0.04 * CW) * ease(u)
            d.rectangle([S(cx + sx * CW - 0.04 * CW), S(ph_), S(cx + sx * CW + 0.04 * CW), S(base)], fill=(104, 68, 42, 255))
            d.rectangle([S(cx + sx * CW), S(ph_), S(cx + sx * CW + 0.04 * CW), S(base)], fill=(84, 54, 34, 255))
    # roof
    u = seg(0.60, 0.75)
    if u > 0:
        drop = (1 - ease(u)) * 0.5 * CW
        ry = base - WH - drop
        peak = ry - 0.34 * CW
        d.polygon([(S(cx - 0.72 * CW), S(ry + 0.04 * CW)), (S(cx), S(peak)), (S(cx + 0.72 * CW), S(ry + 0.04 * CW))], fill=(96, 56, 36, 255))
        d.polygon([(S(cx - 0.64 * CW), S(ry)), (S(cx), S(peak + 0.05 * CW)), (S(cx + 0.64 * CW), S(ry))], fill=(132, 78, 48, 255))
        for k in range(1, 8):  # shingle lines
            f = k / 8
            d.line([S(cx - 0.64 * CW * (1 - f) - 0.02 * CW), S(ry - (ry - peak - 0.05 * CW) * f),
                    S(cx + 0.64 * CW * (1 - f) + 0.02 * CW), S(ry - (ry - peak - 0.05 * CW) * f)], fill=(110, 64, 40, 255), width=int(S(0.01 * CW)))
    # front spikes, angled outward, gap for the door
    for i, x in enumerate(spx):
        if abs(x - cx) < 0.16 * CW: continue
        k = min(max(u_sp * nsp * 1.0 - i, 0), 1)
        if k > 0:
            spike(x, gy + 0.05 * CW, 0.3 * CW * ease(k), (x - cx) / CW * 0.45, (142, 96, 58, 255))
            d.line([S(x), S(gy + 0.05 * CW), S(x + math.sin((x - cx) / CW * 0.45) * 0.3 * CW * ease(k)),
                    S(gy + 0.05 * CW - 0.3 * CW * ease(k))], fill=(112, 74, 46, 255), width=int(S(0.012 * CW)))
    # torches
    u = seg(0.95, 1.0)
    if u > 0:
        for sx in (-1.12, 1.12):
            tx = cx + sx * CW
            d.line([S(tx), S(gy + 0.03 * CW), S(tx), S(gy - 0.42 * CW)], fill=(92, 60, 38, 255), width=int(S(0.03 * CW)))
            fl = 1 + 0.15 * math.sin(t * 23 + sx * 5) + 0.08 * math.sin(t * 41)
            fh_ = 0.13 * CW * ease(u) * fl
            fy = gy - 0.42 * CW
            tgt = e or d
            tgt.polygon([(S(tx - 0.035 * CW), S(fy)), (S(tx + 0.035 * CW), S(fy)), (S(tx + 0.01 * CW * math.sin(t * 17)), S(fy - fh_))], fill=(255, 150, 40, 255))
            tgt.polygon([(S(tx - 0.018 * CW), S(fy)), (S(tx + 0.018 * CW), S(fy)), (S(tx), S(fy - fh_ * 0.6))], fill=(255, 236, 140, 255))
            glows.append((tx, fy - fh_ * 0.4, 0.5 * CW, (255, 140, 40), (0.35 + 0.65 * night) * ease(u) * fl))


# =========================================================================== glows / compositing
_gl = {}


def glow_sprite(r):
    r = max(2, int(r))
    if r not in _gl:
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32)
        dd = np.sqrt(xx ** 2 + yy ** 2) / r
        _gl[r] = (np.exp(-dd ** 2 * 4.5) * 0.8 + np.clip(1 - dd, 0, 1) ** 3 * 0.4)[..., None]
    return _gl[r]


def add_glow(fr, x, y, r, col, amt):
    if amt <= 0.003: return
    g = glow_sprite(r); R = g.shape[0] // 2
    x, y = int(x), int(y)
    x0, y0, x1, y1 = max(0, x - R), max(0, y - R), min(W, x + R + 1), min(H, y + R + 1)
    if x0 >= x1 or y0 >= y1: return
    fr[y0:y1, x0:x1] += g[y0 - (y - R):y1 - (y - R), x0 - (x - R):x1 - (x - R)] * (np.array(col, np.float32) * amt)


def comp(fr, L, x0, mult, add):
    x0 = int(round(x0))
    rgb = L["rgb"][:, x0:x0 + W]; a = L["a"][:, x0:x0 + W]
    fr *= (1 - a)
    fr += rgb * mult + a * add


def comp_img(fr, img2x, mult=None, add=None):
    a = np.asarray(img2x.reduce(SS), np.float32)
    al = a[..., 3:4] / 255.0
    fr *= (1 - al)
    if mult is None:
        fr += a[..., :3] * al
    else:
        fr += a[..., :3] * al * mult + al * add


GRADE = {"d": (np.array([1.0, 1.0, 1.0], np.float32), np.zeros(3, np.float32)),
         "g": (np.array([1.10, 0.86, 0.64], np.float32), np.array([14, 4, 0], np.float32)),
         "n": (np.array([0.25, 0.31, 0.58], np.float32), np.array([3, 5, 16], np.float32))}


def grade(w):
    m = GRADE["d"][0] * w[0] + GRADE["g"][0] * w[1] + GRADE["n"][0] * w[2]
    a = GRADE["d"][1] * w[0] + GRADE["g"][1] * w[1] + GRADE["n"][1] * w[2]
    return m, a


# =========================================================================== UI
def text_c(d, xy, txt, size, fill=(255, 255, 255), weight="Black", stroke=None, anchor="mm", sw=None):
    f = font(size, weight)
    sw = sw if sw is not None else max(3, int(size * 0.09))
    d.text(xy, txt, font=f, fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=stroke or (16, 14, 26))


def pop_scale(age):
    if age < 0: return 0
    if age < 0.12: return lerp(0.6, 1.12, age / 0.12)
    if age < 0.22: return lerp(1.12, 1.0, (age - 0.12) / 0.1)
    return 1.0


def draw_icon(d, kind, cx, cy, s):
    if kind == "axe":
        d.line([cx - s * .45, cy + s * .5, cx + s * .3, cy - s * .35], fill=(130, 86, 50), width=int(s * .14))
        d.polygon([(cx + s * .05, cy - s * .55), (cx + s * .55, cy - s * .2), (cx + s * .35, cy + s * .05), (cx + s * .02, cy - s * .2)], fill=(140, 144, 154))
    elif kind == "cabin":
        d.rectangle([cx - s * .45, cy - s * .1, cx + s * .45, cy + s * .5], fill=(156, 104, 62))
        d.polygon([(cx - s * .6, cy - s * .05), (cx, cy - s * .55), (cx + s * .6, cy - s * .05)], fill=(110, 64, 40))
        d.rectangle([cx - s * .12, cy + s * .12, cx + s * .12, cy + s * .5], fill=(70, 44, 30))
    else:
        for i, a in zip((-1, 0, 1), (-0.35, 0, 0.35)):
            bx = cx + i * s * .32
            d.polygon([(bx - s * .09, cy + s * .5), (bx + s * .09, cy + s * .5), (bx + math.sin(a) * s * .9, cy - s * .5)], fill=(150, 100, 60))


def draw_ui(img, t, st):
    d = ImageDraw.Draw(img)
    # sun timer
    if 3.25 < t < 8.5:
        tx, ty, ts = TIMER
        a_in = ease((t - 3.25) / 0.2) * (1 - ease((t - 8.3) / 0.2))
        u = min(max((t - 3.35) / (7.3 - 3.35), 0), 1)
        mins = int(round((1 - u) * 600))
        txt = f"{mins // 60}:{mins % 60:02d}"
        red = t > 7.3
        blink = not red or int(t * 4) % 2 == 0
        r = 26 * ts
        cx, cy = tx + r, ty + r
        if st["night"] > 0.5:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(236, 236, 255), outline=(16, 14, 26), width=int(4 * ts))
            d.ellipse([cx - r * .35, cy - r * 1.05, cx + r * 1.3, cy + r * .7], fill=(30, 36, 80))
        else:
            for k in range(8):
                a = k * math.pi / 4 + t
                d.line([cx + math.cos(a) * r * 1.15, cy + math.sin(a) * r * 1.15, cx + math.cos(a) * r * 1.5, cy + math.sin(a) * r * 1.5],
                       fill=(255, 210, 60), width=int(5 * ts))
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 210, 60), outline=(16, 14, 26), width=int(4 * ts))
        if a_in > 0.05 and blink:
            text_c(d, (cx + r * 1.9, cy + 2), txt, 54 * ts, fill=(255, 70, 60) if red else (255, 255, 255), weight="ExtraBold", anchor="lm")
    # crafting icons
    for t0, label, kind in ICONS:
        age = t - t0
        if 0 <= age < 0.95:
            sc = pop_scale(age)
            x, y = st["icon_xy"].get(label, (W / 2, H / 2))
            x = min(max(x, 140 * K), (0.80 if FMT == "reel" else 0.95) * W - 140 * K)
            if FMT == "reel" and y < 0.30 * H:  # roof work: keep the icon clear of the timer and captions
                y, x = 0.30 * H, x - 0.2 * W
            y = y - 40 * K * ease(age / 0.95)
            s = 46 * K * sc
            d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 255, 255), outline=(16, 14, 26), width=int(5 * K))
            draw_icon(d, kind, x, y, s * 0.9)
            if age < 0.85:
                text_c(d, (x, y + s + 26 * K), label, 34 * K * sc, weight="ExtraBold")
    # captions (2-3 words)
    for a, b, txt in CAPTIONS:
        if a <= t <= b:
            sc = pop_scale(t - a)
            maxw = (0.76 if FMT == "reel" else 0.8) * W   # reel: stay inside the left 5% / right 15% margins
            fit = min(1.0, maxw / d.textlength(txt, font=font(CAP_SIZE)))
            text_c(d, (CAP_X, CAP_Y), txt, CAP_SIZE * fit * sc, sw=int(CAP_SIZE * fit * 0.11))
    # end card
    if t >= 8.45:
        lines = [(8.50, "WHAT IF YOU HAD", 0.42, (255, 214, 90)), (8.62, "10 HOURS", 1.0, (255, 255, 255)),
                 (8.78, "TO BUILD A", 0.48, (255, 255, 255)), (8.92, "ZOMBIE-PROOF", 0.62, (110, 255, 110)),
                 (8.92, "HOME?", 0.62, (110, 255, 110))]
        base = 170 if FMT == "yt" else 150
        ys = ([0.19, 0.33, 0.47, 0.58, 0.69] if FMT == "yt" else [0.24, 0.31, 0.375, 0.43, 0.485])
        cx = W / 2 if FMT == "yt" else 0.46 * W
        for (t0, txt, sz, col), yf in zip(lines, ys):
            if t >= t0:
                text_c(d, (cx, yf * H), txt, base * sz * pop_scale(t - t0), fill=col, sw=int(base * sz * 0.1))
        if t >= 9.15:
            sc = pop_scale(t - 9.15)
            q = "What would you build first?"
            qs = (54 if FMT == "yt" else 56) * sc
            qy = (0.84 if FMT == "yt" else 0.57) * H
            f = font(qs, "ExtraBold")
            tw = d.textlength(q, font=f)
            d.rounded_rectangle([cx - tw / 2 - 30, qy - qs * 0.85, cx + tw / 2 + 30, qy + qs * 0.85], radius=int(qs * 0.85), fill=(226, 38, 40))
            text_c(d, (cx, qy), q, qs, weight="ExtraBold", sw=0)
            text_c(d, (cx, qy + qs * 1.65), "Tell me in the comments", qs * 0.62, weight="Bold", sw=int(qs * 0.06))


# =========================================================================== frame
FIREFLIES = [(random.Random(i).uniform(-200, W + OMAX * 0.8), random.Random(i * 7 + 1).uniform(YH - 0.1 * H, GY + 0.08 * H),
              random.Random(i * 3).uniform(0, 6.28)) for i in range(int(70 * (W * H) / (1920 * 1080)) + 40)]
EYES = []
_er = random.Random(12)
EYES.append((7.55, 0.07 * W if FMT == "yt" else 0.16 * W, GY - 70 * K))
for i in range(5):
    EYES.append((7.9 + i * 0.06, _er.uniform(0.03, 0.97) * W, GY - _er.uniform(30, 130) * K))
for i in range(int(26 if FMT == "yt" else 30)):
    for _ in range(20):
        x = _er.uniform(0.02, 0.98) * W
        if abs(x - CAB_X) > 1.25 * CAB_W: break
    y = GY - _er.uniform(20, 150) * K if (FMT == "yt" or _er.random() < 0.55) else _er.uniform(GY + 40, 0.76 * H)
    EYES.append((8.15 + _er.uniform(0, 0.35), x, y))
EYES = [(t0, x, y, _er.uniform(0.8, 1.2), _er.uniform(0, 10)) for t0, x, y in EYES]

ZOMBIES = [(0.25, 0.30, 0.95, 11), (0.42, 0.16, 1.05, 12), (0.62, 0.03, 0.9, 13)] if FMT == "yt" else \
          [(0.25, 0.30, 0.95, 11), (0.42, 0.10, 1.05, 12), (0.62, -0.06, 0.9, 13)]
HITS = hammer_hits()


def hero_state(t):
    for t0, t1, act, xr, roof, dr in SCHED:
        if t0 <= t < t1:
            return t0, t1, act, xr, roof, dr
    return SCHED[-1]


def roof_y(xr):
    WH = 0.56 * CAB_W
    base = ground_y(CAB_X) - 0.1 * CAB_W - WH
    return base - 0.34 * CAB_W * (1 - abs(xr) / 0.64) + 0.02 * CAB_W


def render_frame(t, L, sky, vig):
    w = tod(t)
    night = w[2]
    o = camera_o(t)
    fr = sky[0] * w[0] + sky[1] * w[1] + sky[2] * w[2]
    fr += sky[3] * (w[0] + 0.5 * w[1])
    fr = fr.astype(np.float32)
    # sun / moon
    su = ease((t - 4.5) / 2.9) if t >= 3.2 else 0
    sx, sy = lerp(SUN_DAY[0], SUN_SET[0], su), lerp(SUN_DAY[1], SUN_SET[1], su ** 1.4)
    add_glow(fr, sx, sy, 200 * K, (255, 220, 140), (w[0] + w[1]) * 0.9)
    add_glow(fr, sx, sy, 46 * K, (255, 255, 230), (w[0] + w[1]) * 1.6)
    add_glow(fr, MOON[0], MOON[1], 150 * K, (120, 150, 255), night * 0.45)
    add_glow(fr, MOON[0], MOON[1], 34 * K, (250, 250, 255), night * 1.8)
    m, a = grade(w)
    comp(fr, L["far"], o * 0.12, m * 0.9 + 0.1, a + np.array([10, 14, 20], np.float32) * night)
    comp(fr, L["mid"], o * 0.45, m, a)
    comp(fr, L["ground"], o, m, a)

    lit = Image.new("RGBA", (S(W), S(H)), (0, 0, 0, 0))
    emi = Image.new("RGBA", (S(W), S(H)), (0, 0, 0, 0))
    d, e = ImageDraw.Draw(lit), ImageDraw.Draw(emi)
    glows = []
    st = {"night": night, "icon_xy": {}}
    p = cabin_p(t)
    cabin(d, e, glows, CAB_X - o, ground_y(CAB_X), CAB_W, p, t, night)

    tc = chase_tc(t)
    rew = rewind_u(t)
    shift = O0 * rew
    if t < 3.2 and rew < 0.75:
        # chase: hero + zombies, in screen space
        hx = HERO_X * W + shift
        hero(d, e, glows, hx, GY, HERO, "run", 1, tc, ph=tc * 13, night=night)
        for i, (te, x0, hs, seed) in enumerate(ZOMBIES):
            if tc < te: continue
            age = tc - te
            zx = x0 * W + 55 * K * age + shift
            jump = min(age / 0.32, 1)
            zy = GY - math.sin(jump * math.pi) * 0.45 * HERO - (1 - jump) * 0.2 * HERO
            zh = HERO * hs * lerp(0.75, 1, jump)
            if i == 0 and tc > 1.45:
                u = (tc - 1.45) / 0.75
                sc = 1 + (6.5 if FMT == "yt" else 5.2) * u ** 2.2
                cxz = lerp(zx, 0.5 * W + shift, u ** 1.5); cyz = lerp(GY - 0.5 * zh, 0.52 * H, u ** 1.5)
                zz = zh * sc
                zombie(e, e, glows, cxz, cyz + 0.5 * zz, zz, 0, 1, seed, pose="leap")
            else:
                zombie(d, e, glows, zx, zy, zh, age * 12 + i, 1, seed)
        # leaves bursting out of the bushes
        for i, (te, x0, hs, seed) in enumerate(ZOMBIES):
            age = tc - te
            if 0 < age < 0.8:
                r = random.Random(seed)
                for k in range(14):
                    vx, vy = r.uniform(-260, 420) * K, r.uniform(-620, -200) * K
                    lx = x0 * W + vx * age + shift; ly = GY - 0.3 * HERO + vy * age + 1400 * K * age ** 2
                    s = 9 * K
                    d.ellipse([S(lx - s), S(ly - s * .5), S(lx + s), S(ly + s * .5)], fill=r.choice([(60, 150, 64, 255), (110, 196, 80, 255)]))
    elif t >= 3.2:
        t0, t1, act, xr, roof, dr = hero_state(t)
        k = (t - t0) / (t1 - t0)
        idx = [s[0] for s in SCHED].index(t0)
        prev = SCHED[idx - 1] if idx > 0 else SCHED[0]
        def pos(xr_, roof_):
            x = CAB_X + xr_ * CAB_W
            if not roof_: x = min(max(x, 0.13 * W), 0.87 * W)   # keep the hero in frame (matters in 9:16)
            return x, (roof_y(xr_) if roof_ else ground_y(x))
        x, y = pos(xr, roof)
        tool = None
        if act == "dash":
            px, py = pos(prev[3], prev[4])
            x, y = lerp(px, x, ease(k)), lerp(py, y, ease(k))
            hero(d, e, glows, x, y, HERO, "run", dr, t, ph=t * 16, tool="axe" if t > 3.8 else None)
        elif act == "jump":
            px, py = pos(prev[3], prev[4])
            x = lerp(px, x, ease(k))
            y = lerp(py, y, k) - math.sin(k * math.pi) * 0.55 * HERO
            hero(d, e, glows, x, y, HERO, "jump", dr, t, tool="spear" if t > 7.1 else None, night=night)
        elif act in ("hammer", "chop"):
            hero(d, e, glows, x, y, HERO, act, dr, t, swing=(t - t0) / SWING_T, tool="axe" if act == "chop" or t < 4.6 else "hammer")
        elif act == "spear":
            hero(d, e, glows, x, y, HERO, "spear", dr, t, tool="spear", night=night)
        else:
            hero(d, e, glows, x, y, HERO, "idle", dr, t, tool="axe" if t > 3.8 else None)
        for t0_, label, _ in ICONS:
            st["icon_xy"][label] = (CAB_X + hero_state(t0_ - 0.01)[3] * CAB_W,
                                    (roof_y(hero_state(t0_ - 0.01)[3]) if hero_state(t0_ - 0.01)[4] else GY) - HERO * 1.55)
        # impact sparks on each hammer hit
        for hit in HITS:
            if 0 <= t - hit < 0.1:
                hx_ = x + dr * 0.32 * HERO; hy_ = y - 0.3 * HERO
                for j in range(6):
                    a = j * math.pi / 3 + hit
                    e.line([S(hx_ + math.cos(a) * 10 * K), S(hy_ + math.sin(a) * 10 * K), S(hx_ + math.cos(a) * 26 * K), S(hy_ + math.sin(a) * 26 * K)],
                           fill=(255, 250, 210, 255), width=int(S(3 * K)))
    # eyes in the bushes
    for t0, ex, ey, es, ph in EYES:
        if t >= t0:
            op = ease((t - t0) / 0.18)
            blink = 0.1 if (math.sin(t * 1.3 + ph) > 0.985) else 1
            eyes(e, glows, ex + math.sin(t * 1.5 + ph) * 3 * K, ey, 9 * K * es, 1 if ex < CAB_X else -1, night, op * blink)
    # fireflies
    for fx, fy, ph in FIREFLIES:
        x = fx - o * 0.8 + math.sin(t * 0.9 + ph) * 18 * K
        y = fy + math.sin(t * 1.3 + ph * 2) * 14 * K
        if -20 < x < W + 20:
            amt = (0.25 * w[0] + 0.55 * w[1] + 0.7 * night) * (0.6 + 0.4 * math.sin(t * 4 + ph * 3))
            add_glow(fr, x, y, 13 * K, (255, 236, 150), amt)
            add_glow(fr, x, y, 3 * K, (255, 255, 220), amt * 1.2)

    comp_img(fr, lit, m, a)
    for gx, gy_, gr, gc, ga in glows:
        add_glow(fr, gx, gy_, gr, gc, ga)
    comp(fr, L["fg"], o * 1.3, m * 0.8, a * 0.5)
    comp_img(fr, emi)

    # ---- post
    if 2.2 <= t < 2.45:  # freeze flash
        f = 1 - (t - 2.2) / 0.25
        g = fr.mean(axis=2, keepdims=True)
        fr = fr * (1 - 0.6) + g * 0.6 + 120 * f
    if 2.4 <= t < 3.25:  # tape rewind
        k = math.sin(min(max((t - 2.4) / 0.85, 0), 1) * math.pi)
        sh = int(16 * k * K)
        if sh:
            fr[:, :, 0] = np.roll(fr[:, :, 0], sh, axis=1)
            fr[:, :, 2] = np.roll(fr[:, :, 2], -sh, axis=1)
        r = np.random.default_rng(int(t * 1000))
        for _ in range(int(14 * k) + 1):
            y0 = r.integers(0, H); hgt = r.integers(2, 10)
            fr[y0:y0 + hgt] = fr[y0:y0 + hgt] * 0.5 + 170 * k
        band = int((t * 3.1 % 1) * H)
        fr[band:band + int(40 * K)] += 40 * k
    vamt = 0.25 + 0.45 * night
    fr *= (1 - vig * vamt)
    if t >= 8.45:  # end-card darkening
        fr *= 1 - 0.5 * ease((t - 8.45) / 0.3)
    fr += RNG.normal(0, 2.0, (H, W, 1)).astype(np.float32)
    img = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8))
    # slow push-in at night
    if t > 7.3:
        z = 1 + 0.07 * ease((t - 7.3) / 2.7)
        cw, ch = W / z, H / z
        cx = min(max(CAB_X, cw / 2), W - cw / 2); cy = min(max(GY - 0.3 * CAB_W, ch / 2), H - ch / 2)
        img = img.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((W, H), Image.BICUBIC)
    # camera shake as the zombie leaps / the freeze hits
    if 1.9 < t < 2.3:
        k = (t - 1.9) / 0.4
        dx, dy = int(math.sin(t * 97) * 12 * k * K), int(math.cos(t * 83) * 9 * k * K)
        img = img.transform((W, H), Image.AFFINE, (1, 0, dx, 0, 1, dy), resample=Image.BILINEAR)
    draw_ui(img, t, st)
    return img


# =========================================================================== audio
SR = 44100


def make_audio(path):
    n = int(DUR * SR); L = np.zeros(n); R = np.zeros(n)
    rng = np.random.default_rng(1)

    def add(sig, t0, g=1.0, pan=0.0):
        i = int(t0 * SR); j = min(n, i + len(sig))
        if i >= n or j <= 0: return
        L[i:j] += sig[: j - i] * g * (1 - pan); R[i:j] += sig[: j - i] * g * (1 + pan)

    def tt(d): return np.arange(int(d * SR)) / SR

    def lp(x, k):
        return np.convolve(x, np.ones(k) / k, "same")

    def thump(f=55, d=0.25, dec=14):
        t = tt(d); return np.sin(2 * np.pi * np.cumsum(f * (1 + 1.5 * np.exp(-t * 30))) / SR) * np.exp(-t * dec)

    def noise(d, dec, k=1):
        t = tt(d); x = rng.normal(0, 1, len(t))
        if k > 1: x = lp(x, k)
        return x * np.exp(-t * dec)

    def glock(f, d=1.4):
        t = tt(d)
        return (np.sin(2 * np.pi * f * t) * np.exp(-t * 3) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 9)) * np.minimum(1, t / 0.002)

    def screech(d, f0, f1):
        t = tt(d); f = f0 + (f1 - f0) * t / d
        ph = 2 * np.pi * np.cumsum(f * (1 + 0.03 * np.sin(2 * np.pi * 31 * t))) / SR
        s = np.tanh(3 * (np.sin(ph) + 0.6 * np.sin(2.01 * ph) + 0.4 * np.sin(3.02 * ph))) * 0.5 + rng.normal(0, 0.35, len(t))
        env = np.minimum(1, t / 0.03) * np.clip((d - t) / (d * 0.6), 0, 1)
        return lp(s, 3) * env

    # night chase: drone, heartbeat, steps, rustles, screeches
    t = tt(2.3)
    drone = (np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 82.5 * t) + 0.3 * np.sign(np.sin(2 * np.pi * 27.5 * t))) * (0.15 + 0.2 * t / 2.3)
    add(lp(drone, 20), 0, 0.5)
    for b in np.arange(0, 2.2, 0.42):
        add(thump(52), b, 0.9); add(thump(48), b + 0.15, 0.55)
    ph_step = math.pi / 13
    for s in np.arange(0.05, 2.2, ph_step):
        add(lp(noise(0.08, 50), 6), s, 0.35, pan=0.1)
    for te, *_ in ZOMBIES:
        add(lp(noise(0.45, 7), 4), te, 0.45, pan=-0.4)
    add(screech(0.55, 520, 340), 0.35, 0.35, pan=-0.5)
    add(screech(0.8, 420, 760), 1.45, 0.55)
    # freeze thud + tape rewind
    add(thump(42, 0.9, 5), 2.2, 1.4); add(noise(0.12, 40), 2.2, 0.5)
    t = tt(0.85)
    f = 900 * np.exp(-t * 2.2) + 120 + 60 * np.sin(2 * np.pi * 11 * t)
    whirr = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.25 + lp(rng.normal(0, 0.6, len(t)), 3)
    add(lp(whirr, 4) * np.sin(np.pi * t / 0.85), 2.38, 0.42)
    # day theme (code/music.py) under the build montage
    bgm = os.environ.get("BGM")
    if bgm and os.path.exists(bgm):
        with wave.open(bgm) as wv:
            raw = np.frombuffer(wv.readframes(wv.getnframes()), np.int16).reshape(-1, 2) / 32768.0
        seg = raw[: int(4.2 * SR)].copy()
        fade = np.ones(len(seg)); fade[-int(0.6 * SR):] = np.linspace(1, 0, int(0.6 * SR)); fade[:int(0.05 * SR)] = np.linspace(0, 1, int(0.05 * SR))
        i = int(3.15 * SR)
        L[i:i + len(seg)] += seg[:, 0] * fade * 0.75; R[i:i + len(seg)] += seg[:, 1] * fade * 0.75
    for h in HITS:
        add(thump(170, 0.12, 40) * 0.6, h, 0.42, pan=0.15); add(lp(noise(0.06, 60), 3) * 0.5, h, 0.42, pan=0.15)
    for t0, *_ in ICONS:
        add(glock(1046.5) + glock(1318.5) * 0.6, t0, 0.32, pan=-0.1)
    # nightfall: heartbeat returns, eyes "shing", title hit
    t = tt(2.7)
    add(lp(np.sin(2 * np.pi * 49 * t) * (0.2 + 0.25 * t / 2.7) + 0.2 * np.sin(2 * np.pi * 73.4 * t), 30), 7.3, 0.6)
    for b in np.arange(7.5, 8.45, 0.5):
        add(thump(50), b, 0.8); add(thump(46), b + 0.16, 0.5)
    for t0 in (7.55, 7.92, 8.18):
        tw = tt(0.5); add(np.sin(2 * np.pi * (2400 + 1200 * tw) * tw) * np.exp(-tw * 8) * 0.25 + lp(noise(0.5, 6), 2) * 0.1, t0, 0.5, pan=0.3)
    add(thump(40, 1.4, 3), 8.48, 1.5); add(noise(0.8, 4), 8.48, 0.35)
    t = tt(1.6)
    pad = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) for f in (130.8, 155.6, 196.0, 261.6)) / 4
    add(pad * np.minimum(1, t / 0.08) * np.clip((1.6 - t) / 0.7, 0, 1), 8.48, 0.35)
    for i, nn in enumerate((523.3, 622.3, 784.0, 1046.5)):
        add(glock(nn, 1.2), 9.15 + i * 0.07, 0.25)
    st = np.stack([L, R], 1)
    st /= np.max(np.abs(st)) / 0.9
    fl = int(0.15 * SR); st[-fl:] *= np.linspace(1, 0, fl)[:, None]
    with wave.open(path, "wb") as wv:
        wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(SR)
        wv.writeframes((st * 32767).astype(np.int16).tobytes())


# =========================================================================== channel art
def make_channel_art(L, sky, vig, outdir):
    """YouTube banner 2560x1440 (text + hero inside the 1546x423 all-device safe area) and an 800x800 avatar."""
    w = (0.8, 0.2, 0.0)
    fr = (sky[0] * w[0] + sky[1] * w[1]).astype(np.float32) + sky[3] * 0.9
    add_glow(fr, SUN_DAY[0], SUN_DAY[1], 260, (255, 220, 140), 0.9)
    add_glow(fr, SUN_DAY[0], SUN_DAY[1], 60, (255, 255, 230), 1.6)
    m, a = grade(w)
    comp(fr, L["far"], 0, m, a); comp(fr, L["mid"], 0, m, a); comp(fr, L["ground"], 0, m, a)
    lit = Image.new("RGBA", (S(W), S(H)), (0, 0, 0, 0)); d = ImageDraw.Draw(lit); glows = []
    cabin(d, None, glows, CAB_X, ground_y(CAB_X), CAB_W, 1.0, 0.3, 0.0)
    hero(d, None, glows, 1900, GY, HERO, "run", 1, 0.35, ph=1.1)
    comp_img(fr, lit, m, a)
    for gx, gy_, gr, gc, ga in glows: add_glow(fr, gx, gy_, gr, gc, ga)
    for fx, fy, ph in FIREFLIES[:60]:
        add_glow(fr, fx % W, fy, 14, (255, 236, 150), 0.35)
    comp(fr, L["fg"], 0, m * 0.8, a * 0.5)
    fr *= (1 - vig * 0.25)
    img = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8))
    dd = ImageDraw.Draw(img)
    text_c(dd, (1150, 640), "RED SCARF TALES", 128, sw=12)
    text_c(dd, (1150, 760), "What if...? Adventures in a painted world", 52, weight="ExtraBold", sw=6)
    dd.rounded_rectangle([1150 - 230, 830, 1150 + 230, 900], radius=35, fill=(226, 38, 40))
    text_c(dd, (1150, 865), "WHAT WOULD YOU DO?", 34, weight="ExtraBold", sw=0)
    img.save(os.path.join(outdir, "banner_2560x1440.png"))
    # safe-area guide (for checking only)
    g = img.copy(); gd = ImageDraw.Draw(g)
    gd.rectangle([507, 508, 2053, 931], outline=(255, 0, 255), width=4)
    gd.rectangle([0, 509, 2560, 931], outline=(0, 255, 255), width=2)
    g.save(os.path.join(outdir, "banner_safe_area_check.png"))

    # avatar: big hero head + flowing scarf on a sky disc
    A = 800
    yy, xx = np.mgrid[0:A, 0:A].astype(np.float32)
    bg = vgrad(A, [(0, (40, 126, 220)), (0.6, (120, 200, 240)), (1, (255, 214, 140))])
    bg = np.repeat(bg, A, axis=1)
    dd_ = np.sqrt((xx - 560) ** 2 + (yy - 170) ** 2)
    bg += (np.clip(1 - dd_ / 420, 0, 1) ** 2)[..., None] * np.array([120, 100, 40], np.float32)
    av = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).convert("RGBA")
    c = Image.new("RGBA", (S(A), S(A)), (0, 0, 0, 0)); cd = ImageDraw.Draw(c)
    cumulus(cd, S(170), S(640), S(420), S(120), (205, 228, 244, 255), (252, 254, 255, 255), seed=3)
    cumulus(cd, S(680), S(700), S(380), S(110), (205, 228, 244, 255), (252, 254, 255, 255), seed=5)
    hh = 1150
    hero(cd, None, [], 385, 380 + 0.865 * hh, hh, "idle", 1, 0.5, flow=1.0)
    av.alpha_composite(c.reduce(SS))
    av.convert("RGB").save(os.path.join(outdir, "avatar_800x800.png"))


# =========================================================================== main
def main():
    print("building layers...", flush=True)
    sky = build_sky()
    L = {"far": build_far(), "mid": build_mid(), "ground": build_ground(), "fg": build_fg()}
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dd = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    vig = (np.clip((dd - 0.6) / 0.8, 0, 1) ** 1.5)[..., None]
    if FMT in ("banner", "avatar"):
        make_channel_art(L, sky, vig, sys.argv[2]); return
    if sys.argv[2] == "preview":
        for v in sys.argv[3:]:
            img = render_frame(float(v), L, sky, vig)
            img.save(os.path.join(os.environ.get("OUTDIR", "."), f"prev_{FMT}_{float(v):05.2f}.png"))
        return
    out = sys.argv[2]
    wav = out + ".wav"
    make_audio(wav)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-i", wav, "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(NF):
        ff.stdin.write(render_frame(i / FPS, L, sky, vig).tobytes())
        if i % 30 == 0: print(f"frame {i}/{NF}", flush=True)
    ff.stdin.close(); ff.wait()
    os.remove(wav)
    print("wrote", out)


if __name__ == "__main__":
    main()
