"""背景音乐 + 旁白混音。

音乐取自仓库根目录 opus5.5涌现.mp4（约 112 BPM）。结构（原曲时间）：
  0–9.6s 前奏 → 9.6s 鼓点抽空 → 17.10s 第一个重拍（能量从 -19dB 跳到 -4dB）→ 主律动。
做法：成片 0s 起直接播放原曲，第一个重拍正好落在巴菲特原话开始前；
旁白快结束时，在同一小节相位的节拍上无缝跳回原曲 8.6s（鼓点抽空前一小节），
这样「抽空 → 上扬 → 重拍」再走一遍，重拍落在片尾「巴芒价值」出现的那一刻。
重拍时刻按能量突变精确定位，不直接用 librosa 的节拍估计（后者落后约 40ms）。

用法：python3 src/audio.py WORK BGM_WAV
输出：WORK/mix.wav（成片音轨）、WORK/music.json（重拍时刻、片长、成片节拍网格）
"""
import json, sys
import numpy as np, soundfile as sf, librosa

HIT_SRC_BEAT = 30       # 原曲第一个重拍附近的节拍（约 17.1s）
DROP_SRC_BEAT = 14      # 原曲 8.6s，跳回点（与重拍同一小节相位，下一小节鼓点抽空）
ANSWER_AT = 17.10       # 与 tts.py 一致：原话从第一个重拍开始
TAIL_AFTER_HIT = 5.0    # 重拍后保留的时长（片尾淡出）


def main():
    work, src = sys.argv[1], sys.argv[2]
    y, sr = sf.read(src)                                   # 立体声 44100
    m = librosa.to_mono(y.T).astype(np.float32)
    _, b = librosa.beat.beat_track(y=librosa.resample(m, orig_sr=sr, target_sr=22050), sr=22050, hop_length=512)
    bt = librosa.frames_to_time(b, sr=22050, hop_length=512)
    # 精确重拍：节拍估计附近能量上升最陡的时刻
    hop = 110
    r = librosa.feature.rms(y=m, frame_length=1024, hop_length=hop)[0]
    tr = np.arange(len(r)) * hop / sr
    w = (tr > bt[HIT_SRC_BEAT] - 0.3) & (tr < bt[HIT_SRC_BEAT] + 0.1)
    d = np.diff(20 * np.log10(r + 1e-9), prepend=-200)
    hit_src = float(tr[w][np.argmax(d[w])])
    off = hit_src - bt[HIT_SRC_BEAT]
    bt = bt + off                                          # 整体校正节拍网格
    assert abs(hit_src - ANSWER_AT) < 0.06, hit_src
    tl = json.load(open(work + '/timeline.json'))
    motto = [it for it in tl['items'] if it['part'] == 'motto'][0]
    lead = hit_src - bt[DROP_SRC_BEAT]                     # 跳回点到重拍的时长（约 8.5s）
    # 希望重拍落在最后一句旁白结束后约 5 秒（留出汇聚成 logo 的时间）
    want_hit = motto['end'] + 5.0
    cands = [i for i in range(len(bt)) if i % 4 == DROP_SRC_BEAT % 4 and bt[i] + lead >= want_hit - 0.3]
    i = cands[0]
    splice = bt[i]
    hit = splice + lead
    assert splice > motto['start'] - 6, '跳回点太早'
    end = hit + TAIL_AFTER_HIT
    # 拼接：[0, splice) + 原曲 [bt[16], ...)，60ms 等功率交叉淡化
    xf = int(0.06 * sr)
    a = y[:int(splice * sr) + xf // 2]
    s0 = int(bt[DROP_SRC_BEAT] * sr) - xf // 2
    bseg = y[s0:s0 + int((end - splice) * sr) + xf]
    t = np.linspace(0, 1, xf)[:, None]
    music = np.concatenate([a[:-xf], a[-xf:] * np.cos(t * np.pi / 2) + bseg[:xf] * np.sin(t * np.pi / 2), bseg[xf:]])
    n = int(end * sr)
    music = music[:n] if len(music) >= n else np.concatenate([music, np.zeros((n - len(music), 2))])
    # 旁白（24k 单声道）→ 44.1k
    vo, vsr = sf.read(work + '/vo.wav')
    vo = librosa.resample(vo.astype(np.float32), orig_sr=vsr, target_sr=sr)
    vo = vo[:n] if len(vo) >= n else np.concatenate([vo, np.zeros(n - len(vo))])
    # 旁白压低音乐（侧链式闪避）：有人声时 -15dB，起落 0.25s / 0.6s
    env = np.zeros(n, np.float32)
    for it in tl['items']:
        env[int((it['start'] - 0.15) * sr):int((it['end'] + 0.25) * sr)] = 1.0
    k = int(0.4 * sr)
    env = np.convolve(env, np.ones(k) / k, 'same')
    gain = 10 ** (-15 * np.clip(env, 0, 1) / 20)
    # 开场前奏与片尾不压；整首音乐 -4dB 作底
    music = music * (gain * 0.63)[:, None]
    # 片尾淡出（最后 2.6s）
    f = int(2.6 * sr)
    music[-f:] *= (np.linspace(1, 0, f) ** 1.6)[:, None]
    mix = music + vo[:, None] * 1.0
    mix *= 0.93 / np.abs(mix).max()
    sf.write(work + '/mix.wav', mix.astype(np.float32), sr)
    # 成片节拍网格（供画面节拍脉动）
    beats = np.concatenate([bt[bt < splice], splice + (bt[bt >= bt[DROP_SRC_BEAT]] - bt[DROP_SRC_BEAT])])
    beats = beats[beats < end]
    json.dump(dict(splice=round(float(splice), 3), hit=round(float(hit), 3), end=round(float(end), 3),
                   first_hit=round(hit_src, 3), beats=[round(float(x), 3) for x in beats]),
              open(work + '/music.json', 'w'), indent=1)
    print('source hit %.3f  splice %.2f  hit %.2f  end %.2f' % (hit_src, splice, hit, end))


if __name__ == '__main__':
    main()
