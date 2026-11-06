"""竖屏版配乐（使用参照片配乐，用户已获使用授权）：延长 + 重拍卡点 + 情绪递进 + 阅读节奏。

原曲：assets/music/ref_bgm.m4a（取自参照片音轨，单声道 AAC 48kbps，3:33，约 84.7 BPM）。
特点：约每 4–7 秒一次明显的重拍（比周围高约 9 dB），199s 后进入尾奏。

做法：
1. 延长：按 SEGS 拼接原曲片段，每个接缝两边都是重拍，全曲约 5:55。
2. 阅读节奏：每个镜头按字幕字数估算阅读时长（每秒约 8 字，至少 3.5 秒；地图、数据动画、引语卡另加时间）。
   各章按阅读需要分配时长，章节开头吸附到最近的重拍；章内按需要比例分配，
   其余重拍就近吸附到切镜点（不能让镜头短于阅读需要），其余切点对齐拍点。
3. 情绪递进（时变低通 + 增益）：序章发闷 → 少年时代偏暖 → 拜师逐渐打开 → 1956 年完全打开；
   错误清单压暗收窄 → 落幕慢慢打开 → 尾声全开。大落点前上升音效 + 半拍空白。
4. 合成音效：章节冲击、重拍切镜轻冲击、切镜呼啸、错误清单故障声与印章闷响、片尾 logo 冲击与闪光。
5. 正片中途关注语时刻：开始约 50s 后第一次，之后每隔约 150s 一次（距收尾 ≥90s），收尾一次在片尾前约 25s。
输出：work/bgm_r.wav、work/timeline_r.json（render_v.py 用 TL=r 读取）
"""
import json, os, subprocess, sys
import numpy as np, soundfile as sf, librosa

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
from shots import SHOTS
from music_v import impact, riser, whoosh, glitch, stamp, shimmer, reverse_swell, place, lowpass_auto, chapters

SR = 44100
SRC = os.path.join(ROOT, "assets", "music", "ref_bgm.m4a")
SEGS = [(0.0, 143.37), (59.26, 171.93), (111.27, 213.2)]     # 原曲片段，接缝都在重拍上
HITS_SRC = [1.58, 6.58, 12.21, 16.5, 21.57, 26.47, 32.97, 39.32, 43.6, 48.59, 55.08, 59.26, 64.25, 68.52, 76.45,
            82.11, 87.16, 91.35, 95.65, 100.58, 107.0, 111.27, 117.02, 124.12, 128.49, 133.4, 139.11, 143.37,
            148.46, 153.38, 159.16, 166.22, 171.93, 176.19, 181.96, 188.1, 192.3, 198.76]
SEG_OFF, _o = [], 0.0
for _a, _b in SEGS:
    SEG_OFF.append(_o - _a)
    _o += _b - _a


def mapt(t_src, seg):
    return t_src + SEG_OFF[seg]


HITS = sorted({round(mapt(h, k), 3) for k, (a_, b_) in enumerate(SEGS) for h in HITS_SRC if a_ - 0.01 <= h < b_ - 0.5})
FINALE = mapt(192.3, len(SEGS) - 1)       # 粒子汇聚开始
LOGO_HIT = mapt(198.76, len(SEGS) - 1)    # 最后一个大重拍：logo 浮现
CH_NAMES = ["序章", "少年生意经", "拜师格雷厄姆", "合伙基金时代", "从烟蒂到伟大企业", "坚守与逆行", "股神的错误清单", "落幕", "尾声"]
DROPS = {"少年生意经", "合伙基金时代", "从烟蒂到伟大企业", "尾声"}
ENERGY = {"序章": .35, "少年生意经": .6, "拜师格雷厄姆": .65, "合伙基金时代": .85, "从烟蒂到伟大企业": .95,
          "坚守与逆行": .95, "股神的错误清单": .65, "落幕": .45, "尾声": 1.0, "片尾": 1.0}
READ_RATE, READ_BASE, READ_MIN = 8.0, 1.0, 3.5
BEAT = 0.708


def need(s):
    """按字幕字数估算阅读所需时长（秒）"""
    if s["kind"] == "title":
        return 5.0
    n = sum(len(l.replace("【", "").replace("】", "")) for l in s["lines"])
    d = READ_BASE + n / READ_RATE
    if s["kind"] == "map" or (s["kind"] == "data" and s.get("fx")):
        d += 0.8
    if s["kind"] in ("quote", "card"):
        d += 0.5
    return max(READ_MIN, d)


def load_src():
    wav = os.path.join(ROOT, "work", "ref_bgm.wav")
    if not os.path.exists(wav):
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", SRC, "-ar", str(SR), "-ac", "2", wav], check=True)
    y, _ = sf.read(wav, dtype="float32")
    return y


def beats_of(y):
    m = librosa.resample(librosa.to_mono(y.T), orig_sr=SR, target_sr=22050)
    o = librosa.onset.onset_strength(y=m, sr=22050, hop_length=256)
    _, b = librosa.beat.beat_track(onset_envelope=o, sr=22050, hop_length=256, tightness=300)
    return librosa.frames_to_time(b, sr=22050, hop_length=256)


def build_timeline(beats, total):
    ch = chapters()
    needs = [need(s) for s in SHOTS]
    body = [i for i in range(len(SHOTS)) if SHOTS[i]["kind"] != "end"]
    ch_need = [sum(needs[i] for i in body if ch[i] == nm) for nm in CH_NAMES]
    scale = FINALE / sum(ch_need)
    # 在重拍里整体挑选各章起点：让每章实际时长尽量贴近阅读需要（动态规划）
    H = [h for h in HITS if 8 < h < FINALE - 10]
    K = len(CH_NAMES)
    INF = 1e18
    cost = lambda span, k: ((span - ch_need[k] * scale) / ch_need[k]) ** 2 * (4 if span < ch_need[k] * scale else 1)
    # dp[k][j]：第 k 章（k>=1）起点取 H[j] 时，前 k 章的最小代价
    dp = [[INF] * len(H) for _ in range(K)]
    back = [[-1] * len(H) for _ in range(K)]
    for j, h in enumerate(H):
        dp[1][j] = cost(h - 0.0, 0)
    for k in range(2, K):
        for j, h in enumerate(H):
            for i in range(j):
                if dp[k - 1][i] < INF and h - H[i] > 8:
                    c = dp[k - 1][i] + cost(h - H[i], k - 1)
                    if c < dp[k][j]:
                        dp[k][j], back[k][j] = c, i
    best = min(range(len(H)), key=lambda j: dp[K - 1][j] + cost(FINALE - H[j], K - 1) if dp[K - 1][j] < INF else INF)
    idxs = [best]
    for k in range(K - 1, 1, -1):
        idxs.append(back[k][idxs[-1]])
    idxs = idxs[::-1]
    anchor = {CH_NAMES[0]: 0.0}
    for k, j in enumerate(idxs, 1):
        anchor[CH_NAMES[k]] = H[j]
    starts = [None] * len(SHOTS)
    hit_cuts = set()
    for k, nm in enumerate(CH_NAMES):
        idx = [i for i in body if ch[i] == nm]
        t0 = anchor[nm]
        t1 = anchor[CH_NAMES[k + 1]] if k + 1 < len(CH_NAMES) else FINALE
        nd = np.array([needs[i] for i in idx])
        sc = (t1 - t0) / nd.sum()                      # 本章实际伸缩比
        cum = np.cumsum(np.r_[0, nd]) * sc + t0
        bounds = list(cum[1:-1])
        floor = [max(3.0, needs[i] * min(1.0, sc) * 0.88) for i in idx]
        for h in [h for h in HITS if t0 + 1.0 < h < t1 - 1.0]:
            if not bounds:
                break
            j = int(np.argmin([abs(b - h) for b in bounds]))
            if abs(bounds[j] - h) > 1.3:
                continue
            old = bounds[j]
            bounds[j] = h
            d = np.diff([t0] + bounds + [t1])
            if all(d_ >= f_ for d_, f_ in zip(d, floor)):
                hit_cuts.add(idx[j + 1])
            else:
                bounds[j] = old
        for j, b in enumerate(bounds):
            if idx[j + 1] not in hit_cuts:
                bounds[j] = float(beats[np.argmin(np.abs(beats - b))])
        starts[idx[0]] = t0
        for j, b in enumerate(bounds):
            starts[idx[j + 1]] = float(b)
    starts[-1] = FINALE
    ends = starts[1:] + [total]
    shots = [dict(i=i, t0=float(starts[i]), t1=float(ends[i]), ch=ch[i] if SHOTS[i]["kind"] != "end" else "片尾",
                  hit=i in hit_cuts, need=round(needs[i], 2)) for i in range(len(SHOTS))]
    return anchor, shots, hit_cuts


def main():
    os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
    y = load_src()
    # 1) 拼接延长：接缝在重拍前 20ms 交叉
    n = int(0.02 * SR)
    tt = np.linspace(0, 1, n, dtype=np.float32)[:, None]
    mus = y[int(SEGS[0][0] * SR):int(SEGS[0][1] * SR) - n].copy()
    for a_, b_ in SEGS[1:]:
        seg = y[int(a_ * SR) - n:int(b_ * SR) - n]
        mus = np.concatenate([mus[:-n], mus[-n:] * np.cos(tt * np.pi / 2) + seg[:n] * np.sin(tt * np.pi / 2), seg[n:]])
    total = LOGO_HIT + 11.0
    N = int(total * SR)
    if len(mus) < N:
        mus = np.concatenate([mus, np.zeros((N - len(mus), 2), np.float32)])
    mus = mus[:N]
    bsrc = beats_of(y)
    beats = np.array(sorted({round(mapt(b_, k), 4) for k, (a_, e_) in enumerate(SEGS) for b_ in bsrc if a_ - 0.05 <= b_ < e_ - 0.05}))
    beats = beats[beats < total]
    a, shots, hit_cuts = build_timeline(beats, total)
    # 2) 情绪递进
    E0, E1 = a["股神的错误清单"], a["落幕"]

    def cutoff(t):
        if t < a["少年生意经"] - 3:
            return 900
        if t < a["少年生意经"]:
            return 900 + (3200 - 900) * ((t - a["少年生意经"] + 3) / 3) ** 2
        if t < a["拜师格雷厄姆"]:
            return 3200
        if t < a["合伙基金时代"]:
            x = (t - a["拜师格雷厄姆"]) / (a["合伙基金时代"] - a["拜师格雷厄姆"])
            return 5500 * (18000 / 5500) ** (x ** 2)
        if E0 <= t < E1:
            return 1500 + 600 * np.exp(-(t - E0) / 0.6)
        if E1 <= t < a["尾声"]:
            x = (t - E1) / (a["尾声"] - E1)
            return 1800 * (18000 / 1800) ** (x ** 2)
        return 20000
    mus = lowpass_auto(mus, cutoff)
    gain = np.ones(N, np.float32)
    gain[int(E0 * SR):int(E1 * SR)] = 0.72
    for name in DROPS:
        t = a[name]
        j0, j1 = int((t - BEAT * 0.6) * SR), int((t - 0.02) * SR)
        gain[j0:j1] = np.minimum(gain[j0:j1], np.linspace(1, 0.15, j1 - j0) ** 0.6)
    k = int(4.0 * SR)
    gain[-k:] *= np.linspace(1, 0, k) ** 1.4
    mus *= gain[:, None]
    # 3) 合成音效
    sfx = np.zeros_like(mus)
    events = []
    for name in CH_NAMES[1:]:
        t = a[name]
        big = name in DROPS
        if name != "股神的错误清单":
            L = 4 * BEAT if big else 2 * BEAT
            place(sfx, riser(L), t - L, 0.45 if big else 0.25)
        place(sfx, impact(1.0 if big else 0.6), t, 0.75 if big else 0.45)
        events.append(dict(t=t, type="impact", big=big))
    t_st = a["股神的错误清单"] + 2 * BEAT
    place(sfx, stamp(), t_st, 0.9)
    place(sfx, impact(0.5), t_st, 0.45)
    events.append(dict(t=t_st, type="stamp"))
    chs = set(round(x, 3) for x in a.values())
    pan = 1
    for s in shots[1:]:
        t = s["t0"]
        if round(t, 3) in chs or s["ch"] == "片尾":
            continue
        if s["ch"] == "股神的错误清单":
            place(sfx, glitch(), t - 0.02, 0.3)
            events.append(dict(t=t, type="glitch"))
        elif s["hit"]:
            place(sfx, impact(0.45), t, 0.3)
            events.append(dict(t=t, type="hit"))
        elif ENERGY[s["ch"]] >= 0.6:
            place(sfx, whoosh(pan), t - 0.3, 0.12)
            pan = -pan
            events.append(dict(t=t, type="whoosh"))
    TEXT_HIT = LOGO_HIT + 4 * BEAT
    place(sfx, riser(LOGO_HIT - FINALE), FINALE, 0.4)
    place(sfx, reverse_swell(1.4), LOGO_HIT - 1.4, 0.35)
    place(sfx, impact(1.1), LOGO_HIT, 0.8)
    place(sfx, impact(0.8), TEXT_HIT, 0.6)
    place(sfx, shimmer(), TEXT_HIT, 0.7)
    events += [dict(t=LOGO_HIT, type="logo"), dict(t=TEXT_HIT, type="text")]
    out = mus * 0.9 + sfx
    out = np.tanh(out * 1.1) / np.tanh(1.1)
    out *= 0.93 / np.abs(out).max()
    sf.write(os.path.join(ROOT, "work", "bgm_r.wav"), out, SR)
    # 4) 关注语时刻（取镜头开始后 0.8s，避开切镜瞬间）
    st = [s["t0"] for s in shots]
    first = lambda x: next(v for v in st if v >= x) + 0.8
    fl = [first(50)]
    closing = first(FINALE - 28)
    while fl[-1] + 150 < closing - 90 and first(fl[-1] + 150) < closing - 90:
        fl.append(first(fl[-1] + 150))
    follows = [dict(t=x, tagged=False) for x in fl] + [dict(t=closing, tagged=True)]
    json.dump(dict(total=total, beats=beats.tolist(), downbeats=[h for h in HITS if h < total], hits=HITS, anchors=a,
                   finale=dict(start=FINALE, logo=LOGO_HIT, text=TEXT_HIT, end=total),
                   energy=ENERGY, events=sorted(events, key=lambda e: e["t"]), follows=follows, shots=shots),
              open(os.path.join(ROOT, "work", "timeline_r.json"), "w"), ensure_ascii=False)
    d = [s["t1"] - s["t0"] for s in shots[:-1]]
    short = [(s["i"] + 1, round(s["t1"] - s["t0"], 1), s["need"]) for s in shots[:-1] if s["t1"] - s["t0"] < s["need"] * 0.85]
    print(f"总长 {total:.2f}s；镜头 {min(d):.2f}–{max(d):.2f}s（平均 {np.mean(d):.2f}s）；踩在重拍上的切镜 {len(hit_cuts)} 个")
    print("  明显短于阅读需要的镜头：", short or "无")
    for name in CH_NAMES:
        print(f"  {name:<10} {a[name]:7.2f}s")
    print(f"  片尾       {FINALE:7.2f}s  logo {LOGO_HIT:.2f}s  文字 {TEXT_HIT:.2f}s")
    print("  关注语", [round(f["t"], 1) for f in follows])


if __name__ == "__main__":
    main()
