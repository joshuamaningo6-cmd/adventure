"""Original test scene in a cinematic-stickman style.
Premise: "What if you could see three seconds into the future?"
Renders frames with PIL and pipes them to ffmpeg.
"""
import math, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DUR = 1280, 720, 30, 12.0
SS = 2                      # supersampling
BW, BH = W * SS, H * SS
GROUND = 560                # ground line (output px)
random.seed(7)

def s(v):  # output px -> supersampled px
    return int(round(v * SS))

# ---------------------------------------------------------------- background
def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))

def build_background():
    sky = Image.new("RGB", (BW, BH))
    px = np.zeros((BH, BW, 3), dtype=np.float32)
    top, mid, hor = np.array([34, 26, 58]), np.array([120, 70, 110]), np.array([246, 160, 110])
    for y in range(BH):
        t = y / (s(GROUND) - s(60))
        t = min(max(t, 0), 1)
        c = top + (mid - top) * min(t * 1.6, 1) if t < 0.62 else mid + (hor - mid) * ((t - 0.62) / 0.38)
        px[y, :, :] = c
    # sun glow near horizon, right of centre
    yy, xx = np.mgrid[0:BH, 0:BW]
    d = np.sqrt((xx - s(900)) ** 2 + ((yy - s(470)) * 1.6) ** 2) / s(420)
    glow = np.clip(1 - d, 0, 1) ** 2
    px += glow[..., None] * np.array([90, 55, 20])
    sky = Image.fromarray(np.clip(px, 0, 255).astype(np.uint8))

    # far skyline (heavily blurred)
    far = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(far)
    x = -s(20)
    while x < BW:
        w = s(random.randint(50, 120)); h = s(random.randint(70, 200))
        d.rectangle([x, s(GROUND) - h, x + w, s(GROUND)], fill=(70, 50, 85, 255))
        x += w + s(random.randint(-10, 6))
    far = far.filter(ImageFilter.GaussianBlur(s(7)))
    sky.paste(far, (0, 0), far)

    # mid buildings with warm windows (medium blur)
    mid_l = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(mid_l)
    for bx, bw_, bh in [(860, 150, 260), (1030, 120, 330), (1160, 160, 220), (640, 110, 170)]:
        d.rectangle([s(bx), s(GROUND - bh), s(bx + bw_), s(GROUND)], fill=(48, 36, 60, 255))
        for wy in range(GROUND - bh + 20, GROUND - 30, 34):
            for wx in range(bx + 14, bx + bw_ - 20, 30):
                if random.random() < 0.35:
                    d.rectangle([s(wx), s(wy), s(wx + 12), s(wy + 16)], fill=(255, 190, 120, 255))
    mid_l = mid_l.filter(ImageFilter.GaussianBlur(s(3.5)))
    sky.paste(mid_l, (0, 0), mid_l)

    # distant blurred figure with a red coat
    fig = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(fig)
    fx, fy = 1010, GROUND - 4
    d.rounded_rectangle([s(fx - 11), s(fy - 70), s(fx + 11), s(fy - 22)], s(8), fill=(200, 60, 50, 255))
    d.line([s(fx - 5), s(fy - 25), s(fx - 6), s(fy)], fill=(15, 12, 20, 255), width=s(6))
    d.line([s(fx + 5), s(fy - 25), s(fx + 6), s(fy)], fill=(15, 12, 20, 255), width=s(6))
    d.ellipse([s(fx - 11), s(fy - 96), s(fx + 11), s(fy - 74)], fill=(15, 12, 20, 255))
    fig = fig.filter(ImageFilter.GaussianBlur(s(2.5)))
    sky.paste(fig, (0, 0), fig)

    # street + sidewalk (sharp foreground)
    d = ImageDraw.Draw(sky)
    d.rectangle([0, s(GROUND), BW, BH], fill=(30, 24, 36))
    d.rectangle([0, s(GROUND), BW, s(GROUND + 8)], fill=(70, 52, 66))
    for kx in range(0, W, 120):
        d.line([s(kx), s(GROUND + 8), s(kx - 60), BH], fill=(38, 30, 44), width=s(3))

    # left building with balcony (sharp, dark)
    d.rectangle([0, 0, s(330), s(GROUND)], fill=(26, 20, 32))
    d.rectangle([s(330), 0, s(345), s(GROUND)], fill=(70, 46, 60))       # warm rim edge
    d.rectangle([s(300), s(178), s(820), s(196)], fill=(22, 17, 28))     # balcony slab
    d.rectangle([s(300), s(174), s(820), s(178)], fill=(120, 80, 80))    # lit top edge
    for rx in range(340, 820, 26):
        d.line([s(rx), s(120), s(rx), s(176)], fill=(22, 17, 28), width=s(4))
    d.line([s(300), s(120), s(820), s(120)], fill=(22, 17, 28), width=s(6))

    # lamp post
    d.rectangle([s(1120), s(250), s(1128), s(GROUND)], fill=(18, 14, 22))
    d.rectangle([s(1100), s(244), s(1150), s(254)], fill=(18, 14, 22))
    return sky.convert("RGBA")

def build_vignette():
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    v = np.clip((d - 0.55) / 0.75, 0, 1) ** 1.6 * 0.65
    return v[..., None]

# ---------------------------------------------------------------- figure
BLACK = (12, 10, 16, 255)
RIM = (255, 196, 140, 255)
SCARF = (40, 196, 180, 255)
SCARF_DARK = (22, 130, 122, 255)

def limb(d, pts, col, w):
    d.line([(s(x), s(y)) for x, y in pts], fill=col, width=s(w), joint="curve")
    for x, y in (pts[0], pts[-1]):
        d.ellipse([s(x - w / 2), s(y - w / 2), s(x + w / 2), s(y + w / 2)], fill=col)

def figure(d, x, phase, walk, look_up=0.0, flinch=0.0, col=BLACK, rim=True, scarf=True, t=0.0):
    gy = GROUND
    bob = abs(math.sin(phase)) * 4 * walk
    hip = (x - flinch * 10, gy - 82 + bob)
    sho = (x - flinch * 16 + 3 * walk, gy - 140 + bob)
    head = (sho[0] + 2 - flinch * 6, sho[1] - 30 + look_up * 2)

    def leg(sign):
        a = math.sin(phase + (0 if sign > 0 else math.pi)) * 0.55 * walk + sign * 0.16 * (1 - walk)
        knee = (hip[0] + math.sin(a) * 42, hip[1] + math.cos(a) * 42)
        b = a - max(0, math.sin(phase + (0 if sign > 0 else math.pi) + 1.2)) * 0.7 * walk
        foot = (knee[0] + math.sin(b) * 42, min(gy, knee[1] + math.cos(b) * 42))
        return [hip, knee, foot]

    def arm(sign):
        a = -math.sin(phase + (0 if sign > 0 else math.pi)) * 0.5 * walk + flinch * 0.9
        el = (sho[0] + math.sin(a) * 32, sho[1] + math.cos(a) * 32)
        hand = (el[0] + math.sin(a + 0.35 + flinch * 0.8) * 30, el[1] + math.cos(a + 0.35 + flinch * 0.8) * 30)
        return [sho, el, hand]

    parts = [(leg(-1), 13), (arm(-1), 11), ([hip, sho], 16), (leg(1), 13), (arm(1), 11)]
    if rim:
        for pts, w in parts:
            limb(d, [(px + 2.2, py - 1.2) for px, py in pts], RIM, w + 1.5)
        d.ellipse([s(head[0] - 21), s(head[1] - 23), s(head[0] + 25), s(head[1] + 21)], fill=RIM)
    for pts, w in parts:
        limb(d, pts, col, w)
    d.ellipse([s(head[0] - 22), s(head[1] - 22), s(head[0] + 22), s(head[1] + 22)], fill=col)
    if col == BLACK:  # eyes: small, look direction changes
        ex, ey = head[0] + 9, head[1] - 2 - look_up * 7
        for dx in (0, 9):
            d.ellipse([s(ex + dx - 2.5), s(ey - 3.2), s(ex + dx + 2.5), s(ey + 3.2)], fill=(245, 240, 235, 255))
    if scarf:
        n = (sho[0], sho[1] - 6)
        d.rounded_rectangle([s(n[0] - 12), s(n[1] - 5), s(n[0] + 12), s(n[1] + 6)], s(5), fill=SCARF)
        flap = math.sin(t * 7) * 5
        tail = [(n[0] - 8, n[1]), (n[0] - 30 - 10 * walk, n[1] + 6 + flap),
                (n[0] - 34 - 10 * walk, n[1] + 14 + flap), (n[0] - 6, n[1] + 8)]
        d.polygon([(s(a), s(b)) for a, b in tail], fill=SCARF_DARK)

# ---------------------------------------------------------------- timeline
POT_X, POT_Y = 760, 162
G = 1500.0
def ease(u): u = min(max(u, 0), 1); return u * u * (3 - 2 * u)

def char_x(t):
    if t < 4.0: return 200 + 80 * t
    if t < 5.6: return 520 + 80 * 0.25 * (t - 4.0)    # slows in "vision" time
    if t < 6.2: return 552 + 40 * ease((t - 5.6) / 0.6) # stops short
    return 592 - 26 * ease((t - 6.3) / 0.35)            # steps back

def walk_amt(t):
    if t < 5.6: return 1.0
    return max(0.0, 1 - (t - 5.6) / 0.6)

def pot_drawing(d, x, y, col=(196, 96, 60, 255), plant=True, rot=0.0):
    pts = [(-16, -14), (16, -14), (11, 16), (-11, 16)]
    c, sn = math.cos(rot), math.sin(rot)
    poly = [(s(x + px * c - py * sn), s(y + px * sn + py * c)) for px, py in pts]
    if plant:
        for a in (-0.5, 0, 0.5):
            ex = x + math.sin(a + rot) * 24; ey = y - 14 - math.cos(a + rot) * 22
            d.line([s(x), s(y - 12), s(ex), s(ey)], fill=(60, 140, 80, col[3]), width=s(5))
    d.polygon(poly, fill=col)

SUBS = [(0.3, 3.8, "Imagine you could see three seconds into the future."),
        (4.1, 6.0, "At first, it just feels like déjà vu."),
        (6.9, 9.5, "Then one day, it saves your life."),
        (9.8, 11.9, "And you start wondering what else is coming.")]
FONT = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 30)

class Shards:
    def __init__(self):
        self.p = []
    def spawn(self, x, y):
        for i in range(16):
            a = random.uniform(math.pi * 1.05, math.pi * 1.95)
            v = random.uniform(150, 420)
            self.p.append([x, y, math.cos(a) * v, math.sin(a) * v, random.uniform(0, 6),
                           random.choice([(196, 96, 60), (150, 70, 45), (70, 50, 40)]), random.uniform(4, 9)])
    def step(self, dt):
        for q in self.p:
            q[2] *= 0.985; q[3] += G * dt
            q[0] += q[2] * dt; q[1] += q[3] * dt; q[4] += q[2] * 0.01
            if q[1] > GROUND + 4: q[1] = GROUND + 4; q[3] *= -0.25; q[2] *= 0.6
    def draw(self, d):
        for x, y, _, _, r, c, sz in self.p:
            pts = [(x + math.cos(r + k * 2.1) * sz, y + math.sin(r + k * 2.1) * sz) for k in range(3)]
            d.polygon([(s(a), s(b)) for a, b in pts], fill=c + (255,))

def render(out_path, only=None):
    bg = build_background()
    vig = build_vignette()
    shards = Shards(); smashed = False
    n = int(DUR * FPS)
    frames = only if only is not None else range(n)
    ff = None
    if only is None:
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
                               "-preset", "veryfast", "-pix_fmt", "yuv420p", out_path], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / FPS
        # physics must advance every frame even when previewing
        fall_t = t - 6.2
        if fall_t > 0 and not smashed:
            py = POT_Y + 0.5 * G * fall_t ** 2
            if py >= GROUND - 16:
                smashed = True; shards.spawn(POT_X, GROUND - 10)
        if smashed: shards.step(1 / FPS)
        if i not in frames: continue

        frame = bg.copy()
        fg = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
        d = ImageDraw.Draw(fg)
        x = char_x(t)
        phase = (t if t < 4.0 else 4.0 + (t - 4.0) * 0.25) * 7.0
        vision = ease((t - 3.9) / 0.3) * (1 - ease((t - 5.5) / 0.3))

        # shadow
        d.ellipse([s(x - 50), s(GROUND - 4), s(x + 22), s(GROUND + 8)], fill=(0, 0, 0, 110))
        # pot on balcony / falling
        if fall_t <= 0:
            pot_drawing(d, POT_X, POT_Y)
        elif not smashed:
            pot_drawing(d, POT_X, POT_Y + 0.5 * G * fall_t ** 2, rot=fall_t * 3.0)
        if smashed:
            d.chord([s(POT_X - 26), s(GROUND - 9), s(POT_X + 26), s(GROUND + 9)], 180, 360, fill=(52, 38, 34, 255))
            for k, a in enumerate((-0.9, -0.2, 0.6)):
                d.line([s(POT_X - 8 + k * 9), s(GROUND - 4), s(POT_X - 8 + k * 9 + math.sin(a) * 18), s(GROUND - 4 - math.cos(a) * 9)],
                       fill=(60, 140, 80, 255), width=s(4))
        shards.draw(d)
        look = ease((t - 6.6) / 0.4)
        flinch = ease((t - 6.3) / 0.25) * (1 - ease((t - 7.6) / 0.8))
        figure(d, x, phase, walk_amt(t), look_up=look, flinch=flinch, t=t)

        # vision: ghost of the future (pot falls on where you'd be)
        if vision > 0.01:
            gl = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
            gd = ImageDraw.Draw(gl)
            gt = ease((t - 4.0) / 1.4)                     # ghost timeline 0..1
            gx = 520 + 240 * gt
            figure(gd, gx, 4.0 * 7 + gt * 20, 1.0, col=(140, 230, 255, 255), rim=False, scarf=False)
            gpy = POT_Y + (GROUND - 16 - POT_Y) * min(1, gt * 1.25) ** 2
            pot_drawing(gd, POT_X, gpy, col=(140, 230, 255, 255), plant=False, rot=gt * 3)
            a = np.array(gl); a[..., 3] = (a[..., 3] * 0.45 * vision).astype(np.uint8)
            fg.alpha_composite(Image.fromarray(a))
        frame.alpha_composite(fg)

        # camera: slow push-in toward the character
        z = 1.0 + 0.08 * (t / DUR)
        shake = max(0.0, 1 - (t - 6.62) / 0.3) if t > 6.62 else 0.0
        cx = s(min(max(x, 420), 860) + math.sin(t * 90) * 5 * shake); cy = s(400 + math.cos(t * 77) * 4 * shake)
        cw, ch = BW / z, BH / z
        l = min(max(cx - cw / 2, 0), BW - cw); tp = min(max(cy - ch / 2, 0), BH - ch)
        img = frame.crop((int(l), int(tp), int(l + cw), int(tp + ch))).resize((W, H), Image.LANCZOS).convert("RGB")

        arr = np.asarray(img).astype(np.float32)
        if vision > 0.01:  # desaturate + cool tint during the vision
            g = arr.mean(axis=2, keepdims=True)
            cool = g * np.array([0.75, 0.95, 1.15])
            arr = arr * (1 - 0.7 * vision) + cool * 0.7 * vision
        arr = arr * (1 - vig)
        arr += np.random.normal(0, 3.0, arr.shape)  # light grain
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

        d2 = ImageDraw.Draw(img)
        d2.rectangle([0, 0, W, 34], fill=(0, 0, 0)); d2.rectangle([0, H - 34, W, H], fill=(0, 0, 0))
        for a, b, txt in SUBS:
            if a <= t <= b:
                op = min(1, (t - a) / 0.2, (b - t) / 0.2)
                tw = d2.textlength(txt, font=FONT)
                c = int(255 * op)
                d2.text(((W - tw) / 2 + 2, H - 92 + 2), txt, font=FONT, fill=(0, 0, 0))
                d2.text(((W - tw) / 2, H - 92), txt, font=FONT, fill=(c, c, c))
        if ff:
            ff.stdin.write(img.tobytes())
        else:
            img.save(f"{out_path}_{i:03d}.png")
    if ff:
        ff.stdin.close(); sys.exit(ff.wait())

if __name__ == "__main__":
    if sys.argv[1] == "preview":
        render("preview", only=[int(float(v) * FPS) for v in sys.argv[2:]])
    else:
        render(sys.argv[1])
