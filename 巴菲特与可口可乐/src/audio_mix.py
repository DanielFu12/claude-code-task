"""混音：配乐剪辑 + 低频声音设计 + 旁白 + 自动闪避（ducking）→ work/mix.wav

声音设计原则（按需求）：
  · 转场只用 sub drop / 低频冲击 / 低频脉冲，能量集中在 200Hz 以下；
  · 不使用白噪声、沙沙声、高频 whoosh 和上升音；配乐整体做高频柔化，
    对配乐里少量的上扬/镲片过渡段（用频谱检测出来）再额外低通；
  · 有旁白时配乐压低，无旁白时音乐抬起。
同时输出 work/audio_feats.json（节拍、能量包络），给画面做卡点。
"""
import sys, os, json, subprocess
import numpy as np, soundfile as sf
from scipy import signal
import pyloudnorm as pyln

SR = 48000


def load(path):
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def sos_lp(fc, order=4): return signal.butter(order, fc, 'low', fs=SR, output='sos')
def sos_hp(fc, order=2): return signal.butter(order, fc, 'high', fs=SR, output='sos')


def shelf_soften(x):
    """高频柔化：8kHz 以上约 -6dB，16kHz 低通"""
    hi = signal.sosfiltfilt(sos_hp(7000, 2), x, axis=0)
    y = x - 0.5 * hi
    return signal.sosfiltfilt(sos_lp(15000, 4), y, axis=0)


def tame_risers(x, thr=2.2):
    """检测“高频能量突然高于本地基线”的片段（上扬/镲片/whoosh），在这些片段里叠加 3kHz 低通"""
    hop = 1024
    hi = signal.sosfiltfilt(sos_hp(4000, 4), x.mean(1))
    e = np.sqrt(np.convolve(hi ** 2, np.ones(hop) / hop, 'same'))[::hop]
    base = signal.medfilt(e, 61) + 1e-6
    mask = (e / base > thr).astype(np.float32)
    mask = np.convolve(mask, np.ones(9) / 9, 'same').clip(0, 1)        # 平滑过渡
    m = np.interp(np.arange(len(x)), np.arange(len(mask)) * hop, mask)[:, None]
    low = signal.sosfiltfilt(sos_lp(3000, 4), x, axis=0)
    return x * (1 - m) + low * m, float(mask.mean())


def peaking(f0, gain_db, q=1.0):
    """RBJ 峰值均衡（返回 sos）"""
    A = 10 ** (gain_db / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]; a = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    return signal.tf2sos(np.array(b) / a[0], np.array(a) / a[0])


def lp_windows(x, wins, fc=2500):
    """在指定时间窗内把配乐低通（去掉原曲里的上扬/镲片过渡），窗口两端 0.4s 渐变"""
    low = signal.sosfiltfilt(sos_lp(fc, 4), x, axis=0)
    m = np.zeros(len(x), np.float32)
    t = np.arange(len(x)) / SR
    for a, b in wins:
        m = np.maximum(m, np.clip(np.minimum((t - a) / 0.4 + 1, (b - t) / 0.4 + 1), 0, 1))
    return x * (1 - m[:, None]) + low * m[:, None]


def deess(v, thr_db=-30, ratio=3.0):
    """简单去齿音：5.5kHz 以上频段超过阈值时压缩"""
    hi = signal.sosfiltfilt(sos_hp(5500, 4), v)
    e = env_follow(hi, 0.002, 0.06)
    thr = 10 ** (thr_db / 20) * np.abs(v).max()
    g = np.where(e > thr, (thr / np.maximum(e, 1e-9)) ** (1 - 1 / ratio), 1.0)
    return v - hi + hi * g


def env_follow(v, att=0.06, rel=0.45):
    """旁白包络（用于闪避）"""
    a = np.abs(v)
    blk = 480
    e = np.sqrt(np.convolve(a ** 2, np.ones(blk) / blk, 'same'))[::blk]
    out = np.zeros_like(e); g = 0.0
    ka, kr = np.exp(-blk / (SR * att)), np.exp(-blk / (SR * rel))
    for i, s in enumerate(e):
        k = ka if s > g else kr
        g = k * g + (1 - k) * s
        out[i] = g
    return np.interp(np.arange(len(v)), np.arange(len(out)) * blk, out)


# ------------------------------------------------------------------ 低频声音设计（全部合成，原创）
def sub_drop(dur=2.2, f0=72, f1=26, amp=0.9):
    t = np.arange(int(dur * SR)) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 2.6)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t * 1.25) * amp
    y += 0.25 * np.tanh(3 * np.sin(ph)) * np.exp(-t * 3.0) * amp      # 一点谐波让小音箱也听得到
    a = np.minimum(t / 0.008, 1)
    return signal.sosfilt(sos_lp(180, 4), y * a)


def impact(dur=3.5, amp=1.0, seed=1):
    """低频冲击：sub 正弦 + 低通后的隆隆声（只保留 <160Hz，不是白噪声的嘶嘶声）"""
    rng = np.random.default_rng(seed)
    t = np.arange(int(dur * SR)) / SR
    body = np.sin(2 * np.pi * (38 + 30 * np.exp(-t * 9)) * t) * np.exp(-t * 1.6)
    rumble = signal.sosfilt(sos_lp(160, 6), rng.standard_normal(len(t))) * np.exp(-t * 1.1) * 2.2
    click = np.sin(2 * np.pi * 95 * t) * np.exp(-t * 28) * 0.6
    y = (body + rumble + click) * amp
    return np.tanh(1.4 * y) / 1.4


def heartbeat(amp=0.55):
    t = np.arange(int(0.9 * SR)) / SR
    def thump(t0, a):
        tt = np.clip(t - t0, 0, None)
        return np.sin(2 * np.pi * (48 + 25 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 13) * a * (t >= t0)
    return signal.sosfilt(sos_lp(140, 4), thump(0, 1.0) + thump(0.24, 0.7)) * amp


def low_pulse(amp=0.35):
    t = np.arange(int(0.6 * SR)) / SR
    return np.sin(2 * np.pi * (52 + 20 * np.exp(-t * 25)) * t) * np.exp(-t * 9) * amp


def drone(dur, f=36.7, amp=0.18):
    t = np.arange(int(dur * SR)) / SR
    y = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.5 * t + 0.4) + 0.3 * np.sin(2 * np.pi * f * 2 * t))
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.17 * t)
    fade = np.minimum(np.minimum(t / 1.5, (dur - t) / 2.0), 1).clip(0, 1)
    return signal.sosfilt(sos_lp(150, 4), y * lfo * fade) * amp


def place(buf, clip, t, gain=1.0):
    i = int(round(t * SR))
    if i >= len(buf): return
    c = clip if clip.ndim == 2 else np.stack([clip, clip], 1)
    n = min(len(c), len(buf) - i)
    if i < 0: c = c[-i:]; n = min(len(c), len(buf)); i = 0
    buf[i:i + n] += c[:n] * gain


def main(work):
    tl = json.load(open(os.path.join(work, 'timeline.json')))
    mp = json.load(open(os.path.join(work, 'music_plan.json')))
    N = int((tl['total'] + 0.5) * SR)

    # ------------------------------------------------ 配乐剪辑
    mus = np.zeros((N, 2), np.float32)
    end_t = tl['chapters']['end'][1]
    for p in mp['pieces']:
        x = load(os.path.join(work, 'music', p['file']))
        a = int(p['src_in'] * SR)
        until = p['until'] if p['until'] is not None else end_t
        seg = x[a:a + int((until - p['at']) * SR)].copy()
        n = len(seg)
        g = np.ones(n, np.float32)
        fi, fo = int(p['fade_in'] * SR), int(p['fade_out'] * SR)
        if fi: g[:fi] = np.sin(np.linspace(0, np.pi / 2, fi)) ** 2
        if fo and p['until'] is not None: g[-fo:] = np.cos(np.linspace(0, np.pi / 2, fo)) ** 2
        place(mus, seg * g[:, None], p['at'])
    # 片尾：最后 2.5 秒整体淡出
    tail = int(2.5 * SR); e = int(end_t * SR)
    mus[e - tail:e] *= (np.cos(np.linspace(0, np.pi / 2, tail)) ** 2)[:, None]; mus[e:] = 0
    mus = shelf_soften(mus)
    mus = lp_windows(mus, mp.get('lp_windows', []))
    mus, frac = tame_risers(mus)
    print('riser-tamed fraction %.3f' % frac)

    # ------------------------------------------------ 旁白
    vo = np.zeros((N, 2), np.float32)
    for s in tl['segs']:
        y, _ = sf.read(os.path.join(work, 'vo', s['id'] + '.wav'), dtype='float32')
        if y.ndim == 2: y = y.mean(1)
        y = signal.sosfilt(sos_hp(85, 2), y)
        y = signal.sosfilt(peaking(210, -1.5, 1.0), y)
        y = signal.sosfilt(peaking(3200, 1.5, 0.9), y)
        y = deess(y)
        place(vo, np.stack([y, y], 1), s['start'])
    meter = pyln.Meter(SR)
    vl = meter.integrated_loudness(vo[vo.any(1)] if vo.any() else vo)
    vo *= 10 ** ((-17.0 - vl) / 20)
    # 轻压缩，让句尾不掉
    env = env_follow(vo.mean(1), 0.01, 0.25)
    thr = np.percentile(env[env > 1e-4], 70)
    gain = np.where(env > thr, (thr / np.maximum(env, 1e-9)) ** 0.35, 1.0)
    vo *= gain[:, None]

    # ------------------------------------------------ 闪避：有旁白时音乐 -11dB，无旁白时音乐抬起
    # 用“说话区间”（句子起止 + 0.25s 保持）生成闪避曲线，而不是逐字包络 → 句间不会忽大忽小
    act = np.zeros(N, np.float32)
    for s in tl['segs']:
        a = int((s['start'] - 0.25) * SR); b = int((s['start'] + s['dur'] + 0.35) * SR)
        act[max(a, 0):b] = 1
    k = int(0.5 * SR)                                            # 0.5s 升余弦平滑（≈ 起 250ms / 落 500ms）
    win = np.hanning(2 * k + 1); win /= win.sum()
    on = np.convolve(act, win, 'same').clip(0, 1)
    duck_db = -10.0 * on
    mg = 10 ** (duck_db / 20)
    ml = meter.integrated_loudness(mus)
    mus *= 10 ** ((-20.0 - ml) / 20)
    # 人声频段（1–4kHz）再多让 3dB，给旁白留出清晰度
    band = signal.sosfiltfilt(signal.butter(2, [1000, 4000], 'band', fs=SR, output='sos'), mus, axis=0)
    mus = mus - band * (1 - 10 ** (-3 / 20)) * on[:, None]
    mus *= mg[:, None]
    # 1998 泡沫破裂：音乐瞬间压低 7dB 并低通，1.6 秒后恢复（配合画面中的“爆裂”与低频冲击）
    seg0 = {s['id']: s for s in tl['segs']}
    pop = seg0['s35']['start'] + 2.1
    tt = np.arange(N) / SR
    dip = np.clip(np.minimum((tt - pop) / 0.05, (pop + 1.6 - tt) / 0.8), 0, 1)
    lowm = signal.sosfiltfilt(sos_lp(700, 2), mus, axis=0)
    mus = (mus * (1 - dip[:, None]) + lowm * dip[:, None]) * (10 ** (-7 * dip / 20))[:, None]

    # ------------------------------------------------ 低频声音设计
    sfx = np.zeros((N, 2), np.float32)
    ch = tl['chapters']
    # 开场：心跳 + 深沉嗡鸣
    for k, t in enumerate(np.arange(0.25, ch['title'][0] - 1.0, 1.55)):
        place(sfx, heartbeat(0.5 + 0.25 * k / 16), t)
    place(sfx, drone(ch['title'][0] + 1.0, amp=0.12), 0.0)
    # 标题：大冲击 + sub drop
    place(sfx, impact(4.0, 1.0, 3), ch['title'][0]); place(sfx, sub_drop(2.6, 80, 24, 0.9), ch['title'][0])
    # 章节：sub drop（第一章轻一点）
    for c, a in (('ch1', 0.45), ('ch2', 0.75), ('ch3', 0.85), ('ch4', 1.0), ('ch5', 0.6)):
        place(sfx, sub_drop(2.2, 70, 26, a), ch[c][0])
    place(sfx, impact(3.0, 0.7, 5), ch['ch4'][0])
    place(sfx, drone(6.0, 32.7, 0.16), ch['ch4'][0] - 0.5)          # “并不平坦”的低频空拍
    # 数字揭晓的低频脉冲（与画面里的数字跳出同步）
    seg = {s['id']: s for s in tl['segs']}
    for sid, dt, a in (('s03', 2.2, 0.45), ('s04', 2.6, 0.45), ('s25', 0.2, 0.3), ('s26', 3.6, 0.35),
                       ('s28', 0.15, 0.6), ('s29', 3.5, 0.4), ('s30', 0.4, 0.4), ('s38', 3.0, 0.35)):
        place(sfx, low_pulse(a), seg[sid]['start'] + dt)
    place(sfx, impact(2.8, 0.75, 7), seg['s35']['start'] + 2.1)       # 泡沫破裂
    for k in range(4):                                                # 拆股 1→2→4→8→16
        place(sfx, low_pulse(0.3 + 0.08 * k), seg['s27']['start'] + 0.6 + k * 0.62)
    # 片尾：粒子汇聚 → logo 重拍
    place(sfx, impact(4.5, 0.9, 9), mp['hits']['logo'])
    place(sfx, sub_drop(3.0, 66, 22, 0.8), mp['hits']['logo'])
    sfx = signal.sosfilt(sos_lp(220, 4), sfx, axis=0)
    sfx = signal.sosfilt(sos_hp(28, 4), sfx, axis=0)               # 切掉听不见、只占能量的超低频
    sl = meter.integrated_loudness(sfx[sfx.any(1)])
    sfx *= 10 ** ((-23.0 - sl) / 20)

    mix = mus + vo + sfx
    # 主总线：响度 -14 LUFS，软限幅 -1 dBTP 左右
    L = meter.integrated_loudness(mix)
    mix *= 10 ** ((-14.0 - L) / 20)
    peak = 0.89
    mix = np.where(np.abs(mix) > peak * 0.8, np.sign(mix) * (peak * 0.8 + (peak * 0.2) * np.tanh((np.abs(mix) - peak * 0.8) / (peak * 0.2))), mix)
    sf.write(os.path.join(work, 'mix.wav'), mix.astype(np.float32), SR, subtype='PCM_24')
    for nm, b in (('music', mus), ('vo', vo), ('sfx', sfx)):
        sf.write(os.path.join(work, f'stem_{nm}.wav'), b.astype(np.float32), SR, subtype='PCM_16')
    print('mix LUFS', round(meter.integrated_loudness(mix), 2), 'peak', float(np.abs(mix).max()))

    # ------------------------------------------------ 画面卡点用的音频特征
    import librosa
    m = librosa.resample(mus.mean(1), orig_sr=SR, target_sr=22050)
    on_env = librosa.onset.onset_strength(y=m, sr=22050, hop_length=256)
    tempo, beats = librosa.beat.beat_track(onset_envelope=on_env, sr=22050, hop_length=256)
    bt = librosa.frames_to_time(beats, sr=22050, hop_length=256)
    rms = librosa.feature.rms(y=m, hop_length=735)[0]                  # 30 fps
    full = librosa.feature.rms(y=librosa.resample((mus / np.maximum(mg[:, None], 1e-3)).mean(1), orig_sr=SR, target_sr=22050), hop_length=735)[0]
    feats = dict(beats=[round(float(b), 3) for b in bt], tempo=float(np.atleast_1d(tempo)[0]),
                 energy=[round(float(v), 4) for v in (full / full.max())],
                 onset=[round(float(v), 3) for v in np.interp(np.arange(len(rms)) * 735 / 22050,
                                                             librosa.times_like(on_env, sr=22050, hop_length=256),
                                                             on_env / on_env.max())])
    json.dump(feats, open(os.path.join(work, 'audio_feats.json'), 'w'))


if __name__ == '__main__':
    main(sys.argv[1])
