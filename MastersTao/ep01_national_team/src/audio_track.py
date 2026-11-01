"""用授权曲目《Movement Proposition》（Kevin MacLeod，CC BY 4.0，126 BPM）按小节重新剪辑成全片配乐，
再叠加由数据驱动的低频冲击（不含任何音高元素，避免与原曲调性冲突）。输出 work/score.wav。

原曲小节网格（实测）：拍长 0.476198 s（126.0 BPM），首个强拍 1.470 s，逐拍误差 < 10 ms。
画面小节 b(k) 与原曲小节一一对应，只在强拍处拼接（12 ms 等功率交叉淡化），所以重拍、季度切换都踩在原曲鼓点上。
"""
import json, os, subprocess, sys
import numpy as np
import soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synth import SR, Bus, thump, boom, subdrop, taiko, kick, reverb, lp, hp
from timeline import BAR, HITS, QSCHED, DURATION, b

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "music", "Movement_Proposition.mp3")
SRC_IBI = 0.4761980798954863
SRC_T0 = 3.3748436788769838            # 线性拟合得到的某个强拍
SRC_BAR = SRC_IBI * 4
SRC_FIRST = SRC_T0 - np.floor(SRC_T0 / SRC_BAR) * SRC_BAR     # ≈ 1.470 s

# 画面小节 → 原曲小节（None = 静音）。原曲段落：0–16 / 31–48 满编律动；17–23 停顿式重击；
# 24–30 无镲的低沉段；49–55 去掉低音的悬疑段；56–59 重击蓄力；60–65 回归；66–70 终段高潮；71 尾音
EDIT = (
    [51, 52, 53, 58, 59]          # 0–4   钩子：悬疑无低音 → 两小节重击蓄力
    + [60, 61]                    # 5–6   标题：回归重拍
    + list(range(0, 8))           # 7–14  对决前半：满编律动
    + list(range(31, 41))         # 15–24 对决后半：律动 + 更亮的镲
    + [49, 50]                    # 25–26 今年以来：低音骤停
    + [17, 18]                    # 27–28 2026Q1：停顿式重击
    + [23]                        # 29    二季度前：停顿小节（吸气）
    + [24, 25, 26, 27]            # 30–33 断崖：低沉重型段
    + [28, 29]                    # 34–35 2026Q3：低沉延续
    + [41, 42, 43, 44]            # 36–39 今年以来·总结：满编（第一次高潮）
    + [8, 9, 10, 11, 12]          # 40–44 它们是谁·汇金
    + [13, 14, 15, 16]            # 45–48 它们是谁·证金
    + [56, 57]                    # 49–50 一句话区分：重击蓄力
    + list(range(60, 70))         # 51–60 三条启示：回归 → 终段高潮
    + [70, 71, 72]                # 61–63 片尾：终段最后一小节 + 自然尾音
)
assert len(EDIT) == 64, len(EDIT)


def load_src():
    tmp = os.path.join(HERE, "..", "work", "src_track.wav")
    if not os.path.exists(tmp):
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", SRC, "-ac", "2", "-ar", str(SR), tmp], check=True)
    x, sr = sf.read(tmp, dtype="float32")
    assert sr == SR
    return x.astype(np.float64)


def main(out):
    src = load_src()
    n = int((DURATION + 1) * SR)
    music = np.zeros((n, 2))
    xf = int(0.012 * SR)
    for k, sb in enumerate(EDIT):
        if sb is None:
            continue
        s0 = int(round((SRC_FIRST + sb * SRC_BAR) * SR))
        L = int(round(BAR * SR))
        seg = src[max(s0 - xf, 0): s0 + L + xf]
        if len(seg) < L + 2 * xf:
            seg = np.pad(seg, ((0, L + 2 * xf - len(seg)), (0, 0)))
        env = np.ones(len(seg))
        ramp = np.sin(np.linspace(0, np.pi / 2, 2 * xf)) ** 2
        env[:2 * xf] = ramp
        env[-2 * xf:] = ramp[::-1]
        d0 = int(round(b(k) * SR)) - xf
        a0 = max(d0, 0)
        seg = (seg * env[:, None])[a0 - d0:]
        music[a0:a0 + len(seg)] += seg[:n - a0]
    ref_rms = np.sqrt((src[int(SRC_FIRST * SR):int((SRC_FIRST + 70 * SRC_BAR) * SR)] ** 2).mean())

    # ---------------- 数据驱动的低频冲击（无音高）
    hits = Bus(DURATION + 2)
    st = json.load(open(os.path.join(HERE, "..", "data", "stats.json"), encoding="utf-8"))
    A_, B_ = st["duo"]["huijin_am"], st["duo"]["csf"]
    hit_times = {round(h[0], 3) for h in HITS}
    ducks = []
    for i, s, d, note in QSCHED:
        tt = b(s)
        if round(tt, 3) in hit_times or i == 0:
            continue
        m = max(abs(A_[i] - A_[i - 1]), abs(B_[i] - B_[i - 1]))
        sev = min(m / 40.0, 1.0)
        hits.add(thump(0.35, 120, 50), tt, 0.25 + 0.5 * sev)
        if m >= 5:
            hits.add(taiko(1.4), tt, 0.25 + 0.45 * sev)
        if m >= 12:
            hits.add(boom(3.0), tt, 0.4 + 0.4 * sev)
            hits.add(subdrop(1.8, 80, 26), tt, 0.35 + 0.4 * sev)
            ducks.append((tt, 0.35))
    for tt, strength, kind in HITS:
        if kind in ("boom", "drop"):
            hits.add(boom(4.0), tt, 0.8 * strength)
            hits.add(taiko(1.6), tt, 0.5 * strength)
            hits.add(kick(0.6, 175, 38, 0.4), tt, 0.6 * strength)
            if strength >= 0.8:
                ducks.append((tt, 0.2))
        if kind == "drop":
            hits.add(subdrop(3.0, 92, 22), tt, 1.0)
        if kind == "pulse":
            hits.add(thump(0.6, 110, 40), tt, 0.6 * strength + 0.2)
            hits.add(taiko(1.4), tt, 0.35 * strength)
    H = reverb(hits.x[:n], 3.0, 0.2, lpf=1600, seed=19)

    # 大重拍前「吸一口气」：原曲压低，重拍落下时恢复
    duck = np.ones(n)
    for ht, depth in ducks:
        i1 = int(ht * SR); i0 = max(i1 - int(0.2 * SR), 0)
        duck[i0:i1] = np.minimum(duck[i0:i1], 1 - (1 - depth) * np.linspace(0, 1, i1 - i0) ** 1.5)
    mix = music * duck[:, None] + H * 0.55
    mix = hp(mix, 22, 2)
    tt = np.arange(n) / SR
    mix *= np.clip(tt / 0.25, 0, 1)[:, None]
    mix *= np.clip(1 - (tt - (DURATION - 2.0)) / 2.0, 0, 1)[:, None] ** 1.3
    mix = mix[:int(DURATION * SR)]
    rms = np.sqrt((mix ** 2).mean())
    mix *= ref_rms / rms * 1.05
    mix = np.tanh(mix * 1.1) / 1.1
    mix *= min(1.0, 0.95 / np.abs(mix).max())
    sf.write(out, mix.astype(np.float32), SR, subtype="PCM_24")
    print("score ->", out, f"{len(mix) / SR:.2f}s rms={np.sqrt((mix ** 2).mean()):.3f} peak={np.abs(mix).max():.3f}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "work", "score.wav"))
