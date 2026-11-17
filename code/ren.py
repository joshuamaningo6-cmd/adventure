"""REN ASHGRAVE — original edgy isekai protagonist. Character rig + design sheet.

draw_ren(d, glow, x, gy, sc, pose, t) draws him facing right with feet at (x, gy) in supersampled
pixel space. `glow` is a second ImageDraw whose shapes get blurred into a crimson glow.
pose: 'idle' (sword on back) or 'battle' (sword drawn, low stance).
"""
import math, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = (14, 17, 26, 255)          # outline
SKIN, SKIN_SH = (246, 224, 212, 255), (222, 186, 176, 255)
HAIR, HAIR_SH, HAIR_HI = (220, 226, 236, 255), (150, 160, 182, 255), (255, 255, 255, 255)
CRIMSON, CRIMSON_D, CRIMSON_G = (196, 30, 48, 255), (122, 14, 32, 255), (255, 60, 70, 255)
CHAR, CHAR_SH = (48, 51, 62, 255), (32, 34, 43, 255)
NAVY, NAVY_SH = (34, 44, 74, 255), (24, 30, 52, 255)
SILVER, SILVER_SH = (190, 198, 212, 255), (128, 138, 158, 255)
TROUSER = (38, 41, 52, 255)
BANDAGE, BANDAGE_SH = (226, 214, 196, 255), (186, 170, 150, 255)
GUN, GUN_HI = (64, 70, 84, 255), (120, 128, 146, 255)

def P(x, y, a, L):
    return (x + math.sin(a) * L, y + math.cos(a) * L)

def seg(d, a, b, col, w, o=4):
    for c, ww in ((OUT, w + o), (col, w)):
        d.line([a, b], fill=c, width=int(ww))
        for p in (a, b):
            r = ww / 2; d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=c)

def limb(d, a, b, w1, w2, col, o=4):
    ang = math.atan2(b[1] - a[1], b[0] - a[0]) + math.pi / 2
    for c, extra in ((OUT, o), (col, 0)):
        r1, r2 = (w1 + extra) / 2, (w2 + extra) / 2
        q = [(a[0] + math.cos(ang) * r1, a[1] + math.sin(ang) * r1), (b[0] + math.cos(ang) * r2, b[1] + math.sin(ang) * r2),
             (b[0] - math.cos(ang) * r2, b[1] - math.sin(ang) * r2), (a[0] - math.cos(ang) * r1, a[1] - math.sin(ang) * r1)]
        d.polygon(q, fill=c)
        d.ellipse([a[0] - r1, a[1] - r1, a[0] + r1, a[1] + r1], fill=c)
        d.ellipse([b[0] - r2, b[1] - r2, b[0] + r2, b[1] + r2], fill=c)

def poly(d, pts, col, o=0):
    if o:
        cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
        big = []
        for x, y in pts:
            dx, dy = x - cx, y - cy; L = math.hypot(dx, dy) or 1
            big.append((x + dx / L * o, y + dy / L * o))
        d.polygon(big, fill=OUT)
    d.polygon(pts, fill=col)

POSES = {
    'idle':   dict(hip=(0, -150), sho=(4, -252), lf=(0.05, -0.03), lb=(-0.12, -0.06),
                   af=(0.06, 0.22), ab=(-0.14, 0.0), tilt=0.12, wind=0.35),
    'battle': dict(hip=(-4, -120), sho=(24, -214), lf=(0.95, -0.10), lb=(-0.85, -0.45),
                   af=(0.85, 1.35), ab=(-0.45, 0.35), tilt=-0.02, wind=1.0),
}

def draw_ren(d, g, x, gy, sc, pose='idle', t=0.0):
    p = POSES[pose]
    k = sc
    X = lambda v: x + v * k
    Y = lambda v: gy + v * k
    hip = (X(p['hip'][0]), Y(p['hip'][1])); sho = (X(p['sho'][0]), Y(p['sho'][1]))
    O = 3.0 * k
    battle = pose == 'battle'

    def leg(a1, a2):
        knee = P(*hip, a1, 72 * k); foot = P(*knee, a2, 72 * k)
        return knee, (foot[0], min(foot[1], Y(-7)))

    def arm(a1, a2):
        el = P(*sho, a1, 48 * k); hand = P(*el, a2, 45 * k)
        return el, hand

    # ---------------- half-cape (behind)
    wind = p['wind']
    top_back = (sho[0] - 14 * k, sho[1] - 2 * k)
    edge = []
    for i in range(10):
        u = i / 9
        ex = top_back[0] - (16 + u * (40 + 120 * wind)) * k
        ey = top_back[1] + (30 + u * (150 - 95 * wind)) * k + math.sin(u * 7 + t * 4) * 8 * k * u
        edge.append((ex, ey))
    cape = [top_back, (sho[0] + 2 * k, sho[1] + 8 * k), (hip[0] - 4 * k, hip[1] + 24 * k)] + edge[::-1]
    poly(d, cape, CHAR, O)
    inner = [(hip[0] - 6 * k, hip[1] + 18 * k)] + [(ex + 3 * k, ey - 4 * k) for ex, ey in edge[::-1][:4]] + [(edge[-5][0] + 10 * k, edge[-5][1] - 14 * k)]
    d.polygon(inner, fill=CRIMSON_D)
    for i in range(2, 10):
        ex, ey = edge[i]
        d.polygon([(ex - 5 * k, ey - 2 * k), (ex + 5 * k, ey - 2 * k), (ex - 1 * k, ey + 9 * k)], fill=CHAR)

    # ---------------- sheathed sword on back (idle)
    if not battle:
        mouth = (sho[0] + 10 * k, sho[1] - 22 * k)
        a = -0.62
        end = P(*mouth, a, 175 * k)
        limb(d, mouth, end, 11 * k, 8 * k, CHAR_SH, O)
        for u in (0.02, 0.5, 0.97):
            q = (mouth[0] + (end[0] - mouth[0]) * u, mouth[1] + (end[1] - mouth[1]) * u)
            limb(d, P(*q, a + 1.57, 6 * k), P(*q, a - 1.57, 6 * k), 5 * k, 5 * k, SILVER, 2 * k)
        guard = P(*mouth, a + math.pi, 4 * k)
        hilt_end = P(*guard, a + math.pi, 44 * k)
        limb(d, guard, hilt_end, 8 * k, 7 * k, CRIMSON_D, O)
        for j in range(5):
            q = P(*guard, a + math.pi, (7 + j * 8) * k)
            d.line([P(*q, a + 1.57, 3.5 * k), P(*q, a - 1.57, 3.5 * k)], fill=CRIMSON, width=max(1, int(2 * k)))
        gl = [P(*guard, a + 1.57, 13 * k), P(*guard, a + 0.5, 7 * k), P(*guard, a - 1.57, 13 * k), P(*guard, a + math.pi - 0.5, 5 * k)]
        poly(d, gl, SILVER, O * 0.7)
        q = hilt_end
        for j in range(6):
            q = (q[0] - 4.5 * k, q[1] + (3 + j * 0.8) * k)
            d.ellipse([q[0] - 3 * k, q[1] - 2 * k, q[0] + 3 * k, q[1] + 2 * k], outline=SILVER, width=max(1, int(1.4 * k)))

    # ---------------- back limbs
    kb, fb = leg(*p['lb']); eb, hb = arm(*p['ab'])
    limb(d, hip, kb, 20 * k, 14 * k, (30, 32, 42, 255), O); limb(d, kb, fb, 14 * k, 10 * k, (30, 32, 42, 255), O)
    boot(d, kb, fb, k, O, back=True)
    limb(d, sho, eb, 14 * k, 11 * k, CHAR_SH, O); limb(d, eb, hb, 11 * k, 9 * k, CHAR_SH, O)
    hand(d, hb, k, O)
    if battle:
        g.ellipse([hb[0] - 18 * k, hb[1] - 18 * k, hb[0] + 18 * k, hb[1] + 18 * k], fill=(255, 40, 60, 200))
        for j in range(5):
            a = j * 1.25 + t
            d.line([P(*hb, a, 10 * k), P(*hb, a + 0.3, 20 * k)], fill=CRIMSON_G, width=max(1, int(1.6 * k)))

    # ---------------- coat tails
    lean = (sho[0] - hip[0]) / k
    tails = [(hip[0] - 20 * k, hip[1] - 10 * k), (hip[0] + 19 * k, hip[1] - 10 * k),
             (hip[0] + (21 + lean * 0.15) * k, hip[1] + 44 * k), (hip[0] + 6 * k, hip[1] + 34 * k),
             (hip[0] - 6 * k, hip[1] + 56 * k), (hip[0] - (26 + 22 * wind) * k, hip[1] + (50 - 12 * wind) * k)]
    poly(d, tails, CHAR, O)
    d.line([tails[2], tails[3], tails[4], tails[5]], fill=CRIMSON, width=int(2.5 * k))

    # ---------------- torso (fitted jacket, broad shoulders → narrow waist)
    body = [(hip[0] - 17 * k, hip[1]), (hip[0] + 17 * k, hip[1]), (sho[0] + 20 * k, sho[1] + 10 * k),
            (sho[0] + 14 * k, sho[1] - 2 * k), (sho[0] - 20 * k, sho[1] - 2 * k), (sho[0] - 24 * k, sho[1] + 14 * k)]
    poly(d, body, NAVY, O)
    d.polygon([body[0], (hip[0] - 4 * k, hip[1]), (sho[0] - 8 * k, sho[1]), body[4], body[5]], fill=NAVY_SH)
    # zip line + chest strap
    d.line([(sho[0] + 12 * k, sho[1] + 2 * k), (hip[0] + 12 * k, hip[1] - 8 * k)], fill=NAVY_SH, width=max(1, int(2 * k)))
    a0, a1_ = (sho[0] + 16 * k, sho[1] + 6 * k), (hip[0] - 14 * k, hip[1] - 6 * k)
    d.line([a0, a1_], fill=OUT, width=int(8 * k)); d.line([a0, a1_], fill=SILVER_SH, width=int(5 * k))
    mid = (a0[0] * 0.55 + a1_[0] * 0.45, a0[1] * 0.55 + a1_[1] * 0.45)
    d.rectangle([mid[0] - 5 * k, mid[1] - 5 * k, mid[0] + 5 * k, mid[1] + 5 * k], fill=OUT)
    d.rectangle([mid[0] - 3.5 * k, mid[1] - 3.5 * k, mid[0] + 3.5 * k, mid[1] + 3.5 * k], fill=SILVER)
    d.rectangle([hip[0] - 18 * k, hip[1] - 9 * k, hip[0] + 18 * k, hip[1] + 1 * k], fill=OUT)
    d.rectangle([hip[0] - 16 * k, hip[1] - 7 * k, hip[0] + 16 * k, hip[1] - 1 * k], fill=(26, 26, 32, 255))
    d.rectangle([hip[0] + 4 * k, hip[1] - 9 * k, hip[0] + 12 * k, hip[1] + 1 * k], fill=SILVER)
    for j in range(7):
        u = j / 6
        q = (hip[0] + (10 - 24 * u) * k, hip[1] + (4 + math.sin(u * math.pi) * 16) * k)
        d.ellipse([q[0] - 2.6 * k, q[1] - 1.8 * k, q[0] + 2.6 * k, q[1] + 1.8 * k], outline=SILVER, width=max(1, int(1.3 * k)))

    # ---------------- front leg
    kf, ff = leg(*p['lf'])
    limb(d, hip, kf, 21 * k, 15 * k, TROUSER, O); limb(d, kf, ff, 15 * k, 11 * k, TROUSER, O)
    boot(d, kf, ff, k, O)

    # ---------------- head & collar
    head(d, g, sho, k, O, p['tilt'], t)

    # ---------------- front arm (bandaged forearm with runes)
    ef, hf = arm(*p['af'])
    limb(d, sho, ef, 16 * k, 12 * k, CHAR, O)
    d.line([P(*sho, 3.14, 2 * k), P(*sho, 0.6, 12 * k)], fill=CHAR_SH, width=max(1, int(2 * k)))
    limb(d, ef, hf, 11.5 * k, 9 * k, BANDAGE, O)
    aa = math.atan2(hf[0] - ef[0], hf[1] - ef[1])
    for j in range(6):
        u = 0.1 + j * 0.15
        q = (ef[0] + (hf[0] - ef[0]) * u, ef[1] + (hf[1] - ef[1]) * u)
        d.line([P(*q, aa + 1.1, 6 * k), P(*q, aa + 1.1 + math.pi, 6 * k)], fill=BANDAGE_SH, width=max(1, int(1.4 * k)))
    for j in range(3):
        u = 0.22 + j * 0.25
        q = (ef[0] + (hf[0] - ef[0]) * u, ef[1] + (hf[1] - ef[1]) * u)
        rune = [P(*q, aa + 2.4, 3.5 * k), P(*q, aa + 1.57, 0.5 * k), P(*q, aa + 0.6, 3.5 * k)]
        d.line(rune, fill=CRIMSON_G, width=max(1, int(1.7 * k)))
        g.line(rune, fill=(255, 40, 60, 160), width=int(4 * k))
    limb(d, P(*ef, aa + 1.57, 7 * k), P(*ef, aa - 1.57, 7 * k), 4 * k, 4 * k, CRIMSON, 2 * k)

    # ---------------- drawn sword (battle)
    if battle:
        a = 1.30
        guard = P(*hf, a, 10 * k)
        hilt_end = P(*hf, a + math.pi, 26 * k)
        limb(d, guard, hilt_end, 8 * k, 7 * k, CRIMSON_D, O)
        tip = P(*guard, a, 168 * k)
        mid_ = P(*guard, a - 0.05, 95 * k)
        nrm = a - 1.57
        blade = [P(*guard, a + 1.57, 5 * k), P(*mid_, a + 1.57, 4 * k), tip, P(*mid_, nrm, 8 * k), P(*guard, nrm, 6 * k)]
        poly(d, blade, GUN, O * 0.7)
        edge = [P(*guard, nrm, 5 * k), P(*mid_, nrm, 7 * k), tip]
        d.line(edge, fill=CRIMSON_G, width=max(1, int(2.4 * k)))
        g.line(edge, fill=(255, 40, 60, 220), width=int(8 * k))
        d.line([P(*guard, a + 1.0, 2 * k), P(*mid_, a + 1.2, 1 * k)], fill=GUN_HI, width=max(1, int(1.4 * k)))
        gl = [P(*guard, a + 1.57, 14 * k), P(*guard, a + 0.5, 7 * k), P(*guard, nrm, 14 * k), P(*guard, a + math.pi - 0.5, 5 * k)]
        poly(d, gl, SILVER, O * 0.7)
        q = hilt_end
        for j in range(7):
            q = (q[0] - 3.5 * k, q[1] + (4 + j * 0.6) * k)
            d.ellipse([q[0] - 2.8 * k, q[1] - 1.8 * k, q[0] + 2.8 * k, q[1] + 1.8 * k], outline=SILVER, width=max(1, int(1.4 * k)))
    hand(d, hf, k, O)

def boot(d, knee, foot, k, O, back=False):
    col = (26, 27, 34, 255) if back else (36, 38, 48, 255)
    sole = [(foot[0] - 8 * k, foot[1] - 12 * k), (foot[0] + 20 * k, foot[1] - 5 * k), (foot[0] + 22 * k, foot[1] + 5 * k), (foot[0] - 10 * k, foot[1] + 5 * k)]
    poly(d, sole, col, O)
    a = math.atan2(foot[0] - knee[0], foot[1] - knee[1])
    # small knee guard + slim shin plate
    kg = [P(*knee, a + 1.57, 8 * k), P(*knee, a, -7 * k), P(*knee, a - 1.57, 8 * k), P(*knee, a, 8 * k)]
    poly(d, kg, SILVER_SH if back else SILVER, O * 0.6)
    s0 = P(*knee, a, 26 * k); s1 = P(*foot, a, -8 * k)
    limb(d, P(*s0, a - 1.57, 3 * k), P(*s1, a - 1.57, 3 * k), 5 * k, 6 * k, SILVER_SH if back else SILVER, 2 * k)

def hand(d, h, k, O):
    d.ellipse([h[0] - 7.5 * k - O / 2, h[1] - 7.5 * k - O / 2, h[0] + 7.5 * k + O / 2, h[1] + 7.5 * k + O / 2], fill=OUT)
    d.ellipse([h[0] - 7.5 * k, h[1] - 7.5 * k, h[0] + 7.5 * k, h[1] + 7.5 * k], fill=(34, 36, 46, 255))
    d.ellipse([h[0] + 1 * k, h[1] - 1 * k, h[0] + 6.5 * k, h[1] + 5.5 * k], fill=SKIN)

def head(d, g, sho, k, O, tilt, t):
    # collar back
    poly(d, [(sho[0] - 20 * k, sho[1] + 6 * k), (sho[0] - 20 * k, sho[1] - 30 * k), (sho[0] + 2 * k, sho[1] - 36 * k),
             (sho[0] + 12 * k, sho[1] - 4 * k), (sho[0] + 14 * k, sho[1] + 8 * k)], CHAR, O)
    hx, hy = sho[0] + 9 * k, sho[1] - 46 * k + tilt * 6 * k
    R = 23 * k
    def ang_pt(deg, rr):
        return (hx + math.cos(math.radians(deg)) * rr, hy + math.sin(math.radians(deg)) * rr)
    # ---- back spikes (behind head), shaded silver
    spikes = [(150, 1.75, 30), (175, 1.95, 32), (200, 1.85, 30), (225, 1.7, 28), (250, 1.55, 26), (130, 1.5, 26)]
    for deg, ln, w in spikes:
        b1, b2 = ang_pt(deg - w, R * 0.7), ang_pt(deg + w, R * 0.7)
        tip = ang_pt(deg + 8, R * ln)
        poly(d, [b1, tip, b2], HAIR_SH, O)
    for deg, ln, w in spikes:
        b1, b2 = ang_pt(deg - w * 0.7, R * 0.7), ang_pt(deg + w * 0.4, R * 0.7)
        tip = ang_pt(deg + 6, R * ln * 0.92)
        d.polygon([b1, tip, b2], fill=HAIR)
    # ---- face: skull + sharp jaw
    d.ellipse([hx - R - O, hy - R - O, hx + R + O, hy + R + O], fill=OUT)
    jaw = [(hx - R * 0.45, hy + R * 0.55), (hx + R * 0.30, hy + R * 1.12), (hx + R * 0.72, hy + R * 0.98), (hx + R * 1.02, hy + R * 0.25), (hx, hy - R * 0.2)]
    poly(d, jaw, SKIN, O)
    d.ellipse([hx - R, hy - R, hx + R, hy + R], fill=SKIN)
    d.polygon(jaw, fill=SKIN)
    d.polygon([(hx - R * 0.45, hy + R * 0.55), (hx + R * 0.25, hy + R * 1.02), (hx + R * 0.15, hy + R * 0.55), (hx - R * 0.2, hy + R * 0.2)], fill=SKIN_SH)
    # ---- eye (large, sharp, crimson)
    ex, ey = hx + R * 0.56, hy + R * 0.14
    s_ = k
    white = [(ex - 10 * s_, ey + 1 * s_), (ex - 4 * s_, ey - 6 * s_), (ex + 8 * s_, ey - 5.5 * s_), (ex + 8.5 * s_, ey + 3 * s_), (ex - 4 * s_, ey + 5.5 * s_)]
    d.polygon(white, fill=(255, 250, 248, 255))
    d.ellipse([ex - 4.5 * s_, ey - 6 * s_, ex + 5.5 * s_, ey + 6 * s_], fill=CRIMSON)
    d.ellipse([ex - 3 * s_, ey + 0.5 * s_, ex + 4 * s_, ey + 6 * s_], fill=(255, 70, 80, 255))
    d.polygon([(ex + 0.4 * s_, ey - 4.5 * s_), (ex + 1.6 * s_, ey), (ex + 0.4 * s_, ey + 4.5 * s_), (ex - 0.8 * s_, ey)], fill=(30, 0, 6, 255))  # slit pupil
    d.ellipse([ex + 2 * s_, ey - 4.5 * s_, ex + 4.5 * s_, ey - 2 * s_], fill=(255, 255, 255, 255))
    g.ellipse([ex - 8 * s_, ey - 8 * s_, ex + 9 * s_, ey + 8 * s_], fill=(255, 40, 60, 150))
    d.line([white[0], white[1], white[2], (ex + 11 * s_, ey - 7 * s_)], fill=OUT, width=max(1, int(2.8 * s_)))
    d.line([white[3], white[4]], fill=OUT, width=max(1, int(1.2 * s_)))
    d.line([(hx + R * 0.66, hy + R * 0.78), (hx + R * 0.86, hy + R * 0.74)], fill=OUT, width=max(1, int(1.5 * s_)))  # mouth
    # earring
    ex2, ey2 = hx - R * 0.02, hy + R * 0.42
    d.line([(ex2, ey2), (ex2, ey2 + 7 * s_)], fill=SILVER, width=max(1, int(1.2 * s_)))
    d.polygon([(ex2, ey2 + 6 * s_), (ex2 + 3 * s_, ey2 + 10 * s_), (ex2, ey2 + 14 * s_), (ex2 - 3 * s_, ey2 + 10 * s_)], fill=CRIMSON_G)
    g.ellipse([ex2 - 3 * s_, ey2 + 7 * s_, ex2 + 3 * s_, ey2 + 13 * s_], fill=(255, 40, 60, 110))
    # ---- hair cap: covers back + top, jagged fringe line across forehead
    cap = [ang_pt(deg, R * 1.06) for deg in range(125, 322, 12)]
    fringe = [(hx + R * 0.92, hy - R * 0.42), (hx + R * 0.80, hy - R * 0.16), (hx + R * 0.64, hy - R * 0.40), (hx + R * 0.46, hy - R * 0.12),
              (hx + R * 0.28, hy - R * 0.38), (hx + R * 0.10, hy - R * 0.02), (hx - R * 0.12, hy - R * 0.05), (hx - R * 0.42, hy + R * 0.62)]
    poly(d, cap + fringe, HAIR, O * 0.5)
    d.polygon(cap + fringe, fill=HAIR)
    # shading band + highlight
    d.polygon([ang_pt(deg, R * 0.98) for deg in range(130, 215, 10)] + [(hx - R * 0.25, hy - R * 0.1)], fill=HAIR_SH)
    d.arc([hx - R * 0.75, hy - R * 0.95, hx + R * 0.45, hy - R * 0.2], 205, 300, fill=HAIR_HI, width=max(1, int(2.4 * s_)))
    # long front locks falling past the eye (one crimson streak)
    locks = [((0.78, -0.45), (0.92, 0.42), 2.6, HAIR), ((0.02, -0.30), (0.08, 0.70), 4.0, CRIMSON), ((0.92, -0.35), (1.10, 0.12), 2.6, HAIR)]
    for (sx_, sy_), (tx_, ty_), w, c in locks:
        root = (hx + R * sx_, hy + R * sy_); tip = (hx + R * tx_, hy + R * ty_)
        nx, ny = -(tip[1] - root[1]), tip[0] - root[0]; L = math.hypot(nx, ny); nx, ny = nx / L * w * s_, ny / L * w * s_
        tri = [(root[0] - nx, root[1] - ny), tip, (root[0] + nx, root[1] + ny)]
        poly(d, tri, OUT, 1.6 * s_)
        d.polygon(tri, fill=c)
    d.line([(ex - 9 * s_, ey - 11 * s_), (ex + 9 * s_, ey - 7 * s_)], fill=OUT, width=max(1, int(2.6 * s_)))  # angled brow
    # top spikes (front)
    for deg, ln, w, c in [(275, 1.45, 18, HAIR), (300, 1.35, 16, HAIR), (250, 1.5, 18, HAIR)]:
        b1, b2 = ang_pt(deg - w, R * 0.85), ang_pt(deg + w, R * 0.85)
        tip = ang_pt(deg - 10, R * ln)
        poly(d, [b1, tip, b2], c, O * 0.6)
    # collar front flap with crimson lining (over the neck)
    flap = [(sho[0] + 2 * k, sho[1] - 36 * k), (sho[0] + 15 * k, sho[1] - 24 * k), (sho[0] + 15 * k, sho[1] + 8 * k), (sho[0] + 4 * k, sho[1] - 4 * k)]
    poly(d, flap, CHAR, O * 0.6)
    d.line([flap[0], flap[3]], fill=CRIMSON, width=max(1, int(3 * k)))

# =========================================================================== sheet
def glow_composite(base, glow_img, radius, strength=1.0):
    gb = glow_img.filter(ImageFilter.GaussianBlur(radius))
    a = np.asarray(base).astype(np.float32); g = np.asarray(gb).astype(np.float32)
    add = g[..., :3] * (g[..., 3:4] / 255.0) * strength
    a[..., :3] = np.clip(a[..., :3] + add, 0, 255)
    return Image.fromarray(a.astype(np.uint8))

def sheet(out):
    SS = 2
    W, H = 1920, 1080
    BW, BH = W * SS, H * SS
    yy, xx = np.mgrid[0:BH, 0:BW].astype(np.float32)
    top, bot = np.array([18, 22, 36]), np.array([34, 18, 30])
    bg = top + (bot - top) * (yy / BH)[..., None]
    for cx, cy, r, c in ((700, 640, 900, (90, 10, 24)), (300, 900, 700, (40, 30, 80))):
        d_ = np.sqrt((xx - cx * SS) ** 2 + (yy - cy * SS) ** 2) / (r * SS)
        bg += (np.clip(1 - d_, 0, 1) ** 2)[..., None] * np.array(c)
    base = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(base)
    lines = Image.new("RGBA", (BW, BH), (0, 0, 0, 0)); ld = ImageDraw.Draw(lines)
    for i in range(-40, 80):  # faint diagonal speed lines
        x0 = i * 60 * SS
        ld.line([(x0, 0), (x0 - BH * 0.6, BH)], fill=(255, 255, 255, 10), width=SS)
    base.alpha_composite(lines); d = ImageDraw.Draw(base)
    # ground ring under poses
    for gx in (300, 700):
        d.ellipse([(gx - 150) * SS, 955 * SS, (gx + 150) * SS, 990 * SS], outline=(196, 30, 48, 120), width=2 * SS)
        d.ellipse([(gx - 110) * SS, 962 * SS, (gx + 110) * SS, 983 * SS], fill=(0, 0, 0, 90))
    glow = Image.new("RGBA", (BW, BH), (0, 0, 0, 0)); g = ImageDraw.Draw(glow)
    # embers
    r_ = random.Random(2)
    for i in range(70):
        ex, ey, er = r_.uniform(60, 1080), r_.uniform(80, 1040), r_.uniform(1.5, 4)
        g.ellipse([(ex - er) * SS, (ey - er) * SS, (ex + er) * SS, (ey + er) * SS], fill=(255, 80, 60, 255))
        d.ellipse([(ex - er * 0.5) * SS, (ey - er * 0.5) * SS, (ex + er * 0.5) * SS, (ey + er * 0.5) * SS], fill=(255, 190, 150, 255))

    char = Image.new("RGBA", (BW, BH), (0, 0, 0, 0)); cd = ImageDraw.Draw(char)
    draw_ren(cd, g, 300 * SS, 972 * SS, 1.95 * SS, 'idle', t=0.3)
    draw_ren(cd, g, 660 * SS, 972 * SS, 1.95 * SS, 'battle', t=1.2)
    base.alpha_composite(char)
    base = glow_composite(base, glow, 10 * SS, 1.3)

    # ---------------- close-up portrait (rendered big, cropped)
    big = Image.new("RGBA", (1600, 1200), (0, 0, 0, 0)); bd = ImageDraw.Draw(big)
    bglow = Image.new("RGBA", (1600, 1200), (0, 0, 0, 0)); bg_ = ImageDraw.Draw(bglow)
    draw_ren(bd, bg_, 700, 3700, 11, 'idle', t=0.3)
    face_bg = Image.new("RGBA", (1600, 1200), (34, 24, 44, 255))
    face_bg.alpha_composite(big)
    face_bg = glow_composite(face_bg, bglow, 22, 1.2)
    # head centre sits at x≈560+13*11, y≈3200-294*11
    hx, hy = 700 + 13 * 11, int(3700 - (252 + 46 - 0.72) * 11)
    crop = face_bg.crop((hx - 300, hy - 340, hx + 440, hy + 400)).resize((640, 640), Image.LANCZOS)
    mask = Image.new("L", (640, 640), 0); ImageDraw.Draw(mask).ellipse([0, 0, 639, 639], fill=255)
    portrait = Image.new("RGBA", (640, 640), (0, 0, 0, 0)); portrait.paste(crop, (0, 0), mask)
    px0, py0 = 1250 * SS, 610 * SS
    pd = ImageDraw.Draw(base)
    base.alpha_composite(portrait.resize((330 * SS, 330 * SS), Image.LANCZOS), (px0, py0))
    pd.ellipse([px0, py0, px0 + 330 * SS, py0 + 330 * SS], outline=(196, 30, 48, 255), width=3 * SS)

    # ---------------- status window panel
    F = lambda w, s: ImageFont.truetype(f"/usr/share/fonts/opentype/inter/Inter-{w}.otf", s * SS)
    ui = Image.new("RGBA", (BW, BH), (0, 0, 0, 0)); u = ImageDraw.Draw(ui)
    x0, y0, x1, y1 = 1130 * SS, 70 * SS, 1860 * SS, 585 * SS
    u.rounded_rectangle([x0, y0, x1, y1], 14 * SS, fill=(16, 22, 44, 215), outline=(196, 30, 48, 255), width=2 * SS)
    u.rectangle([x0 + 2 * SS, y0 + 2 * SS, x1 - 2 * SS, y0 + 46 * SS], fill=(120, 14, 32, 200))
    u.text((x0 + 22 * SS, y0 + 10 * SS), "◆ STATUS", font=F("Bold", 22), fill=(255, 235, 235, 255))
    u.text((x1 - 190 * SS, y0 + 12 * SS), "Lv. 1  →  ???", font=F("Medium", 18), fill=(255, 200, 200, 255))
    rows = [("NAME", "REN ASHGRAVE"), ("TITLE", "The Rift-Marked"), ("CLASS", "Cursed Blade Wanderer"),
            ("WEAPON", "Vesperfang — a chained crimson-edged odachi"), ("ORIGIN", "Summoned mid-raid at 3 a.m. Never logged out.")]
    yy_ = y0 + 66 * SS
    for kk, vv in rows:
        u.text((x0 + 24 * SS, yy_), kk, font=F("Bold", 15), fill=(196, 140, 150, 255))
        u.text((x0 + 150 * SS, yy_ - 3 * SS), vv, font=F("SemiBold", 21), fill=(240, 242, 250, 255))
        yy_ += 38 * SS
    u.line([x0 + 20 * SS, yy_ + 2 * SS, x1 - 20 * SS, yy_ + 2 * SS], fill=(196, 30, 48, 160), width=SS)
    yy_ += 16 * SS
    skills = [("[Riftbreaker]", "Cuts through space itself — distance means nothing."),
              ("[Ashen Eye]", "Sees one second ahead of any enemy he has bled."),
              ("[Crimson Pact]", "Grows stronger each time he refuses to give up."),
              ("[Cursed Arm]", "The runes spread every time he uses it. He hides it."),
              ("WEAKNESS", "Acts cold, but can't walk past anyone who needs help.")]
    for sk, desc in skills:
        u.text((x0 + 24 * SS, yy_), sk, font=F("Bold", 18), fill=(255, 90, 100, 255))
        u.text((x0 + 200 * SS, yy_ + 1 * SS), desc, font=F("Regular", 16), fill=(214, 220, 236, 255))
        yy_ += 34 * SS
    # palette
    pal = [("Ash Silver", HAIR), ("Rift Crimson", CRIMSON), ("Charcoal", CHAR), ("Midnight Navy", NAVY), ("Gunmetal", GUN), ("Bandage", BANDAGE)]
    for i, (nm, c) in enumerate(pal):
        cx = 1640 * SS + (i % 2) * 120 * SS; cy = 640 * SS + (i // 2) * 92 * SS
        u.rounded_rectangle([cx, cy, cx + 54 * SS, cy + 54 * SS], 10 * SS, fill=c, outline=(255, 255, 255, 120), width=SS)
        u.text((cx - 4 * SS, cy + 60 * SS), nm, font=F("Medium", 13), fill=(200, 205, 220, 255))
    # title + labels
    u.text((60 * SS, 48 * SS), "REN ASHGRAVE", font=F("ExtraBold", 72), fill=(240, 244, 252, 255))
    u.text((64 * SS, 136 * SS), "ISEKAI PROTAGONIST · CHARACTER SHEET", font=F("Bold", 20), fill=(196, 30, 48, 255))
    u.text((64 * SS, 168 * SS), "A gamer pulled into another world — marked by a curse he refuses to let win.", font=F("Regular", 18), fill=(190, 196, 214, 255))
    for lx, lab in ((300, "IDLE · blade sheathed"), (720, "BATTLE · Vesperfang drawn")):
        tw = u.textlength(lab, font=F("Bold", 16))
        u.text((lx * SS - tw / 2, 1006 * SS), lab, font=F("Bold", 16), fill=(220, 224, 236, 255))
    u.text((1250 * SS, 950 * SS), "Close-up · crimson eye, silver fringe, gem earring", font=F("Medium", 14), fill=(190, 196, 214, 255))
    base.alpha_composite(ui)
    base.convert("RGB").resize((W, H), Image.LANCZOS).save(out)

if __name__ == "__main__":
    sheet(sys.argv[1] if len(sys.argv) > 1 else "ren_sheet.png")
