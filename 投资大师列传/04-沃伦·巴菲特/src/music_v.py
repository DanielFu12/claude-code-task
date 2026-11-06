"""竖屏版配乐编排：章节对齐小节 + 合成音效 + 滤波递进。

素材仍是两段 Lyria 原创配乐（assets/music/），117.45 BPM。
参照片配乐的做法（每 4 小节一次能量爆发、切镜踩拍）只作为节奏参考，不使用其音频。

做法：
1. 每章开头钉在小节第一拍（A 段从第一个底鼓起算；B 段乐句在第 14+16k 拍换段）。
2. 章内镜头按比例伸缩填满，再把每个切点对齐到最近的节拍。
3. 合成音效：章节前的上升音效、冲击重拍、切镜呼啸、错误清单的故障噪声与印章闷响、片尾 logo 的冲击与闪光。
4. 情绪递进：序章和少年时代用低通滤波让音乐发闷（像回忆），拜师后逐渐打开，1956 年完全打开。
   大章节前留一拍空白（drop gap）再砸下冲击。
输出：work/bgm_v.wav、work/timeline_v.json
"""
import json, math, os, sys
import numpy as np, soundfile as sf, librosa

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
from shots import SHOTS
from music import load, xfade, SR, BEAT, A_PHASE, B_PHASE, A_JUMP_FROM, A_JUMP_BACK

rng = np.random.default_rng(11)

# ---------------------------------------------------------------- 时间锚点
A = lambda k: A_PHASE + k * BEAT                     # A' 第 k 拍（A' 的网格与 A 连续）
B_OFF = A(360) - (B_PHASE + 2 * BEAT)               # B 段第 2 拍（小节第一拍）对齐 A' 第 360 拍
Bt = lambda k: B_OFF + B_PHASE + k * BEAT

ANCHOR = {
    "序章": 0.0,
    "少年生意经": A(0),          # 鼓点进入
    "拜师格雷厄姆": A(40),
    "合伙基金时代": A(88),       # 完全打开的第一次大落点
    "从烟蒂到伟大企业": A(160),
    "坚守与逆行": A(276),
    "股神的错误清单": Bt(2),     # 切到 B 段暗色间奏
    "落幕": Bt(78),
    "尾声": Bt(110),             # B 段起势
}
FINALE = Bt(166)                 # 片尾 logo 镜头开始
LOGO_HIT = Bt(174)               # logo 清晰浮现
TEXT_HIT = Bt(178)               # 金色文字随重拍出现
END = B_OFF + 96.6
DROPS = {"少年生意经", "合伙基金时代", "从烟蒂到伟大企业", "尾声"}   # 前面留空拍、配上升音效的大落点
ENERGY = {"序章": .3, "少年生意经": .5, "拜师格雷厄姆": .6, "合伙基金时代": .8, "从烟蒂到伟大企业": .9,
          "坚守与逆行": .9, "股神的错误清单": .65, "落幕": .4, "尾声": 1.0, "片尾": 1.0}


def chapters():
    ch, cur = [], ""
    for s in SHOTS:
        cur = s.get("ch") or cur
        ch.append(cur)
    return ch


def build_timeline():
    ch = chapters()
    names = list(ANCHOR)
    starts = [None] * len(SHOTS)
    grid = np.array([g for g in [A(k) for k in range(-40, 400)] if 0 <= g < B_OFF + B_PHASE + BEAT] +
                    [Bt(k) for k in range(0, 200) if Bt(k) < END])
    for n, name in enumerate(names):
        idx = [i for i, c in enumerate(ch) if c == name and SHOTS[i]["kind"] != "end"]
        t0 = ANCHOR[name]
        t1 = ANCHOR[names[n + 1]] if n + 1 < len(names) else FINALE
        durs = np.array([SHOTS[i]["dur"] for i in idx], float)
        cum = np.cumsum(np.r_[0, durs]) / durs.sum() * (t1 - t0) + t0
        for k, i in enumerate(idx):
            t = cum[k]
            starts[i] = t if k == 0 else float(grid[np.argmin(np.abs(grid - t))])
    starts[-1] = FINALE
    ends = starts[1:] + [END]
    shots = [dict(i=i, t0=float(starts[i]), t1=float(ends[i]), ch=ch[i] if SHOTS[i]["kind"] != "end" else "片尾") for i in range(len(SHOTS))]
    return shots, grid


# ---------------------------------------------------------------- 合成音效
def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR)).astype(np.float32)


def lp_noise(n, cutoff):
    x = rng.standard_normal(n).astype(np.float32)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, n).astype(np.float32) / 3


def bp_sweep_noise(n, f0, f1, q=0.6):
    """时变带通噪声（STFT 掩膜）"""
    x = rng.standard_normal(n + 2048).astype(np.float32)
    S = librosa.stft(x, n_fft=2048, hop_length=512)
    fr = librosa.fft_frequencies(sr=SR, n_fft=2048)[:, None]
    m = S.shape[1]
    fc = np.geomspace(f0, f1, m)[None, :]
    S *= np.exp(-0.5 * (np.log(fr / fc + 1e-9) / q) ** 2)
    y = librosa.istft(S, hop_length=512, length=n + 2048)[:n]
    return (y / (np.abs(y).max() + 1e-9)).astype(np.float32)


def impact(strength=1.0):
    n = int(2.4 * SR)
    t = np.arange(n) / SR
    f = 42 + 90 * np.exp(-t * 9)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.4)
    crack = lp_noise(n, 5000) * np.exp(-t * 28) * 1.2
    tail = lp_noise(n, 1800) * np.exp(-t * 2.2) * 0.35
    y = (boom * 1.0 + crack + tail) * strength
    return np.stack([y, y], 1).astype(np.float32)


def riser(dur):
    n = int(dur * SR)
    x = np.arange(n) / n
    nz = bp_sweep_noise(n, 400, 9000, 0.5) * x ** 2.2
    f = 180 + 1400 * x ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.18 * x ** 3
    y = (nz * 0.55 + tone)
    return np.stack([y * (0.9 + 0.1 * np.sin(x * 40)), y * (0.9 - 0.1 * np.sin(x * 40))], 1).astype(np.float32)


def whoosh(pan):
    n = int(0.55 * SR)
    x = np.arange(n) / n
    y = bp_sweep_noise(n, 3000, 500, 0.7) * np.sin(np.pi * x) ** 2
    l, r = (1 - pan) / 2 + 0.25, (1 + pan) / 2 + 0.25
    return np.stack([y * l, y * r], 1).astype(np.float32)


def glitch():
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    sq = np.sign(np.sin(2 * np.pi * 1300 * t)) * 0.25
    nz = rng.standard_normal(n) * 0.35
    gate = (np.floor(t * 70) % 2).astype(np.float32)
    y = (sq + nz) * gate * np.exp(-t * 12)
    y = np.round(y * 6) / 6
    return np.stack([y, -y * 0.8], 1).astype(np.float32)


def stamp():
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    thud = np.sin(2 * np.pi * (70 + 60 * np.exp(-t * 30)) * t) * np.exp(-t * 7)
    slap = lp_noise(n, 3500) * np.exp(-t * 60) * 1.4
    y = thud + slap
    return np.stack([y, y], 1).astype(np.float32)


def shimmer():
    n = int(3.2 * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f, a in [(1568, .5), (2349, .4), (3136, .35), (4699, .25), (6272, .18), (2093, .3)]:
        y += a * np.sin(2 * np.pi * f * t + rng.random() * 6) * np.exp(-t * (1.2 + f / 6000))
    y += bp_sweep_noise(n, 2500, 12000, 0.4) * np.exp(-t * 2.5) * 0.25
    y *= np.minimum(1, t / 0.01)
    return np.stack([y * 0.9, y], 1).astype(np.float32) * 0.6


def reverse_swell(dur):
    n = int(dur * SR)
    tail = lp_noise(n, 2500)
    x = np.arange(n) / n
    y = tail * x ** 3
    return np.stack([y, y], 1).astype(np.float32)


def place(buf, clip, t, gain):
    i = int(t * SR)
    if i < 0:
        clip, i = clip[-i:], 0
    j = min(len(buf), i + len(clip))
    if j > i:
        buf[i:j] += clip[:j - i] * gain


# ---------------------------------------------------------------- 滤波递进
def lowpass_auto(y, cutoff_at):
    out = np.zeros_like(y)
    fr = librosa.fft_frequencies(sr=SR, n_fft=4096)[:, None]
    for c in range(2):
        S = librosa.stft(y[:, c], n_fft=4096, hop_length=1024)
        tt = librosa.frames_to_time(np.arange(S.shape[1]), sr=SR, hop_length=1024)
        fc = np.array([cutoff_at(t) for t in tt])[None, :]
        S *= 1 / np.sqrt(1 + (fr / fc) ** 6)
        out[:, c] = librosa.istft(S, hop_length=1024, length=len(y))
    return out


def main():
    shots, grid = build_timeline()
    Am, Bm = load("a_main"), load("b_finale")
    j1, j0 = int(A(A_JUMP_FROM) * SR), int(A(A_JUMP_BACK) * SR)
    n = int(0.03 * SR)
    A2 = xfade(Am[:j1 + n], Am[j0:], 2 * n)
    total = END
    N = int(total * SR)
    mus = np.zeros((N + SR, 2), np.float32)
    # A' 在 B 进入时淡出
    fa0, fa1 = B_OFF - 1.0, B_OFF + 2.5
    na = min(len(A2), int(fa1 * SR))
    g = np.ones(na, np.float32)
    i0 = int(fa0 * SR)
    g[i0:na] = np.cos(np.linspace(0, 1, na - i0) * np.pi / 2) ** 2
    mus[:na] += A2[:na] * g[:, None]
    bo = int(B_OFF * SR)
    mus[bo:bo + len(Bm)] += Bm[:max(0, min(len(Bm), len(mus) - bo))]
    mus = mus[:N]
    # 滤波递进：序章 900Hz → 少年 2600Hz → 拜师从 5000Hz 渐开 → 合伙完全打开
    a = ANCHOR

    def cutoff(t):
        if t < a["少年生意经"] - 4.1:
            return 700
        if t < a["少年生意经"]:
            return 700 + (2600 - 700) * ((t - a["少年生意经"] + 4.1) / 4.1) ** 2
        if t < a["拜师格雷厄姆"]:
            return 2600
        if t < a["合伙基金时代"]:
            x = (t - a["拜师格雷厄姆"]) / (a["合伙基金时代"] - a["拜师格雷厄姆"])
            return 5000 * (16000 / 5000) ** (x ** 2)
        return 20000
    mus = lowpass_auto(mus, cutoff)
    # 空拍（drop gap）：大落点前最后一拍音乐压低
    gain = np.ones(N, np.float32)
    for name in DROPS:
        t = a[name]
        i0, i1 = int((t - BEAT) * SR), int(t * SR)
        gain[i0:i1] = np.minimum(gain[i0:i1], np.linspace(1, 0.12, i1 - i0) ** 0.5)
    # 片尾：logo 浮现前 1 拍收一下，最后 2.5s 淡出
    i0, i1 = int((LOGO_HIT - BEAT) * SR), int(LOGO_HIT * SR)
    gain[i0:i1] = np.minimum(gain[i0:i1], np.linspace(1, 0.25, i1 - i0))
    k = int(2.8 * SR)
    gain[-k:] *= np.linspace(1, 0, k) ** 1.6
    mus *= gain[:, None]

    sfx = np.zeros_like(mus)
    events = []
    names = list(ANCHOR)
    for name in names[1:]:
        t = a[name]
        big = name in DROPS
        if name != "股神的错误清单":
            place(sfx, riser(4 * BEAT if big else 2 * BEAT), t - (4 * BEAT if big else 2 * BEAT), 0.55 if big else 0.32)
        place(sfx, impact(1.0 if big else 0.6), t, 0.9 if big else 0.55)
        events.append(dict(t=t, type="impact", big=big))
    # 印章：错误清单首镜第 2 拍
    t_st = a["股神的错误清单"] + 2 * BEAT
    place(sfx, stamp(), t_st, 0.9)
    place(sfx, impact(0.5), t_st, 0.5)
    events.append(dict(t=t_st, type="stamp"))
    # 切镜呼啸 / 故障声
    pan = 1
    chstarts = set(round(x, 3) for x in a.values())
    for s in shots[1:]:
        t = s["t0"]
        if round(t, 3) in chstarts or s["ch"] == "片尾":
            continue
        if s["ch"] == "股神的错误清单":
            place(sfx, glitch(), t - 0.02, 0.32)
            events.append(dict(t=t, type="glitch"))
        elif ENERGY[s["ch"]] >= 0.6:
            place(sfx, whoosh(pan), t - 0.3, 0.16)
            pan = -pan
            events.append(dict(t=t, type="whoosh"))
    # 片尾 logo
    place(sfx, riser(LOGO_HIT - FINALE), FINALE, 0.5)
    place(sfx, reverse_swell(1.2), LOGO_HIT - 1.2, 0.4)
    place(sfx, impact(1.1), LOGO_HIT, 1.0)
    place(sfx, impact(0.7), TEXT_HIT, 0.6)
    place(sfx, shimmer(), TEXT_HIT, 0.75)
    events += [dict(t=LOGO_HIT, type="logo"), dict(t=TEXT_HIT, type="text")]

    out = mus * 0.82 + sfx
    out = np.tanh(out * 1.15) / np.tanh(1.15)
    out *= 0.93 / np.abs(out).max()
    os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
    sf.write(os.path.join(ROOT, "work", "bgm_v.wav"), out, SR)
    beats = grid[grid < total]
    downs = [A(k) for k in range(0, 400, 4) if A(k) < B_OFF] + [Bt(k) for k in range(2, 200, 4) if Bt(k) < total]
    json.dump(dict(total=total, b_offset=B_OFF, beats=beats.tolist(), downbeats=downs, anchors=a,
                   finale=dict(start=FINALE, logo=LOGO_HIT, text=TEXT_HIT, end=END),
                   energy=ENERGY, events=sorted(events, key=lambda e: e["t"]), shots=shots),
              open(os.path.join(ROOT, "work", "timeline_v.json"), "w"), ensure_ascii=False)
    d = [s["t1"] - s["t0"] for s in shots]
    print(f"总长 {total:.2f}s，B 段进入 {B_OFF:.2f}s；镜头 {min(d):.2f}–{max(d):.2f}s")
    for name in names:
        print(f"  {name:<10} {a[name]:7.2f}s")
    print(f"  片尾       {FINALE:7.2f}s  logo {LOGO_HIT:.2f}s  文字 {TEXT_HIT:.2f}s")


if __name__ == "__main__":
    main()
