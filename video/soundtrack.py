"""Soundtrack, SFX and subtitles for Episode 1 (and the Shorts).

    python3 soundtrack.py episode out.wav out.srt     # full mix: narration + music cues + SFX, ducked under the voice
    python3 soundtrack.py short 1 out.wav             # mix for Short 1 / 2

SFX are timed by replaying every scene's choreography frame by frame (hero poses, arrows, icons, big
on-screen words, shakes) without drawing it, so hits land on the frames they belong to.
Music is synthesised here: M1 day theme, M2 golden hour, M3 siege, M4 sunrise reprise (see script_ep01.md).
"""
import math, os, re, subprocess, sys, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MODE = sys.argv[1]
_argv = sys.argv
sys.argv = [sys.argv[0], "reel" if MODE == "short" else "yt"]
sys.path.insert(0, HERE)
import episode as E  # noqa: E402
sys.argv = _argv
from PIL import Image, ImageDraw  # noqa: E402

SR = 44100
rng = np.random.default_rng(7)


def tt(d): return np.arange(int(d * SR)) / SR


def lp(x, k):
    if k <= 1: return x
    return np.convolve(x, np.ones(k) / k, "same")


def hz(name):
    names = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    return 440.0 * 2 ** ((names[name[:-1]] + 12 * (int(name[-1]) + 1) - 69) / 12)


class Bus:
    def __init__(self, dur):
        self.n = int(dur * SR) + SR
        self.L = np.zeros(self.n); self.R = np.zeros(self.n)

    def add(self, sig, t0, g=1.0, pan=0.0):
        i = int(t0 * SR)
        if i < 0: sig = sig[-i:]; i = 0
        j = min(self.n, i + len(sig))
        if i >= self.n or j <= i: return
        self.L[i:j] += sig[: j - i] * g * (1 - pan); self.R[i:j] += sig[: j - i] * g * (1 + pan)

    def st(self): return np.stack([self.L, self.R], 1)


# ------------------------------------------------------------------ instruments
_cache = {}


def glock(f, d=1.4):
    k = ("g", round(f, 2), d)
    if k not in _cache:
        t = tt(d)
        _cache[k] = (np.sin(2 * np.pi * f * t) * np.exp(-t * 3) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 9)) * np.minimum(1, t / 0.002)
    return _cache[k]


def pluck(f, d=1.2, bright=1.0):
    k = ("p", round(f, 2), d, bright)
    if k not in _cache:
        t = tt(d); s = np.zeros_like(t)
        for h in range(1, 8):
            s += np.sin(2 * np.pi * f * h * t + h) * np.exp(-t * (2.5 + 2.2 * h / bright)) / h ** 1.1
        _cache[k] = s * np.minimum(1, t / 0.003)
    return _cache[k]


def flute(f, d):
    t = tt(d + 0.15)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / 0.25)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    s = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.06 * np.sin(3 * ph)
    env = np.minimum(1, t / 0.04) * np.clip((d + 0.15 - t) / 0.15, 0, 1)
    return s * env


def pad(freqs, d, bright=0.3, att=0.6):
    t = tt(d); s = np.zeros_like(t)
    for f in freqs:
        for det in (-0.3, 0.3):
            ph = 2 * np.pi * (f + det) * t
            s += np.sin(ph) + bright * np.sin(2 * ph) + bright * 0.3 * np.sin(3 * ph)
    return s * np.minimum(1, t / att) * np.clip((d - t) / 0.5, 0, 1) / (2 * len(freqs))


def choir(freqs, d):
    t = tt(d); s = np.zeros_like(t)
    for f in freqs:
        vib = 1 + 0.006 * np.sin(2 * np.pi * 5 * t + f)
        ph = 2 * np.pi * np.cumsum(f * vib) / SR
        for h, a in ((1, 1), (2, 0.5), (3, 0.6), (4, 0.25), (5, 0.3)):  # crude "ah" formant
            s += a * np.sin(h * ph)
    return lp(s, 3) * np.minimum(1, t / 0.8) * np.clip((d - t) / 0.8, 0, 1) / (2.6 * len(freqs))


def kick(f0=110):
    t = tt(0.3); f = f0 * np.exp(-t * 18) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 12)


def tom(f0):
    t = tt(0.5); f = f0 * (1 + 0.5 * np.exp(-t * 20))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) + rng.normal(0, 0.15, len(t)) * np.exp(-t * 40)


def noise(d, dec, k=1, hp=False):
    t = tt(d); x = rng.normal(0, 1, len(t))
    if hp: x = np.diff(np.concatenate([[0], x]))
    return lp(x, k) * np.exp(-t * dec)


def saw(f, d):
    t = tt(d); ph = (f * t) % 1
    return (2 * ph - 1)


# ------------------------------------------------------------------ music cues
CH = {'C': ['C3', 'E3', 'G3', 'C4', 'E4'], 'G': ['G2', 'D3', 'G3', 'B3', 'D4'], 'Am': ['A2', 'E3', 'A3', 'C4', 'E4'], 'F': ['F2', 'C3', 'F3', 'A3', 'C4'],
      'E': ['E2', 'B2', 'E3', 'G#3', 'B3'], 'Dm': ['D3', 'F3', 'A3', 'D4']}
BASS = {'C': 'C2', 'G': 'G1', 'Am': 'A1', 'F': 'F1', 'E': 'E1', 'Dm': 'D2'}
PROG = [['C'], ['G'], ['Am'], ['F'], ['C'], ['G'], ['F', 'G'], ['C']]
MEL_A = [[('E5', .5), ('G5', .5), ('C6', 1), ('B5', .5), ('G5', .5), ('A5', 1)], [('G5', .5), ('D5', .5), ('G5', .5), ('B5', .5), ('D6', 1.5), ('B5', .5)],
         [('C6', .5), ('B5', .5), ('A5', .5), ('E5', .5), ('A5', 1), ('C6', 1)], [('A5', .5), ('G5', .5), ('F5', .5), ('A5', .5), ('G5', 2)],
         [('E5', .5), ('G5', .5), ('C6', 1), ('B5', .5), ('G5', .5), ('A5', 1)], [('G5', .5), ('A5', .5), ('B5', .5), ('D6', .5), ('E6', 1), ('D6', 1)],
         [('C6', .5), ('D6', .5), ('E6', .5), ('F6', .5), ('E6', 1), ('D6', 1)], [('C6', 4)]]
MEL_B = [[('C6', 1), ('G5', .5), ('E5', .5), ('G5', 1), ('C6', 1)], [('B5', 1), ('G5', .5), ('D5', .5), ('G5', 2)],
         [('A5', 1), ('E5', .5), ('C5', .5), ('E5', 1), ('A5', 1)], [('F5', .5), ('A5', .5), ('C6', 1), ('A5', 2)],
         [('E5', .5), ('G5', .5), ('C6', 1), ('D6', 1), ('E6', 1)], [('D6', 1), ('B5', 1), ('G5', 2)],
         [('A5', .5), ('C6', .5), ('F6', 1), ('E6', .5), ('D6', .5), ('B5', 1)], [('C6', 4)]]


def day_theme(bus, t0, t1, bpm=125, soft=False, choir_on=False, fade_in=0.05, fade_out=1.0, gain=1.0):
    beat = 60 / bpm; bar = 4 * beat
    tmp = Bus(t1 - t0 + 4)
    nb = int((t1 - t0) / bar) + 1
    for b in range(nb):
        blk = b // 8; bi = b % 8
        ts = b * bar
        mel = (MEL_A if blk % 2 == 0 else MEL_B)[bi]
        drums = (not soft) and (blk % 3 != 2)
        fl = (not soft) and blk % 2 == 1
        chords = PROG[bi]; seg = bar / len(chords)
        for ci, ch in enumerate(chords):
            cs = ts + ci * seg
            hits = [0, 1.5, 2.5, 3] if len(chords) == 1 else [0, 1.5]
            for k, h in enumerate(hits):
                notes = CH[ch] if k % 2 == 0 else CH[ch][::-1][:3]
                for ni, nn in enumerate(notes):
                    tmp.add(pluck(hz(nn)), cs + h * beat + ni * 0.012, (0.32 if k == 0 else 0.2) * (0.7 if soft else 1), pan=-0.15)
            for h in ([0, 2] if len(chords) == 1 else [0]):
                tmp.add(pluck(hz(BASS[ch]) * 2, 0.6, 0.5), cs + h * beat, 0.7)
            if soft or choir_on:
                tmp.add(pad([hz(n) for n in CH[ch][1:4]], seg + 0.4), cs, 0.45)
            if choir_on:
                tmp.add(choir([hz(n) * 2 for n in CH[ch][1:4]], seg + 0.5), cs, 0.5)
        if drums:
            for bt in range(4):
                if bt in (0, 2): tmp.add(kick(), ts + bt * beat, 0.6)
                if bt in (1, 3): tmp.add(noise(0.18, 22, hp=True), ts + bt * beat, 0.12)
                for ee in (0, 0.5): tmp.add(noise(0.06, 70, hp=True), ts + (bt + ee) * beat, 0.05)
        tt_ = ts
        for note, dd in mel:
            tmp.add(glock(hz(note), 1.6 if dd < 2 else 3.0), tt_, 0.38 * (0.8 if soft else 1), pan=0.15)
            if fl or choir_on: tmp.add(flute(hz(note), dd * beat * 0.95), tt_, 0.22)
            tt_ += dd * beat
    st = tmp.st()[: int((t1 - t0) * SR)]
    n = len(st)
    env = np.ones(n)
    fi = int(fade_in * SR); fo = int(fade_out * SR)
    if fi: env[:fi] = np.linspace(0, 1, fi)
    if fo: env[-fo:] *= np.linspace(1, 0, fo)
    i = int(t0 * SR)
    bus.L[i:i + n] += st[:, 0] * env * gain; bus.R[i:i + n] += st[:, 1] * env * gain


def siege(bus, t0, t1, intensity=1.0, fade_out=0.5):
    bpm = 120; beat = 60 / bpm; bar = 4 * beat
    tmp = Bus(t1 - t0 + 3)
    prog = ['Am', 'Am', 'F', 'E']
    for b in range(int((t1 - t0) / bar) + 1):
        ch = prog[b % 4]; ts = b * bar
        tmp.add(pad([hz(n) for n in CH[ch][:3]], bar + 0.3, bright=0.6, att=0.2), ts, 0.5)
        root = hz(BASS[ch]) * 2
        for e8 in range(8):  # low ostinato
            s = lp(saw(root * (2 if e8 % 4 == 3 else 1), beat * 0.45), 18) * np.exp(-tt(beat * 0.45) * 5)
            tmp.add(s, ts + e8 * beat / 2, 0.22)
        if intensity > 0.5:
            for k, (pos, f0) in enumerate([(0, 90), (0.75, 120), (1.5, 90), (2, 150), (2.5, 120), (3, 90), (3.5, 160)]):
                tmp.add(tom(f0), ts + pos * beat, 0.5 * intensity)
            tmp.add(kick(90), ts, 0.7); tmp.add(kick(90), ts + 2 * beat, 0.5)
            tmp.add(noise(0.3, 9, hp=True), ts + 3.5 * beat, 0.06 * intensity)
    st = tmp.st()[: int((t1 - t0) * SR)]
    n = len(st); env = np.ones(n)
    fo = int(fade_out * SR); env[-fo:] *= np.linspace(1, 0, fo); env[: int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))
    i = int(t0 * SR)
    bus.L[i:i + n] += st[:, 0] * env; bus.R[i:i + n] += st[:, 1] * env


def drone(bus, t0, d, f=49, g=0.5):
    t = tt(d)
    s = lp(np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.5 * t) + 0.25 * np.sign(np.sin(2 * np.pi * f / 2 * t)), 25)
    s *= np.minimum(1, t / 1.5) * np.clip((d - t) / 1.0, 0, 1)
    bus.add(s, t0, g)


# ------------------------------------------------------------------ SFX bank
def thump(f=55, d=0.25, dec=14):
    t = tt(d); return np.sin(2 * np.pi * np.cumsum(f * (1 + 1.5 * np.exp(-t * 30))) / SR) * np.exp(-t * dec)


def screech(d, f0, f1):
    t = tt(d); f = f0 + (f1 - f0) * t / d
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.03 * np.sin(2 * np.pi * 31 * t))) / SR
    s = np.tanh(3 * (np.sin(ph) + 0.6 * np.sin(2.01 * ph) + 0.4 * np.sin(3.02 * ph))) * 0.5 + rng.normal(0, 0.35, len(t))
    return lp(s, 3) * np.minimum(1, t / 0.03) * np.clip((d - t) / (d * 0.6), 0, 1)


def roar(d=1.6):
    t = tt(d); f = 70 + 30 * np.sin(2 * np.pi * 3 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.tanh(2.5 * (np.sin(ph) + 0.7 * np.sin(2 * ph) + 0.5 * np.sin(3.1 * ph))) + lp(rng.normal(0, 0.8, len(t)), 6)
    return s * np.minimum(1, t / 0.1) * np.clip((d - t) / 0.6, 0, 1) * 0.6


def sm(*parts):
    """Sum (signal, gain) pairs of different lengths."""
    n = max(len(p) for p, g in parts)
    out = np.zeros(n)
    for p, g in parts: out[:len(p)] += p * g
    return out


_sfx = {}


def SFX(name):
    if name not in _sfx: _sfx[name] = _SFX(name)
    return _sfx[name]


def _SFX(name):
    if name == "step": return lp(noise(0.08, 50), 6) * 0.6
    if name == "bigstep": return sm((thump(38, 0.6, 6), 1.4), (lp(noise(0.2, 15), 8), 0.4))
    if name == "hammer": return sm((thump(170, 0.12, 40), 0.6), (lp(noise(0.06, 60), 3), 0.5))
    if name == "chop": return sm((thump(220, 0.1, 45), 0.5), (lp(noise(0.09, 45), 2), 0.7))
    if name == "whack": return sm((thump(260, 0.08, 50), 0.6), (lp(noise(0.05, 70), 2), 0.4))
    if name == "snapstick": return sm((noise(0.05, 90), 1.2), (thump(400, 0.06, 60), 0.4))
    if name == "trombone":
        out = []
        for i, (f, d) in enumerate([(233, .3), (220, .3), (208, .3), (196, .9)]):
            t = tt(d); vib = 1 + (0.02 * np.sin(2 * np.pi * 6 * t) if i == 3 else 0)
            ph = 2 * np.pi * np.cumsum(f * vib) / SR
            out.append(np.tanh(1.8 * (np.sin(ph) + 0.6 * np.sin(2 * ph) + 0.4 * np.sin(3 * ph))) * np.minimum(1, t / 0.03) * np.clip((d - t) / 0.08, 0, 1))
        return lp(np.concatenate(out), 4) * 0.35
    if name == "boing":
        t = tt(2.0); f = 300 + 120 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 1.2)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.3) * 0.5
    if name == "rockcrack": return sm((lp(noise(0.25, 18), 2), 0.9), (thump(90, 0.3, 12), 0.6))
    if name == "timber":
        t = tt(1.0); f = 140 - 60 * t
        cr = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 23 * t))) * 0.25 * np.exp(-t * 1.5)
        return np.concatenate([cr, sm((thump(45, 0.6, 7), 1.2), (lp(noise(0.6, 8), 10), 0.4))])
    if name == "ding": return sm((glock(1046.5), 0.7), (glock(1318.5), 0.42))
    if name == "buzzer":
        t = tt(0.45); return np.sign(np.sin(2 * np.pi * 110 * t)) * 0.18 * np.clip((0.45 - t) / 0.05, 0, 1)
    if name == "chime": return sm((glock(784), 0.6), (glock(1046.5), 0.48), (glock(1568), 0.3))
    if name == "shimmer":
        out = np.zeros(int(2.0 * SR))
        for i, f in enumerate([1568, 1760, 2093, 2349, 2637, 3136]):
            g = glock(f, 1.5); j = int(i * 0.07 * SR); out[j:j + len(g)] += g[: len(out) - j] * 0.35
        return out
    if name == "clang": return sm((glock(523, 1.2), 0.6), (glock(880, 1.0), 0.3), (noise(0.1, 40, hp=True), 0.18))
    if name == "dig": return lp(noise(0.18, 14), 4) * 0.7
    if name == "creak":
        t = tt(0.6); f = 300 + 80 * np.sin(2 * np.pi * 2 * t)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 37 * t))) * 0.12 * np.sin(np.pi * t / 0.6)
    if name == "twang":
        t = tt(0.5); return (np.sin(2 * np.pi * 180 * t) + 0.4 * np.sin(2 * np.pi * 360 * t)) * np.exp(-t * 9) * 0.5
    if name == "whoosh":
        t = tt(0.35); return lp(rng.normal(0, 1, len(t)), 3) * np.sin(np.pi * t / 0.35) * 0.25
    if name == "thunk": return sm((thump(140, 0.12, 30), 0.6), (lp(noise(0.05, 60), 2), 0.3), (glock(2093, 0.6), 0.15))
    if name == "screech": return screech(0.6, 520, 340) * 0.5
    if name == "groan": return screech(0.9, 160, 120) * 0.25
    if name == "roar": return roar()
    if name == "splinter": return sm((lp(noise(0.5, 6), 2), 0.8), (thump(70, 0.4, 9), 0.8))
    if name == "ropesnap": return sm((noise(0.04, 80), 1.5), (thump(600, 0.05, 80), 0.4))
    if name == "boom": return sm((thump(36, 2.0, 2.5), 2.0), (lp(noise(1.5, 3), 12), 0.7))
    if name == "freeze": return sm((thump(42, 0.9, 5), 1.4), (noise(0.12, 40), 0.5))
    if name == "rewind":
        t = tt(1.1); f = 900 * np.exp(-t * 2.2) + 120 + 60 * np.sin(2 * np.pi * 11 * t)
        return (np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.25 + lp(rng.normal(0, 0.6, len(t)), 3)) * np.sin(np.pi * t / 1.1) * 0.5
    if name == "hit": return sm((thump(40, 1.4, 3), 1.4), (noise(0.8, 4), 0.3))
    if name == "sting": return sm((thump(50, 0.8, 5), 0.7), (pad([110, 164.8, 220], 1.2, 0.8, 0.02), 1.05))
    if name == "tick": return lp(noise(0.02, 200, hp=True), 1) * 0.4
    if name == "squeak":
        t = tt(0.18); return np.sin(2 * np.pi * np.cumsum(1400 + 600 * np.sin(np.pi * t / 0.18)) / SR) * 0.15 * np.sin(np.pi * t / 0.18)
    if name == "heart": return thump(52) * 0.9
    if name == "shing":
        t = tt(0.6); return sm((np.sin(2 * np.pi * (2400 + 1200 * t) * t) * np.exp(-t * 8), 0.2), (lp(noise(0.5, 6), 2), 0.06))
    if name == "crumble": return lp(noise(0.7, 5), 5) * 0.35
    if name == "tug": return sm((thump(120, 0.15, 25), 0.4), (_SFX("creak"), 0.6))
    raise KeyError(name)


# ------------------------------------------------------------------ choreography replay -> SFX events
def replay(scene_ids, time_map):
    """Run scene choreography for every frame (drawing onto 1x1 canvases) and turn state changes into SFX.
    time_map(n, local_t) -> output time or None. Returns [(t, name, gain, pan)]."""
    events = []
    rec = {}
    orig_hero, orig_arrow, orig_zombie = E.hero, E.arrow, E.zombie

    def hero_rec(d, e, glows, x, y, h, pose, dir, t, ph=0.0, swing=0.0, tool=None, **kw):
        rec["hero"] = (pose, swing, tool, ph, x)
        return (x, y)

    def arrow_rec(d, e, glows, x0, y0, x1, y1, u):
        rec.setdefault("arrows", []).append(round(x1))
        rec.setdefault("arrow_u", {})[round(x1)] = u

    def zombie_rec(*a, **kw):
        rec["zombies"] = rec.get("zombies", 0) + 1
    E.hero, E.arrow, E.zombie = hero_rec, arrow_rec, zombie_rec
    E.brute.__globals__["zombie"] = zombie_rec
    tiny = Image.new("RGBA", (1, 1)); dd = ImageDraw.Draw(tiny)
    for n in scene_ids:
        prev = {}
        nf = int(round(E.DURS[n] * E.FPS))
        for i in range(nf):
            lt = i / E.FPS
            T = time_map(n, lt)
            if T is None: prev = {}; continue
            f = E.F(); E.SCENES[n](lt, f)
            rec.clear()
            for fn in f.draw:
                try: fn(dd, dd, [], tiny)
                except Exception: pass
            pose, swing, tool, ph, hx = rec.get("hero", (None, 0, None, 0, 0))
            pp = prev.get("hero", (None, 0, None, 0, 0))
            if pose in ("hammer", "chop") and pp[0] == pose and math.floor(swing - 0.93) != math.floor(pp[1] - 0.93):
                events.append((T, "chop" if pose == "chop" and tool in ("axe",) else ("dig" if tool == "stick" and n == 11 else ("whack" if tool in ("stick", "rock") else "hammer")), 0.5, 0.1))
            if pose == "thrust" and pp[0] == "thrust" and math.floor(swing) != math.floor(pp[1]):
                events.append((T, "whoosh", 0.7, 0))
            if pose in ("walk", "run", "dash") and pp[0] == pose and math.floor(ph / math.pi) != math.floor(pp[3] / math.pi):
                events.append((T, "step", 0.25 if pose == "walk" else 0.35, 0.05))
            if pose == "jump" and pp[0] != "jump": events.append((T, "whoosh", 0.5, 0))
            if pose == "walk" and n == 9 and pp[0] == "walk" and int(lt * 3) != int((lt - 1 / E.FPS) * 3): events.append((T, "squeak", 0.8, 0))
            # arrows: release + impact
            au = rec.get("arrow_u", {}); pau = prev.get("arrow_u", {})
            for k, u in au.items():
                if k not in pau: events.append((T, "twang", 0.6, 0.1)); events.append((T + 0.02, "whoosh", 0.4, -0.1))
            for k, u in pau.items():
                if k not in au: events.append((T, "thunk", 0.7, -0.2)); events.append((T + 0.05, "crumble", 0.6, -0.2))
            # icons / marks / words
            for lab, *_r in f.icons:
                age = _r[-1]
                if 0 <= age < 1 / E.FPS + 1e-6: events.append((T, "ding", 0.55, 0))
            for kind, wx, wy, age in f.marks:
                if 0 <= age < 1 / E.FPS + 1e-6: events.append((T, "buzzer" if kind == "x" else "chime", 0.6, 0))
            for kind, age in f.rules:
                if 0 <= age < 1 / E.FPS + 1e-6: events.append((T, "ding", 0.5, 0))
            for txt, age, life in f.big:
                if 0 <= age < 1 / E.FPS + 1e-6:
                    m = {"SNAP.": [("snapstick", 1.0), ("trombone", 0.9)], "BZZZZ": [("boing", 0.8)], "BRUTE": [("roar", 0.9), ("sting", 0.6)], "SNAP!": [("ropesnap", 1.0), ("splinter", 0.9)],
                         "CRACK!": [("rockcrack", 0.6), ("whack", 0.6)], "BOOM": [("boom", 1.0)], "0:00": [("sting", 0.6)], "NIGHT 1 SURVIVED": [("hit", 0.6)],
                         "TEN HOURS EARLIER": [("whoosh", 0.6)], "10:00 LEFT": [("tick", 0.8)], "8:00 LEFT": [("tick", 0.8)], "6:00 LEFT": [("tick", 0.8)], "3:00 LEFT": [("tick", 0.8)]}
                    for nm, g in m.get(txt, []): events.append((T, nm, g, 0))
            if f.flash and not prev.get("flash"): events.append((T, "freeze", 1.0, 0))
            if f.rewind and not prev.get("rewind"): events.append((T, "rewind", 0.8, 0))
            if f.badge and not prev.get("badge"): events.append((T, "whoosh", 0.5, 0))
            if f.shake > 0.45 and prev.get("shake", 0) <= 0.45 and n in (16, 17): events.append((T, "bigstep", 0.9, 0))
            prev = dict(hero=(pose, swing, tool, ph, hx), arrow_u=dict(au), flash=f.flash, rewind=f.rewind, badge=f.badge, shake=f.shake)
    E.hero, E.arrow, E.zombie = orig_hero, orig_arrow, orig_zombie
    E.brute.__globals__["zombie"] = orig_zombie
    return events


# ------------------------------------------------------------------ hand-placed SFX (things replay can't see)
def manual_sfx():
    ev = []
    A = E.STARTS
    # 01 chase: heartbeat, rustles, screeches
    for b in np.arange(0, 2.2, 0.42): ev += [(b, "heart", 0.9, 0), (b + 0.15, "heart", 0.55, 0)]
    for te, *_ in E.T.ZOMBIES: ev.append((te, "dig", 0.6, -0.4))
    ev += [(0.35, "screech", 0.7, -0.5), (1.45, "screech", 1.0, 0)]
    # 04: whacks get the "stick on wood" sound already; 05 split
    ph = E.vo_phr("05"); ev.append((A[5] + E.LEADS[5] + ph[4] - 0.2, "rockcrack", 0.9, 0))
    # 06: trees fall
    ev += [(A[6] + 1.9, "timber", 0.8, -0.3), (A[6] + 5.0, "timber", 0.8, -0.4)]
    # 09: crystal
    ph = E.vo_phr("09"); ev += [(A[9] + E.LEADS[9] + ph[1], "shimmer", 0.8, 0.2), (A[9] + E.LEADS[9] + ph[7] + 1.8, "clang", 0.6, 0)]
    # 12: tugs on the vine
    ph = E.vo_phr("12"); t_tug = A[12] + E.LEADS[12] + ph[3]
    ev += [(t_tug, "tug", 0.9, 0), (t_tug + 0.6, "tug", 0.9, 0)]
    # 13: boulder hoist creaks
    ph = E.vo_phr("13")
    for k in range(5): ev.append((A[13] + E.LEADS[13] + ph[3] + 1.0 + k * 0.9, "creak", 0.7, -0.2))
    # 14: eyes
    ph = E.vo_phr("14")
    for k in (4, 5, 6): ev.append((A[14] + E.LEADS[14] + ph[k], "shing", 0.7, -0.3))
    for b in np.arange(A[14] + 1.0, A[15], 0.85): ev += [(b, "heart", 0.6, 0), (b + 0.16, "heart", 0.35, 0)]
    # zombie groans through the siege
    r = np.random.default_rng(3)
    for t0 in np.arange(A[15], A[20] + 3, 1.7): ev.append((t0 + r.uniform(0, 1), "groan", 0.5, r.uniform(-0.6, 0.2)))
    # 17: brute steps
    for k in range(10): ev.append((A[17] + 0.3 + k / 1.1, "bigstep", 0.8, -0.3))
    # 20: crumble wave
    ph = E.vo_phr("20")
    for k in range(10): ev.append((A[20] + E.LEADS[20] + ph[2] + 0.2 + k * 0.25, "crumble", 0.6, 0.5 - k * 0.1))
    return ev


# ------------------------------------------------------------------ narration + subtitles
def load_mp3(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float64) / 32768.0


def clean(txt):
    t = re.sub(r"\[[^\]]+\]", "", txt)
    return re.sub(r"\s+", " ", t).strip()


def srt_time(s):
    h = int(s // 3600); m = int(s % 3600 // 60); sec = s % 60
    return f"{h:02d}:{m:02d}:{int(sec):02d},{int(round((sec % 1) * 1000)):03d}"


def subtitles(path):
    """Sentence-level captions placed on the detected speech segments of each clip."""
    cues = []
    for n in range(1, 22):
        key = f"{n:02d}"
        tim = E.TIMING[key]; dur = tim["dur"]
        speech, last = [], 0.0
        for a, b in tim["silences"]:
            if a > last + 0.05: speech.append((last, a))
            last = b
        if dur > last + 0.05: speech.append((last, dur))
        total = sum(b - a for a, b in speech)
        sents = [s.strip() for s in re.split(r"(?<=[.?!…])\s+", clean(TEXTS[key])) if s.strip()]
        chars = [max(4, len(s)) for s in sents]; ct = sum(chars)

        def at(frac):
            rem = frac * total
            for a, b in speech:
                if rem <= b - a: return a + rem
                rem -= b - a
            return speech[-1][1]
        acc = 0
        t0s = E.STARTS[n] + E.LEADS[n]
        for s, c in zip(sents, chars):
            a = at(acc / ct); acc += c; b = at(acc / ct)
            # split long sentences into two caption lines
            cues.append((t0s + a, t0s + b + 0.15, s))
    cues.sort()
    cues = [(a, min(b, cues[i + 1][0] - 0.02) if i + 1 < len(cues) else b, s) for i, (a, b, s) in enumerate(cues)]
    with open(path, "w") as fh:
        for i, (a, b, s) in enumerate(cues, 1):
            fh.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{s}\n\n")


TEXTS = E.TEXTS


def write_wav(path, st):
    st = st / max(1e-9, np.max(np.abs(st))) * 0.95
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def duck(music, vo_mono, depth=0.6):
    env = np.abs(vo_mono)
    k = int(0.25 * SR)
    c = np.cumsum(np.concatenate([np.zeros(k), env, np.zeros(k)]))
    env = (c[k + k // 2:k + k // 2 + len(env)] - c[k // 2:k // 2 + len(env)]) / k   # running mean (fast)
    env = np.clip(env / (np.percentile(env[env > 1e-4], 70) if np.any(env > 1e-4) else 1), 0, 1)
    return music * (1 - depth * env)[:, None]


def episode_mix(out_wav, out_srt):
    A = E.STARTS
    total = E.TOTAL
    vo = Bus(total); mus = Bus(total); fx = Bus(total)
    for n in range(1, 22):
        clip = load_mp3(os.path.join(E.NARR, f"{n:02d}.mp3"))
        fi, fo = int(0.015 * SR), int(0.08 * SR)          # soften clip edges so scene-to-scene joins don't click
        clip[:fi] *= np.linspace(0, 1, fi); clip[-fo:] *= np.linspace(1, 0, fo)
        vo.add(clip, A[n] + E.LEADS[n], 1.0)
    # music cues
    drone(mus, 0, 2.3, 55, 0.35)
    day_theme(mus, 3.4, A[11] + 0.5, fade_out=2.0, gain=0.55)                                        # M1
    ph13 = E.vo_phr("13"); t_sunset = A[13] + E.LEADS[13] + ph13[6]
    day_theme(mus, A[11], t_sunset + 0.5, bpm=100, soft=True, fade_in=2.0, fade_out=3.0, gain=0.55)  # M2
    drone(mus, t_sunset, A[15] + 2.5 - t_sunset, 49, 0.5)                                           # silence: drone + heartbeat
    ph16 = E.vo_phr("16")
    siege(mus, A[15] + E.LEADS[15] - 0.4, A[16] + 0.5, 1.0)                                         # M3
    siege(mus, A[16] + E.LEADS[16] + ph16[2], A[19], 1.0)
    drone(mus, A[19], A[20] + 1.5 - A[19], 55, 0.6)                                                 # one tense held note
    mus.add(pad([110, 164.8], A[20] + 1.0 - A[19], 0.8, 0.5), A[19], 0.5)
    ph20 = E.vo_phr("20"); t_rise = A[20] + E.LEADS[20] + ph20[1]
    day_theme(mus, t_rise, A[21] + E.DURS[21], choir_on=True, fade_in=1.5, fade_out=3.0, gain=0.6)  # M4
    for i, nn in enumerate(['C5', 'E5', 'G5', 'C6', 'E6', 'G6', 'C7']):
        mus.add(glock(hz(nn), 2.0), A[21] + E.DURS[21] - 3.0 + i * 0.07, 0.25)
    # SFX
    def tm(n, lt): return A[n] + lt
    evs = replay(list(range(1, 22)), tm) + manual_sfx()
    for t, nm, g, pan in evs:
        fx.add(SFX(nm), t, g, pan)
    v = vo.st(); m = mus.st(); x = fx.st()
    m = duck(m, vo.L, 0.8)
    mix = v * 1.0 + m / max(1e-9, np.max(np.abs(m))) * 0.13 + x / max(1e-9, np.max(np.abs(x))) * 0.38
    write_wav(out_wav, mix[: int(total * SR)])
    subtitles(out_srt)
    print("events", len(evs))


# ------------------------------------------------------------------ shorts
def short_mix(k, out_wav):
    seq, total = E.short_plan(k)
    body = seq[-1][1]
    bus_v = Bus(total); mus = Bus(total); fx = Bus(total)

    def tm(n, lt):
        for s0, s1, nn, a, spd, seg in seq:
            if nn == n and a <= lt <= a + (s1 - s0) * spd:
                return s0 + (lt - a) / spd
        return None
    used = sorted(set(x[2] for x in seq))
    evs = replay(used, tm) + [(t, nm, g, p) for t, nm, g, p in manual_sfx_short(k, seq)]
    evs.sort(); keep = []; last = {}
    for t, nm, g, pan in evs:  # thin out machine-gun hits in fast-forward parts
        if nm in ("hammer", "chop", "step", "whack", "dig", "groan") and t - last.get(nm, -9) < 0.14: continue
        last[nm] = t; keep.append((t, nm, g * (0.6 if nm in ("hammer", "chop", "step") else 1), pan))
    for t, nm, g, pan in keep: fx.add(SFX(nm), t, g, pan)
    # music follows the story
    def seg_start(n, nth=0):
        hits = [x for x in seq if x[2] == n]
        return hits[min(nth, len(hits) - 1)][0]
    if k == 1:
        drone(mus, 0, 2.4, 55, 0.4)
        t_sun = seg_start(13)
        day_theme(mus, 2.6, t_sun + 1.0, bpm=128, gain=0.7, fade_in=0.4, fade_out=1.5)
        drone(mus, t_sun, total - t_sun, 49, 0.7)
        for b_ in np.arange(t_sun + 2.0, body, 0.8): fx.add(SFX("heart"), b_, 0.5)
    else:
        drone(mus, 0, seg_start(15) + 0.5, 49, 0.7)
        t20 = seg_start(20)
        siege(mus, seg_start(15), t20 + 0.3, 1.0)
        drone(mus, t20, 3.5, 55, 0.6)
        day_theme(mus, t20 + (E.LEADS[20] + 3.13) - 0.2, total, choir_on=True, gain=0.75, fade_in=1.0, fade_out=1.0)
    fx.add(SFX("hit"), body, 0.7)
    for clip, a, b, at in E.short_vo(k):
        sig = load_mp3(os.path.join(E.NARR, f"{clip}.mp3"))[int(a * SR):int(b * SR)].copy()
        fi, fo = int(0.01 * SR), int(0.06 * SR)
        sig[:fi] *= np.linspace(0, 1, fi); sig[-fo:] *= np.linspace(1, 0, fo)
        bus_v.add(sig, at, 1.0)
    v = bus_v.st(); m = duck(mus.st(), bus_v.L, 0.8); x = fx.st()
    mix = v + m / max(1e-9, np.max(np.abs(m))) * 0.2 + x / max(1e-9, np.max(np.abs(x))) * 0.45
    write_wav(out_wav, mix[: int(total * SR)])


def manual_sfx_short(k, seq):
    ev = []
    for s0, s1, n, a, spd, seg in seq:
        if n == 1 and s0 == 0:
            for b in np.arange(0, 2.2, 0.42): ev += [(b, "heart", 0.9, 0), (b + 0.15, "heart", 0.55, 0)]
            ev += [(0.35, "screech", 0.7, -0.5), (1.45, "screech", 1.0, 0)]
        if n == 14:
            ev += [(s0 + 0.2, "shing", 0.6, -0.3)]
        if n == 17 and seg[4] and seg[4][0] == 0.0:
            ev += [(s0 + 0.3 + i / 1.1, "bigstep", 0.8, -0.3) for i in range(int((s1 - s0) * 1.1))]
        if n == 20:
            ph = E.vo_phr("20")
            ev += [(s0 + (E.LEADS[20] + ph[2] + 0.2 + i * 0.25 - a) / spd, "crumble", 0.6, 0.5 - i * 0.1) for i in range(10)]
    return ev


if __name__ == "__main__":
    if MODE == "episode":
        episode_mix(sys.argv[2], sys.argv[3])
    elif MODE == "short":
        short_mix(int(sys.argv[2]), sys.argv[3])
