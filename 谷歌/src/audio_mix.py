"""混音：旁白（work/vo/<id>.wav）按时间线落位 + 原创配乐（work/music/score_raw.wav）按旁白闪避 → work/mix.wav
同时输出 work/audio_feats.json（节拍、每帧配乐能量），供画面里的光效呼吸与节拍脉冲使用。

  · 旁白：每句切片的“发声起点”（vo.json 的 lead）对准时间线上的 start；
  · 配乐：有旁白时压到 −15 dB 左右（柔和的起落，攻 0.25s / 释 0.9s），章节卡、要点卡、片名与片尾时抬起；
    三处重拍（片名、“是我发起的”、片尾 logo）前后各 1.2s 不闪避；
  · 母带：整体响度 −16 LUFS，峰值限制 −1.5 dBFS。
python3 src/audio_mix.py WORK
"""
import sys, os, json
import numpy as np, soundfile as sf

SR = 48000; FPS = 30
WORK = sys.argv[1] if len(sys.argv) > 1 else 'work'
TL = json.load(open(os.path.join(WORK, 'timeline.json')))
VO = json.load(open(os.path.join(WORK, 'vo', 'vo.json')))
BEATS = json.load(open(os.path.join(WORK, 'music', 'beats.json')))
N = int((TL['total'] + 0.5) * SR)


def smooth(env, att, rel):
    """单极点包络跟随（攻 / 释时间常数，秒）"""
    out = np.empty_like(env); a = np.exp(-1 / (att * SR / 64)); r = np.exp(-1 / (rel * SR / 64)); y = 0.0
    for k, x in enumerate(env):
        c = a if x > y else r
        y = c * y + (1 - c) * x; out[k] = y
    return out


if __name__ == '__main__':
    import pyloudnorm as pyln
    voice = np.zeros(N, np.float32); sotm = np.zeros(N, np.float32)
    from scipy.signal import butter, sosfilt
    for s in TL['segs']:
        if s.get('kind') == 'sot':                     # 巴菲特原声：80Hz 高通去低频嗡声，整段响度对齐旁白（−21 LUFS）
            y, sr = sf.read(os.path.join(WORK, 'sot', s['id'][4:] + '.wav'), dtype='float32')
            y = sosfilt(butter(2, 80, 'highpass', fs=SR, output='sos'), y).astype(np.float32)
            y *= 10 ** ((-21.0 - pyln.Meter(SR).integrated_loudness(y)) / 20)
            p = int((s['start'] - s['lead']) * SR)
            e = min(p + len(y), N); voice[p:e] += y[:e - p]; sotm[p:e] = 1.0
            continue
        y, sr = sf.read(os.path.join(WORK, 'vo', s['id'] + '.wav'), dtype='float32')
        if y.ndim > 1: y = y.mean(1)
        p = int((s['start'] - VO[s['id']]['lead']) * SR)
        e = min(p + len(y), N); voice[max(p, 0):e] += y[max(-p, 0):e - p]
    mus, sr = sf.read(os.path.join(WORK, 'music', 'score_raw.wav'), dtype='float32')
    if mus.ndim == 1: mus = np.stack([mus, mus], 1)
    mus = np.pad(mus, ((0, max(N - len(mus), 0)), (0, 0)))[:N]
    meter = pyln.Meter(SR)
    # 配乐按章节校平：程序作曲各章配器疏密不同，响度相差可达 17 dB；每章整体拉到目标响度（章内渐强保留），章节交界 3s 过渡
    TARGET = {'hook': -24.0, 'title': -20.0, 'end': -20.0, 'ch5': -22.0, 'ch7': -22.5}
    keys = [k for k in TL['chapters'] if not k.startswith('tk_')]
    spans = sorted((TL['chapters'][k][0], TL['chapters'][k][1], k) for k in keys)
    gdb = np.zeros(N, np.float32); pts = []
    for a, b, k in spans:
        seg = mus[int(a * SR):int(min(b, N / SR) * SR)]
        if len(seg) < SR * 3: continue
        L = meter.integrated_loudness(seg)
        pts.append(((a + b) / 2, a, b, float(np.clip(TARGET.get(k, -23.0) - L, -12, 16))))
    t_all = np.arange(N) / SR
    for c, a, b, d in pts:
        w = np.clip((t_all - a + 1.5) / 3.0, 0, 1) * np.clip((b + 1.5 - t_all) / 3.0, 0, 1)
        gdb += w * d
    # 归一化交界处的权重（相邻两章的过渡区权重之和为 1）
    wsum = np.zeros(N, np.float32)
    for c, a, b, d in pts: wsum += np.clip((t_all - a + 1.5) / 3.0, 0, 1) * np.clip((b + 1.5 - t_all) / 3.0, 0, 1)
    mus *= (10 ** (gdb / np.maximum(wsum, 1e-3) / 20))[:, None]
    mus *= 10 ** ((-20.0 - meter.integrated_loudness(mus)) / 20)
    # 旁白活动包络（每 64 样本一格）
    v64 = np.abs(voice[:N // 64 * 64]).reshape(-1, 64).max(1)
    act = (v64 > 10 ** (-40 / 20)).astype(np.float32)
    act = smooth(act, 0.25, 0.9)
    # 重拍附近不闪避
    tt = np.arange(len(act)) * 64 / SR
    for h in BEATS['hits']:
        act *= 1 - np.exp(-((tt - h) / 1.2) ** 8)
    gain_db = -13.0 * np.clip(act * 1.4, 0, 1)
    s64 = smooth(sotm[:N // 64 * 64].reshape(-1, 64).max(1), 0.3, 0.8)
    gain_db -= 5.0 * np.clip(s64 * 1.2, 0, 1)            # 原声下配乐再低 5 dB（原声底噪较高，需要更干净的空间）
    g = np.repeat(10 ** (gain_db / 20), 64)
    g = np.pad(g, (0, N - len(g)), mode='edge')
    np.save(os.path.join(WORK, 'music', 'leveled_gain.npy'), g[::480])
    mix = mus * g[:, None] * 0.9 + voice[:, None] * 1.0
    # 母带：−16 LUFS，峰值 −1.5 dBFS（简单的软限幅）
    mix *= 10 ** ((-16.0 - meter.integrated_loudness(mix)) / 20)
    lim = 10 ** (-1.5 / 20)
    mix = np.where(np.abs(mix) > lim * 0.8, np.sign(mix) * (lim * 0.8 + (lim * 0.2) * np.tanh((np.abs(mix) - lim * 0.8) / (lim * 0.2))), mix)
    sf.write(os.path.join(WORK, 'mix.wav'), mix, SR, subtype='PCM_24')
    # 画面用的配乐能量（每帧，0..1）
    m = (mus * g[:, None]).mean(1)
    hop = SR // FPS
    rms = np.sqrt(np.convolve(m ** 2, np.ones(hop) / hop, 'same'))[::hop]
    e = rms / (np.percentile(rms, 98) + 1e-9)
    json.dump(dict(beats=BEATS['beats'], energy=np.clip(e, 0, 1).round(3).tolist(), hits=BEATS['hits']),
              open(os.path.join(WORK, 'audio_feats.json'), 'w'))
    print('mix', round(meter.integrated_loudness(mix), 2), 'LUFS', 'peak', round(20 * np.log10(np.abs(mix).max()), 2), 'dBFS')
