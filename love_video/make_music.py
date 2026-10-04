"""把《opus5.5涌现.mp4》的背景音乐延长到约 180 秒，并导出节拍/能量信息。

做法：原曲 51~57s 与 107~112s 是同一段旋律的重复（色度+MFCC 相似度 0.95），
于是在 111.2s 处无缝跳回 55.94s，再播放到结尾：111.2 + (124.88 - 55.94) ≈ 180.1s。
"""
import json
import os
import subprocess
import sys

import librosa
import numpy as np
import scipy.io.wavfile as wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "opus5.5涌现.mp4")
BUILD = os.path.join(HERE, "build")
JUMP_FROM, JUMP_TO = 111.2, 55.937  # 秒，均落在节拍上
FPS = 30


def main():
    os.makedirs(BUILD, exist_ok=True)
    raw = os.path.join(BUILD, "bgm_src.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-vn", "-c:a", "pcm_s16le",
                    "-ar", "44100", raw], check=True)
    sr, x = wavfile.read(raw)
    x = x.astype(np.float32) / 32768

    a, b = int(JUMP_FROM * sr), int(JUMP_TO * sr)
    # 在 ±30ms 内用互相关微调跳转点，避免相位错位
    win = int(0.5 * sr)
    ref = x[a:a + win, 0]
    best = max(range(-int(0.03 * sr), int(0.03 * sr)),
               key=lambda d: np.dot(ref, x[b + d:b + d + win, 0]) /
               (np.linalg.norm(x[b + d:b + d + win, 0]) + 1e-9))
    b += best
    fade = int(0.25 * sr)
    k = np.linspace(0, 1, fade)[:, None]
    out = np.concatenate([x[:a],
                          x[a:a + fade] * np.cos(k * np.pi / 2) + x[b:b + fade] * np.sin(k * np.pi / 2),
                          x[b + fade:]])
    ext = os.path.join(BUILD, "bgm_ext.wav")
    wavfile.write(ext, sr, (np.clip(out, -1, 1) * 32767).astype(np.int16))
    print(f"extended music: {len(out) / sr:.2f}s")

    y, sr2 = librosa.load(ext, sr=22050)
    _, beats = librosa.beat.beat_track(y=y, sr=sr2, hop_length=512)
    bt = librosa.frames_to_time(beats, sr=sr2, hop_length=512)
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    on = librosa.onset.onset_strength(y=y, sr=sr2, hop_length=512)
    ts = librosa.times_like(rms, sr=sr2, hop_length=512)
    grid = np.arange(0, len(y) / sr2 + 1, 1 / FPS)
    env = np.interp(grid, ts, rms)
    ons = np.interp(grid, librosa.times_like(on, sr=sr2, hop_length=512), on)
    json.dump({"duration": len(out) / sr,
               "beats": bt.tolist(),
               "env": (env / np.percentile(env, 98)).tolist(),
               "onset": (ons / np.percentile(ons, 99)).tolist()},
              open(os.path.join(BUILD, "music.json"), "w"))


if __name__ == "__main__":
    sys.exit(main())
