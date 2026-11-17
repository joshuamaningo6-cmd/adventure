"""Original cheerful adventure cue: C - G - Am - F, 125 BPM, 8 bars (~15.4 s).
Glockenspiel + flute melody, plucked guitar strums, pizzicato bass, shaker/kick/tambourine, string swell.
"""
import numpy as np, wave, sys

SR = 44100
BPM = 125
BEAT = 60 / BPM
BAR = 4 * BEAT
BARS = 8
TOTAL = BARS * BAR + 2.0          # tail for the final ring-out
N = int(TOTAL * SR)
rng = np.random.default_rng(3)

def hz(name):
    names = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[n] + 12 * (o + 1) - 69) / 12)

def add(buf, sig, t0, gain=1.0):
    i = int(t0 * SR); j = min(N, i + len(sig))
    if i < N: buf[i:j] += sig[: j - i] * gain

def glock(f, dur=1.2):
    t = np.arange(int(dur * SR)) / SR
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 3.2)
         + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 9)
         + 0.12 * np.sin(2 * np.pi * f * 5.40 * t) * np.exp(-t * 18))
    att = np.minimum(1, t / 0.002)
    return s * att

def flute(f, dur):
    t = np.arange(int((dur + 0.15) * SR)) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / 0.25)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    s = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.06 * np.sin(3 * ph)
    breath = rng.normal(0, 1, len(t)); breath = np.convolve(breath, np.ones(30) / 30, 'same') * 0.08
    env = np.minimum(1, t / 0.04) * np.clip((dur + 0.15 - t) / 0.15, 0, 1)
    return (s + breath) * env

def pluck(f, dur=1.6, bright=0.5):
    """Karplus-Strong string."""
    n = int(dur * SR); p = int(SR / f)
    buf = rng.uniform(-1, 1, p)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = (bright * buf[i % p] + (1 - bright) * buf[(i + 1) % p]) * 0.996
    return out

def pad(freqs, dur):
    t = np.arange(int(dur * SR)) / SR
    s = np.zeros_like(t)
    for f in freqs:
        for det in (-0.25, 0.25):
            ph = 2 * np.pi * (f + det) * t
            s += np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)
    env = np.minimum(1, t / 0.6) * np.clip((dur - t) / 0.5, 0, 1)
    return s * env / (2 * len(freqs))

def kick():
    t = np.arange(int(0.25 * SR)) / SR
    f = 110 * np.exp(-t * 18) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)

def noise_hit(dur, decay, hp=True):
    t = np.arange(int(dur * SR)) / SR
    n = rng.normal(0, 1, len(t))
    if hp: n = np.diff(np.concatenate([[0], n]))
    return n * np.exp(-t * decay)

CHORDS = {'C': ['C3', 'E3', 'G3', 'C4', 'E4'], 'G': ['G2', 'D3', 'G3', 'B3', 'D4'],
          'Am': ['A2', 'E3', 'A3', 'C4', 'E4'], 'F': ['F2', 'C3', 'F3', 'A3', 'C4']}
BASS = {'C': 'C2', 'G': 'G1', 'Am': 'A1', 'F': 'F1'}
PROG = [['C'], ['G'], ['Am'], ['F'], ['C'], ['G'], ['F', 'G'], ['C']]

MEL = [
    [('E5', .5), ('G5', .5), ('C6', 1), ('B5', .5), ('G5', .5), ('A5', 1)],
    [('G5', .5), ('D5', .5), ('G5', .5), ('B5', .5), ('D6', 1.5), ('B5', .5)],
    [('C6', .5), ('B5', .5), ('A5', .5), ('E5', .5), ('A5', 1), ('C6', 1)],
    [('A5', .5), ('G5', .5), ('F5', .5), ('A5', .5), ('G5', 2)],
    [('E5', .5), ('G5', .5), ('C6', 1), ('B5', .5), ('G5', .5), ('A5', 1)],
    [('G5', .5), ('A5', .5), ('B5', .5), ('D6', .5), ('E6', 1), ('D6', 1)],
    [('C6', .5), ('D6', .5), ('E6', .5), ('F6', .5), ('E6', 1), ('D6', 1)],
    [('C6', 4)],
]

mix_g = np.zeros(N); mix_f = np.zeros(N); mix_r = np.zeros(N); mix_b = np.zeros(N); mix_d = np.zeros(N); mix_p = np.zeros(N)

for b in range(BARS):
    t0 = b * BAR
    chords = PROG[b]
    seg = BAR / len(chords)
    for ci, ch in enumerate(chords):
        cs = t0 + ci * seg
        # strum pattern: down on 1, up-down on the "and"s
        hits = [0, 1.5, 2.5, 3] if len(chords) == 1 else [0, 1.5]
        for k, h in enumerate(hits):
            notes = CHORDS[ch] if k % 2 == 0 else CHORDS[ch][::-1][:3]
            for ni, nn in enumerate(notes):
                add(mix_r, pluck(hz(nn), 1.4, 0.55), cs + h * BEAT + ni * 0.012, 0.5 if k == 0 else 0.32)
        # pizzicato bass on 1 and 3 (the final bar just holds)
        for h in ([0, 2] if len(chords) == 1 else [0]):
            add(mix_b, pluck(hz(BASS[ch]) * 2, 0.6, 0.3), cs + h * BEAT, 0.9)
        if b >= 4:  # string swell in the second half
            add(mix_p, pad([hz(n) for n in CHORDS[ch][1:4]], seg + 0.4), cs, 0.55 if b < 7 else 0.75)
    # drums
    if b < 7:
        for beat in range(4):
            if beat in (0, 2): add(mix_d, kick(), t0 + beat * BEAT, 0.8)
            if beat in (1, 3): add(mix_d, noise_hit(0.18, 22), t0 + beat * BEAT, 0.20)
            for e in (0, 0.5):  # shaker 8ths
                add(mix_d, noise_hit(0.06, 70), t0 + (beat + e) * BEAT, 0.08 if e else 0.05)
    else:
        add(mix_d, kick(), t0, 1.0)
    # melody: glockenspiel always, flute doubles from bar 5
    tt = t0
    for note, d in MEL[b]:
        f = hz(note)
        add(mix_g, glock(f, 1.6 if d < 2 else 3.0), tt, 0.55)
        if b >= 4:
            add(mix_f, flute(f, d * BEAT * 0.95), tt, 0.32)
        tt += d * BEAT

# final sparkle arpeggio
end = 7 * BAR
for i, n in enumerate(['C5', 'E5', 'G5', 'C6', 'E6', 'G6', 'C7']):
    add(mix_g, glock(hz(n), 2.0), end + 0.35 + i * 0.07, 0.35)

def reverb(x, seconds=1.6, wet=0.22):
    L = int(seconds * SR); t = np.arange(L) / SR
    ir = rng.normal(0, 1, L) * np.exp(-t * 4.0); ir[0] = 0
    ir /= np.sqrt((ir ** 2).sum())
    from numpy.fft import rfft, irfft
    n = len(x) + L; nfft = 1 << (n - 1).bit_length()
    y = irfft(rfft(x, nfft) * rfft(ir, nfft), nfft)[: len(x)]
    return x + wet * y

mel = reverb(mix_g + mix_f, 1.8, 0.35)
rhythm = reverb(mix_r * 0.7 + mix_b + mix_p, 1.2, 0.18)
drums = mix_d
mono = mel * 0.9 + rhythm * 0.75 + drums * 0.6
# simple stereo: guitar slightly left, glock slightly right
L = mono + 0.08 * (mix_r - mix_g); R = mono - 0.08 * (mix_r - mix_g)
st = np.stack([L, R], 1)
st /= np.max(np.abs(st)) / 0.89
fade = np.ones(N); fl = int(1.0 * SR); fade[-fl:] = np.linspace(1, 0, fl)
st *= fade[:, None]
pcm = (st * 32767).astype(np.int16)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'bgm.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('seconds', TOTAL)
