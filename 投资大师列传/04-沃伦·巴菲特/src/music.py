"""配乐拼接 + 镜头时间对齐到节拍。

两段音乐都由 Lyria 生成（assets/music/），117.45 BPM：
  A 段 a_main.mp3：主曲，2:58。中间按节拍重复 64 拍（16 小节），延长到约 3:30。
  B 段 b_finale.mp3：暗色间奏 → 起势 → 62.95s 高潮 → 收尾，1:38。
B 段的高潮对准「尾声」第一个镜头；B 段进入时 A 段淡出。
输出：work/bgm.wav、work/timeline.json（每个镜头对齐到节拍后的起止时间）。
"""
import json, os, subprocess, sys
import numpy as np, soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
from shots import SHOTS

SR = 44100
BEAT = 0.510839
A_PHASE, B_PHASE = 15.3716, 0.1161      # 两段各自第一拍的时间
A_JUMP_FROM, A_JUMP_BACK = 244, 180     # A 段在第 244 拍跳回第 180 拍（64 拍）
B_CLIMAX = B_PHASE + 123 * BEAT         # 62.95s


def load(name):
    wav = os.path.join(ROOT, "work", name + ".wav")
    if not os.path.exists(wav):
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(ROOT, "assets/music", name + ".mp3"),
                        "-ar", str(SR), "-ac", "2", wav], check=True)
    y, _ = sf.read(wav, dtype="float32")
    return y


def xfade(a, b, n):
    t = np.linspace(0, 1, n, dtype=np.float32)[:, None]
    return np.concatenate([a[:-n], a[-n:] * np.cos(t * np.pi / 2) + b[:n] * np.sin(t * np.pi / 2), b[n:]])


def main():
    os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
    A, B = load("a_main"), load("b_finale")
    # A'：节拍对齐的循环
    j1 = int((A_PHASE + A_JUMP_FROM * BEAT) * SR)
    j0 = int((A_PHASE + A_JUMP_BACK * BEAT) * SR)
    n = int(0.03 * SR)
    A2 = xfade(A[:j1 + n], A[j0:], 2 * n)
    # 镜头起点（按脚本时长）
    starts = np.cumsum([0] + [s["dur"] for s in SHOTS])
    ending = next(i for i, s in enumerate(SHOTS) if s.get("ch") == "尾声")
    off = starts[ending] - B_CLIMAX                      # B 段进入时间
    total = off + len(B) / SR
    out = np.zeros((int(total * SR) + SR, 2), np.float32)
    # A' 在 B 进入前 1s 开始 4.5s 淡出
    fa0, fa1 = off - 1.0, off + 3.5
    na = min(len(A2), int(fa1 * SR))
    g = np.ones(na, np.float32)
    i0 = int(fa0 * SR)
    g[i0:na] = np.cos(np.linspace(0, 1, na - i0) * np.pi / 2) ** 2
    out[:na] += A2[:na] * g[:, None]
    bo = int(off * SR)
    out[bo:bo + len(B)] += B
    out = out[:int(total * SR)]
    out *= 0.89 / max(1e-6, np.abs(out).max())
    sf.write(os.path.join(ROOT, "work", "bgm.wav"), out, SR)
    # 节拍网格：B 进入前用 A 的网格，之后用 B 的网格
    grid = [A_PHASE + k * BEAT for k in range(-40, 1000) if A_PHASE + k * BEAT < off]
    grid = [g for g in grid if g >= 0] + [off + B_PHASE + k * BEAT for k in range(0, 1000) if off + B_PHASE + k * BEAT < total]
    grid = np.array(grid)
    snap = [0.0] + [float(grid[np.argmin(np.abs(grid - t))]) for t in starts[1:-1]] + [float(total)]
    tl = dict(total=float(total), b_offset=float(off), beats=grid.tolist(),
              shots=[dict(i=i, t0=snap[i], t1=snap[i + 1]) for i in range(len(SHOTS))])
    json.dump(tl, open(os.path.join(ROOT, "work", "timeline.json"), "w"))
    print(f"bgm {total:.2f}s，B 段进入 {off:.2f}s；镜头对齐到节拍：最短 {min(s['t1']-s['t0'] for s in tl['shots']):.2f}s")


if __name__ == "__main__":
    main()
