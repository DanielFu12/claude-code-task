"""混音：片头音乐 → 巴菲特原始录音（无配乐）→ 投资启示（音乐 + 解说）→ 片尾重拍。

音乐取自仓库根目录 opus5.5涌现.mp4（约 112 BPM）。结构（原曲时间）：
  0–9.6s 前奏 → 9.6s 鼓点抽空 → 17.09s 重拍（能量从 -19dB 跳到 -4dB）→ 主律动。
- 片头：原曲从 0s 播放，原声开始前淡出；原始录音期间不垫音乐。
- 投资启示：原曲从重拍前 1.5s 淡入，重拍正好落在“投资启示”开始处；
  解说快结束时，在同一小节相位的节拍上无缝跳回原曲 8.6s（鼓点抽空前一小节），
  于是“抽空 → 上扬 → 重拍”再走一遍，重拍落在片尾「巴芒价值」出现的那一刻。
重拍时刻按能量突变精确定位，不直接用 librosa 的节拍估计（后者落后约 40ms）。

用法：python3 src/audio.py WORK BGM_WAV
输出：WORK/mix.wav、WORK/orig_env.npy（原声音量包络，画面波形用）、WORK/music.json
"""
import json, sys
import numpy as np, soundfile as sf, librosa, scipy.signal as ss

HIT_SRC_BEAT = 30       # 原曲重拍附近的节拍（约 17.1s）
DROP_SRC_BEAT = 14      # 原曲 8.6s，跳回点（与重拍同一小节相位）
TAIL_AFTER_HIT = 5.0    # 片尾重拍后保留的时长
SR = 48000


def speech_rms(x):
    """有声部分的 RMS（忽略静音段）"""
    f = 2400
    r = np.array([np.sqrt(np.mean(x[i:i + f] ** 2)) for i in range(0, len(x) - f, f)])
    return np.sqrt(np.mean(r[r > r.max() * 0.1] ** 2))


def fade(n, kind='in'):
    v = np.sin(np.linspace(0, np.pi / 2, n)) ** 2
    return v if kind == 'in' else v[::-1]


def main():
    work, src = sys.argv[1], sys.argv[2]
    tl = json.load(open(work + '/timeline.json'))
    y, sr0 = sf.read(src)
    y = librosa.resample(y.T, orig_sr=sr0, target_sr=SR).T
    m = librosa.to_mono(y.T).astype(np.float32)
    _, b = librosa.beat.beat_track(y=librosa.resample(m, orig_sr=SR, target_sr=22050), sr=22050, hop_length=512)
    bt = librosa.frames_to_time(b, sr=22050, hop_length=512)
    hop = 120
    r = librosa.feature.rms(y=m, frame_length=1024, hop_length=hop)[0]
    tr = np.arange(len(r)) * hop / SR
    w = (tr > bt[HIT_SRC_BEAT] - 0.3) & (tr < bt[HIT_SRC_BEAT] + 0.1)
    d = np.diff(20 * np.log10(r + 1e-9), prepend=-200)
    hit_src = float(tr[w][np.argmax(d[w])])
    bt = bt + (hit_src - bt[HIT_SRC_BEAT])                 # 整体校正节拍网格
    S = lambda t: int(round(t * SR))

    # ------------------------------------------------ 解说 / 投资启示的重拍与片尾重拍
    narr = [it for it in tl['items'] if it['lang'] == 'zh']
    L0 = tl['lesson_at']
    lead = hit_src - bt[DROP_SRC_BEAT]
    want_hit = narr[-1]['end'] + 5.0
    out_beats_b = L0 + (bt - hit_src)                     # 投资启示段音乐的节拍（成片时间）
    cands = [i for i in range(len(bt)) if i % 4 == DROP_SRC_BEAT % 4 and bt[i] > hit_src
             and out_beats_b[i] + lead >= want_hit - 0.3]
    i = cands[0]
    splice = out_beats_b[i]
    hit = splice + lead
    end = hit + TAIL_AFTER_HIT
    n = S(end)
    music = np.zeros((n, 2), np.float32)

    # 片头：原曲 0s 起，原声开始前淡出
    t_orig = tl['title_end'] + 0.5 - 0.5               # 原声片段起点（提问前 0.5s）
    a_end = t_orig + 0.4
    seg = y[:S(a_end)].copy()
    k = S(1.6); seg[-k:] *= fade(k, 'out')[:, None]
    music[:len(seg)] += seg
    # 投资启示：重拍前 1.5s 淡入，到 splice 跳回 8.6s
    pre = 1.5
    s0 = S(hit_src - pre)
    segb = y[s0:s0 + S(splice - (L0 - pre)) + S(0.03)].copy()
    k = S(1.2); segb[:k] *= fade(k, 'in')[:, None]
    c0 = S(bt[DROP_SRC_BEAT])
    segc = y[c0 - S(0.03):c0 + S(end - splice)].copy()
    xf = S(0.06)
    tt = np.linspace(0, 1, xf)[:, None]
    joined = np.concatenate([segb[:-xf], segb[-xf:] * np.cos(tt * np.pi / 2) + segc[:xf] * np.sin(tt * np.pi / 2), segc[xf:]])
    p0 = S(L0 - pre)
    music[p0:p0 + len(joined)] += joined[:n - p0]
    k = S(2.6); music[-k:] *= (np.linspace(1, 0, k) ** 1.6)[:, None]

    # ------------------------------------------------ 原始录音：单声道（原录音两声道几乎相同）、去低频隆隆声、首尾淡入淡出
    o, osr = sf.read(work + '/orig48.wav', dtype='float32')
    o = o.mean(1)
    bb, aa = ss.butter(2, 70 / (SR / 2), 'high'); o = ss.lfilter(bb, aa, o).astype(np.float32)
    o = o[S(tl['clip_in']):S(tl['clip_out'])]
    k = S(0.25); o[:k] *= fade(k, 'in'); o[-S(0.4):] *= fade(S(0.4), 'out')
    target = 10 ** (-20 / 20)                              # 有声部分 RMS 统一到 -20 dBFS
    o *= target / speech_rms(o)
    voice = np.zeros(n, np.float32)
    po = S(tl['clip_in'] + tl['off'])
    voice[po:po + len(o)] += o
    # 原声音量包络（每帧一个值，画面波形用）
    fps = 30
    env = np.array([np.sqrt(np.mean(voice[S(j / fps):S((j + 1) / fps)] ** 2) + 1e-12) for j in range(int(end * fps) + 1)])
    np.save(work + '/orig_env.npy', env.astype(np.float32))

    # ------------------------------------------------ 解说
    vo_parts = []
    for it in narr:
        x, vsr = sf.read('%s/vo/%s.wav' % (work, it['id']), dtype='float32')
        vo_parts.append((it, librosa.resample(x, orig_sr=vsr, target_sr=SR)))
    gain = target / speech_rms(np.concatenate([x for _, x in vo_parts]))
    for it, x in vo_parts:
        p = S(it['start']); voice[p:p + len(x)] += x[:n - p] * gain

    # ------------------------------------------------ 解说时压低音乐（-14dB），片头和片尾不压
    duck = np.zeros(n, np.float32)
    for it, _ in vo_parts:
        duck[S(it['start'] - 0.2):S(it['end'] + 0.3)] = 1.0
    k = S(0.4); duck = np.convolve(duck, np.ones(k) / k, 'same')
    music *= (10 ** (-14 * np.clip(duck, 0, 1) / 20) * 0.5)[:, None]
    mix = music + voice[:, None]
    mix *= 0.95 / np.abs(mix).max()
    sf.write(work + '/mix.wav', mix.astype(np.float32), SR)

    beats = np.concatenate([bt[bt < a_end], out_beats_b[(out_beats_b >= L0 - pre) & (out_beats_b < splice)],
                            splice + (bt[bt >= bt[DROP_SRC_BEAT]] - bt[DROP_SRC_BEAT])])
    beats = beats[beats < end]
    json.dump(dict(lesson_hit=round(float(L0), 3), splice=round(float(splice), 3), hit=round(float(hit), 3),
                   end=round(float(end), 3), beats=[round(float(x), 3) for x in beats]),
              open(work + '/music.json', 'w'), indent=1)
    print('source hit %.3f | lesson hit %.2f  splice %.2f  end hit %.2f  end %.2f' % (hit_src, L0, splice, hit, end))


if __name__ == '__main__':
    main()
