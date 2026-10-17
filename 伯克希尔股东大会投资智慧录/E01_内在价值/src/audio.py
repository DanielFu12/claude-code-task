"""混音：原始录音 + AI 口播 + 背景音乐 + 低频转场音效。

用法：python3 src/audio.py WORK MUSIC_DIR
输入：WORK/timeline.json、WORK/vo/*.wav、WORK/orig_src.m4a、MUSIC_DIR/<曲名>.mp3
输出：WORK/mix.wav（48kHz 立体声，未做最终响度归一）、WORK/stems/*.wav、WORK/orig_env.npy（原声逐帧频带包络，画面波形用）

声音设计原则（见 README）：
- 原始问答期间不放音乐，保留现场声音；只做 70Hz 高通和整体电平统一，不降噪、不改速。
- 口播期间音乐按人声包络做侧链压缩（提前 0.15 秒开始压，压低约 14dB）。
- 转场音效全部由正弦波合成，经 4 阶 180Hz 低通：低频下潜、低沉冲击、低频膨胀，加一段低通过的空间混响尾。
  不用任何噪声源、高频 whoosh 或金属声。
"""
import json, os, subprocess, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt, fftconvolve

work, music_dir = sys.argv[1], sys.argv[2]
SR = 48000
tl = json.load(open(os.path.join(work, 'timeline.json')))
N = int((tl['dur'] + 0.5) * SR)
os.makedirs(os.path.join(work, 'stems'), exist_ok=True)


def db(x): return 10 ** (x / 20)


def load(path, ch=2):
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-ac', str(ch), '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, ch).astype(np.float64)


def fade(x, fi, fo):
    n = len(x); a = int(fi * SR); b = int(fo * SR)
    g = np.ones(n)
    if a > 0: g[:min(a, n)] = np.sin(np.linspace(0, np.pi / 2, a))[:n] ** 2
    if b > 0: g[max(n - b, 0):] = np.cos(np.linspace(0, np.pi / 2, b))[-min(b, n):] ** 2
    return x * (g[:, None] if x.ndim == 2 else g)


def put(buf, x, t):
    i = int(round(t * SR))
    if i < 0: x = x[-i:]; i = 0
    n = min(len(x), len(buf) - i)
    if n > 0: buf[i:i + n] += x[:n]


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


def voiced_rms_db(x, thr=-40):
    """只统计有声部分的 RMS（50ms 帧）"""
    m = x if x.ndim == 1 else x.mean(1)
    f = int(0.05 * SR); k = len(m) // f
    fr = np.sqrt((m[:k * f].reshape(k, f) ** 2).mean(1) + 1e-12)
    top = fr.max()
    sel = fr[20 * np.log10(fr / top) > thr]
    return 20 * np.log10(np.sqrt((sel ** 2).mean()))


# ITU-R BS.1770 K 计权（48kHz 系数），用来按响度（LUFS）而不是 RMS 给音乐定电平
from scipy.signal import lfilter
KB1, KA1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
KB2, KA2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]


def lufs(x):
    x = x if x.ndim == 2 else x[:, None]
    y = lfilter(KB2, KA2, lfilter(KB1, KA1, x, axis=0), axis=0)
    b = int(0.4 * SR); h = b // 4
    ms = np.array([np.mean(y[i:i + b] ** 2, 0).sum() for i in range(0, len(y) - b, h)])
    ms = ms[ms > 10 ** ((-70 + 0.691) / 10)]
    rel = 10 * np.log10(ms.mean()) - 0.691 - 10
    ms = ms[-0.691 + 10 * np.log10(ms) > rel]
    return -0.691 + 10 * np.log10(ms.mean())


LP = butter(4, 180, 'lowpass', fs=SR, output='sos')
HP70 = butter(2, 70, 'highpass', fs=SR, output='sos')


# ------------------------------------------------------------------ 低频转场音效（纯正弦合成）
def room_tail(x, secs=3.2, mix=0.32):
    """深沉空间混响：指数衰减的低频正弦簇作为冲激响应（无噪声），只留 200Hz 以下"""
    t = np.arange(int(secs * SR)) / SR
    rng = np.random.default_rng(7)
    ir = np.zeros_like(t)
    for f in rng.uniform(32, 170, 48):
        ir += np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-t / rng.uniform(0.5, 1.4))
    ir *= np.exp(-t / 0.9); ir /= np.abs(ir).sum() / 40
    wet = fftconvolve(x, ir)[:len(x) + len(ir)]
    out = np.zeros(len(wet)); out[:len(x)] = x
    out = out * (1 - mix) + wet / (np.abs(wet).max() + 1e-9) * np.abs(x).max() * mix
    return sosfilt(LP, out)


def impact(dur=3.0):
    t = np.arange(int(dur * SR)) / SR
    f = 44 + 30 * np.exp(-t / 0.09)                       # 74Hz → 44Hz 的快速下滑，给出“落地感”
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.85)
    sub = np.sin(2 * np.pi * 33 * t) * np.exp(-t / 1.5) * 0.7
    knock = np.sin(2 * np.pi * np.cumsum(120 - 60 * np.minimum(t / 0.05, 1)) / SR) * np.exp(-t / 0.045) * 0.6
    x = np.tanh((body + sub + knock) * 1.4)
    x *= np.minimum(t / 0.004, 1)
    return room_tail(x, mix=0.3)


def subdrop(dur=3.2):
    t = np.arange(int(dur * SR)) / SR
    f = 28 + (96 - 28) * np.exp(-t / 0.55)                # 96Hz → 28Hz 指数下潜
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.18 * np.sin(2 * ph)) * np.exp(-t / 1.25) * np.minimum(t / 0.012, 1)
    return room_tail(np.tanh(x * 1.2), mix=0.28)


def swell(dur):
    t = np.arange(int(dur * SR)) / SR
    u = t / dur
    env = u ** 2.4 * (1 + 0.08 * np.sin(2 * np.pi * 4.5 * t))
    x = (np.sin(2 * np.pi * 41 * t) + 0.6 * np.sin(2 * np.pi * 61.5 * t) + 0.3 * np.sin(2 * np.pi * 82 * t)) * env
    x[-int(0.03 * SR):] *= np.linspace(1, 0, int(0.03 * SR))
    return sosfilt(LP, x)


sfx = np.zeros(N)
for e in tl['sfx']:
    x = {'impact': lambda: impact(), 'subdrop': lambda: subdrop(), 'swell': lambda: swell(e['dur'])}[e['kind']]()
    x = x / np.abs(x).max() * db(e['gain'])
    put(sfx, x, e['t'])
sfx = np.stack([sfx, sfx], 1)

# ------------------------------------------------------------------ 原始录音
orig = load(os.path.join(work, 'orig_src.m4a'), 2).mean(1)
orig = sosfiltfilt(HP70, orig)


def fill_dropouts(x):
    """档案录音里有几处数字静音（-85dB 以下的“死寂”，是原始录像的拼接痕迹）。
    用同一录音里句间停顿的环境底噪（room tone）按 20ms 交叉淡化补上，不改动任何人声。"""
    f = SR // 100
    lev = 20 * np.log10(np.sqrt((x[:len(x) // f * f].reshape(-1, f) ** 2).mean(1)) + 1e-12)
    dead = lev < -85
    # 取一段最长的、电平在 -70~-52dB 之间的停顿作为底噪样本
    q = (lev > -70) & (lev < -52)
    best, cur, st = (0, 0), 0, 0
    for i, v in enumerate(q):
        if v:
            if cur == 0: st = i
            cur += 1
            if cur > best[1] - best[0]: best = (st, i + 1)
        else: cur = 0
    tone = x[best[0] * f:best[1] * f]
    tone = np.tile(tone, 40)
    w = np.zeros(len(x))
    for i, d in enumerate(dead):
        if d: w[i * f:(i + 1) * f] = 1
    k = int(0.02 * SR)
    w = np.convolve(w, np.ones(k) / k, 'same')
    fill = tone[:len(x)] if len(tone) >= len(x) else np.resize(tone, len(x))
    n_dead = int(dead.sum())
    print(f'room tone: {best[0] / 100:.2f}–{best[1] / 100:.2f}s，补齐 {n_dead * 10} ms 数字静音')
    return x * (1 - w) + fill * w


orig = fill_dropouts(orig)
ostem = np.zeros(N)
TARGET = -20.0                                       # 人声（原声与口播）有声部分的统一 RMS
qa = tl['qa']
seg = orig[int(qa['src_in'] * SR):int(qa['src_out'] * SR)]
# 提问（现场麦克风，较远）与回答分别统一电平
cut = int((qa['answer_t'] - qa['t0'] - 0.3) * SR)
q, a = seg[:cut], seg[cut:]
q = q * db(TARGET - voiced_rms_db(q)); a = a * db(TARGET - voiced_rms_db(a))
xf = int(0.08 * SR)                                  # 两段之间 80ms 交叉淡化
seg = np.concatenate([q[:-xf], q[-xf:] * np.linspace(1, 0, xf) + a[:xf] * np.linspace(0, 1, xf), a[xf:]])
put(ostem, fade(seg, 0.25, 0.45), qa['t0'])
c = tl['cold']
cs = orig[int(c['src_in'] * SR):int(c['src_out'] * SR)]
cs = cs * db(TARGET - voiced_rms_db(cs))
put(ostem, fade(cs, 0.015, 0.15), c['t0'])
ostem = np.stack([ostem, ostem], 1)

# 画面用：原声逐帧 24 频带包络（对数频率 80Hz–4kHz）
FPS = tl['fps']; nf = tl['nframes']; hop = SR // FPS
mono = ostem[:, 0]
env = np.zeros((nf, 24), np.float32)
win = np.hanning(4096)
edges = np.geomspace(80, 4000, 25); fr = np.fft.rfftfreq(4096, 1 / SR)
for i in range(nf):
    s = mono[i * hop:i * hop + 4096]
    if len(s) < 4096 or not s.any(): continue
    P = np.abs(np.fft.rfft(s * win))
    env[i] = [P[(fr >= edges[k]) & (fr < edges[k + 1])].mean() for k in range(24)]
env = np.log10(1 + env * 4) ; env /= max(np.percentile(env[env > 0], 99), 1e-6)
np.save(os.path.join(work, 'orig_env.npy'), np.clip(env, 0, 1.2))

# ------------------------------------------------------------------ AI 口播
vstem = np.zeros(N)
LS = butter(1, 160, 'lowpass', fs=SR, output='sos')
for part in ('intro', 'insight', 'summary'):
    for v in tl[part]['vo']:
        x, sr = sf.read(os.path.join(work, 'vo', v['id'] + '.wav'))
        x = x[int(v['src_in'] * SR):int((v['src_in'] + v['t1'] - v['t0']) * SR)]
        x = x + sosfilt(LS, x) * 0.35                  # 轻微低频温暖感（约 +2.5dB @ <160Hz）
        x = x * db(TARGET - voiced_rms_db(x))
        put(vstem, fade(x, 0.01, 0.05), v['t0'])
vstem = np.stack([vstem, vstem], 1)

# ------------------------------------------------------------------ 背景音乐
mstem = np.zeros((N, 2))
cache = {}
BED = {0: -22.0, 1: -23.0, 2: -19.5}   # 各段音乐（无人声时）的响度 LUFS：片头 / 投资启示 / 总结与片尾
for k, m in enumerate(tl['music']):
    if m['track'] not in cache:
        cache[m['track']] = load(os.path.join(music_dir, m['track'] + '.mp3'))
    tr = cache[m['track']]
    x = tr[int(m['src_in'] * SR):int((m['src_in'] + m['t1'] - m['t0']) * SR)]
    x = x * db(BED[k] - lufs(x))
    put(mstem, fade(x, m['fade_in'], m['fade_out']), m['t0'])

# 侧链：人声（口播 + 冷开场原声）包络 → 音乐增益
voice = np.abs(vstem[:, 0]) + np.abs(ostem[:, 0])
f = int(0.01 * SR); k = len(voice) // f
lev = np.sqrt((voice[:k * f].reshape(k, f) ** 2).mean(1))
act = (20 * np.log10(lev + 1e-9) > -42).astype(float)
look = 15                                            # 提前 150ms 开始压
act = np.maximum(act, np.concatenate([act[look:], np.zeros(look)]))
g = np.zeros_like(act); s = 0.0
for i, v in enumerate(act):                          # attack 80ms / release 650ms
    s += (v - s) * (1 - np.exp(-1 / (8 if v > s else 65)))
    g[i] = s
duck_db = -13.0 * g
gain = np.repeat(db(duck_db), f)
gain = np.concatenate([gain, np.full(N - len(gain), gain[-1])])
mstem *= gain[:, None]

# ------------------------------------------------------------------ 合成
mix = ostem + vstem + mstem + sfx
peak = np.abs(mix).max()
print(f'mix peak {20*np.log10(peak):.1f} dBFS  orig {rms_db(ostem):.1f}  vo {rms_db(vstem):.1f}  music {rms_db(mstem):.1f}  sfx {rms_db(sfx):.1f}')
if peak > db(-1.0):
    mix *= db(-1.0) / peak
for name, x in (('orig', ostem), ('vo', vstem), ('music', mstem), ('sfx', sfx)):
    sf.write(os.path.join(work, 'stems', name + '.wav'), x.astype(np.float32), SR)
sf.write(os.path.join(work, 'mix.wav'), mix.astype(np.float32), SR)
json.dump(dict(duck_db=duck_db[::10].round(2).tolist()), open(os.path.join(work, 'duck.json'), 'w'))
print('wrote', os.path.join(work, 'mix.wav'), f'{len(mix) / SR:.1f}s')
