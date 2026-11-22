"""旁白合成：豆包 Seed-TTS 2.0（openspeech.bytedance.com，凭证由环境代理注入）。

每句一个 wav，按内容哈希缓存到 work/tts/。随后做「标点 ↔ 停顿」对齐，
得到每个字被念到的时刻，用于字幕切分和画面提示点(cue)。
"""
import base64, hashlib, json, math, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np, soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from script import SCENES, TTS_REPL

VOICE = 'zh_male_ruyayichen_uranus_bigtts'   # 儒雅逸辰 2.0
SR = 24000
SPEECH_RATE = 15
WORK = os.path.join(HERE, '..', 'work')
CUE_RE = re.compile(r'\[([A-Za-z0-9_]+)\]')
PUNCT = '，。；：？！、—…'


def parse(u):
    """'[a]文字[b]…' -> (纯文本, {cue: 字下标})"""
    cues, out, i = {}, [], 0
    for m in re.finditer(r'\[([A-Za-z0-9_]+)\]|.', u, re.S):
        if m.group(1):
            cues[m.group(1)] = len(out)
        else:
            out.append(m.group(0))
    return ''.join(out), cues


def tts_text(s):
    for k in sorted(TTS_REPL, key=len, reverse=True):
        s = s.replace(k, TTS_REPL[k])
    return s


def synth(text, out):
    rp = {"text": text, "speaker": VOICE,
          "audio_params": {"format": "wav", "sample_rate": SR, "speech_rate": SPEECH_RATE}}
    body = {"user": {"uid": "bmjz"}, "req_params": rp}
    for attempt in range(5):
        try:
            req = urllib.request.Request(
                "https://openspeech.bytedance.com/api/v3/tts/unidirectional", data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "X-Api-App-Id": "x", "X-Api-Access-Key": "x",
                         "X-Api-Resource-Id": "seed-tts-2.0"})
            r = urllib.request.urlopen(req, timeout=180).read().decode()
            audio = b''
            for line in r.splitlines():
                if line.strip():
                    d = json.loads(line)
                    if d.get('data'):
                        audio += base64.b64decode(d['data'])
            if not audio:
                raise RuntimeError(r[:300])
            tmp = out + '.tmp.wav'
            open(tmp, 'wb').write(audio)
            os.replace(tmp, out)
            return
        except Exception as e:
            print('retry', attempt, text[:20], e, file=sys.stderr)
            time.sleep(2 + attempt * 3)
    raise RuntimeError('tts failed: ' + text)


def wav_path(text):
    h = hashlib.md5((VOICE + str(SPEECH_RATE) + text).encode()).hexdigest()[:16]
    return os.path.join(WORK, 'tts', h + '.wav')


# ---------------------------------------------------------------- 对齐
def char_weight(ch):
    if ch in PUNCT or ch in ' 　“”"\'（）()': return 0.0
    if ch.isascii() and ch.isalpha(): return 0.75
    if ch.isdigit(): return 0.9
    if ch == '.': return 0.6
    return 1.0


def trim(y):
    """去掉首尾静音和孤立的杂音（TTS 偶尔在句尾长静音后带一声气口/咔哒），返回 (y, 去掉的头部秒数)"""
    hop = 240
    n = len(y) // hop
    if n < 3: return y, 0.0
    rms = np.sqrt((y[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    act = db > db.max() - 30
    segs, i = [], 0
    while i < n:
        if act[i]:
            j = i
            while j < n and act[j]: j += 1
            segs.append([i, j]); i = j
        else:
            i += 1
    if not segs: return y, 0.0
    fr = hop / SR
    while len(segs) > 1 and (segs[-1][1] - segs[-1][0]) * fr < 0.3 and (segs[-1][0] - segs[-2][1]) * fr > 0.45:
        segs.pop()
    while len(segs) > 1 and (segs[0][1] - segs[0][0]) * fr < 0.3 and (segs[1][0] - segs[0][1]) * fr > 0.45:
        segs.pop(0)
    s = max(segs[0][0] * hop - 360, 0)
    e = min(segs[-1][1] * hop + int(0.10 * SR), len(y))
    out = y[s:e].copy()
    f = min(int(0.03 * SR), len(out) // 4)
    out[-f:] *= np.linspace(1, 0, f)
    return out, s / SR


def pauses(y):
    """检测句内停顿，返回 [(开始, 结束)] 秒"""
    hop = 240
    n = len(y) // hop
    rms = np.sqrt((y[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    ref = np.percentile(db, 90)
    quiet = db < ref - 28
    out, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]: j += 1
            if (j - i) * hop / SR >= 0.08 and i > 0 and j < n:
                out.append((i * hop / SR, j * hop / SR))
            i = j
        else:
            i += 1
    return out


def align(text, y):
    """返回每个字的开始时刻（秒，相对本句开头）。"""
    dur = len(y) / SR
    w = np.array([char_weight(c) for c in text])
    ps = pauses(y)
    # 候选锚点：标点位置（停顿应出现在标点处）
    marks = [i for i, c in enumerate(text) if c in PUNCT and 0 < i < len(text) - 1]
    tot_pause = sum(b - a for a, b in ps)
    speech = max(dur - tot_pause, 0.1)
    cw = np.concatenate([[0], np.cumsum(w)])
    exp_t = lambda i: cw[i] / max(cw[-1], 1e-6) * speech   # 不含停顿的期望时刻
    # DP：把停顿单调匹配到标点，代价 = 各段语速偏离平均语速的程度（对数）+ 未匹配惩罚
    K, M = len(marks), len(ps)
    rate = speech / max(cw[-1], 1e-6)

    def seg_cost(c0, t0, c1, t1):
        Wt = cw[c1] - cw[c0]
        T = t1 - t0
        if Wt <= 0.5:
            return 0.0 if T < 0.4 else 2.0 * T
        if T <= 0.02:
            return 50.0
        return 3.0 * abs(math.log((T / Wt) / rate)) * min(1.0, Wt / 3.0)

    SK_MARK, SK_PAUSE = 0.25, 0.6
    INF = 1e9
    D = np.full((K, M), INF)
    Bk = np.full((K, M, 2), -1, np.int32)
    for k in range(K):
        for m in range(M):
            best = seg_cost(0, 0.0, marks[k], ps[m][0]) + k * SK_MARK + m * SK_PAUSE
            bp_ = (-1, -1)
            for k2 in range(k):
                for m2 in range(m):
                    if D[k2, m2] >= INF: continue
                    c = D[k2, m2] + seg_cost(marks[k2] + 1, ps[m2][1], marks[k], ps[m][0]) + \
                        (k - k2 - 1) * SK_MARK + (m - m2 - 1) * SK_PAUSE
                    if c < best: best, bp_ = c, (k2, m2)
            D[k, m] = best; Bk[k, m] = bp_
    best = seg_cost(0, 0.0, len(text), dur) + K * SK_MARK + M * SK_PAUSE
    last = None
    for k in range(K):
        for m in range(M):
            c = D[k, m] + seg_cost(marks[k] + 1, ps[m][1], len(text), dur) + (K - k - 1) * SK_MARK + (M - m - 1) * SK_PAUSE
            if c < best: best, last = c, (k, m)
    pairs = []
    while last is not None and last[0] >= 0:
        k, m = last
        pairs.append((marks[k], ps[m]))
        nk = tuple(Bk[k, m])
        last = nk if nk[0] >= 0 else None
    pairs.sort()
    # 分段线性：锚点 (字下标, 时刻)
    anchors = [(0, 0.0)]
    for i, (a, b) in pairs:
        anchors.append((i, a)); anchors.append((i + 1, b))
    anchors.append((len(text), dur))
    times = np.zeros(len(text) + 1)
    for (i0, t0), (i1, t1) in zip(anchors, anchors[1:]):
        if i1 <= i0: continue
        seg = cw[i0:i1 + 1] - cw[i0]
        tot = seg[-1] if seg[-1] > 0 else 1
        times[i0:i1 + 1] = t0 + seg / tot * (t1 - t0)
    return times


def build():
    os.makedirs(os.path.join(WORK, 'tts'), exist_ok=True)
    jobs = []
    for sc in SCENES:
        for u in sc['say']:
            text, _ = parse(u)
            p = wav_path(tts_text(text))
            if not os.path.exists(p):
                jobs.append((tts_text(text), p))
    print('tts jobs', len(jobs))
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda j: synth(*j), jobs))


if __name__ == '__main__':
    build()
