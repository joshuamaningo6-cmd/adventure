"""Word timings for a narration clip: script text aligned to the detected pauses (no paid transcription).

Pause tags and punctuation in the script are the candidate phrase breaks; the detected silences are matched to
them with a small dynamic program, then words share each speech segment in proportion to their length.
"""
import re


def tokens(text):
    """[(word, can_break_after)] with audio tags removed."""
    parts = re.split(r"(\[[^\]]+\])", text)
    out = []
    for p in parts:
        if p.startswith("["):
            if out and "pause" in p: out[-1] = (out[-1][0], True)
            continue
        for w in p.split():
            out.append((w, bool(re.search(r"[.,?!…:;]$", w))))
    return out


def align(text, dur, silences):
    toks = tokens(text)
    speech, last = [], 0.0
    for a, b in silences:
        if a > last + 0.05: speech.append((last, a))
        last = b
    if dur > last + 0.05: speech.append((last, dur))
    K = len(speech)
    L = [len(w) + 1 for w, _ in toks]
    N = len(toks)
    cum = [0]
    for x in L: cum.append(cum[-1] + x)
    total_c, total_d = cum[-1], sum(b - a for a, b in speech)
    cand = [i + 1 for i, (_, br) in enumerate(toks) if br and i + 1 < N]
    if K - 1 > len(cand):  # not enough breaks: plain proportional
        bounds = [0, N]; speech = [(speech[0][0], speech[-1][1])]; K = 1
    else:
        INF = 1e18
        pts = [0] + cand + [N]
        # dp[k][j]: best cost using k segments ending at pts[j]
        dp = [[INF] * len(pts) for _ in range(K + 1)]; bk = [[-1] * len(pts) for _ in range(K + 1)]
        dp[0][0] = 0
        for k in range(1, K + 1):
            sd = (speech[k - 1][1] - speech[k - 1][0]) / total_d
            for j in range(1, len(pts)):
                if k == K and j != len(pts) - 1: continue
                for i in range(j):
                    if dp[k - 1][i] >= INF: continue
                    sc = (cum[pts[j]] - cum[pts[i]]) / total_c
                    c = dp[k - 1][i] + (sc - sd) ** 2
                    if c < dp[k][j]: dp[k][j] = c; bk[k][j] = i
        bounds, j = [N], len(pts) - 1
        for k in range(K, 0, -1):
            j = bk[k][j]; bounds.append(pts[j])
        bounds = bounds[::-1]
    words = []
    for k in range(K):
        a, b = speech[k]; i0, i1 = bounds[k], bounds[k + 1]
        span = cum[i1] - cum[i0] or 1
        for i in range(i0, i1):
            ws = a + (b - a) * (cum[i] - cum[i0]) / span
            we = a + (b - a) * (cum[i + 1] - cum[i0]) / span
            words.append((toks[i][0], ws, we))
    return words
