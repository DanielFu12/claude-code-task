"""汇金退出榜配乐：复用 EP01 的原创配乐素材（Google Lyria 3.5 生成，136 BPM，见 ep01_national_team/music/README.md），
按小节重新剪辑，并叠加由「当季退出市值」驱动的低频冲击。输出 work/score.wav。"""
import os, subprocess, sys
import numpy as np
import soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.join(HERE, "..", "..", "ep01_national_team", "src"))
from synth import SR, Bus, thump, boom, subdrop, taiko, kick, reverb, hp
from timeline import BAR, HITS, QSCHED, DURATION, BIG, MAIN_END, PRE_DROP, S, b

SRC = os.path.join(HERE, "..", "..", "ep01_national_team", "music", "score_lyria_A.mp3")
SRC_IBI = 0.4412112063749337
SRC_T0 = 0.07407129589861128
SRC_BAR = SRC_IBI * 4

# 画面小节 → 素材小节（素材段落见 EP01 audio_track.py 注释）
GROOVE = list(range(10, 16)) + list(range(18, 28)) + list(range(40, 48)) + list(range(48, 55))   # 31 小节，能量递增
EDIT = (
    [4, 5, 6, 7]                  # 0–3   钩子：前奏，最后一小节自带停顿
    + [8, 9]                      # 4–5   标题：主律动落下
    + GROOVE[:PRE_DROP - 6]       # 6–36  逐季：律动逐段加满
    + [32]                        # 37    2026Q2 前：上扬蓄力
    + [33, 34, 35, 38, 39, 42]    # 38–43 2026Q2：重低音段（倒数揭晓）
    + [36, 37]                    # 44–45 2026Q3：较轻
    + [72, 73, 74, 75]            # 46–49 总结：终段高潮
    + [88, 89, 90]                # 50–52 片尾：最后一击 + 尾音
)
assert len(EDIT) == MAIN_END + 7, (len(EDIT), MAIN_END + 7)


def main(out):
    tmp = os.path.join(HERE, "..", "work", "src_track.wav")
    if not os.path.exists(tmp):
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", SRC, "-ac", "2", "-ar", str(SR), tmp], check=True)
    src, sr = sf.read(tmp, dtype="float32"); src = src.astype(np.float64)
    n = int((DURATION + 1) * SR)
    music = np.zeros((n, 2)); xf = int(0.012 * SR)
    ramp = np.sin(np.linspace(0, np.pi / 2, 2 * xf)) ** 2
    for k, sb in enumerate(EDIT):
        s0 = int(round((SRC_T0 + sb * SRC_BAR) * SR)); L = int(round(BAR * SR))
        seg = src[max(s0 - xf, 0): s0 + L + xf]
        if len(seg) < L + 2 * xf: seg = np.pad(seg, ((0, L + 2 * xf - len(seg)), (0, 0)))
        env = np.ones(len(seg)); env[:2 * xf] = ramp; env[-2 * xf:] = ramp[::-1]
        d0 = int(round(b(k) * SR)) - xf; a0 = max(d0, 0)
        seg = (seg * env[:, None])[a0 - d0:]
        music[a0:a0 + len(seg)] += seg[:n - a0]
    ref = np.sqrt((src[int(SRC_T0 * SR):int((SRC_T0 + 88 * SRC_BAR) * SR)] ** 2).mean())

    hits = Bus(DURATION + 2); ducks = []
    hit_times = {round(h[0], 3) for h in HITS}
    for i, s, d in QSCHED:
        tt = b(s)
        if i == 0 or round(tt, 3) in hit_times: continue
        cap = S["steps"][i]["exit_cap_yi"]
        sev = min(cap / 60.0, 1.0)
        hits.add(thump(0.35, 120, 50), tt, 0.25 + 0.5 * sev)
        if cap >= 5: hits.add(taiko(1.4), tt, 0.25 + 0.45 * sev)
        if cap >= 20:
            hits.add(boom(3.0), tt, 0.4 + 0.4 * sev); hits.add(subdrop(1.8, 80, 26), tt, 0.35 + 0.4 * sev)
            ducks.append((tt, 0.35))
    for tt, st, kind in HITS:
        if kind in ("boom", "drop"):
            hits.add(boom(4.0), tt, 0.8 * st); hits.add(taiko(1.6), tt, 0.5 * st); hits.add(kick(0.6, 175, 38, 0.4), tt, 0.6 * st)
            if st >= 0.8: ducks.append((tt, 0.2))
        if kind == "drop":
            hits.add(subdrop(3.0, 92, 22), tt, 1.0)
    # 2026Q2 倒数揭晓：第 10 → 2 名每拍一声低频脉冲，第 1 名落在重拍（HITS）
    t0 = b(QSCHED[BIG][1])
    for j in range(9):
        hits.add(thump(0.3, 110, 48), t0 + j * (BAR / 4), 0.3 + 0.04 * j)
    H = reverb(hits.x[:n], 3.0, 0.2, lpf=1600, seed=19)
    duck = np.ones(n)
    for ht, depth in ducks:
        i1 = int(ht * SR); i0 = max(i1 - int(0.2 * SR), 0)
        duck[i0:i1] = np.minimum(duck[i0:i1], 1 - (1 - depth) * np.linspace(0, 1, i1 - i0) ** 1.5)
    mix = music * duck[:, None] + H * 0.55
    mix = hp(mix, 22, 2)
    tt = np.arange(n) / SR
    mix *= np.clip(tt / 0.02, 0, 1)[:, None]
    mix *= np.clip(1 - (tt - (DURATION - 1.5)) / 1.5, 0, 1)[:, None] ** 1.3
    mix = mix[:int(DURATION * SR)]
    mix *= ref / np.sqrt((mix ** 2).mean()) * 1.05
    mix = np.tanh(mix * 1.1) / 1.1
    mix *= min(1.0, 0.95 / np.abs(mix).max())
    sf.write(out, mix.astype(np.float32), SR, subtype="PCM_24")
    print("score ->", out, f"{len(mix) / SR:.2f}s")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "work", "score.wav"))
