"""竖屏版配乐（使用参照片配乐，用户已获使用授权）：延长 + 重拍卡点 + 情绪递进。

原曲：assets/music/ref_bgm.m4a（取自参照片音轨，单声道 AAC 48kbps，3:33，约 84.7 BPM）。
特点：约每 4–7 秒一次明显的重拍（比周围高约 9 dB），199s 后进入尾奏。

做法：
1. 延长：在 143.37s 的重拍处接回 59.26s 的重拍继续播放，接缝被重拍掩盖，全曲约 4:57。
2. 章节开头全部钉在重拍上；章内其余重拍就近吸附到切镜点（±1.3s 内），这些切镜在画面上用强转场。
3. 其余切点对齐到逐拍追踪出的拍点。
4. 情绪递进（时变低通 + 增益）：序章发闷 → 少年时代偏暖 → 拜师逐渐打开 → 1956 年完全打开；
   错误清单压暗收窄 → 落幕慢慢打开 → 尾声全开。大落点前上升音效 + 留半拍空白。
5. 叠加合成音效：章节冲击、切镜呼啸、错误清单故障声与印章闷响、片尾 logo 冲击与闪光。
输出：work/bgm_r.wav、work/timeline_r.json（与 timeline_v.json 同结构，render_v.py 用 TL=r 读取）
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
CUT_FROM, CUT_TO = 143.37, 59.26          # 接回点（两边都是重拍）
HITS_SRC = [1.58, 6.58, 12.21, 16.5, 21.57, 26.47, 32.97, 39.32, 43.6, 48.59, 55.08, 59.26, 64.25, 68.52, 76.45,
            82.11, 87.16, 91.35, 95.65, 100.58, 107.0, 111.27, 117.02, 124.12, 128.49, 133.4, 139.11, 143.37,
            148.46, 153.38, 159.16, 166.22, 171.93, 176.19, 181.96, 188.1, 192.3, 198.76]
OFF = CUT_FROM - CUT_TO


def ext(t):
    """原曲时间 → 延长后时间（接回点之后的部分）"""
    return t + OFF


HITS = [h for h in HITS_SRC if h <= CUT_FROM] + [ext(h) for h in HITS_SRC if h > CUT_TO + 1]
ANCHOR = {
    "序章": 0.0,
    "少年生意经": 16.5,
    "拜师格雷厄姆": 39.32,
    "合伙基金时代": 59.26,
    "从烟蒂到伟大企业": 95.65,
    "坚守与逆行": ext(68.52),         # 152.63
    "股神的错误清单": ext(111.27),    # 195.38
    "落幕": ext(153.38),              # 237.49
    "尾声": ext(171.93),              # 256.04
}
FINALE = ext(192.3)                   # 276.41：粒子汇聚开始
LOGO_HIT = ext(198.76)                # 282.87：最后一个大重拍，logo 浮现
DROPS = {"少年生意经", "合伙基金时代", "从烟蒂到伟大企业", "尾声"}
ENERGY = {"序章": .35, "少年生意经": .6, "拜师格雷厄姆": .65, "合伙基金时代": .85, "从烟蒂到伟大企业": .95,
          "坚守与逆行": .95, "股神的错误清单": .65, "落幕": .45, "尾声": 1.0, "片尾": 1.0}


def load_src():
    wav = os.path.join(ROOT, "work", "ref_bgm.wav")
    if not os.path.exists(wav):
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", SRC, "-ar", str(SR), "-ac", "2", wav], check=True)
    y, _ = sf.read(wav, dtype="float32")
    return y


def beats_of(y):
    m = librosa.to_mono(y.T)
    m = librosa.resample(m, orig_sr=SR, target_sr=22050)
    o = librosa.onset.onset_strength(y=m, sr=22050, hop_length=256)
    _, b = librosa.beat.beat_track(onset_envelope=o, sr=22050, hop_length=256, tightness=300)
    return librosa.frames_to_time(b, sr=22050, hop_length=256)


def main():
    os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
    y = load_src()
    beat_len = 0.708
    # 1) 延长：A = [0, CUT_FROM) + B = [CUT_TO, end)，在重拍前 20ms 交叉
    n = int(0.02 * SR)
    i1, i0 = int(CUT_FROM * SR) - n, int(CUT_TO * SR) - n
    t = np.linspace(0, 1, 2 * n, dtype=np.float32)[:, None]
    mus = np.concatenate([y[:i1 - n], y[i1 - n:i1 + n] * np.cos(t * np.pi / 2) + y[i0 - n:i0 + n] * np.sin(t * np.pi / 2), y[i0 + n:]])
    total = LOGO_HIT + 11.0
    N = int(total * SR)
    if len(mus) < N:
        mus = np.concatenate([mus, np.zeros((N - len(mus), 2), np.float32)])
    mus = mus[:N]
    # 拍点：原曲拍点映射到延长后
    bsrc = beats_of(y)
    beats = np.array(sorted([b for b in bsrc if b < CUT_FROM - 0.05] + [ext(b) for b in bsrc if b >= CUT_TO - 0.05]))
    beats = beats[beats < total]
    # 2) 时间线
    ch = chapters()
    names = list(ANCHOR)
    starts = [None] * len(SHOTS)
    hit_cuts = set()
    for k, name in enumerate(names):
        idx = [i for i, c in enumerate(ch) if c == name and SHOTS[i]["kind"] != "end"]
        t0 = ANCHOR[name]
        t1 = ANCHOR[names[k + 1]] if k + 1 < len(names) else FINALE
        durs = np.array([SHOTS[i]["dur"] for i in idx], float)
        cum = np.cumsum(np.r_[0, durs]) / durs.sum() * (t1 - t0) + t0
        bounds = list(cum[1:-1])
        # 章内重拍吸附到最近的切点
        for h in [h for h in HITS if t0 + 1.0 < h < t1 - 1.0]:
            j = int(np.argmin([abs(b - h) for b in bounds])) if bounds else -1
            if j >= 0 and abs(bounds[j] - h) < 1.3:
                lo = (bounds[j - 1] if j > 0 else t0) + 1.6
                hi = (bounds[j + 1] if j + 1 < len(bounds) else t1) - 1.6
                if lo <= h <= hi:
                    old = bounds[j]
                    bounds[j] = h
                    seq = [t0] + bounds + [t1]
                    if min(np.diff(seq)) < 2.2:     # 吸附后不能让任何镜头短于 2.2s
                        bounds[j] = old
                    else:
                        hit_cuts.add(idx[j + 1])
        for j, b in enumerate(bounds):
            if idx[j + 1] not in hit_cuts:
                bounds[j] = float(beats[np.argmin(np.abs(beats - b))])
        starts[idx[0]] = t0
        for j, b in enumerate(bounds):
            starts[idx[j + 1]] = float(b)
    starts[-1] = FINALE
    ends = starts[1:] + [total]
    shots = [dict(i=i, t0=float(starts[i]), t1=float(ends[i]), ch=ch[i] if SHOTS[i]["kind"] != "end" else "片尾",
                  hit=i in hit_cuts) for i in range(len(SHOTS))]
    # 3) 情绪递进：时变低通
    a = ANCHOR
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
        if E0 <= t < E1:                          # 错误清单：收窄压暗
            return 1500 + 600 * np.exp(-(t - E0) / 0.6)
        if E1 <= t < a["尾声"]:                   # 落幕：慢慢打开
            x = (t - E1) / (a["尾声"] - E1)
            return 1800 * (18000 / 1800) ** (x ** 2)
        return 20000
    mus = lowpass_auto(mus, cutoff)
    gain = np.ones(N, np.float32)
    i0, i1 = int(E0 * SR), int(E1 * SR)
    gain[i0:i1] = 0.72                            # 错误清单整体压低约 3 dB
    for name in DROPS:                            # 大落点前半拍空白
        tt = a[name]
        j0, j1 = int((tt - beat_len * 0.6) * SR), int((tt - 0.02) * SR)
        gain[j0:j1] = np.minimum(gain[j0:j1], np.linspace(1, 0.15, j1 - j0) ** 0.6)
    k = int(4.0 * SR)                             # 尾奏淡出
    gain[-k:] *= np.linspace(1, 0, k) ** 1.4
    mus *= gain[:, None]
    # 4) 合成音效
    sfx = np.zeros_like(mus)
    events = []
    for name in names[1:]:
        tt = a[name]
        big = name in DROPS
        if name != "股神的错误清单":
            L = 4 * beat_len if big else 2 * beat_len
            place(sfx, riser(L), tt - L, 0.45 if big else 0.25)
        place(sfx, impact(1.0 if big else 0.6), tt, 0.75 if big else 0.45)
        events.append(dict(t=tt, type="impact", big=big))
    t_st = a["股神的错误清单"] + 2 * beat_len
    place(sfx, stamp(), t_st, 0.9)
    place(sfx, impact(0.5), t_st, 0.45)
    events.append(dict(t=t_st, type="stamp"))
    chs = set(round(x, 3) for x in a.values())
    pan = 1
    for s in shots[1:]:
        tt = s["t0"]
        if round(tt, 3) in chs or s["ch"] == "片尾":
            continue
        if s["ch"] == "股神的错误清单":
            place(sfx, glitch(), tt - 0.02, 0.3)
            events.append(dict(t=tt, type="glitch"))
        elif s["hit"]:
            place(sfx, impact(0.45), tt, 0.3)
            events.append(dict(t=tt, type="hit"))
        elif ENERGY[s["ch"]] >= 0.6:
            place(sfx, whoosh(pan), tt - 0.3, 0.12)
            pan = -pan
            events.append(dict(t=tt, type="whoosh"))
    TEXT_HIT = LOGO_HIT + 4 * beat_len
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
    json.dump(dict(total=total, beats=beats.tolist(), downbeats=[h for h in HITS if h < total], hits=HITS, anchors=a,
                   finale=dict(start=FINALE, logo=LOGO_HIT, text=TEXT_HIT, end=total),
                   energy=ENERGY, events=sorted(events, key=lambda e: e["t"]), shots=shots),
              open(os.path.join(ROOT, "work", "timeline_r.json"), "w"), ensure_ascii=False)
    d = [s["t1"] - s["t0"] for s in shots]
    print(f"总长 {total:.2f}s；镜头 {min(d):.2f}–{max(d):.2f}s；踩在重拍上的切镜 {len(hit_cuts)} 个")
    for name in names:
        print(f"  {name:<10} {a[name]:7.2f}s")
    print(f"  片尾       {FINALE:7.2f}s  logo {LOGO_HIT:.2f}s  文字 {TEXT_HIT:.2f}s")


if __name__ == "__main__":
    main()
