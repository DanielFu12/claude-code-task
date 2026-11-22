"""小型合成器 DSP 内核（numba 加速）。"""
import math
import numpy as np
from numba import njit
from scipy import signal

SR = 44100


# ---------------------------------------------------------------- oscillators
@njit(cache=True)
def _polyblep(t, dt):
    if t < dt:
        t /= dt
        return t + t - t * t - 1.0
    elif t > 1.0 - dt:
        t = (t - 1.0) / dt
        return t * t + t + t + 1.0
    return 0.0


@njit(cache=True)
def saw(freq, n, phase0=0.0, sr=SR):
    """带限锯齿波；freq 可以是长度 n 的数组（滑音/颤音）"""
    out = np.empty(n, np.float32)
    ph = phase0
    for i in range(n):
        f = freq[i] if freq.shape[0] > 1 else freq[0]
        dt = f / sr
        out[i] = 2.0 * ph - 1.0 - _polyblep(ph, dt)
        ph += dt
        if ph >= 1.0: ph -= 1.0
    return out


@njit(cache=True)
def square(freq, n, phase0=0.0, pw=0.5, sr=SR):
    out = np.empty(n, np.float32)
    ph = phase0
    for i in range(n):
        f = freq[i] if freq.shape[0] > 1 else freq[0]
        dt = f / sr
        v = 1.0 if ph < pw else -1.0
        v += _polyblep(ph, dt)
        p2 = ph - pw
        if p2 < 0: p2 += 1.0
        v -= _polyblep(p2, dt)
        out[i] = v
        ph += dt
        if ph >= 1.0: ph -= 1.0
    return out


def sine(freq, n, phase0=0.0):
    freq = np.broadcast_to(np.asarray(freq, np.float64), (n,))
    ph = phase0 + 2 * np.pi * np.cumsum(freq) / SR
    return np.sin(ph).astype(np.float32)


def noise(n, seed=None):
    rng = np.random.default_rng(seed)
    return rng.standard_normal(n).astype(np.float32)


# ---------------------------------------------------------------- filters
@njit(cache=True)
def svf(x, cutoff, q, mode):
    """TPT 状态变量滤波器。cutoff 可逐样本变化。mode 0=LP 1=BP 2=HP"""
    n = x.shape[0]
    out = np.empty(n, np.float32)
    ic1 = 0.0; ic2 = 0.0
    k = 1.0 / q
    for i in range(n):
        fc = cutoff[i] if cutoff.shape[0] > 1 else cutoff[0]
        if fc > SR * 0.45: fc = SR * 0.45
        if fc < 10.0: fc = 10.0
        g = math.tan(math.pi * fc / SR)
        a1 = 1.0 / (1.0 + g * (g + k))
        a2 = g * a1
        a3 = g * a2
        v3 = x[i] - ic2
        v1 = a1 * ic1 + a2 * v3
        v2 = ic2 + a2 * ic1 + a3 * v3
        ic1 = 2.0 * v1 - ic1
        ic2 = 2.0 * v2 - ic2
        if mode == 0: out[i] = v2
        elif mode == 1: out[i] = v1
        else: out[i] = x[i] - k * v1 - v2
    return out


def lp(x, fc, q=0.707):
    return svf(x.astype(np.float32), np.atleast_1d(np.asarray(fc, np.float32)), q, 0)


def hp(x, fc, q=0.707):
    return svf(x.astype(np.float32), np.atleast_1d(np.asarray(fc, np.float32)), q, 2)


def bp(x, fc, q=1.0):
    return svf(x.astype(np.float32), np.atleast_1d(np.asarray(fc, np.float32)), q, 1)


def sos_filter(x, kind, f, order=2):
    sos = signal.butter(order, f, btype=kind, fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=0).astype(np.float32)


def shelf(x, f, gain_db, kind='low'):
    """RBJ 搁架滤波器"""
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f / SR
    cs, sn = np.cos(w0), np.sin(w0)
    al = sn / 2 * np.sqrt(2)
    if kind == 'low':
        b = [A * ((A + 1) - (A - 1) * cs + 2 * np.sqrt(A) * al), 2 * A * ((A - 1) - (A + 1) * cs),
             A * ((A + 1) - (A - 1) * cs - 2 * np.sqrt(A) * al)]
        a = [(A + 1) + (A - 1) * cs + 2 * np.sqrt(A) * al, -2 * ((A - 1) + (A + 1) * cs),
             (A + 1) + (A - 1) * cs - 2 * np.sqrt(A) * al]
    else:
        b = [A * ((A + 1) + (A - 1) * cs + 2 * np.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * cs),
             A * ((A + 1) + (A - 1) * cs - 2 * np.sqrt(A) * al)]
        a = [(A + 1) - (A - 1) * cs + 2 * np.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * cs),
             (A + 1) - (A - 1) * cs - 2 * np.sqrt(A) * al]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0).astype(np.float32)


def peak(x, f, gain_db, q=1.0):
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f / SR
    al = np.sin(w0) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w0), 1 - al * A]
    a = [1 + al / A, -2 * np.cos(w0), 1 - al / A]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0).astype(np.float32)


# ---------------------------------------------------------------- dynamics
@njit(cache=True)
def follow(x, att, rel):
    """包络跟随（x 为非负）；att/rel 单位秒"""
    n = x.shape[0]
    out = np.empty(n, np.float32)
    a = math.exp(-1.0 / (att * SR)); r = math.exp(-1.0 / (rel * SR))
    e = 0.0
    for i in range(n):
        v = x[i]
        if v > e: e = a * e + (1 - a) * v
        else: e = r * e + (1 - r) * v
        out[i] = e
    return out


def compress(x, thr_db=-18, ratio=3.0, att=0.01, rel=0.15, makeup_db=0.0, knee=6.0):
    """立体声 RMS 压缩（联动）"""
    m = np.abs(x).max(1) if x.ndim == 2 else np.abs(x)
    env = follow((m ** 2).astype(np.float32), att, rel)
    lvl = 10 * np.log10(env + 1e-12)
    over = lvl - thr_db
    gr = np.where(over <= -knee / 2, 0.0,
                  np.where(over >= knee / 2, over * (1 - 1 / ratio),
                           (over + knee / 2) ** 2 / (2 * knee) * (1 - 1 / ratio)))
    g = 10 ** ((-gr + makeup_db) / 20)
    return (x * (g[:, None] if x.ndim == 2 else g)).astype(np.float32)


def limiter(x, ceiling=0.95, look=0.004, rel=0.08):
    m = np.abs(x).max(1)
    L = int(look * SR)
    # 前瞻：取未来窗口的最大值
    from scipy.ndimage import maximum_filter1d
    pk = maximum_filter1d(m, size=2 * L + 1, origin=0)
    need = np.maximum(pk / ceiling, 1.0)
    r = math.exp(-1.0 / (rel * SR))
    gs = _gain_smooth((1.0 / need).astype(np.float32), r)
    # 前瞻窗口内平滑起始，避免增益突变的咔哒声
    gs = np.minimum(gs, np.convolve(gs, np.ones(L) / L, 'same').astype(np.float32))
    return np.clip(x * gs[:, None], -ceiling, ceiling).astype(np.float32)


@njit(cache=True)
def _gain_smooth(target, r):
    n = target.shape[0]
    out = np.empty(n, np.float32)
    cur = 1.0
    for i in range(n):
        t = target[i]
        if t < cur: cur = t
        else: cur = r * cur + (1 - r) * t
        out[i] = cur
    return out


# ---------------------------------------------------------------- reverb / delay
def make_ir(seconds=2.5, predelay=0.02, damp=6000, seed=1, early=True):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    ir = np.zeros((n + int(predelay * SR), 2), np.float32)
    for c in range(2):
        nz = rng.standard_normal(n).astype(np.float32)
        env = np.exp(-t * 6.9 / seconds)            # -60 dB at `seconds`
        # 高频衰减更快：分两段滤波混合
        lo = lp(nz, damp * 0.35)
        hi = nz - lo
        tail = lo * env + hi * np.exp(-t * 6.9 / (seconds * 0.45))
        ir[int(predelay * SR):, c] = tail
        if early:
            for k in range(10):
                d = int(rng.uniform(0.004, 0.06) * SR)
                ir[int(predelay * SR) + d, c] += rng.uniform(0.2, 0.6) * (1 if rng.random() > .5 else -1)
    ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    return ir


def reverb(x, ir, wet=0.25):
    out = np.zeros((x.shape[0] + ir.shape[0] - 1, 2), np.float32)
    for c in range(2):
        out[:, c] = signal.fftconvolve(x[:, c], ir[:, c])
    return (out[:x.shape[0]] * wet).astype(np.float32)


def delay(x, t_l, t_r, fb=0.35, n=6, lpf=4000):
    out = np.zeros_like(x)
    dl, dr = int(t_l * SR), int(t_r * SR)
    src = lp(x.mean(1), lpf)
    g = 1.0
    for k in range(1, n + 1):
        g *= fb
        # 乒乓：奇数次在左，偶数次在右
        d = dl * ((k + 1) // 2) + dr * (k // 2)
        if d >= x.shape[0]: break
        ch = 0 if k % 2 else 1
        out[d:, ch] += src[:x.shape[0] - d] * g
    return out


def tanh_sat(x, drive=1.0):
    return (np.tanh(x * drive) / np.tanh(drive)).astype(np.float32)


# ---------------------------------------------------------------- utilities
def env_adsr(n, a, d, s, r, sr=SR, hold=None):
    """ADSR；hold 为按住时长（秒），之后释放。返回长度 n"""
    t = np.arange(n) / sr
    if hold is None: hold = n / sr - r
    e = np.where(t < a, t / max(a, 1e-4),
                 np.where(t < a + d, 1 - (1 - s) * (t - a) / max(d, 1e-4), s))
    rel = np.clip((t - hold) / max(r, 1e-4), 0, 1)
    e = e * np.where(t > hold, (1 - rel) ** 2, 1.0)
    return e.astype(np.float32)


def pan_gains(p):
    """p in [-1,1] -> (gl, gr) 等功率"""
    a = (p + 1) * np.pi / 4
    return np.cos(a), np.sin(a)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)
