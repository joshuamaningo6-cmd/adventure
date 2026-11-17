"""Episode 1 — "What If You Had 10 Hours to Build a Zombie-Proof Home?"

Full episode (16:9) scene by scene, timed to the recorded narration in audio/narration/, plus two
native 9:16 timelapse Shorts built from the same scenes.

    python3 episode.py yt scene 8 out.mp4          # render one scene (video only)
    python3 episode.py yt preview 8 0.5 3 9         # PNG stills of scene 8 at those seconds
    python3 episode.py yt all                       # every scene in parallel, then audio + mux -> video/out/ep01/
    python3 episode.py reel short 1 out.mp4         # Short 1 (day timelapse), Short 2 (night timelapse)
    python3 episode.py yt timeline                  # print the scene timeline

Shares the world, hero, zombies and compositing with teaser.py.
"""
import json, math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
FMT = sys.argv[1] if len(sys.argv) > 1 else "yt"
_argv = sys.argv
sys.argv = [sys.argv[0], FMT]
import teaser as T  # noqa: E402
sys.argv = _argv
if FMT == "reel":           # move the build site right so the meadow, trees and defences fit a 1080-wide world view
    T.CAB_X, T.CAB_W = 1300, 420
from teaser import S, ease, lerp, lerpc, font, text_c, pop_scale, draw_icon, add_glow, comp, comp_img, grade, hero, zombie, eyes  # noqa: E402

W, H, GY, HERO, K, FPS = T.W, T.H, T.GY, T.HERO, T.K, T.FPS
CX, CW = T.CAB_X, T.CAB_W
gy = T.ground_y
NARR = os.path.join(ROOT, "audio", "narration")
TIMING = json.load(open(os.path.join(NARR, "timing.json")))
TEXTS = {o["id"]: o["text"] for o in json.load(open(os.path.join(ROOT, "scripts", "ep01_narration.json")))}

# ---------------------------------------------------------------- world geometry
TR = [CX - 2.95 * CW, CX - 2.35 * CW]        # choppable trees
ROCK = CX - 1.75 * CW                          # mossy rock (drawn in the ground layer)
CRY = CX + 1.25 * CW                           # boulder with the crystal (ground layer)
LOGX = CX - 1.0 * CW
SUNDIAL = CX - 0.85 * CW
STICK_X = TR[1] + 0.75 * CW
TRENCH = (CX - 1.52 * CW, CX - 1.22 * CW)
HINGE = TRENCH[1] + 0.02 * CW
HANG = CX - 0.86 * CW
SPOTS = [("tall", CX + 2.9 * CW), ("open", CX + 4.1 * CW), ("tree", CX + 5.3 * CW)]
BASE_Y = gy(CX) - 0.1 * CW
WALL_H = 0.56 * CW
EAVE_Y = BASE_Y - WALL_H
PEAK_Y = EAVE_Y - 0.34 * CW
GATE_L = (TRENCH[1] - TRENCH[0]) + 0.14 * CW


def cam(center):
    return float(min(max(center - W / 2, 0), T.OMAX - 1))


if FMT == "yt":
    O_TREES = O_SITE = O_SIEGE = 0.0
else:
    O_TREES, O_SITE, O_SIEGE = cam((TR[1] + ROCK) / 2), cam(CX - 0.05 * CW), cam(CX - 0.55 * CW)


def kf(t, keys):
    """Piecewise eased keyframes [(t, v), ...]."""
    if t <= keys[0][0]: return keys[0][1]
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if t <= b: return lerp(va, vb, ease((t - a) / max(b - a, 1e-6)))
    return keys[-1][1]


def kfl(t, keys):
    if t <= keys[0][0]: return keys[0][1]
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if t <= b: return lerp(va, vb, (t - a) / max(b - a, 1e-6))
    return keys[-1][1]


def roof_y(xw):
    xr = (xw - CX) / CW
    return T.roof_y(max(-0.6, min(0.6, xr)))


# ---------------------------------------------------------------- frame spec
class F:
    def __init__(self):
        self.o = 0.0; self.zoom = 1.0; self.zf = (W / 2, H / 2)
        self.tod = (1, 0, 0); self.sun = 0.0; self.sunrise = None; self.rays = None
        self.draw = []          # callables (d, e, glows) on the world (lit + emissive) canvases, in order
        self.front = []         # callables drawn after the foreground layer (emissive canvas only)
        self.timer = None; self.timer_red = False; self.badge = None
        self.icons = []; self.marks = []; self.caps = []; self.big = []; self.rules = []
        self.title = None; self.endscreen = None
        self.shake = 0.0; self.flash = 0.0; self.rewind = 0.0; self.dark = 0.0; self.fire = None
        self.eyes = []; self.vig = None; self.desat = 0.0


# ---------------------------------------------------------------- props
_spr = {}


def tree_sprite(seed, h):
    key = (seed, int(h))
    if key not in _spr:
        w = int(h * 0.95)
        img = Image.new("RGBA", (int(S(w)), int(S(h + 20))), (0, 0, 0, 0))
        T.big_tree(ImageDraw.Draw(img), S(w / 2), S(h + 10), S(h), seed)
        _spr[key] = img
    return _spr[key]


def paste_tree(canvas, x, gyy, seed, h, fall=0.0, dir=-1):
    spr = tree_sprite(seed, h)
    if fall > 0:
        ang = 88 * ease(fall) * (1 if dir < 0 else -1)
        bx, by = spr.width // 2, spr.height - S(10)
        spr = spr.rotate(ang, resample=Image.BILINEAR, center=(bx, by), expand=False)
    paste(canvas, spr, int(S(x) - spr.width // 2), int(S(gyy + 10) - spr.height))


def paste(canvas, spr, x, y):
    """alpha_composite that tolerates sprites hanging off the canvas edge."""
    x0, y0 = max(0, -x), max(0, -y)
    x1, y1 = min(spr.width, canvas.width - x), min(spr.height, canvas.height - y)
    if x1 <= x0 or y1 <= y0: return
    canvas.alpha_composite(spr, (x + x0, y + y0), (x0, y0, x1, y1))


def stump(d, x, g):
    w = 0.16 * CW
    d.polygon([(S(x - w * .6), S(g + 4)), (S(x + w * .6), S(g + 4)), (S(x + w * .45), S(g - w * .55)), (S(x - w * .45), S(g - w * .55))], fill=(112, 82, 62, 255))
    d.ellipse([S(x - w * .45), S(g - w * .68), S(x + w * .45), S(g - w * .42)], fill=(196, 158, 112, 255))
    d.ellipse([S(x - w * .22), S(g - w * .61), S(x + w * .22), S(g - w * .49)], fill=(160, 120, 80, 255))


def log_pile(d, x, g, n):
    lr = 0.045 * CW
    rows = [5, 4, 3, 2, 1]
    k = 0
    for r, cnt in enumerate(rows):
        for i in range(cnt):
            if k >= n: return
            lx = x + (i - (cnt - 1) / 2) * lr * 2.05
            ly = g - lr - r * lr * 1.75
            d.rounded_rectangle([S(lx - lr - 0.12 * CW), S(ly - lr), S(lx + lr), S(ly + lr)], radius=S(lr), fill=(140, 92, 54, 255))
            d.ellipse([S(lx - lr), S(ly - lr), S(lx + lr), S(ly + lr)], fill=(204, 164, 112, 255))
            d.ellipse([S(lx - lr * .45), S(ly - lr * .45), S(lx + lr * .45), S(ly + lr * .45)], fill=(160, 116, 72, 255))
            k += 1


def sundial(d, x, g, t, ang):
    w = 0.22 * CW
    d.rounded_rectangle([S(x - w * .35), S(g - w * .55), S(x + w * .35), S(g + 3)], radius=S(4), fill=(150, 152, 156, 255))
    d.ellipse([S(x - w * .6), S(g - w * .72), S(x + w * .6), S(g - w * .45)], fill=(186, 188, 190, 255))
    d.polygon([(S(x), S(g - w * .6)), (S(x + w * .05), S(g - w * .6)), (S(x), S(g - w * 1.0))], fill=(90, 92, 100, 255))
    L = w * 0.55
    d.line([S(x), S(g - w * .585), S(x + math.cos(ang) * L), S(g - w * .585 + math.sin(ang) * L * 0.22)], fill=(70, 70, 80, 255), width=int(S(3 * K)))


def tall_grass(d, x, g, seed):
    r = random.Random(seed)
    for i in range(70):
        gx = x + r.uniform(-0.55, 0.55) * CW; hh = r.uniform(0.5, 1.15) * HERO
        lean = r.uniform(-0.12, 0.12) * hh
        d.polygon([(S(gx - 5 * K), S(g + 6)), (S(gx + 5 * K), S(g + 6)), (S(gx + lean), S(g - hh))],
                  fill=r.choice([(70, 150, 60, 255), (96, 176, 70, 255), (50, 124, 52, 255)]))


def fortress(d, e, glows, o, st, t, night):
    cx, g = CX - o, gy(CX)
    base = BASE_Y
    def P(x): return x - o
    spx = [cx + (-0.95 + 1.9 * i / 14) * CW for i in range(15)]
    broke = random.Random(5)

    def spike(x, b, h, a, col, i):
        if st["damage"] and broke.random() < 0.35:
            a += broke.choice([-1, 1]) * 0.9; h *= 0.7
        dx = math.sin(a) * h
        d.polygon([(S(x - 0.028 * CW), S(b)), (S(x + 0.028 * CW), S(b)), (S(x + dx + 0.015 * CW), S(b - h * 0.85)),
                   (S(x + dx), S(b - h)), (S(x + dx - 0.015 * CW), S(b - h * 0.85))], fill=col)
    u_sp = st["spikes"]
    for i, x in enumerate(spx):
        k = min(max(u_sp * 15 - i, 0), 1)
        if k > 0: spike(x + 0.03 * CW, g - 0.05 * CW, 0.24 * CW * ease(k), (x - cx) / CW * 0.35, (96, 64, 42, 255), i)
    # foundation
    u = st["found"]
    for i in range(int(math.ceil(u * 7))):
        x0 = cx - 0.58 * CW + i * (1.16 * CW / 7)
        d.rounded_rectangle([S(x0), S(base), S(x0 + 1.16 * CW / 7 - 2), S(g + 0.01 * CW)], radius=S(0.025 * CW), fill=(118, 120, 128, 255))
        d.rounded_rectangle([S(x0 + 3), S(base + 2), S(x0 + 1.16 * CW / 7 - 6), S(base + 0.055 * CW)], radius=S(0.02 * CW), fill=(162, 164, 170, 255))
    # walls
    u = st["walls"]; lh = WALL_H / 7
    for i in range(7):
        k = min(max(u * 7 - i, 0), 1)
        if k <= 0: break
        y1 = base - (i + 1) * lh - (1 - ease(k)) * 0.25 * CW
        d.rounded_rectangle([S(cx - 0.52 * CW), S(y1), S(cx + 0.52 * CW), S(y1 + lh)], radius=S(lh * 0.45), fill=(156, 104, 62, 255) if i % 2 else (140, 92, 54, 255))
        d.line([S(cx - 0.48 * CW), S(y1 + lh * 0.3), S(cx + 0.48 * CW), S(y1 + lh * 0.3)], fill=(184, 134, 84, 255), width=int(S(lh * 0.12)))
        for sx in (-0.53, 0.53):
            d.ellipse([S(cx + sx * CW - lh * 0.5), S(y1), S(cx + sx * CW + lh * 0.5), S(y1 + lh)], fill=(200, 160, 108, 255))
    if u > 0.5:
        dh = WALL_H * 0.62 * min(1, (u - 0.5) * 4)
        d.rounded_rectangle([S(cx - 0.13 * CW), S(base - dh), S(cx + 0.13 * CW), S(base)], radius=S(0.05 * CW), fill=(70, 44, 30, 255))
        for k in (-0.045, 0.045):
            d.line([S(cx + k * CW), S(base - dh + 6), S(cx + k * CW), S(base)], fill=(52, 32, 22, 255), width=int(S(0.01 * CW)))
    if u >= 1:
        wx, wy, ws = cx + 0.32 * CW, base - WALL_H * 0.62, 0.075 * CW
        lit = night > 0.3
        d.rectangle([S(wx - ws), S(wy - ws), S(wx + ws), S(wy + ws)], fill=(60, 40, 28, 255))
        (e if lit else d).rectangle([S(wx - ws * .75), S(wy - ws * .75), S(wx + ws * .75), S(wy + ws * .75)], fill=(255, 196, 96, 255) if lit else (40, 30, 30, 255))
        d.line([S(wx), S(wy - ws), S(wx), S(wy + ws)], fill=(60, 40, 28, 255), width=int(S(0.012 * CW)))
        d.line([S(wx - ws), S(wy), S(wx + ws), S(wy)], fill=(60, 40, 28, 255), width=int(S(0.012 * CW)))
        if lit: glows.append((wx, wy, 0.25 * CW, (255, 170, 70), 0.6 * night))
    u = st["posts"]
    if u > 0:
        for sx in (-0.56, 0.56):
            ph_ = base - (WALL_H + 0.04 * CW) * ease(u)
            d.rectangle([S(cx + sx * CW - 0.04 * CW), S(ph_), S(cx + sx * CW + 0.04 * CW), S(base)], fill=(104, 68, 42, 255))
    u = st["roof"]
    if u > 0:
        drop = (1 - ease(u)) * 0.5 * CW
        ry = EAVE_Y - drop; peak = ry - 0.34 * CW
        d.polygon([(S(cx - 0.72 * CW), S(ry + 0.04 * CW)), (S(cx), S(peak)), (S(cx + 0.72 * CW), S(ry + 0.04 * CW))], fill=(96, 56, 36, 255))
        d.polygon([(S(cx - 0.64 * CW), S(ry)), (S(cx), S(peak + 0.05 * CW)), (S(cx + 0.64 * CW), S(ry))], fill=(132, 78, 48, 255))
        for k in range(1, 8):
            f = k / 8
            d.line([S(cx - 0.64 * CW * (1 - f) - 0.02 * CW), S(ry - (ry - peak - 0.05 * CW) * f), S(cx + 0.64 * CW * (1 - f) + 0.02 * CW),
                    S(ry - (ry - peak - 0.05 * CW) * f)], fill=(110, 64, 40, 255), width=int(S(0.01 * CW)))
        if st["damage"]:
            d.polygon([(S(cx + 0.18 * CW), S(ry - 0.1 * CW)), (S(cx + 0.33 * CW), S(ry - 0.05 * CW)), (S(cx + 0.27 * CW), S(ry - 0.16 * CW))], fill=(40, 26, 20, 255))
    # lookout on the ridge
    u = st["lookout"]
    if u > 0:
        lx = cx - 0.05 * CW; ly = PEAK_Y + 0.05 * CW
        hgt = 0.16 * CW * ease(u)
        for k in (-0.16, 0.0, 0.16):
            d.line([S(lx + k * CW), S(ly), S(lx + k * CW), S(ly - hgt)], fill=(98, 64, 40, 255), width=int(S(0.018 * CW)))
        d.line([S(lx - 0.18 * CW), S(ly - hgt), S(lx + 0.18 * CW), S(ly - hgt)], fill=(120, 80, 50, 255), width=int(S(0.02 * CW)))
        d.line([S(lx + 0.16 * CW), S(ly - hgt), S(lx + 0.16 * CW), S(ly - hgt - 0.14 * CW * u)], fill=(98, 64, 40, 255), width=int(S(0.01 * CW)))
        fl = math.sin(t * 6) * 0.02 * CW
        d.polygon([(S(lx + 0.16 * CW), S(ly - hgt - 0.14 * CW * u)), (S(lx + 0.27 * CW), S(ly - hgt - 0.11 * CW * u + fl)),
                   (S(lx + 0.16 * CW), S(ly - hgt - 0.08 * CW * u))], fill=(240, 210, 110, 255))
    # boulder beam + rope + boulder
    if st["beam"] > 0:
        bx0, by = cx - 0.5 * CW, EAVE_Y - 0.02 * CW
        bx1 = lerp(bx0, P(HANG) - 0.08 * CW, ease(st["beam"]))
        d.line([S(bx0), S(by), S(bx1), S(by)], fill=(110, 72, 44, 255), width=int(S(0.035 * CW)))
        d.line([S(bx0 + 0.04 * CW), S(by), S(bx0 + 0.1 * CW), S(by - 0.14 * CW)], fill=(96, 62, 38, 255), width=int(S(0.02 * CW)))  # lever
        br = 0.12 * CW
        hx = P(HANG)
        if st["boulder_y"] is not None:
            byy = st["boulder_y"]
        else:
            byy = lerp(g - br, by + 0.3 * CW, ease(st["hoist"]))
        if st["rope_cut"] < 1 and st["hoist"] > 0:
            d.line([S(hx), S(by), S(hx), S(byy - br * 0.9)], fill=(118, 150, 70, 255), width=max(1, int(S(0.012 * CW))))
        elif st["rope_cut"] >= 1:
            d.line([S(hx), S(by), S(hx + 0.02 * CW), S(by + 0.12 * CW)], fill=(118, 150, 70, 255), width=max(1, int(S(0.012 * CW))))
        if st["hoist"] > 0 or st["boulder_y"] is not None:
            d.ellipse([S(hx - br), S(byy - br), S(hx + br), S(byy + br * 0.9)], fill=(112, 114, 118, 255))
            d.ellipse([S(hx - br * .8), S(byy - br * .95), S(hx + br * .5), S(byy + br * .3)], fill=(150, 152, 150, 255))
            d.chord([S(hx - br * .9), S(byy - br * 1.02), S(hx + br * .8), S(byy - br * .2)], 180, 360, fill=(92, 150, 66, 255))
    # front spikes (gap for the door)
    for i, x in enumerate(spx):
        if abs(x - cx) < 0.16 * CW: continue
        k = min(max(u_sp * 15 - i, 0), 1)
        if k > 0: spike(x, g + 0.05 * CW, 0.3 * CW * ease(k), (x - cx) / CW * 0.45, (142, 96, 58, 255), i + 20)
    # torches
    if st["torches"] > 0:
        for tx in (P(HINGE) + 0.08 * CW, cx + 1.1 * CW):
            d.line([S(tx), S(g + 0.03 * CW), S(tx), S(g - 0.5 * CW)], fill=(92, 60, 38, 255), width=int(S(0.03 * CW)))
            fl = 1 + 0.15 * math.sin(t * 23 + tx) + 0.08 * math.sin(t * 41)
            fh_ = 0.13 * CW * st["torches"] * fl; fy = g - 0.5 * CW
            e.polygon([(S(tx - 0.035 * CW), S(fy)), (S(tx + 0.035 * CW), S(fy)), (S(tx + 0.01 * CW * math.sin(t * 17)), S(fy - fh_))], fill=(255, 150, 40, 255))
            e.polygon([(S(tx - 0.018 * CW), S(fy)), (S(tx + 0.018 * CW), S(fy)), (S(tx), S(fy - fh_ * 0.6))], fill=(255, 236, 140, 255))
            glows.append((tx, fy - fh_ * 0.4, 0.55 * CW, (255, 140, 40), (0.35 + 0.65 * night) * st["torches"] * fl))


def trench_back(d, o, st):
    if st["trench"] <= 0: return
    x0, x1 = TRENCH[0] - o, TRENCH[1] - o
    dep = 0.2 * CW * st["trench"]
    g = gy(TRENCH[0])
    d.polygon([(S(x0), S(g - 0.01 * CW)), (S(x1), S(g - 0.01 * CW)), (S(x1 - 0.03 * CW), S(g + dep)), (S(x0 + 0.03 * CW), S(g + dep))], fill=(40, 26, 20, 255))
    d.polygon([(S(x0 + 0.03 * CW), S(g + dep * 0.55)), (S(x1 - 0.03 * CW), S(g + dep * 0.55)), (S(x1 - 0.03 * CW), S(g + dep)), (S(x0 + 0.03 * CW), S(g + dep))], fill=(82, 58, 38, 255))
    d.polygon([(S(x0 - 0.04 * CW), S(g + 2)), (S(x0 + 0.02 * CW), S(g - 0.03 * CW * st["trench"])), (S(x0 + 0.08 * CW), S(g + 2))], fill=(110, 82, 52, 255))
    d.polygon([(S(x1 - 0.08 * CW), S(g + 2)), (S(x1 - 0.02 * CW), S(g - 0.03 * CW * st["trench"])), (S(x1 + 0.04 * CW), S(g + 2))], fill=(110, 82, 52, 255))


def trench_front(d, o, st):
    """Occluder: the near lip of the trench hides whatever has fallen in."""
    if st["trench"] <= 0: return
    x0, x1 = TRENCH[0] - o, TRENCH[1] - o
    g = gy(TRENCH[0])
    return


def drawbridge(d, o, st, t):
    if st["gate"] <= 0: return
    hx, g = HINGE - o, gy(HINGE)
    u = st["gate"]
    for px in (hx + 0.03 * CW, hx + 0.1 * CW):  # gate posts
        d.rectangle([S(px - 0.025 * CW), S(g - 0.55 * CW * ease(min(u * 2, 1))), S(px + 0.025 * CW), S(g + 0.03 * CW)], fill=(100, 66, 40, 255))
    if u < 0.5: return
    down = st["gate_down"]
    ang = lerp(math.pi / 2, math.pi, ease(down) if down < 1 else 1)  # pi/2 = up (closed), pi = flat to the left
    shake = math.sin(t * 40) * 0.03 * st.get("gate_shake", 0)
    ang += shake
    L = GATE_L * min(1, (u - 0.5) * 2)
    ex, ey = hx + math.cos(ang) * L, g - math.sin(ang) * L
    nx, ny = -math.sin(ang) * 0.035 * CW, -math.cos(ang) * 0.035 * CW
    d.polygon([(S(hx + nx), S(g + ny)), (S(ex + nx), S(ey + ny)), (S(ex - nx), S(ey - ny)), (S(hx - nx), S(g - ny))], fill=(140, 94, 56, 255))
    for k in range(1, 5):
        f = k / 5
        px_, py_ = hx + math.cos(ang) * L * f, g - math.sin(ang) * L * f
        d.line([S(px_ + nx), S(py_ + ny), S(px_ - nx), S(py_ - ny)], fill=(104, 68, 40, 255), width=max(1, int(S(0.008 * CW))))
    # vine rope from the post top to the bridge end
    if st["rope"] == 1:
        top = (hx + 0.1 * CW, g - 0.55 * CW)
        sag = 0.03 * CW * (1 + st.get("rope_tug", 0) * math.sin(t * 30))
        mid = ((top[0] + ex) / 2, (top[1] + ey) / 2 + sag)
        d.line([S(top[0]), S(top[1]), S(mid[0]), S(mid[1]), S(ex), S(ey)], fill=(92, 150, 58, 255), width=max(1, int(S(0.014 * CW))), joint="curve")
        for k in range(6):  # leaves on the vine
            f = (k + 0.5) / 6
            vx, vy = lerp(top[0], ex, f), lerp(top[1], ey, f) + sag * math.sin(f * math.pi)
            d.ellipse([S(vx - 0.012 * CW), S(vy - 0.007 * CW), S(vx + 0.012 * CW), S(vy + 0.007 * CW)], fill=(70, 130, 50, 255))
    elif st["rope"] == 2:
        top = (hx + 0.1 * CW, g - 0.55 * CW)
        d.line([S(top[0]), S(top[1]), S(top[0] - 0.03 * CW), S(top[1] + 0.15 * CW)], fill=(92, 150, 58, 255), width=max(1, int(S(0.014 * CW))))


def crystal_rock(d, e, glows, o, st, t):
    if st["crack"] <= 0: return
    bx, g = CRY - o, GY + 6
    w, h = 0.6 * CW, 0.38 * CW
    u = st["crack"]
    pts = [(bx - w * 0.18, g - h * 0.75), (bx - w * 0.08, g - h * 0.55), (bx - w * 0.14, g - h * 0.4), (bx - w * 0.02, g - h * 0.22), (bx - w * 0.06, g - h * 0.05)]
    n = max(2, int(len(pts) * min(1, u * 1.4)))
    col = (150, 246, 255, 255) if st["crystal"] else (110, 200, 220, 255)
    e.line([(S(a), S(b)) for a, b in pts[:n]], fill=col, width=int(S(3.5 * K)), joint="curve")
    amt = (1.0 if st["crystal"] else 0.35) * min(1, u) * (0.85 + 0.15 * math.sin(t * 5))
    glows.append((bx - w * 0.1, g - h * 0.4, 0.6 * CW * min(1, u), (80, 220, 255), amt))
    if st["crystal"] and u > 0.8:
        for k, (dx, dy, s) in enumerate([(-0.1, -0.45, 1), (-0.05, -0.35, 0.7), (-0.15, -0.3, 0.6)]):
            cx_, cy_ = bx + dx * w, g + dy * h; r = 0.035 * CW * s
            e.polygon([(S(cx_), S(cy_ - r * 2.2)), (S(cx_ + r), S(cy_)), (S(cx_), S(cy_ + r * 0.6)), (S(cx_ - r), S(cy_))], fill=(170, 250, 255, 255))


def world(d, e, glows, o, st, t, night, canvas):
    if st["sundial"]: sundial(d, SUNDIAL - o, GY, t, st.get("dial", 2.6))
    if st["tall"]:
        tall_grass(d, SPOTS[0][1] - o, GY, 3)
    for i, x in enumerate(TR):
        if -0.6 * W < x - o < 1.6 * W:
            f = st["trees"][i]
            if f < 1: paste_tree(canvas, x - o, GY, 40 + i, (0.5 if FMT == "yt" else 0.4) * H, fall=f)
            else: stump(d, x - o, GY)
    if -0.6 * W < SPOTS[2][1] - o < 1.6 * W:
        paste_tree(canvas, SPOTS[2][1] - o, GY, 77, (0.52 if FMT == "yt" else 0.42) * H)
    crystal_rock(d, e, glows, o, st, t)
    if st["logs"]: log_pile(d, LOGX - o, GY + 4, int(st["logs"]))
    if st["logseat"]:
        lx = CX - 0.95 * CW - o
        d.rounded_rectangle([S(lx - 0.16 * CW), S(GY - 0.07 * CW), S(lx + 0.16 * CW), S(GY + 0.02 * CW)], radius=S(0.04 * CW), fill=(140, 92, 54, 255))
        d.ellipse([S(lx + 0.12 * CW), S(GY - 0.07 * CW), S(lx + 0.2 * CW), S(GY + 0.02 * CW)], fill=(200, 160, 108, 255))
    trench_back(d, o, st)
    fortress(d, e, glows, o, st, t, night)
    drawbridge(d, o, st, t)


def base_state(n):
    st = dict(trees=[0.0, 0.0], logs=0, sundial=1, tall=1, found=0, posts=0, walls=0, roof=0, spikes=0, trench=0, gate=0,
              gate_down=0, rope=0, lookout=0, beam=0, hoist=0, boulder_y=None, rope_cut=0, torches=0, crack=0, crystal=0,
              damage=0, logseat=0, dial=2.6)
    if n >= 7: st.update(trees=[1.0, 1.0], logs=12)
    if n >= 9: st.update(found=1, posts=1, walls=1, roof=1, logs=3, sundial=0)
    if n >= 10: st.update(crack=1, crystal=0, logseat=1)
    if n >= 12: st.update(spikes=1, trench=1, logs=0, logseat=0)
    if n >= 13: st.update(gate=1, rope=1)
    if n >= 14: st.update(lookout=1, beam=1, hoist=1, torches=1)
    if n >= 18: st.update(gate_down=1, rope=2)
    if n >= 21: st.update(damage=1, rope_cut=1, boulder_y=gy(HANG) - 0.1 * CW)
    return st


# ---------------------------------------------------------------- effects
def ash(d, x, y, age, seed, n=26, spread=1.0, col=(54, 50, 56)):
    r = random.Random(seed)
    for i in range(n):
        vx, vy = r.uniform(-30, 50) * K * spread, -r.uniform(25, 90) * K
        px = x + r.uniform(-0.14, 0.14) * HERO * spread + vx * age + math.sin(age * 2 + i) * 8 * K
        py = y - r.uniform(0, 0.9) * HERO * spread + vy * age
        a = max(0, 1 - age / 2.5)
        if a <= 0: continue
        s = r.uniform(2, 6) * K
        d.ellipse([S(px - s), S(py - s), S(px + s), S(py + s)], fill=col + (int(255 * a),))


def dust(d, x, y, age, seed, n=14, size=1.0, col=(190, 170, 140)):
    r = random.Random(seed)
    for i in range(n):
        a = r.uniform(math.pi, 2 * math.pi); v = r.uniform(80, 260) * K * size
        px = x + math.cos(a) * v * age ** 0.6; py = y + math.sin(a) * v * 0.35 * age ** 0.6
        rad = (16 + 50 * age) * K * size * r.uniform(0.6, 1.2)
        al = max(0, 1 - age / 1.6)
        if al > 0:
            d.ellipse([S(px - rad), S(py - rad), S(px + rad), S(py + rad)], fill=col + (int(170 * al),))


def arrow(d, e, glows, x0, y0, x1, y1, u):
    if not 0 <= u <= 1: return
    x = lerp(x0, x1, u); y = lerp(y0, y1, u) - math.sin(u * math.pi) * 0.25 * HERO
    x2 = lerp(x0, x1, max(0, u - 0.06)); y2 = lerp(y0, y1, max(0, u - 0.06)) - math.sin(max(0, u - 0.06) * math.pi) * 0.25 * HERO
    d.line([S(x2), S(y2), S(x), S(y)], fill=(120, 84, 52, 255), width=int(S(2.5 * K)))
    e.ellipse([S(x - 4 * K), S(y - 4 * K), S(x + 4 * K), S(y + 4 * K)], fill=(170, 250, 255, 255))
    glows.append((x, y, 30 * K, (80, 220, 255), 0.9))


def brute(d, e, glows, x, y, h, ph, dir, t, pose="run", squash=0.0):
    hh = h * (1 - squash)
    zombie(d, e, glows, x, y, hh, ph, dir, 99, pose=pose)
    lean = 0.62 if pose == "run" else 0.95
    hip = (x, y - 0.40 * hh)
    sho = (hip[0] + dir * math.sin(lean) * 0.27 * hh, hip[1] - math.cos(lean) * 0.27 * hh)
    cx_, cy_ = lerp(hip[0], sho[0], 0.55), lerp(hip[1], sho[1], 0.55)
    s = 0.09 * hh
    pts = [(cx_ - s * .4, cy_ - s), (cx_ + s * .2, cy_ - s * .3), (cx_ - s * .3, cy_ + s * .1), (cx_ + s * .3, cy_ + s * .8)]
    e.line([(S(a), S(b)) for a, b in pts], fill=(255, 140, 40, 255), width=int(S(0.012 * hh)), joint="curve")
    glows.append((cx_, cy_, 0.11 * hh, (255, 110, 20), 0.45 + 0.15 * math.sin(t * 6)))


def zdraw(d, e, glows, z, t, night):
    """z: dict x y h ph dir seed pose crumble(0..) knock."""
    c = z.get("crumble", 0)
    if c > 0:
        ash(d, z["x"], z["y"], c * 1.2, z["seed"], 22)
        if c >= 1: return
        zombie(d, e, glows, z["x"], z["y"], z["h"] * (1 - c), z["ph"], z["dir"], z["seed"], pose=z.get("pose", "run"), eye_glow=1 - c)
        return
    zombie(d, e, glows, z["x"], z["y"], z["h"], z["ph"], z["dir"], z["seed"], pose=z.get("pose", "run"))


# ---------------------------------------------------------------- scene machinery
def vo_phr(n):
    """Start times of each phrase inside clip n (after each detected pause)."""
    sil = TIMING[n]["silences"]
    return [0.0] + [b for a, b in sil]


SLOTS = {1: 6, 2: 12, 3: 12, 4: 20, 5: 20, 6: 25, 7: 25, 8: 35, 9: 40, 10: 35, 11: 30, 12: 14, 13: 26, 14: 25, 15: 30, 16: 15, 17: 25, 18: 30, 19: 15, 20: 15, 21: 25}
LEADS = {1: 2.2, 2: 0.8, 3: 0.6, 4: 0.6, 5: 0.6, 6: 1.6, 7: 0.8, 8: 2.0, 9: 1.6, 10: 1.0, 11: 1.4, 12: 0.8, 13: 0.8, 14: 3.0, 15: 2.2, 16: 0.8, 17: 2.0, 18: 1.0, 19: 0.6, 20: 0.3, 21: 2.0}
TAILS = {1: 0.4, 21: 6.5, 13: 1.5, 20: 3.0}


def scene_dur(n):
    vo = TIMING[f"{n:02d}"]["dur"]
    return max(SLOTS[n], LEADS[n] + vo + TAILS.get(n, 1.0))


DURS = {n: round(scene_dur(n) * FPS) / FPS for n in range(1, 22)}
STARTS = {}
_acc = 0.0
for _n in range(1, 22):
    STARTS[_n] = _acc; _acc += DURS[_n]
TOTAL = _acc


def P_(n, k):  # absolute (scene-local) time of phrase k of scene n
    return LEADS[n] + vo_phr(f"{n:02d}")[k]


def timer_lin(t, dur, a, b):
    return lerp(a, b, min(max(t / dur, 0), 1))


# ================================================================ scenes
def sc01(t, f):
    """Night chase hook -> freeze -> rewind -> morning."""
    dur = DURS[1]
    st = base_state(1); st.update(found=1, posts=1, walls=1, roof=1, spikes=1, torches=1, sundial=0, logs=0)
    rew_t0, rew_t1 = 2.4, 3.5
    ru = ease((t - rew_t0) / (rew_t1 - rew_t0)) if t > rew_t0 else 0.0
    if t < 2.2: o = T.O0 + T.RUN_V * t
    elif t < rew_t0: o = T.OMAX
    else: o = T.OMAX * (1 - ru) + O_SITE * ru
    f.o = o
    f.tod = (0, 0, 1) if t < rew_t0 else (ru, 0, 1 - ru)
    tc = min(t, 2.2) if t < rew_t0 else 2.2 * (1 - ru)
    if ru > 0.6: st = base_state(1)
    if t >= rew_t1 - 0.01: st = base_state(1)
    f.flash = max(0, 1 - (t - 2.2) / 0.25) if 2.2 <= t < 2.45 else 0
    f.desat = 0.6 if 2.2 <= t < 2.45 else 0
    f.rewind = math.sin(ru * math.pi) if rew_t0 <= t <= rew_t1 else 0
    f.shake = (t - 1.9) / 0.4 if 1.9 < t < 2.3 else 0
    night = f.tod[2]
    shift = T.O0 * ru

    def draw(d, e, glows, canvas):
        world(d, e, glows, o, st, t, night, canvas)
        if t < rew_t1 and ru < 0.7:
            hx = T.HERO_X * W + shift
            hero(d, e, glows, hx, GY, HERO, "run", 1, tc, ph=tc * 13, night=night)
            for i, (te, x0, hs, seed) in enumerate(T.ZOMBIES):
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
                    f.front.append(lambda d2, e2, g2, cxz=cxz, cyz=cyz, zz=zh * sc, seed=seed: zombie(e2, e2, g2, cxz, cyz + 0.5 * zz, zz, 0, 1, seed, pose="leap"))
                else:
                    zombie(d, e, glows, zx, zy, zh, age * 12 + i, 1, seed)
        elif t >= rew_t1 - 0.2:
            k = t - rew_t1
            pose = "crouch" if k < 0.8 else "idle"
            hero(d, e, glows, SUNDIAL - 0.45 * CW - o, GY, HERO, pose, 1, t)
    f.draw.append(draw)
    if t >= P_(1, 2) - 0.1:
        f.big.append(("TEN HOURS EARLIER", t - (P_(1, 2) - 0.1), 1.6))
    return f


def sc02(t, f):
    dur = DURS[2]
    st = base_state(2)
    f.o = O_SITE; f.tod = (1, 0, 0); f.sun = 0.0
    hx = SUNDIAL - 0.45 * CW
    look = 1 if (t % 4) < 2 else -1

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0, canvas)
        hero(d, e, glows, hx - f.o, GY, HERO, "idle", look if t > 3 else 1, t)
    f.draw.append(draw)
    f.title = ("WHAT IF YOU HAD 10 HOURS", "TO BUILD A ZOMBIE-PROOF HOME?", t)
    ph = vo_phr("02")
    f.rules = [(kind, t - (LEADS[2] + tt)) for kind, tt in (("sunmoon", 2.2), ("hands", ph[1] + 2.4), ("island", ph[2] + 0.6))]
    f.zoom = kf(t, [(0, 1.12), (dur, 1.0)]); f.zf = (hx - f.o, GY - HERO * 0.6)
    return f


def sc03(t, f):
    dur = DURS[3]
    st = base_state(3)
    f.o = O_SITE; f.tod = (1, 0, 0); f.sun = 0.02
    st["dial"] = 2.6 + t * 0.05
    f.zoom = kf(t, [(0, 2.0), (P_(3, 1) + 0.3, 2.0), (P_(3, 2) + 0.2, 1.0)])
    f.zf = (SUNDIAL - f.o, GY - 0.2 * CW)
    hx = SUNDIAL - 0.45 * CW
    look = 1 if int((t - P_(3, 3)) / 0.9) % 2 == 0 or t < P_(3, 3) else -1

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0, canvas)
        hero(d, e, glows, hx - f.o, GY, HERO, "idle", look, t)
    f.draw.append(draw)
    if t >= P_(3, 0) + 0.2:
        f.timer = 600
    if P_(3, 0) <= t < P_(3, 0) + 2.4: f.big.append(("10:00 LEFT", t - P_(3, 0), 2.4))
    for k, (ph, txt) in enumerate([(0, "RULE 1 · THE SUN KEEPS TIME"), (2, "RULE 2 · EVERYTHING IS IN THIS MEADOW"), (4, "RULE 3 · AT SUNSET, THEY COME")]):
        a = P_(3, ph); b = P_(3, ph + 2) if ph + 2 < 7 else P_(3, 6)
        if a <= t < b: f.caps.append((txt, t - a))
    return f


def sc04(t, f):
    dur = DURS[4]
    st = base_state(4)
    f.o = O_TREES; f.tod = (1, 0, 0); f.sun = 0.04; f.timer = 600 - 6 * t / dur
    ph = vo_phr("04")
    L = LEADS[4]
    t_pick = L + ph[4]           # "So you grab the best tool..."
    t_whack = L + ph[5] + 0.3
    t_snap = L + ph[6] - 0.25    # just before "And now your only tool is…"
    hx_tree = TR[1] + 0.32 * CW
    look = -1 if int(t / 0.7) % 2 else 1
    if t < L + ph[2]:
        x, pose, dr, tool = SUNDIAL - 0.45 * CW, "idle", look, None
    elif t < t_pick:
        u = (t - (L + ph[2])) / (t_pick - (L + ph[2]))
        x, pose, dr, tool = lerp(SUNDIAL - 0.45 * CW, STICK_X + 0.1 * CW, ease(u)), "walk", -1, None
    elif t < t_pick + 0.5:
        x, pose, dr, tool = STICK_X + 0.1 * CW, "crouch", -1, None
    elif t < t_whack:
        u = (t - t_pick - 0.5) / max(0.1, t_whack - t_pick - 0.5)
        x, pose, dr, tool = lerp(STICK_X + 0.1 * CW, hx_tree, ease(u)), "walk", -1, "stick"
    elif t < t_snap:
        x, pose, dr, tool = hx_tree, "hammer", -1, "stick"
    else:
        x, pose, dr, tool = hx_tree, "idle", -1, "halfstick"
    swing = (t - t_whack) / 0.32

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0, canvas)
        if t < t_pick + 0.4:
            d.line([S(STICK_X - 0.12 * CW - f.o), S(GY - 3), S(STICK_X + 0.12 * CW - f.o), S(GY - 8)], fill=(126, 88, 52, 255), width=int(S(5 * K)))
        hero(d, e, glows, x - f.o, GY, HERO, pose, dr, t, swing=swing, tool=tool, ph=t * 9)
        if t >= t_snap:  # the other half flying off
            a = t - t_snap
            px = x - f.o + 60 * K + 220 * K * a; py = GY - HERO * 0.9 - 380 * K * a + 900 * K * a * a
            if py < GY:
                ang = a * 14
                d.line([S(px - math.cos(ang) * 0.1 * HERO), S(py - math.sin(ang) * 0.1 * HERO), S(px + math.cos(ang) * 0.1 * HERO), S(py + math.sin(ang) * 0.1 * HERO)],
                       fill=(126, 88, 52, 255), width=int(S(5 * K)))
            else:
                d.line([S(px - 0.1 * HERO), S(GY - 3), S(px + 0.1 * HERO), S(GY - 3)], fill=(126, 88, 52, 255), width=int(S(5 * K)))
    f.draw.append(draw)
    if t_snap <= t < t_snap + 1.2: f.big.append(("SNAP.", t - t_snap, 1.2))
    return f


def sc05(t, f):
    dur = DURS[5]
    st = base_state(5)
    f.o = O_TREES; f.tod = (1, 0, 0); f.sun = 0.06; f.timer = 594 - 10 * t / dur
    ph = vo_phr("05")
    L = LEADS[5]
    hx = ROCK + 0.42 * CW
    t_hit = L + ph[1] + 0.3; t_vib0 = L + ph[2]; t_vib1 = t_vib0 + 2.2
    t_try = L + ph[3]; t_split = L + ph[4] - 0.2; t_tie = L + ph[4] + 1.5; t_axe = L + ph[5] + 2.6
    pose, tool, x, sw = "idle", "halfstick" if t < L + ph[1] else "rock", hx, 0
    if t < L + ph[1]:
        x = lerp(TR[1] + 0.32 * CW, hx, ease(t / (L + ph[1]))); pose = "walk"
    elif t < t_vib0:
        pose, sw = "hammer", (t - t_hit) / 0.6
    elif t < t_vib1:
        pose = "idle"; x = hx + math.sin(t * 90) * 6 * K * (1 - (t - t_vib0) / 2.2)
    elif t < t_split + 0.3:
        pose, sw = "hammer", (t - t_try) / 0.45
    elif t < t_tie + 1.6:
        pose, tool = "crouch", "rock"
    elif t < t_axe:
        pose, tool = "idle", "axe"
    else:
        pose, tool = "cheer", "axe"

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0, canvas)
        if t_split <= t < t_split + 0.25:
            sx, sy = ROCK + 0.2 * CW - f.o, GY - 0.25 * CW
            for j in range(8):
                a = j * math.pi / 4
                e.line([S(sx + math.cos(a) * 10 * K), S(sy + math.sin(a) * 10 * K), S(sx + math.cos(a) * 34 * K), S(sy + math.sin(a) * 34 * K)], fill=(255, 250, 210, 255), width=int(S(3 * K)))
        hero(d, e, glows, x - f.o, GY, HERO, pose, -1, t, swing=sw, tool=tool)
        if t_vib0 <= t < t_vib1:  # buzz lines
            for j in range(3):
                bx = x - f.o + (j - 1) * 0.25 * HERO + math.sin(t * 60 + j) * 4 * K
                d.arc([S(bx - 0.2 * HERO), S(GY - 1.15 * HERO), S(bx + 0.2 * HERO), S(GY - 0.75 * HERO)], 200, 340, fill=(255, 255, 255, 200), width=int(S(3 * K)))
    f.draw.append(draw)
    if t_vib0 <= t < t_vib1: f.big.append(("BZZZZ", t - t_vib0, 2.2))
    if t >= t_axe - 0.8: f.icons.append(("STONE AXE", "axe", x, GY - 1.6 * HERO, t - (t_axe - 0.8)))
    return f


def sc06(t, f):
    dur = DURS[6]
    st = base_state(6)
    f.o = O_TREES; f.tod = (1, 0, 0); f.sun = kfl(t, [(0, 0.08), (dur, 0.18)])
    f.timer = kfl(t, [(0, 584), (dur - 1.5, 480)]); f.badge = "TIMELAPSE  x40"
    L = LEADS[6]; ph = vo_phr("06")
    t_shield = L + ph[3]
    # two trees: chop 1.6 s, fall 0.9 s each; then logs land on the pile
    t1a, t1b = 0.3, 1.9; t2a, t2b = 3.4, 5.0
    st["trees"] = [ease((t - t2b) / 0.9) if t > t2b else 0.0, ease((t - t1b) / 0.9) if t > t1b else 0.0]
    st["logs"] = int(min(12, max(0, (t - 3.0) * 1.5) + max(0, (t - 6.2) * 1.5)))
    if t < t1b: x, pose, sw, dr = TR[1] + 0.3 * CW, "chop", (t - t1a) / 0.2, -1
    elif t < t2a: x, pose, sw, dr = lerp(TR[1] + 0.3 * CW, TR[0] + 0.3 * CW, ease((t - t1b) / (t2a - t1b))), "dash", 0, -1
    elif t < t2b: x, pose, sw, dr = TR[0] + 0.3 * CW, "chop", (t - t2a) / 0.2, -1
    elif t < t_shield - 0.6:
        # ferry logs to the pile, back and forth
        k = ((t - t2b) % 1.6) / 1.6
        x = lerp(TR[0] + 0.5 * CW, LOGX - 0.25 * CW, math.sin(k * math.pi)); pose, sw, dr = "dash", 0, (1 if k < 0.5 else -1)
    elif t < t_shield + 2.8:
        x, pose, sw, dr = LOGX - 0.3 * CW, "hammer", (t - t_shield) / 0.22, 1
    else:
        x, pose, sw, dr = LOGX - 0.3 * CW, "idle", 0, 1
    has_shield = t > t_shield + 2.8

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0, canvas)
        hero(d, e, glows, x - f.o, GY, HERO, pose, dr, t, swing=sw, tool="axe" if pose == "chop" or t < t_shield else "hammer", ph=t * 16, shield=has_shield)
        for (ta, tb) in ((t1a, t1b), (t2a, t2b)):  # wood chips
            if ta < t < tb:
                r = random.Random(int(t * 10))
                for j in range(4):
                    cx_ = x - f.o - 0.3 * HERO + r.uniform(-20, 20) * K; cy_ = GY - 0.45 * HERO + r.uniform(-30, 10) * K
                    d.rectangle([S(cx_), S(cy_), S(cx_ + 5 * K), S(cy_ + 3 * K)], fill=(220, 180, 120, 255))
    f.draw.append(draw)
    if t >= t_shield + 2.6: f.icons.append(("WOODEN SHIELD", "shield", x, GY - 1.6 * HERO, t - (t_shield + 2.6)))
    if dur - 3 < t: f.big.append(("8:00 LEFT", t - (dur - 3), 3))
    return f


def sc07(t, f):
    dur = DURS[7]
    st = base_state(7)
    f.tod = (1, 0, 0); f.sun = 0.2; f.timer = 480
    L = LEADS[7]; ph = vo_phr("07")
    cen = {k: x for k, x in SPOTS}
    t_tall, t_open, t_tree, t_back = L + ph[1] - 0.3, L + ph[2] - 0.3, L + ph[3] - 1.0, L + ph[3] + 0.2
    keys = [(0, O_SITE), (t_tall - 0.6, O_SITE), (t_tall + 0.3, cam(cen["tall"])), (t_open, cam(cen["tall"])), (t_open + 0.7, cam(cen["open"])),
            (t_tree, cam(cen["open"])), (t_tree + 0.5, cam(cen["tree"])), (t_back, cam(cen["tree"])), (t_back + 0.9, O_SITE)]
    f.o = kf(t, keys)
    for (k, x), tt in zip(SPOTS, (t_tall + 0.6, t_open + 0.9, t_tree + 0.6)):
        if t >= tt: f.marks.append(("x", x, GY - 0.6 * HERO, t - tt))
    t_tick = L + ph[4]
    if t >= t_tick: f.marks.append(("tick", CX, gy(CX) - 0.5 * HERO, t - t_tick))
    hx = kf(t, [(0, LOGX - 0.3 * CW), (t_tick, LOGX - 0.3 * CW), (t_tick + 2.5, CX - 0.1 * CW)])
    pose = "walk" if t_tick < t < t_tick + 2.5 else "idle"

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0, canvas)
        if t_tall + 0.6 < t < t_open + 0.5:  # something is watching from the tall grass
            ex = cen["tall"] - f.o + 0.1 * CW
            eyes(e, glows, ex, GY - 0.55 * HERO, 8 * K, -1, 0.9, ease((t - t_tall - 0.6) / 0.3))
        hero(d, e, glows, hx - f.o, gy(hx), HERO, pose, 1, t, ph=t * 9, shield=True, tool="axe")
    f.draw.append(draw)
    return f


BUILD = [(0.0, "found"), (0.17, "posts"), (0.32, "walls"), (0.7, "roof")]


def sc08(t, f):
    dur = DURS[8]
    st = base_state(8); st["sundial"] = 0
    f.o = O_SITE; f.tod = (1, 0, 0); f.sun = kfl(t, [(0, 0.2), (dur, 0.33)])
    L = LEADS[8]; ph = vo_phr("08")
    tb0, tb1 = 1.0, L + ph[4]          # build until "Four hours in"
    u = min(max((t - tb0) / (tb1 - tb0), 0), 1)
    st["found"] = min(1, u / 0.17); st["posts"] = min(1, max(0, (u - 0.17) / 0.15)); st["walls"] = min(1, max(0, (u - 0.32) / 0.38))
    st["roof"] = min(1, max(0, (u - 0.7) / 0.3))
    st["logs"] = int(lerp(12, 3, u))
    f.timer = kfl(t, [(0, 480), (tb1, 360)]); f.badge = "TIMELAPSE  x120" if t < tb1 else None
    # sped-up hero hopping around the build
    spots = [-0.8, 0.75, -0.7, 0.8, -0.6, 0.7]
    seg = 0.55
    if t < tb1:
        if st["roof"] > 0 and st["roof"] < 1:
            x, y, pose, dr, sw = CX - 0.05 * CW, roof_y(CX - 0.05 * CW), "hammer", 1, (t - tb0) / 0.18
        else:
            i = int((t - tb0) / seg) % len(spots); k = ((t - tb0) % seg) / seg
            j = (i - 1) % len(spots)
            if k < 0.25:
                x = lerp(CX + spots[j] * CW, CX + spots[i] * CW, ease(k / 0.25)); pose = "dash"; sw = 0
            else:
                x = CX + spots[i] * CW; pose = "hammer"; sw = (k - 0.25) * seg / 0.17
            dr = 1 if spots[i] < 0 else -1; y = gy(x)
            if t < tb0: x, pose, dr, y = CX - 0.1 * CW, "idle", 1, gy(CX)
    else:
        k = t - tb1
        x = CX - 0.35 * CW; y = gy(x); pose = "jump" if k < 0.5 else "cheer" if k < 2.5 else "idle"; dr = 1; sw = 0
        if k < 0.5: y = gy(x) - math.sin(k / 0.5 * math.pi) * 0.4 * HERO

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0, canvas)
        hero(d, e, glows, x - f.o, y, HERO, pose, dr, t, swing=sw, tool="hammer", ph=t * 16, shield=pose not in ("hammer",))
    f.draw.append(draw)
    if t >= tb1 + 0.3: f.icons.append(("CABIN", "cabin", CX, PEAK_Y - 0.6 * HERO, t - tb1 - 0.3))
    if tb1 <= t < tb1 + 3: f.big.append(("6:00 LEFT", t - tb1, 3))
    return f


def sc09(t, f):
    dur = DURS[9]
    st = base_state(9)
    f.o = O_SITE if FMT == "yt" else cam(CRY - 0.4 * CW)
    f.tod = (1, 0, 0); f.sun = kfl(t, [(0, 0.33), (dur, 0.45)])
    f.timer = kfl(t, [(0, 360), (dur, 240)])
    L = LEADS[9]; ph = vo_phr("09")
    t_find = L + ph[1]; t_take = L + ph[2] + 0.3; t_weap = L + ph[6]; t_lash = L + ph[7]; t_strap = L + ph[9]; t_ugly = L + ph[11]; t_love = L + ph[13]
    st["crack"] = min(1, max(0, (t - t_find) / 1.5)); st["crystal"] = 1 if t > t_find else 0
    hx = CRY - 0.62 * CW
    f.zoom = kf(t, [(0, 1.0), (t_find, 1.0), (t_find + 1.4, 1.7), (t_weap, 1.7), (t_weap + 1.2, 1.0)])
    f.zf = (CRY - 0.15 * CW - f.o, GY - 0.25 * CW)
    pads, tool, pose, sw = 0, "axe", "chop", (t - 0.2) / 0.26
    if t > t_find: pose, sw = "idle", 0
    if t > t_take: pose, tool = "cheer", "crystal"
    if t > t_weap: pose, tool = "idle", "crystal"
    if t > t_lash: pose, tool, sw = "hammer", "hammer", (t - t_lash) / 0.22
    if t > t_lash + 2.2: pose, tool = "idle", "spear"
    if t > t_strap: pose, tool = "crouch", None
    if t > t_strap + 2.0: pose, tool, pads = "idle", "spear", 1
    x = hx
    if t > t_ugly: pose, x = "walk", hx - 0.25 * CW * math.sin((t - t_ugly) * 1.5)
    if t > t_love: pose, x = "spear", hx - 0.25 * CW * math.sin((t_love - t_ugly) * 1.5)
    pads = 1 if t > t_strap + 2.0 else 0
    dr = -1 if pose == "walk" and math.cos((t - t_ugly) * 1.5) > 0 else 1

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0, canvas)
        if st["crack"] < 1 and t < t_find:
            pass
        hero(d, e, glows, x - f.o, GY, HERO, pose, dr, t, swing=sw, tool=tool, shield=True, pads=pads, ph=t * 6)
    f.draw.append(draw)
    if t >= t_lash + 1.8: f.icons.append(("CRYSTAL SPEAR", "spear", x, GY - 1.6 * HERO, t - (t_lash + 1.8)))
    if t >= t_strap + 2.0: f.icons.append(("ARMOR PADS", "pads", x, GY - 1.6 * HERO, t - (t_strap + 2.0)))
    return f


def sc10(t, f):
    dur = DURS[10]
    st = base_state(10)
    f.o = O_SITE; g_ = kfl(t, [(0, 0.0), (dur, 0.35)]); f.tod = (1 - g_, g_, 0); f.sun = kfl(t, [(0, 0.5), (dur, 0.58)])
    f.timer = kfl(t, [(0, 240), (2.0, 180), (dur, 175)])
    L = LEADS[10]; ph = vo_phr("10")
    t_look = L + ph[4]
    sx = CX - 0.95 * CW
    f.zoom = kf(t, [(0, 1.45), (t_look, 1.3), (t_look + 4, 1.0)])
    f.zf = (CX - 0.4 * CW - f.o, GY - 0.25 * CW)

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, f.tod[2], canvas)
        hero(d, e, glows, sx - f.o, GY - 0.05 * CW, HERO, "sit", 1, t, shield=True, pads=1)
        d.line([S(sx - 0.25 * HERO - f.o), S(GY - 0.12 * CW), S(sx + 0.15 * HERO - f.o), S(GY - 0.6 * HERO)], fill=(122, 82, 50, 255), width=int(S(0.028 * HERO)))
    f.draw.append(draw)
    if t < 2.5: f.big.append(("3:00 LEFT", t, 2.5))
    return f


def sc11(t, f):
    dur = DURS[11]
    st = base_state(11)
    f.o = O_SIEGE; f.tod = (0.35, 0.65, 0); f.sun = kfl(t, [(0, 0.6), (dur, 0.75)])
    f.timer = kfl(t, [(0, 175), (dur, 100)]); f.badge = "TIMELAPSE  x60"
    L = LEADS[11]; ph = vo_phr("11")
    t_sp0, t_sp1 = 0.8, L + ph[3]; t_tr0, t_tr1 = L + ph[4], dur - 1.2
    st["spikes"] = min(1, max(0, (t - t_sp0) / (t_sp1 - t_sp0)))
    st["trench"] = min(1, max(0, (t - t_tr0) / (t_tr1 - t_tr0)))
    st["logs"] = int(lerp(3, 0, st["spikes"])); st["logseat"] = 0
    spots = [-0.95, 0.9, -0.7, 0.75, -0.85]
    if t < t_sp1:
        i = int(t / 0.7) % len(spots); k = (t % 0.7) / 0.7
        x = CX + spots[i] * CW; pose = "dash" if k < 0.25 else "hammer"; sw = (k - 0.25) * 0.7 / 0.17; dr = 1 if spots[i] < 0 else -1; tool = "hammer"
        if k < 0.25: x = lerp(CX + spots[(i - 1) % len(spots)] * CW, x, ease(k / 0.25))
    elif t < t_tr0:
        x, pose, sw, dr, tool = lerp(CX - 0.95 * CW, (TRENCH[0] + TRENCH[1]) / 2, ease((t - t_sp1) / max(0.2, t_tr0 - t_sp1))), "walk", 0, -1, "hammer"
    else:
        x, pose, sw, dr, tool = (TRENCH[0] + TRENCH[1]) / 2, "chop", (t - t_tr0) / 0.24, -1, "stick"
    y = gy(x)

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0, canvas)
        hero(d, e, glows, x - f.o, y, HERO, pose, dr, t, swing=sw, tool=tool, ph=t * 16, pads=1)
        if t >= t_tr0:
            r = random.Random(int(t * 8))
            for j in range(5):
                a = (t * 8 % 1)
                px = x - f.o + r.uniform(-60, 60) * K; py = GY - r.uniform(0, 1) * 160 * K * math.sin(a * math.pi)
                d.ellipse([S(px - 6 * K), S(py - 5 * K), S(px + 6 * K), S(py + 5 * K)], fill=(120, 86, 56, 255))
            trench_front(d, f.o, st)
    f.draw.append(draw)
    if t >= t_sp1 - 0.6: f.icons.append(("SPIKE WALL", "spikes", CX - 0.6 * CW, GY - 1.7 * HERO, t - (t_sp1 - 0.6)))
    if t >= t_tr1 - 0.3: f.icons.append(("TRENCH", "trench", (TRENCH[0] + TRENCH[1]) / 2, GY - 1.6 * HERO, t - (t_tr1 - 0.3)))
    return f


def sc12(t, f):
    dur = DURS[12]
    st = base_state(12)
    f.o = O_SIEGE; f.tod = (0.2, 0.8, 0); f.sun = kfl(t, [(0, 0.75), (dur, 0.82)])
    f.timer = kfl(t, [(0, 100), (dur, 70)])
    L = LEADS[12]; ph = vo_phr("12")
    t_rope = L + ph[1]; t_tug = L + ph[3]; t_hold = L + ph[4]; t_prob = L + ph[6]
    st["gate"] = min(1, t / max(0.5, t_rope - 0.3)); st["rope"] = 1 if t > t_rope + 0.3 else 0
    tugging = t_tug <= t < t_tug + 1.2
    st["rope_tug"] = 1 if tugging else 0
    x = HINGE + 0.25 * CW
    pose = "hammer" if t < t_rope else ("pull" if tugging and int((t - t_tug) / 0.3) % 2 == 0 else "idle")
    if t > t_prob - 0.2: pose = "shrug"

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0, canvas)
        hero(d, e, glows, x - f.o, gy(x), HERO, pose, -1, t, swing=t / 0.22, tool="hammer" if t < t_rope else None, pads=1)
        trench_front(d, f.o, st)
    f.draw.append(draw)
    if t >= t_rope + 0.8: f.icons.append(("DRAWBRIDGE", "bridge", HINGE, GY - 1.7 * HERO, t - t_rope - 0.8))
    f.zoom = kf(t, [(0, 1.0), (t_tug - 0.5, 1.0), (t_tug + 0.5, 1.35), (dur, 1.35)]); f.zf = (HINGE - f.o, GY - 0.35 * HERO)
    return f


def sc13(t, f):
    dur = DURS[13]
    st = base_state(13)
    L = LEADS[13]; ph = vo_phr("13")
    t_look, t_arrows, t_flare, t_boul, t_hope, t_sun = L + ph[1], L + ph[1] + 1.6, L + ph[2], L + ph[3], L + ph[5], L + ph[6]
    f.o = O_SIEGE
    gk = kfl(t, [(0, 0.0), (t_sun, 0.15), (dur, 0.55)])
    f.tod = (0.05 * (1 - gk), 0.95 - gk * 0.4, gk * 0.45); f.sun = kfl(t, [(0, 0.82), (t_sun, 1.0)])
    f.timer = kfl(t, [(0, 70), (t_sun, 0)]); f.timer_red = t >= t_sun
    st["lookout"] = min(1, max(0, (t - 0.3) / 2.0)); st["beam"] = min(1, max(0, (t - t_boul) / 1.0))
    st["hoist"] = min(1, max(0, (t - t_boul - 1.0) / max(0.5, t_hope - t_boul - 1.0)))
    st["torches"] = min(1, max(0, (t - t_sun - 0.5) / 0.6))
    rx = CX - 0.05 * CW
    if t < t_arrows: x, y, pose, tool, sw, dr = rx, roof_y(rx), "hammer", "hammer", t / 0.22, -1
    elif t < t_boul: x, y, pose, tool, sw, dr = rx, roof_y(rx), "aim", "bow", 0, -1
    elif t < t_hope: x, y, pose, tool, sw, dr = CX - 0.42 * CW, roof_y(CX - 0.42 * CW), "pull", None, 0, 1
    else: x, y, pose, tool, sw, dr = rx, roof_y(rx), "idle", "bow", 0, -1

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, f.tod[2], canvas)
        hero(d, e, glows, x - f.o, y, HERO, pose, dr, t, swing=sw, tool=tool, pads=1, night=f.tod[2])
        if t_flare <= t < t_flare + 2.2:  # test flare arrow into the sky
            u = (t - t_flare) / 1.2
            ax0, ay0 = x - f.o - 0.3 * HERO, y - 0.75 * HERO
            if u <= 1:
                arrow(d, e, glows, ax0, ay0, ax0 - 0.5 * W, ay0 - 0.25 * H, u)
            else:
                k = (t - t_flare - 1.2)
                glows.append((ax0 - 0.5 * W, ay0 - 0.25 * H, 160 * K * (1 + k), (90, 220, 255), max(0, 1.4 - k * 1.4)))
        trench_front(d, f.o, st)
    f.draw.append(draw)
    if t >= t_look - 0.2: f.icons.append(("LOOKOUT", "lookout", rx, PEAK_Y - 0.9 * HERO, t - t_look + 0.2))
    if t >= t_arrows: f.icons.append(("CRYSTAL ARROWS", "arrows", rx, PEAK_Y - 0.9 * HERO, t - t_arrows))
    if t >= t_hope - 0.3: f.icons.append(("BOULDER TRAP", "boulder", HANG, EAVE_Y - 0.9 * HERO, t - t_hope + 0.3))
    if t >= t_sun: f.big.append(("0:00", t - t_sun, 2.5))
    return f


def eyes_list(seed, n, t0, t1, side="left"):
    r = random.Random(seed)
    out = []
    for i in range(n):
        x = r.uniform(-0.1, 0.42) * W + (O_SIEGE if FMT == "reel" else 0) if side == "left" else r.uniform(0.6, 1.0) * W
        y = GY - r.uniform(20, 160) * K
        if FMT == "reel" and r.random() < 0.4: y = r.uniform(GY + 40, 0.74 * H)
        out.append((lerp(t0, t1, r.random()), x, y, r.uniform(0.8, 1.2), r.uniform(0, 10)))
    return out


def draw_eyes(e, glows, lst, t, o, night, fade=1.0):
    for t0, ex, ey, es, phs in lst:
        if t >= t0:
            op = ease((t - t0) / 0.18) * fade
            blink = 0.1 if math.sin(t * 1.3 + phs) > 0.985 else 1
            eyes(e, glows, ex - o + math.sin(t * 1.5 + phs) * 3 * K, ey, 9 * K * es, 1, night, op * blink)


def sc14(t, f):
    dur = DURS[14]
    st = base_state(14)
    L = LEADS[14]; ph = vo_phr("14")
    f.o = O_SIEGE; f.tod = (0, 0.1, 0.9); f.sun = 1.0
    f.timer = 0 if t < 4 else None; f.timer_red = True
    t1, t10, tmany = L + ph[4], L + ph[5], L + ph[6]
    lst = [(t1, (0.08 * W + (O_SIEGE if FMT == "reel" else 0)), GY - 80 * K, 1.1, 0)] + eyes_list(3, 9, t10, t10 + 0.5) + eyes_list(4, 36, tmany, tmany + 1.2)
    f.zoom = kf(t, [(0, 1.0), (dur, 1.12)]); f.zf = (0.35 * W, GY - 0.3 * HERO)
    rx = CX - 0.05 * CW

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0.9, canvas)
        hero(d, e, glows, rx - f.o, roof_y(rx), HERO, "aim" if t > tmany else "idle", -1, t, tool="bow", pads=1, night=0.9)
        trench_front(d, f.o, st)
    f.draw.append(draw)
    f.front.append(lambda d, e, glows: draw_eyes(e, glows, lst, t, f.o, 0.9 + 0.1))
    return f


def wave(seed, n, t0, spacing, o):
    """Zombie wave: each walks from off-screen left toward the trench."""
    r = random.Random(seed)
    zs = []
    for i in range(n):
        zs.append(dict(ts=t0 + i * spacing + r.uniform(-0.2, 0.2), x0=o - 0.12 * W - r.uniform(0, 0.2) * W, v=r.uniform(0.55, 0.8) * HERO,
                       h=HERO * r.uniform(0.85, 1.05), seed=200 + seed * 50 + i))
    return zs


def sc15(t, f):
    dur = DURS[15]
    st = base_state(15)
    L = LEADS[15]; ph = vo_phr("15")
    f.o = O_SIEGE; f.tod = (0, 0.05, 0.95); f.sun = 1.0
    zs = wave(15, 12, 0.0, 1.35, f.o)
    fill = TRENCH[0] + 0.05 * CW
    spike_x = HINGE - 0.02 * CW
    kills = [L + ph[2] + 0.3, L + ph[3] + 0.3, L + ph[4] + 0.2, L + ph[4] + 1.0, L + ph[5] + 0.6, L + ph[5] + 1.6, dur - 1.8]
    count = [L + ph[2], L + ph[3], L + ph[4]]  # One. Two. Five.
    rx = CX - 0.05 * CW
    hx, hy = rx - f.o, roof_y(rx)
    zstate = []
    k_i = 0
    fallen = 0
    for i, z in enumerate(zs):
        if t < z["ts"]: continue
        x = z["x0"] + z["v"] * (t - z["ts"])
        dct = dict(x=x - f.o, y=GY, h=z["h"], ph=(t - z["ts"]) * 8, dir=1, seed=z["seed"])
        if i < 3:  # the first three tumble into the trench
            arrive = z["ts"] + (fill - z["x0"]) / z["v"]
            if t > arrive:
                k = min(1, (t - arrive) / 0.45)
                dct.update(x=fill + 0.12 * CW * k - f.o, y=GY + 0.1 * CW * k, crumble=0, h=z["h"] * (1 - k))
                if k >= 1: fallen += 1; continue
        else:
            stop = spike_x - 0.06 * CW * (i % 3)
            if x >= stop: dct["x"] = stop - f.o + math.sin(t * 9 + i) * 4 * K; dct["ph"] = t * 3
            if x > TRENCH[0] and x < TRENCH[1]: dct["y"] = GY - math.sin((x - TRENCH[0]) / (TRENCH[1] - TRENCH[0]) * math.pi) * 0.12 * CW
            kt = kills[k_i] if k_i < len(kills) else None
            k_i += 1
            if kt is not None and t > kt:
                dct["crumble"] = min(1.5, (t - kt) / 0.5)
            dct["kill_t"] = kt
        zstate.append(dct)
    shots = [(z.get("kill_t"), z) for z in zstate if z.get("kill_t") is not None]
    flash = 0
    for kt, z in shots:
        if kt and 0 <= t - kt < 0.25: flash = max(flash, 1 - (t - kt) / 0.25)
    aiming = any(kt and -0.4 <= t - kt <= 0.05 for kt, z in shots)

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0.95, canvas)
        for z in zstate: zdraw(d, e, glows, z, t, 0.95)
        for kt, z in shots:
            u = (t - (kt - 0.35)) / 0.35
            if 0 <= u <= 1: arrow(d, e, glows, hx - 0.3 * HERO, hy - 0.75 * HERO, z["x"], GY - 0.6 * z["h"], u)
            if 0 <= t - kt < 0.5: glows.append((z["x"], GY - 0.6 * z["h"], 160 * K, (90, 220, 255), 1.6 * (1 - (t - kt) / 0.5)))
        hero(d, e, glows, hx, hy, HERO, "aim", -1, t, tool="bow", pads=1, night=0.95)
        trench_front(d, f.o, st)
    f.draw.append(draw)
    f.front.append(lambda d, e, glows: draw_eyes(e, glows, eyes_list(4, 30, -5, -4), t, f.o, 1.0, fade=0.6))
    for c, txt in zip(count, ("ONE", "TWO", "FIVE")):
        if c <= t < c + 0.7: f.big.append((txt, t - c, 0.7))
    return f


def sc16(t, f):
    dur = DURS[16]
    st = base_state(16)
    L = LEADS[16]; ph = vo_phr("16")
    f.o = O_SIEGE; f.tod = (0, 0.05, 0.95); f.sun = 1.0
    t_peb = L + ph[2]
    rx = CX - 0.05 * CW
    zs = []
    r = random.Random(16)
    for i in range(5):
        x = HINGE - 0.15 * CW - i * 0.22 * CW - r.uniform(0, 0.1) * CW - 0.35 * HERO * t
        zs.append(dict(x=x - f.o, y=GY, h=HERO * r.uniform(0.85, 1.0), ph=t * 6 + i, dir=-1, seed=300 + i))
    thud = max(0, t - t_peb)
    beat = (thud % 0.75) / 0.75 if thud > 0 else 1
    f.shake = (1 - beat) * 0.6 * min(1, thud / 2) if thud > 0 else 0

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0.95, canvas)
        for z in zs: zdraw(d, e, glows, z, t, 0.95)
        hero(d, e, glows, rx - f.o, roof_y(rx), HERO, "idle", -1, t, tool="bow", pads=1, night=0.95)
        if thud > 0:
            for j in range(9):
                px = CX + (-0.5 + j / 8) * 1.0 * CW - f.o
                py = roof_y(CX + (-0.5 + j / 8) * CW) - 4 * K - abs(math.sin(t * 9 + j * 1.7)) * 22 * K * (1 - beat) * min(1, thud)
                d.ellipse([S(px - 4 * K), S(py - 4 * K), S(px + 4 * K), S(py + 4 * K)], fill=(150, 150, 150, 255))
        trench_front(d, f.o, st)
    f.draw.append(draw)
    return f


def brute_x(t, dur, L, ph):
    """Brute path in scene 17 (world x, y, pose)."""
    t_in, t_tr, t_gate = 0.0, L + ph[1], L + ph[2] + 0.9
    x0 = (O_SIEGE - 0.25 * W)
    tx = (TRENCH[0] + TRENCH[1]) / 2
    if t < t_tr: return lerp(x0, tx - 0.05 * CW, t / t_tr), 0
    if t < t_gate: return lerp(tx - 0.05 * CW, tx + 0.02 * CW, (t - t_tr) / (t_gate - t_tr)), 0.18 * CW * min(1, (t - t_tr) / 0.6)
    return tx + 0.02 * CW, 0.18 * CW


def sc17(t, f):
    dur = DURS[17]
    st = base_state(17)
    L = LEADS[17]; ph = vo_phr("17")
    f.o = O_SIEGE; f.tod = (0, 0.05, 0.95); f.sun = 1.0
    bh = 2.8 * HERO
    bx, sink = brute_x(t, dur, L, ph)
    t_smash = L + ph[2] + 1.0; t_snap = L + ph[3] - 0.1
    smashing = t_smash <= t < t_snap + 0.4
    if smashing: st["gate_shake"] = 1
    if t >= t_snap:
        st["rope"] = 2; st["gate_down"] = min(1.0, ((t - t_snap) / 0.45) ** 2)
    step = (t * 1.1) % 1
    f.shake = max(f.shake, (1 - step) * 0.5 if t < L + ph[2] else 0)
    if t_snap <= t < t_snap + 0.5: f.shake = 1.2
    rx = CX - 0.05 * CW
    flood = wave(17, 7, t_snap + 0.8, 0.45, f.o) if t > t_snap else []

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0.95, canvas)
        ph_b = t * 3.0 if not smashing else 0
        brute(d, e, glows, bx - f.o, GY + sink, bh, ph_b, 1, t, pose="leap" if smashing and int(t * 3) % 2 else "run")
        for z in flood:
            if t < z["ts"]: continue
            x = TRENCH[0] - 0.3 * CW + z["v"] * 1.6 * (t - z["ts"])
            y = GY - (0.05 * CW if TRENCH[0] < x < TRENCH[1] + 0.1 * CW else 0)
            zdraw(d, e, glows, dict(x=min(x, CX - 0.2 * CW) - f.o, y=y, h=z["h"], ph=(t - z["ts"]) * 12, dir=1, seed=z["seed"]), t, 0.95)
        hero(d, e, glows, rx - f.o, roof_y(rx), HERO, "aim", -1, t, tool="bow", pads=1, night=0.95)
        if t_snap <= t < t_snap + 0.6:
            dust(d, HINGE - f.o - GATE_L * 0.5, GY, (t - t_snap), 7, size=1.2)
        trench_front(d, f.o, st)
    f.draw.append(draw)
    f.front.append(lambda d, e, glows: draw_eyes(e, glows, eyes_list(4, 30, -5, -4), t, f.o, 1.0, fade=0.5))
    if 0.6 <= t < 3.4: f.big.append(("BRUTE", t - 0.6, 2.8))
    if t_snap <= t < t_snap + 1.0: f.big.append(("SNAP!", t - t_snap, 1.0))
    return f


def sc18(t, f):
    dur = DURS[18]
    st = base_state(18)
    L = LEADS[18]; ph = vo_phr("18")
    f.o = O_SIEGE; f.tod = (0, 0.05, 0.95); f.sun = 1.0
    t_land = 0.9
    t_wall, t_duck, t_spin, t_door, t_hit = L + ph[1] + 1.4, L + ph[1] + 2.4, L + ph[1] + 3.1, L + ph[1] + 4.0, L + ph[2] + 0.4
    rx = CX - 0.05 * CW
    door = CX - 0.18 * CW
    pads = 2 if t > t_hit else 1
    if t < t_land:
        k = t / t_land; x = lerp(rx, door - 0.2 * CW, k); y = lerp(roof_y(rx), gy(door), k) - math.sin(k * math.pi) * 0.5 * HERO; pose, tool, dr, sw = "jump", "spear", -1, 0
    elif t < t_wall:
        x, y, pose, tool, dr, sw = door - 0.2 * CW, gy(door), "thrust", "spear", -1, (t - t_land) / 0.55
    elif t < t_duck:
        k = (t - t_wall) / (t_duck - t_wall); x = lerp(door - 0.2 * CW, CX - 0.45 * CW, k); y = gy(x) - math.sin(k * math.pi) * 0.7 * HERO; pose, tool, dr, sw = "jump", "spear", -1, 0
    elif t < t_spin:
        x, y, pose, tool, dr, sw = CX - 0.45 * CW, gy(CX - 0.45 * CW), "crouch", None, -1, 0
    elif t < t_door:
        x, y = CX - 0.45 * CW, gy(CX - 0.45 * CW); pose, tool = "thrust", "spear"; dr = -1 if int((t - t_spin) * 8) % 2 else 1; sw = (t - t_spin) / 0.3
    else:
        x, y, pose, tool, dr, sw = door, gy(door), "thrust", "spear", -1, (t - t_door) / 0.5
    zs = []
    r = random.Random(18)
    for i in range(6):
        ts = i * 0.9
        if t < ts: continue
        base_x = TRENCH[1] + 0.05 * CW + (t - ts) * 0.6 * HERO
        stop = x - 0.32 * HERO - i * 0.04 * CW
        zx = min(base_x, stop)
        # knock-back whenever the hero thrusts
        if pose == "thrust" and (sw % 1) < 0.5 and zx >= stop - 1: zx -= 0.25 * CW * math.sin((sw % 1) / 0.5 * math.pi)
        zs.append(dict(x=zx - f.o, y=gy(zx), h=HERO * r.uniform(0.85, 1.0), ph=t * 9 + i, dir=1, seed=400 + i))
    bx = (TRENCH[0] + TRENCH[1]) / 2 + 0.02 * CW + max(0, t - 2) * 0.05 * CW

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0.95, canvas)
        brute(d, e, glows, bx - f.o, GY + 0.18 * CW * max(0, 1 - max(0, t - 6) / 2), 2.8 * HERO, t * 2.4, 1, t)
        for z in zs: zdraw(d, e, glows, z, t, 0.95)
        hero(d, e, glows, x - f.o, y, HERO, pose, dr, t, swing=sw, tool=tool, pads=pads, night=0.95)
        if t_hit <= t < t_hit + 0.3:
            for j in range(7):
                a = j * 0.9
                e.line([S(x - f.o + math.cos(a) * 12 * K), S(y - 0.4 * HERO + math.sin(a) * 12 * K), S(x - f.o + math.cos(a) * 40 * K), S(y - 0.4 * HERO + math.sin(a) * 40 * K)],
                       fill=(255, 240, 200, 255), width=int(S(3 * K)))
        trench_front(d, f.o, st)
    f.draw.append(draw)
    if t_hit <= t < t_hit + 1.2: f.big.append(("CRACK!", t - t_hit, 1.2))
    f.zoom = kf(t, [(0, 1.0), (t_land, 1.25), (dur, 1.25)]); f.zf = (CX - 0.45 * CW - f.o, GY - 0.5 * HERO)
    return f


def sc19(t, f):
    dur = DURS[19]
    st = base_state(19)
    L = LEADS[19]; ph = vo_phr("19")
    f.o = O_SIEGE; f.tod = (0, 0.05, 0.95); f.sun = 1.0
    t_up = 1.6; t_big = L + ph[1]; t_rope = L + ph[3]; t_boulder = L + ph[4]
    rx = CX - 0.5 * CW
    if t < t_up:
        k = t / t_up; x = lerp(CX - 0.18 * CW, rx, k); y = lerp(gy(CX), roof_y(rx), k) - math.sin(k * math.pi) * 0.4 * HERO; pose = "jump"
    else:
        x, y, pose = rx, roof_y(rx), "spear"
    bx = lerp((TRENCH[0] + TRENCH[1]) / 2 + 0.2 * CW, HANG, ease(min(1, t / max(1, t_big + 1.0))))
    climbers = []
    for i in range(4):
        cxw = CX + (-0.5 + 0.3 * i) * CW
        cy = BASE_Y - (0.1 + 0.18 * t / dur + 0.06 * i) * WALL_H * 2.0
        climbers.append((cxw, cy, i))
    f.zoom = kf(t, [(0, 1.0), (t_big, 1.15), (dur, 1.45)]); f.zf = (HANG - f.o + 0.15 * CW, EAVE_Y)
    glow_rope = t >= t_rope

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0.95, canvas)
        brute(d, e, glows, bx - f.o, GY, 2.8 * HERO, t * 2.0 if bx < HANG - 1 else 0, 1, t)
        for cxw, cy, i in climbers:
            zombie(d, e, glows, cxw - f.o, cy + HERO * 0.9, HERO * 0.9, t * 4 + i, 1, 500 + i, pose="leap")
        hero(d, e, glows, x - f.o, y, HERO, pose, -1, t, tool="spear", pads=2, night=0.95)
        if glow_rope:
            glows.append((HANG - f.o, EAVE_Y + 0.12 * CW, 0.2 * CW, (255, 240, 180), 0.5 + 0.4 * math.sin(t * 8)))
        if t >= t_boulder:
            glows.append((HANG - f.o, EAVE_Y + 0.3 * CW, 0.35 * CW, (255, 240, 180), 0.6 + 0.4 * math.sin(t * 8)))
    f.draw.append(draw)
    f.front.append(lambda d, e, glows: draw_eyes(e, glows, eyes_list(4, 30, -5, -4), t, f.o, 1.0, fade=0.4))
    return f


def sc20(t, f):
    dur = DURS[20]
    st = base_state(20)
    L = LEADS[20]; ph = vo_phr("20")
    f.o = O_SIEGE
    t_cut = 0.35; t_imp = L + ph[1] - 0.6; t_rise = L + ph[1]; t_sun = L + ph[2] + 0.2
    rise = ease((t - t_rise) / 3.0) if t > t_rise else 0
    f.tod = (0, rise * 0.9, 1 - rise * 0.9)
    f.sunrise = rise
    st["rope_cut"] = 1 if t > t_cut else 0
    hang_y = EAVE_Y - 0.02 * CW + 0.3 * CW
    land_y = GY - 1.1 * HERO
    if t > t_cut:
        k = min(1, (t - t_cut) / (t_imp - t_cut))
        k2 = k * 0.35 if k < 0.75 else 0.35 * 0.75 / 0.75 + (k - 0.75) / 0.25 * 0.65  # slow-mo, then real speed
        st["boulder_y"] = lerp(hang_y, land_y if t < t_imp + 0.5 else GY - 0.1 * CW, min(1, k2 if t < t_imp else 1))
        if t > t_imp + 0.5: st["boulder_y"] = lerp(land_y, gy(HANG) - 0.1 * CW, min(1, (t - t_imp - 0.5) / 0.4))
    squash = min(0.75, max(0, (t - t_imp) / 0.25) * 0.75) if t > t_imp else 0
    f.shake = 1.5 * max(0, 1 - (t - t_imp) / 0.6) if t > t_imp else 0
    f.slowmo = t_cut < t < t_imp
    rx = CX - 0.5 * CW
    front_x = W * 1.1 - (t - t_sun) / 2.6 * W * 1.3 if t > t_sun else W * 2  # light sweeps right -> left
    zs = []
    r = random.Random(20)
    for i in range(10):
        zx = TRENCH[0] - 0.4 * CW + i * 0.17 * CW + r.uniform(-0.04, 0.04) * CW
        z = dict(x=zx - f.o, y=gy(zx), h=HERO * r.uniform(0.85, 1.0), ph=t * 5 + i, dir=1, seed=600 + i)
        if (zx - f.o) > front_x: z["crumble"] = min(1.5, (z["x"] - front_x) / (0.25 * W))
        zs.append(z)
    climbers = [(CX + (-0.5 + 0.3 * i) * CW, BASE_Y - (0.28 + 0.06 * i) * WALL_H * 2.0, i) for i in range(4)]

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, f.tod[2], canvas)
        bc = (HANG - f.o) > front_x
        if not bc or squash < 0.75:
            brute(d, e, glows, HANG - f.o, GY, 2.8 * HERO, 0, 1, t, squash=squash)
        if t > t_imp and (HANG - f.o) > front_x:
            ash(d, HANG - f.o, GY, (t - t_sun), 77, n=60, spread=2.2)
        for z in zs: zdraw(d, e, glows, z, t, f.tod[2])
        for cxw, cy, i in climbers:
            zz = dict(x=cxw - f.o, y=cy + HERO * 0.9, h=HERO * 0.9, ph=0, dir=1, seed=500 + i, pose="leap")
            if (cxw - f.o) > front_x: zz["crumble"] = min(1.5, ((cxw - f.o) - front_x) / (0.25 * W))
            zdraw(d, e, glows, zz, t, f.tod[2])
        hero(d, e, glows, rx - f.o, roof_y(rx), HERO, "thrust" if t < t_cut + 0.3 else ("cheer" if t > t_sun + 1.5 else "spear"), -1, t,
             swing=(t / 0.6), tool="spear", pads=2, night=f.tod[2])
        if t > t_imp:
            dust(d, HANG - f.o, GY, t - t_imp, 21, n=22, size=1.8)
    f.draw.append(draw)
    if t > t_imp and t < t_imp + 1.2: f.big.append(("BOOM", t - t_imp, 1.2))
    if t > t_sun: f.rays = (min(1, (t - t_sun) / 1.5), front_x)
    f.zoom = kf(t, [(0, 1.45), (t_imp, 1.2), (t_imp + 1.0, 1.0)]); f.zf = (HANG - f.o + 0.15 * CW, EAVE_Y + 0.2 * CW)
    return f


def sc21(t, f):
    dur = DURS[21]
    st = base_state(21)
    L = LEADS[21]; ph = vo_phr("21")
    f.o = O_SIEGE
    dk = kfl(t, [(0, 0.0), (dur, 0.85)])
    f.tod = (dk, 1 - dk, 0); f.sun = kfl(t, [(0, 0.85), (dur, 0.6)])
    t_end = L + ph[3]
    rx = CX - 0.05 * CW
    f.zoom = kf(t, [(0, 1.5), (t_end - 1, 1.0)]); f.zf = (rx - f.o, roof_y(rx) - 0.4 * HERO)

    def draw(d, e, glows, canvas):
        world(d, e, glows, f.o, st, t, 0, canvas)
        hero(d, e, glows, rx - f.o, roof_y(rx) + 0.18 * HERO, HERO, "sit", 1, t, pads=2, flow=0.8)
        d.line([S(rx - f.o - 0.25 * HERO), S(roof_y(rx) - 0.05 * HERO), S(rx - f.o + 0.35 * HERO), S(roof_y(rx) - 0.2 * HERO)], fill=(122, 82, 50, 255), width=int(S(0.028 * HERO)))
        ash(d, 0.4 * W, GY - 0.2 * HERO, 0.6 + (t % 2.5), 900 + int(t / 2.5), n=40, spread=3.0, col=(110, 100, 100))
        trench_front(d, f.o, st)
    f.draw.append(draw)
    if 0.3 <= t < 4.3: f.big.append(("NIGHT 1 SURVIVED", t - 0.3, 4.0))
    if t >= t_end: f.endscreen = t - t_end
    return f


SCENES = {1: sc01, 2: sc02, 3: sc03, 4: sc04, 5: sc05, 6: sc06, 7: sc07, 8: sc08, 9: sc09, 10: sc10, 11: sc11, 12: sc12, 13: sc13,
          14: sc14, 15: sc15, 16: sc16, 17: sc17, 18: sc18, 19: sc19, 20: sc20, 21: sc21}


# ================================================================ renderer
def sun_xy(u):
    return lerp(T.SUN_DAY[0], T.SUN_SET[0], u), lerp(T.SUN_DAY[1], T.SUN_SET[1], u ** 1.4)


def extra_icon(d, kind, x, y, s):
    if kind in ("axe", "cabin", "spikes"): return draw_icon(d, kind, x, y, s)
    if kind == "shield":
        d.ellipse([x - s * .5, y - s * .5, x + s * .5, y + s * .5], fill=(150, 104, 62)); d.ellipse([x - s * .12, y - s * .12, x + s * .12, y + s * .12], fill=(140, 140, 150))
    elif kind == "spear":
        d.line([x - s * .5, y + s * .5, x + s * .3, y - s * .3], fill=(122, 82, 50), width=int(s * .12))
        d.polygon([(x + s * .55, y - s * .55), (x + s * .38, y - s * .2), (x + s * .2, y - s * .38)], fill=(90, 220, 255))
    elif kind == "pads":
        d.rounded_rectangle([x - s * .35, y - s * .45, x + s * .35, y + s * .45], radius=int(s * .15), fill=(150, 150, 160))
    elif kind == "trench":
        d.polygon([(x - s * .55, y - s * .1), (x + s * .55, y - s * .1), (x + s * .35, y + s * .45), (x - s * .35, y + s * .45)], fill=(90, 60, 40))
    elif kind == "bridge":
        d.rectangle([x - s * .55, y - s * .1, x + s * .55, y + s * .12], fill=(150, 100, 60)); d.line([x - s * .5, y - s * .1, x - s * .1, y - s * .55, x + s * .5, y - s * .1], fill=(92, 150, 58), width=int(s * .08))
    elif kind == "lookout":
        d.line([x - s * .4, y + s * .5, x - s * .4, y - s * .2], fill=(120, 80, 50), width=int(s * .1)); d.line([x + s * .4, y + s * .5, x + s * .4, y - s * .2], fill=(120, 80, 50), width=int(s * .1))
        d.line([x - s * .5, y - s * .2, x + s * .5, y - s * .2], fill=(120, 80, 50), width=int(s * .12)); d.polygon([(x, y - s * .2), (x, y - s * .6), (x + s * .35, y - s * .45)], fill=(240, 210, 110))
    elif kind == "arrows":
        for k in (-0.2, 0.2):
            d.line([x - s * .5 + k * s, y + s * .5, x + s * .3 + k * s, y - s * .3], fill=(122, 82, 50), width=int(s * .08))
            d.polygon([(x + s * .45 + k * s, y - s * .45), (x + s * .3 + k * s, y - s * .15), (x + s * .15 + k * s, y - s * .3)], fill=(90, 220, 255))
    elif kind == "boulder":
        d.line([x, y - s * .6, x, y - s * .2], fill=(92, 150, 58), width=int(s * .08)); d.ellipse([x - s * .38, y - s * .25, x + s * .38, y + s * .5], fill=(130, 132, 136))
    elif kind in ("sunmoon", "hands", "island"):
        if kind == "sunmoon":
            d.pieslice([x - s * .5, y - s * .5, x + s * .5, y + s * .5], 90, 270, fill=(255, 210, 60))
            d.pieslice([x - s * .5, y - s * .5, x + s * .5, y + s * .5], 270, 90, fill=(30, 36, 80))
            for k in (0.12, 0.3): d.ellipse([x + s * k - s * .06, y - s * .1, x + s * k + s * .06, y + s * .02], fill=(255, 160, 40))
        elif kind == "hands":
            for sx in (-1, 1):
                d.rounded_rectangle([x + sx * s * .3 - s * .17, y - s * .25, x + sx * s * .3 + s * .17, y + s * .35], radius=int(s * .1), fill=(30, 28, 36))
                for k in range(4): d.rounded_rectangle([x + sx * s * .3 - s * .17 + k * s * .09, y - s * .5, x + sx * s * .3 - s * .1 + k * s * .09, y - s * .2], radius=int(s * .03), fill=(30, 28, 36))
        else:
            d.polygon([(x - s * .5, y), (x + s * .5, y), (x, y + s * .55)], fill=(120, 120, 130)); d.ellipse([x - s * .5, y - s * .12, x + s * .5, y + s * .1], fill=(110, 190, 90))
            d.ellipse([x - s * .2, y - s * .5, x + s * .2, y - s * .05], fill=(80, 160, 80))


def draw_ui(img, f, tx):
    d = ImageDraw.Draw(img)
    night = f.tod[2]
    if f.timer is not None:
        tx0, ty0, ts = T.TIMER
        r = 26 * ts; cx, cy = tx0 + r, ty0 + r
        mins = max(0, int(round(f.timer)))
        txt = f"{mins // 60}:{mins % 60:02d}"
        if night > 0.5:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(236, 236, 255), outline=(16, 14, 26), width=int(4 * ts))
            d.ellipse([cx - r * .35, cy - r * 1.05, cx + r * 1.3, cy + r * .7], fill=(30, 36, 80))
        else:
            for k in range(8):
                a = k * math.pi / 4
                d.line([cx + math.cos(a) * r * 1.15, cy + math.sin(a) * r * 1.15, cx + math.cos(a) * r * 1.5, cy + math.sin(a) * r * 1.5], fill=(255, 210, 60), width=int(5 * ts))
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 210, 60), outline=(16, 14, 26), width=int(4 * ts))
        blink = not f.timer_red or int(f._t * 4) % 2 == 0
        if blink:
            text_c(d, (cx + r * 1.9, cy + 2), txt, 54 * ts, fill=(255, 70, 60) if f.timer_red else (255, 255, 255), weight="ExtraBold", anchor="lm")
    if f.badge:
        bs = 30 * (1.25 if FMT == "reel" else 1)
        bx = W - 40 if FMT == "yt" else 0.80 * W
        by = 52 if FMT == "yt" else T.TIMER[1] + 30
        fnt = font(bs, "ExtraBold"); tw = d.textlength(f.badge, font=fnt)
        d.rounded_rectangle([bx - tw - 70, by - bs * .9, bx, by + bs * .9], radius=int(bs * .9), fill=(16, 14, 26))
        d.polygon([(bx - tw - 52, by - bs * .45), (bx - tw - 52, by + bs * .45), (bx - tw - 30, by)], fill=(255, 210, 60))
        d.polygon([(bx - tw - 36, by - bs * .45), (bx - tw - 36, by + bs * .45), (bx - tw - 14, by)], fill=(255, 210, 60))
        d.text((bx - 18, by), f.badge, font=fnt, fill=(255, 255, 255), anchor="rm")
    for kind, wx, wy, age in f.marks:
        if age < 0: continue
        x, y = tx(wx - f.o, wy)
        sc = pop_scale(age); s = 60 * K * sc
        if kind == "x":
            for a in (1, -1):
                d.line([x - s, y - s * a, x + s, y + s * a], fill=(16, 14, 26), width=int(30 * K)); d.line([x - s, y - s * a, x + s, y + s * a], fill=(255, 64, 54), width=int(20 * K))
        else:
            pts = [(x - s, y), (x - s * .3, y + s * .7), (x + s * 1.1, y - s * .8)]
            d.line(pts, fill=(16, 14, 26), width=int(30 * K), joint="curve"); d.line(pts, fill=(90, 230, 90), width=int(20 * K), joint="curve")
    for label, kind, wx, wy, age in f.icons:
        if 0 <= age < 1.6:
            x, y = tx(wx - f.o, wy)
            x = min(max(x, 160 * K), (0.80 if FMT == "reel" else 0.95) * W - 160 * K); y = max(y, (0.2 if FMT == "reel" else 0.12) * H)
            sc = pop_scale(age); y -= 30 * K * ease(age / 1.6)
            s = 50 * K * sc
            d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 255, 255), outline=(16, 14, 26), width=int(5 * K))
            extra_icon(d, kind, x, y, s * 0.9)
            if age < 1.45: text_c(d, (x, y + s + 28 * K), label, 34 * K * sc, weight="ExtraBold")
    if f.rules:
        n = 0
        for kind, age in f.rules:
            if age < 0: continue
            n += 1
        xs = [0.32, 0.5, 0.68] if FMT == "yt" else [0.2, 0.46, 0.72]
        for i, (kind, age) in enumerate(f.rules):
            if age < 0: continue
            x, y = xs[i] * W, (0.62 if FMT == "yt" else 0.5) * H
            s = 70 * K * pop_scale(age)
            d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 255, 255), outline=(16, 14, 26), width=int(6 * K))
            extra_icon(d, kind, x, y, s * 0.9)
    if f.title:
        l1, l2, age = f.title
        cxp = W / 2 if FMT == "yt" else 0.46 * W
        y0 = 0.17 * H if FMT == "yt" else 0.25 * H
        sz = 76 if FMT == "yt" else 58
        a = pop_scale(age - 0.2)
        if a > 0:
            text_c(d, (cxp, y0), l1, sz * a, fill=(255, 214, 90), sw=int(sz * .1))
            text_c(d, (cxp, y0 + sz * 1.25), l2, sz * 1.0 * a, sw=int(sz * .1))
    for txt, age in f.caps:
        sz = getattr(f, "capsz", None) or (44 if FMT == "yt" else 46)
        cxp = W / 2 if FMT == "yt" else 0.46 * W
        y = 0.86 * H if FMT == "yt" else 0.22 * H
        fit = min(1, (0.8 if FMT == "yt" else 0.76) * W / d.textlength(txt, font=font(sz, "ExtraBold")))
        text_c(d, (cxp, y), txt, sz * fit * pop_scale(age), weight="Black" if sz > 60 else "ExtraBold", sw=int(sz * fit * .11))
    for txt, age, life in f.big:
        if age < 0 or age > life: continue
        sz = (120 if FMT == "yt" else 104) * pop_scale(age)
        cxp = W / 2 if FMT == "yt" else 0.46 * W
        y = 0.2 * H if FMT == "yt" else 0.3 * H
        col = (255, 70, 60) if txt in ("0:00", "BRUTE", "SNAP!", "CRACK!") else (255, 255, 255)
        if txt == "NIGHT 1 SURVIVED": col = (255, 214, 90)
        fit = min(1, (0.85 if FMT == "yt" else 0.76) * W / max(1, d.textlength(txt, font=font(sz))))
        text_c(d, (cxp, y), txt, sz * fit, fill=col, sw=int(sz * fit * .1))
    if f.endscreen is not None:
        a = ease(f.endscreen / 0.6)
        if a > 0:
            text_c(d, (W / 2, 0.14 * H), "WHAT WOULD YOU BUILD FIRST?", 70 * a, sw=7)
            # end-screen element zones (YouTube places the real video + subscribe elements on top)
            vx0, vy0, vw = 0.12 * W, 0.3 * H, 0.42 * W
            d.rounded_rectangle([vx0, vy0, vx0 + vw, vy0 + vw * 9 / 16], radius=18, fill=(20, 26, 60), outline=(255, 255, 255), width=6)
            # mini Floating Islands teaser card
            cxm, cym = vx0 + vw / 2, vy0 + vw * 9 / 32
            for k, (dx, dy, s) in enumerate([(-0.25, -0.05, 1.0), (0.18, 0.05, 0.75), (0.02, -0.2, 0.5)]):
                ix, iy, iw = cxm + dx * vw, cym + dy * vw * 0.56, 0.18 * vw * s
                d.polygon([(ix - iw / 2, iy), (ix + iw / 2, iy), (ix, iy + iw * 0.8)], fill=(120, 130, 150)); d.ellipse([ix - iw * .55, iy - iw * .12, ix + iw * .55, iy + iw * .1], fill=(110, 200, 100))
            text_c(d, (cxm, vy0 + vw * 9 / 16 - 40), "NEXT: FLOATING ISLANDS", 40, weight="ExtraBold", sw=4)
            sx, sy, sr = 0.73 * W, vy0 + vw * 9 / 32, 0.1 * W
            try:
                av = Image.open(os.path.join(ROOT, "channel", "art", "avatar_800x800.png")).convert("RGB").resize((int(sr * 2), int(sr * 2)))
                m = Image.new("L", av.size, 0); ImageDraw.Draw(m).ellipse([0, 0, av.size[0] - 1, av.size[1] - 1], fill=255)
                img.paste(av, (int(sx - sr), int(sy - sr)), m)
            except Exception:
                pass
            d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], outline=(255, 255, 255), width=6)
            d.rounded_rectangle([sx - 150, sy + sr + 24, sx + 150, sy + sr + 90], radius=33, fill=(226, 38, 40))
            text_c(d, (sx, sy + sr + 57), "SUBSCRIBE", 36, weight="ExtraBold", sw=0)


def render(f, t, L, sky, vig):
    f._t = t
    w = f.tod
    night = w[2]
    o = f.o
    fr = (sky[0] * w[0] + sky[1] * w[1] + sky[2] * w[2]).astype(np.float32)
    fr += sky[3] * (w[0] + 0.5 * w[1]) * (0 if f.sunrise is not None else 1)
    if f.sunrise is not None:
        sx, sy = T.SUN_SET[0], T.SUN_SET[1] - f.sunrise * 0.12 * H
        add_glow(fr, sx, sy, 320 * K, (255, 190, 110), f.sunrise * 1.2)
        add_glow(fr, sx, sy, 60 * K, (255, 250, 220), f.sunrise * 1.8)
    else:
        sx, sy = sun_xy(f.sun)
        add_glow(fr, sx, sy, 200 * K, (255, 220, 140), (w[0] + w[1]) * 0.9)
        add_glow(fr, sx, sy, 46 * K, (255, 255, 230), (w[0] + w[1]) * 1.6)
    add_glow(fr, T.MOON[0], T.MOON[1], 150 * K, (120, 150, 255), night * 0.45)
    add_glow(fr, T.MOON[0], T.MOON[1], 34 * K, (250, 250, 255), night * 1.8)
    m, a = grade(w)
    if f.rays:  # sunrise light front: everything right of it is warm-lit
        k, fx = f.rays
        mask = np.clip((np.arange(W, dtype=np.float32) - fx) / (0.2 * W), 0, 1)[None, :, None] * k
    comp(fr, L["far"], o * 0.12, m * 0.9 + 0.1, a + np.array([10, 14, 20], np.float32) * night)
    comp(fr, L["mid"], o * 0.45, m, a)
    comp(fr, L["ground"], o, m, a)
    lit = Image.new("RGBA", (S(W), S(H)), (0, 0, 0, 0)); emi = Image.new("RGBA", (S(W), S(H)), (0, 0, 0, 0))
    d, e = ImageDraw.Draw(lit), ImageDraw.Draw(emi)
    glows = []
    for fn in f.draw:
        fn(d, e, glows, lit)
    for fx_, fy_, ph_ in T.FIREFLIES:
        x = fx_ - o * 0.8 + math.sin(t * 0.9 + ph_) * 18 * K
        y = fy_ + math.sin(t * 1.3 + ph_ * 2) * 14 * K
        if -20 < x < W + 20:
            amt = (0.25 * w[0] + 0.55 * w[1] + 0.7 * night) * (0.6 + 0.4 * math.sin(t * 4 + ph_ * 3))
            add_glow(fr, x, y, 13 * K, (255, 236, 150), amt); add_glow(fr, x, y, 3 * K, (255, 255, 220), amt * 1.2)
    comp_img(fr, lit, m, a)
    for gx, gy_, gr, gc, ga in glows:
        add_glow(fr, gx, gy_, gr, gc, ga)
    comp(fr, L["fg"], o * 1.3, m * 0.8, a * 0.5)
    if f.front:
        g2 = []
        for fn in f.front: fn(e, e, g2)
        for gx, gy_, gr, gc, ga in g2: add_glow(fr, gx, gy_, gr, gc, ga)
    comp_img(fr, emi)
    if f.rays:
        fr += mask * np.array([70, 40, 0], np.float32)
    if f.desat:
        g = fr.mean(axis=2, keepdims=True); fr = fr * (1 - f.desat) + g * f.desat
    if f.flash: fr += 120 * f.flash
    if f.rewind:
        k = f.rewind; sh = int(16 * k * K)
        if sh:
            fr[:, :, 0] = np.roll(fr[:, :, 0], sh, axis=1); fr[:, :, 2] = np.roll(fr[:, :, 2], -sh, axis=1)
        r = np.random.default_rng(int(t * 1000))
        for _ in range(int(14 * k) + 1):
            y0 = r.integers(0, H); hgt = r.integers(2, 10)
            fr[y0:y0 + hgt] = fr[y0:y0 + hgt] * 0.5 + 170 * k
    if getattr(f, "slowmo", False):
        g = fr.mean(axis=2, keepdims=True); fr = fr * 0.6 + g * 0.4 * np.array([0.9, 1.0, 1.2], np.float32)
    fr *= (1 - vig * (0.25 + 0.45 * night))
    if f.endscreen is not None:
        fr *= 1 - 0.55 * ease(f.endscreen / 0.6)
    fr += T.RNG.normal(0, 2.0, (H, W, 1)).astype(np.float32)
    img = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8))
    # camera zoom (crop around the focus point)
    z = max(1.0, f.zoom)
    crop = (0.0, 0.0, 1.0)
    if z > 1.001:
        cw, ch = W / z, H / z
        cx = min(max(f.zf[0], cw / 2), W - cw / 2); cy = min(max(f.zf[1], ch / 2), H - ch / 2)
        x0, y0 = cx - cw / 2, cy - ch / 2
        img = img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
        crop = (x0, y0, z)
    if f.shake:
        dx, dy = int(math.sin(t * 97) * 14 * f.shake * K), int(math.cos(t * 83) * 10 * f.shake * K)
        img = img.transform((W, H), Image.AFFINE, (1, 0, dx, 0, 1, dy), resample=Image.BILINEAR)

    def tx(x, y):
        return (x - crop[0]) * crop[2], (y - crop[1]) * crop[2]
    draw_ui(img, f, tx)
    return img


def scene_frame(n, t, L, sky, vig):
    f = F()
    SCENES[n](t, f)
    return render(f, t, L, sky, vig)


def build_layers():
    sky = T.build_sky()
    L = {"far": T.build_far(), "mid": T.build_mid(), "ground": T.build_ground(), "fg": T.build_fg()}
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dd = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    vig = (np.clip((dd - 0.6) / 0.8, 0, 1) ** 1.5)[..., None]
    return L, sky, vig


def ffmpeg_writer(out, fps=FPS):
    return subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                             "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)


def render_scene(n, out):
    L, sky, vig = build_layers()
    ff = ffmpeg_writer(out)
    nf = int(round(DURS[n] * FPS))
    for i in range(nf):
        ff.stdin.write(scene_frame(n, i / FPS, L, sky, vig).tobytes())
    ff.stdin.close(); ff.wait()


# ================================================================ shorts (native 9:16 timelapse summaries)
# (scene, from, to, speed) — speed > 1 is the timelapse
SHORTS = {
    1: dict(title="10 hours in 45 seconds", clips=[(1, 0.0, 3.6, 1.0), (4, 9.0, 20.0, 3.0), (5, 3.0, 22.0, 4.0), (6, 0.0, 25.0, 4.0), (8, 0.5, 30.0, 4.5),
                                               (9, 4.0, 34.0, 5.0), (11, 0.0, 28.0, 5.0), (12, 0.5, 14.0, 2.5), (13, 0.0, 22.0, 4.0), (14, 8.0, 15.0, 1.4)],
            caps=["ZOMBIES COME", "AT SUNSET.", "YOU HAVE", "10 HOURS.", "STONE AXE", "LOGS", "A CABIN", "A CRYSTAL", "SPIKES", "A TRENCH",
                  "VINE ROPE…", "PROBABLY FINE.", "SUNSET.", "THEY'RE HERE."],
            end="WHAT WOULD YOU BUILD FIRST?"),
    2: dict(title="Surviving night one", clips=[(14, 7.0, 14.5, 1.6), (15, 2.0, 26.0, 3.5), (16, 3.0, 14.0, 3.0), (17, 0.0, 22.0, 2.4),
                                                 (18, 0.0, 22.0, 2.8), (19, 0.0, 14.0, 2.4), (20, 0.0, 14.0, 1.6), (21, 0.0, 5.0, 1.0)],
            caps=["NIGHT FALLS.", "THEY COME", "ARROWS", "THAT GLOW", "THEN…", "THE BRUTE.", "THE VINE ROPE", "SNAPPED.", "SPEAR OUT", "NO WAY OUT",
                  "ONE BOULDER", "SUNRISE.", "NIGHT 1 SURVIVED"],
            end="WOULD YOUR FORT SURVIVE?"),
}


def short_plan(k):
    sp = SHORTS[k]
    seq = []
    acc = 0.0
    for n, a, b, sp_ in sp["clips"]:
        b = min(b, DURS[n]); d = (b - a) / sp_
        seq.append((acc, acc + d, n, a, sp_)); acc += d
    return seq, acc + 3.0  # +3 s end card


def short_frame(k, ts, L, sky, vig):
    seq, total = short_plan(k)
    sp = SHORTS[k]
    f = F()
    for a, b, n, s0, spd in seq:
        if ts < b or (a, b) == seq[-1][:2]:
            lt = min(s0 + (ts - a) * spd, DURS[n] - 1e-3)
            SCENES[n](lt, f)
            f.badge = f"TIMELAPSE  x{round(spd)}" if spd >= 2 else None
            break
    f.capsz = 96
    f.caps = []; f.title = None; f.rules = []; f.endscreen = None
    f.big = [b_ for b_ in f.big if b_[0] in ("BRUTE", "SNAP!", "BOOM", "STONE AXE", "0:00", "NIGHT 1 SURVIVED")]
    # captions: evenly paced 2–3 word beats across the body of the short
    body = seq[-1][1]
    caps = sp["caps"]
    if ts < body:
        i = min(len(caps) - 1, int(ts / body * len(caps)))
        a = i * body / len(caps)
        f.caps = [(caps[i], ts - a)]
    img = render(f, lt if ts < body else DURS[seq[-1][2]] - 0.01, L, sky, vig)
    if ts >= body:
        d = ImageDraw.Draw(img)
        age = ts - body
        a = ease(age / 0.4)
        ov = Image.new("RGBA", (W, H), (10, 12, 30, int(150 * a)))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB"); d = ImageDraw.Draw(img)
        words = sp["end"].split()
        lines = [" ".join(words[:2]), " ".join(words[2:4]), " ".join(words[4:])]
        for j, ln in enumerate([l for l in lines if l]):
            text_c(d, (0.46 * W, 0.3 * H + j * 120), ln, 104 * pop_scale(age - 0.1 * j), fill=(255, 255, 255) if j < 2 else (110, 255, 110), sw=10)
        if age > 0.8:
            text_c(d, (0.46 * W, 0.3 * H + 3 * 120 + 30), "Full episode on the channel", 44 * pop_scale(age - 0.8), weight="ExtraBold", sw=5)
    return img


def render_short(k, out_video):
    L, sky, vig = build_layers()
    seq, total = short_plan(k)
    ff = ffmpeg_writer(out_video)
    for i in range(int(round(total * FPS))):
        ff.stdin.write(short_frame(k, i / FPS, L, sky, vig).tobytes())
    ff.stdin.close(); ff.wait()


# ================================================================ main
def main():
    cmd = sys.argv[2]
    if cmd == "timeline":
        for n in range(1, 22):
            print(f"{n:02d}  {STARTS[n]:7.2f}  {DURS[n]:6.2f}  {int(STARTS[n] // 60)}:{STARTS[n] % 60:05.2f}")
        print("total", TOTAL, f"{int(TOTAL // 60)}:{TOTAL % 60:05.2f}")
        return
    if cmd == "preview":
        n = int(sys.argv[3])
        L, sky, vig = build_layers()
        outd = os.environ.get("OUTDIR", ".")
        for v in sys.argv[4:]:
            scene_frame(n, float(v), L, sky, vig).save(os.path.join(outd, f"ep_{FMT}_{n:02d}_{float(v):05.2f}.png"))
        return
    if cmd == "mpreview":  # mpreview 3:1.5 8:20 ...  -> one contact sheet
        L, sky, vig = build_layers(); outd = os.environ.get("OUTDIR", ".")
        ims = []
        for spec in sys.argv[3:]:
            n, v = spec.split(":")
            im = scene_frame(int(n), float(v), L, sky, vig)
            ImageDraw.Draw(im).text((20, H - 60), spec, font=font(40), fill=(255, 0, 255))
            ims.append(im.resize((W // 3, H // 3)))
        cols = 4 if FMT == "yt" else 6
        rows = (len(ims) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (W // 3), rows * (H // 3)))
        for i, im in enumerate(ims): sheet.paste(im, ((i % cols) * (W // 3), (i // cols) * (H // 3)))
        sheet.save(os.path.join(outd, os.environ.get("SHEET", "sheet.png")))
        return
    if cmd == "scene":
        render_scene(int(sys.argv[3]), sys.argv[4]); return
    if cmd == "spreview":
        k = int(sys.argv[3]); L, sky, vig = build_layers(); outd = os.environ.get("OUTDIR", ".")
        for v in sys.argv[4:]:
            short_frame(k, float(v), L, sky, vig).save(os.path.join(outd, f"short{k}_{float(v):05.2f}.png"))
        return
    if cmd == "short":
        render_short(int(sys.argv[3]), sys.argv[4]); return
    raise SystemExit("unknown command")


if __name__ == "__main__":
    main()
