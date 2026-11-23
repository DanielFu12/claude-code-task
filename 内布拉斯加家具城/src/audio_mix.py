"""混音（docs/旁白一致性与自然衔接.md 第二节 6）：旁白（WORK/vo/<id>.wav）按时间线落位 + 原创配乐（WORK/music/score_raw.wav）→ WORK/mix.wav
同时输出 WORK/audio_feats.json（节拍、每帧配乐能量），供画面里的光效呼吸与节拍脉冲使用。

  · 旁白：每句切片的“发声起点”（vo.json 的 lead）对准时间线上的 start；段内切片首尾相接，就是原来那一条录音；
    整条旁白过 70 Hz 高通、2.2:1 轻压缩、很淡的同一个小房间短混响（RT60 约 0.6 s，湿声 0.1）、−64 dBFS 粉噪底，
    句间与插入的留白不是数字静音；
  · 配乐：各章响度校平后，闪避放在最后一步（压缩之后）：人声时全频 −12 dB、人声频段（700 Hz–4 kHz）再 −5 dB；
    提前 0.15 s 开始压，保持 0.9 s（句间短停顿不放开），起 80 ms、放 550 ms；重拍前后不闪避，句中点题只半闪避；
  · 母带：线性增益到 −14 LUFS + 峰值限制（−1.0 dBFS），不用动态 loudnorm。
python3 src/audio_mix.py WORK
"""
import sys, os, json
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000; FPS = 30
WORK = sys.argv[1] if len(sys.argv) > 1 else 'work'
TL = json.load(open(os.path.join(WORK, 'timeline.json')))
VO = json.load(open(os.path.join(WORK, 'vo', 'vo.json')))
BEATS = json.load(open(os.path.join(WORK, 'music', 'beats.json')))
N = int((TL['total'] + 0.5) * SR)


def smooth(env, att, rel, rate):
    """单极点包络跟随（攻 / 释时间常数，秒；rate 为包络采样率）"""
    out = np.empty_like(env); a = np.exp(-1 / (att * rate)); r = np.exp(-1 / (rel * rate)); y = 0.0
    for k, x in enumerate(env):
        c = a if x > y else r
        y = c * y + (1 - c) * x; out[k] = y
    return out


def compress(x, ratio=2.2, thr_db=-24.0, att=0.01, rel=0.15):
    """前馈 RMS 压缩（10 ms 包络）"""
    hop = 480; n = len(x) // hop * hop
    e = np.sqrt(np.mean(x[:n].reshape(-1, hop) ** 2, 1)) + 1e-9
    db = 20 * np.log10(e)
    gr = np.where(db > thr_db, (db - thr_db) * (1 - 1 / ratio), 0.0)
    gr = smooth(gr, att, rel, SR / hop)
    g = np.repeat(10 ** (-gr / 20), hop); g = np.pad(g, (0, len(x) - len(g)), mode='edge')
    return x * g


def room(x, rt60=0.6, wet=0.1, seed=3):
    rng = np.random.default_rng(seed)
    n = int(rt60 * SR); tt = np.arange(n) / SR
    ir = rng.standard_normal(n).astype(np.float32) * np.exp(-6.9 * tt / rt60)
    ir = sosfilt(butter(1, 4500, 'lowpass', fs=SR, output='sos'), ir); ir[:int(0.012 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum())
    return x * (1 - wet) + fftconvolve(x, ir)[:len(x)] * wet * 3.0


def pink(n, db, seed=5):
    rng = np.random.default_rng(seed)
    f = np.fft.rfft(rng.standard_normal(n)); k = np.arange(len(f)); k[0] = 1
    p = np.fft.irfft(f / np.sqrt(k), n).astype(np.float32)
    return p / np.sqrt(np.mean(p ** 2)) * 10 ** (db / 20)


if __name__ == '__main__':
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    voice = np.zeros(N, np.float32)
    for s in TL['segs']:
        if s.get('kind') == 'sot': continue                 # 本期没有原声段落
        y, sr = sf.read(os.path.join(WORK, 'vo', s['id'] + '.wav'), dtype='float32')
        if y.ndim > 1: y = y.mean(1)
        p = int(round((s['start'] - VO[s['id']]['lead']) * SR))
        e = min(p + len(y), N); voice[max(p, 0):e] += y[max(-p, 0):e - p]
    active = np.abs(voice) > 1e-5
    voice = sosfilt(butter(2, 70, 'highpass', fs=SR, output='sos'), voice).astype(np.float32)
    voice = compress(voice).astype(np.float32)
    voice = room(voice).astype(np.float32)
    voice += pink(N, -64.0) * (np.convolve(active, np.ones(SR // 4), 'same') > 0)     # 只在旁白段落里垫噪底（片头片尾保持干净）
    # ---- 配乐：按章节校平
    mus, sr = sf.read(os.path.join(WORK, 'music', 'score_raw.wav'), dtype='float32')
    if mus.ndim == 1: mus = np.stack([mus, mus], 1)
    mus = np.pad(mus, ((0, max(N - len(mus), 0)), (0, 0)))[:N]
    TARGET = {'hook': -24.0, 'title': -20.0, 'end': -20.0, 'ch7': -22.5}
    keys = [k for k in TL['chapters'] if not k.startswith('tk_')]
    spans = sorted((TL['chapters'][k][0], TL['chapters'][k][1], k) for k in keys)
    t_all = np.arange(N) / SR; gdb = np.zeros(N, np.float32); wsum = np.zeros(N, np.float32)
    for a, b, k in spans:
        seg = mus[int(a * SR):int(min(b, N / SR) * SR)]
        if len(seg) < SR * 3: continue
        d = float(np.clip(TARGET.get(k, -23.0) - meter.integrated_loudness(seg), -12, 16))
        w = np.clip((t_all - a + 1.5) / 3.0, 0, 1) * np.clip((b + 1.5 - t_all) / 3.0, 0, 1)
        gdb += w * d; wsum += w
    mus *= (10 ** (gdb / np.maximum(wsum, 1e-3) / 20))[:, None]
    mus *= 10 ** ((-20.0 - meter.integrated_loudness(mus)) / 20)
    # ---- 闪避（最后一步）：人声活动 → 提前 0.15 s、保持 0.9 s、起 80 ms / 放 550 ms
    hop = 240; rate = SR / hop; n = N // hop
    act = (np.abs(voice[:n * hop]).reshape(-1, hop).max(1) > 10 ** (-42 / 20)).astype(np.float32)
    from scipy.ndimage import maximum_filter1d
    look = int(0.15 * rate); hold = int(0.9 * rate)
    act = np.roll(act, -look); act = maximum_filter1d(act, hold, origin=-(hold // 2))
    act = smooth(act, 0.08, 0.55, rate)
    tt = np.arange(n) / rate
    soft = BEATS.get('soft', [])
    for h in BEATS['hits'] + soft:
        k = 0.5 if any(abs(h - x) < 0.01 for x in soft) else 1.0
        act *= 1 - k * np.exp(-((tt - h) / 1.0) ** 8)
    full_db = -12.0 * act; band_db = -5.0 * act
    gf = np.interp(np.arange(N), np.arange(n) * hop, 10 ** (full_db / 20)).astype(np.float32)
    gb = np.interp(np.arange(N), np.arange(n) * hop, 10 ** (band_db / 20)).astype(np.float32)
    sos_b = butter(2, [700, 4000], 'bandpass', fs=SR, output='sos')
    band = sosfilt(sos_b, mus, axis=0).astype(np.float32)
    mus_d = (mus + band * (gb - 1)[:, None]) * gf[:, None]
    np.save(os.path.join(WORK, 'music', 'leveled_gain.npy'), gf[::480])
    mix = mus_d * 0.9 + voice[:, None]
    # ---- 母带：线性增益到 −14 LUFS，峰值限制 −1.0 dBFS（软膝）
    mix *= 10 ** ((-14.0 - meter.integrated_loudness(mix)) / 20)
    lim = 10 ** (-1.0 / 20); kn = lim * 0.85
    mix = np.where(np.abs(mix) > kn, np.sign(mix) * (kn + (lim - kn) * np.tanh((np.abs(mix) - kn) / (lim - kn))), mix)
    sf.write(os.path.join(WORK, 'mix.wav'), mix.astype(np.float32), SR, subtype='PCM_24')
    # 画面用的配乐能量（每帧，0..1）
    m = mus_d.mean(1); hp = SR // FPS
    rms = np.sqrt(np.convolve(m ** 2, np.ones(hp) / hp, 'same'))[::hp]
    e = rms / (np.percentile(rms, 98) + 1e-9)
    json.dump(dict(beats=BEATS['beats'], energy=np.clip(e, 0, 1).round(3).tolist(), hits=BEATS['hits']),
              open(os.path.join(WORK, 'audio_feats.json'), 'w'))
    # 自检：说话时旁白比配乐高多少
    vm = np.abs(voice) > 10 ** (-35 / 20)
    lv = meter.integrated_loudness(np.stack([voice, voice], 1)[vm[:len(voice)]][:SR * 300]) if vm.sum() > SR else 0
    lm = meter.integrated_loudness((mus_d * 0.9)[vm][:SR * 300]) if vm.sum() > SR else 0
    print('mix', round(meter.integrated_loudness(mix), 2), 'LUFS', 'peak', round(20 * np.log10(np.abs(mix).max()), 2), 'dBFS',
          '| 说话时 旁白 − 配乐 ≈ %.1f LU' % (lv - lm))
