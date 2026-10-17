"""旁白配音。

主引擎：Google Gemini TTS（gemini-3.8-flash-tts，声音 charon），按段落成组合成，风格指令原样放在 speech_metadata.style。
        Gemini 不返回逐字时间，所以用 faster-whisper 对合成结果做强制对齐（识别结果只用来定时，字幕文字以稿子为准），
        再在句间能量最低处切成逐句片段，段内句间停顿保留模型自己的节奏。
备用引擎：微软 Edge 神经网络语音（云健），逐句合成并取逐词边界（TTS_ENGINE=edge，或没有 GEMINI_API_KEY 时）。

用法：python3 src/tts.py WORK
输出：WORK/vo/<id>.wav（48kHz 单声道，逐句）、WORK/vo/<group>.mp3（整段原始合成，Gemini）、WORK/vo_index.json
vo_index.json 每句：scene / text / say / pause / dur / words[[t0, t1, 字]]，段内句子另有 gap（到下一句开口的秒数）。
"""
import base64, difflib, hashlib, json, os, re, ssl, subprocess, sys, time, urllib.request
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import (INTRO, INSIGHT, SUMMARY, SAY, VOICE, RATE, PITCH, GEMINI_MODEL, GEMINI_VOICE, GEMINI_STYLE, GEMINI_URL,
                    TTS_GROUPS, TAGS)

work = sys.argv[1]
VD = os.path.join(work, 'vo'); os.makedirs(VD, exist_ok=True)
CA = '/root/.ccr/ca-bundle.crt'
SR = 48000
ITEMS = {sid: (scene, text, pause) for sid, scene, text, pause in INTRO + INSIGHT + [SUMMARY]}
ENGINE = os.environ.get('TTS_ENGINE') or ('gemini' if os.environ.get('GEMINI_API_KEY') else 'edge')
PUNCT = '，。；：？！、—…“”《》·（）,.;:?! '


def content(s):
    return [c for c in s if c not in PUNCT and not c.isspace()]


def ff(*args):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', *args], check=True)


# ------------------------------------------------------------------ Gemini
def gemini_request(text):
    body = {
        'model': GEMINI_MODEL,
        'input': [{'type': 'user_input', 'content': [{
            'type': 'text', 'text': text,
            'annotations': [{'type': 'speech_metadata', 'style': GEMINI_STYLE}]}]}],
        'response_format': {'type': 'audio'},
        'generation_config': {'speech_config': [{'voice': GEMINI_VOICE}]},
    }
    req = urllib.request.Request(GEMINI_URL, data=json.dumps(body).encode(), method='POST', headers={
        'x-goog-api-key': os.environ['GEMINI_API_KEY'], 'Content-Type': 'application/json'})
    ctx = ssl.create_default_context(cafile=CA if os.path.exists(CA) else None)
    with urllib.request.urlopen(req, timeout=180, context=ctx) as r:
        resp = json.load(r)
    found = []

    def walk(o):                       # 返回结构：steps[].content[] 里 type == "audio" 的 data（base64）
        if isinstance(o, dict):
            if o.get('type') == 'audio' and o.get('data'):
                found.append(o)
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(resp.get('steps', resp))
    if not found:
        raise RuntimeError('no audio in response: ' + json.dumps(resp)[:400])
    raw = b''.join(base64.b64decode(a['data']) for a in found)
    mime = found[0].get('mime_type') or found[0].get('mimeType') or ''
    return raw, mime


def to_wav48(raw, mime, base):
    """保存原始返回（WAV，或无文件头的 16-bit PCM），再转 48kHz 单声道 WAV 和 MP3"""
    src = base + '.src.wav'
    if raw[:4] == b'RIFF':
        open(src, 'wb').write(raw)
    else:
        rate = int(re.search(r'rate=(\d+)', mime).group(1)) if re.search(r'rate=(\d+)', mime) else 24000
        pcm = np.frombuffer(raw[:len(raw) // 2 * 2], '<i2').astype(np.float32) / 32768
        sf.write(src, pcm, rate)
    ff('-i', src, '-ac', '1', '-ar', str(SR), base + '.wav')
    ff('-i', src, '-ac', '1', '-c:a', 'libmp3lame', '-b:a', '192k', base + '.mp3')
    x, _ = sf.read(base + '.wav')
    return x


_ASR = None


def asr_chars(x, prompt):
    """faster-whisper 中文逐词时间 → 逐字时间 [(字, t0, t1)]"""
    global _ASR
    if _ASR is None:
        from faster_whisper import WhisperModel
        _ASR = WhisperModel('medium', device='cpu', compute_type='int8')
    from scipy.signal import resample_poly
    a16 = resample_poly(x, 1, 3).astype(np.float32)
    # 只给一句简短的领域提示：把整段稿子当 prompt 会诱发 Whisper 在音频结束后“复读”稿子
    segs, _ = _ASR.transcribe(a16, language='zh', word_timestamps=True, beam_size=5, condition_on_previous_text=False,
                              initial_prompt='以下是普通话财经纪录片旁白，提到巴菲特、芒格、伯克希尔。')
    out = []
    dur = len(x) / SR
    for s in segs:
        for w in s.words:
            if w.end - w.start < 0.01 or w.start > dur - 0.05: continue    # 丢掉零时长 / 越界的幻觉词
            cs = content(w.word)
            for j, c in enumerate(cs):
                out.append((c, w.start + (w.end - w.start) * j / len(cs), w.start + (w.end - w.start) * (j + 1) / len(cs)))
    return out


def coverage(say_chars, rec_chars):
    """稿子里能在识别结果中按顺序对上的字所占比例（多识别出来的字不扣分）"""
    sm = difflib.SequenceMatcher(None, say_chars, rec_chars, autojunk=False)
    return sum(b.size for b in sm.get_matching_blocks()) / max(len(say_chars), 1)


def align(say_chars, rec):
    """稿子的每个内容字 → 时间（对不上的按前后插值）"""
    sm = difflib.SequenceMatcher(None, say_chars, [c for c, _, _ in rec], autojunk=False)
    tt = [None] * len(say_chars)
    for b in sm.get_matching_blocks():
        for j in range(b.size):
            tt[b.a + j] = rec[b.b + j][1:]
    known = [i for i, v in enumerate(tt) if v]
    for i in range(len(tt)):
        if tt[i] is None:
            lo = max([k for k in known if k < i], default=None); hi = min([k for k in known if k > i], default=None)
            if lo is None: tt[i] = tt[hi]
            elif hi is None: tt[i] = tt[lo]
            else:
                f = (i - lo) / (hi - lo); a, b = tt[lo][1], tt[hi][0]
                tt[i] = (a + (b - a) * f, a + (b - a) * f)
    return tt, coverage(say_chars, [c for c, _, _ in rec])


def voiced_extent(x, a, b):
    """[a, b) 采样区间内有声部分（-45dB），带 40ms / 100ms 余量"""
    seg = x[a:b]; e = np.abs(seg) > 10 ** (-45 / 20)
    if not e.any(): return a, b
    i = int(np.argmax(e)); j = len(seg) - int(np.argmax(e[::-1]))
    return a + max(0, i - int(0.04 * SR)), a + min(len(seg), j + int(0.10 * SR))


def gemini_group(ids):
    say = {sid: SAY.get(sid, ITEMS[sid][1]) for sid in ids}
    text = ''.join((TAGS[sid] + ' ' if sid in TAGS else '') + say[sid] for sid in ids)
    plain = ''.join(say[sid] for sid in ids)
    gname = 'G_' + '_'.join(ids)
    base = os.path.join(VD, gname)
    key = hashlib.md5(f'{GEMINI_MODEL}|{GEMINI_VOICE}|{GEMINI_STYLE}|{text}'.encode()).hexdigest()[:12]
    meta_p = base + '.json'
    if os.path.exists(meta_p) and json.load(open(meta_p)).get('key') == key:
        meta = json.load(open(meta_p)); x, _ = sf.read(base + '.wav')
    else:
        best = None
        for attempt in range(3):            # 识别比对不过关（漏读、误读、把标签念出来）就重新合成，最多 3 次
            for k in range(4):
                try:
                    raw, mime = gemini_request(text); break
                except Exception as e:
                    print('  retry', gname, str(e)[:200]); time.sleep(2 ** (k + 1))
            else:
                raise SystemExit(f'Gemini TTS failed for {gname}')
            x = to_wav48(raw, mime, base)
            rec = asr_chars(x, plain)
            rtxt = ''.join(c for c, _, _ in rec)
            num = set('0123456789零一二三四五六七八九十百千万亿两点')     # 数字写法（2500万 / 两千五百万）不算错
            sim = coverage([c for c in content(plain) if c not in num], [c for c in rtxt if c not in num])
            tag_read = bool(re.search(r'pause|breath|停顿|呼吸', rtxt, re.I))
            print(f'  {gname} try {attempt + 1}: {len(x) / SR:.1f}s  稿子覆盖率 {sim:.2f}{"  [念出了标签]" if tag_read else ""}')
            score = sim - (0.5 if tag_read else 0)
            if best is None or score > best[0]:
                best = (score, raw, mime, rec)
            if sim >= 0.88 and not tag_read: break
        _, raw, mime, rec = best
        x = to_wav48(raw, mime, base)
        meta = dict(key=key, text=text, rec=rec, dur=len(x) / SR)
        json.dump(meta, open(meta_p, 'w'), ensure_ascii=False)
    # 对齐并切句
    sc = content(plain)
    tt, ratio = align(sc, [tuple(r) for r in meta['rec']])
    spans, k = [], 0
    for sid in ids:
        n = len(content(say[sid])); spans.append((k, k + n - 1)); k += n
    st = [tt[a][0] for a, b in spans]; en = [tt[b][1] for a, b in spans]
    f = SR // 100
    lev = np.sqrt((x[:len(x) // f * f].reshape(-1, f) ** 2).mean(1))
    cuts = [0]
    for i in range(len(ids) - 1):                      # 句间：在能量最低的 10ms 处切
        lo, hi = int((en[i] - 0.15) * 100), int((st[i + 1] + 0.15) * 100)
        lo, hi = max(lo, 0), max(hi, lo + 1)
        cuts.append((lo + int(np.argmin(lev[lo:hi]))) * f)
    cuts.append(len(x))
    out = {}
    ext = [voiced_extent(x, cuts[i], cuts[i + 1]) for i in range(len(ids))]
    for i, sid in enumerate(ids):
        a, b = cuts[i], cuts[i + 1]
        sf.write(os.path.join(VD, sid + '.wav'), x[a:b], SR)
        s0, s1 = spans[i]
        words = [[round(tt[j][0] - a / SR, 3), round(tt[j][1] - a / SR, 3), sc[j]] for j in range(s0, s1 + 1)]
        d = dict(words=words, dur=(b - a) / SR, say=say[sid])
        if i < len(ids) - 1:
            d['gap'] = round((ext[i + 1][0] - ext[i][1]) / SR, 3)
        out[sid] = d
    print(f'{gname}: {len(x) / SR:5.1f}s  对齐覆盖率 {ratio:.2f}  ' + ' '.join(f'{sid}={out[sid]["dur"]:.1f}s' for sid in ids))
    return out


# ------------------------------------------------------------------ Edge（备用）
def edge_all():
    import asyncio
    if os.path.exists(CA):
        import certifi
        certifi.where = lambda: CA
    import edge_tts

    async def synth(sid, text, rate):
        base = os.path.join(VD, sid)
        c = edge_tts.Communicate(text, VOICE, rate=rate, pitch=PITCH, boundary='WordBoundary')
        audio, words = bytearray(), []
        async for ch in c.stream():
            if ch['type'] == 'audio': audio += ch['data']
            elif ch['type'] == 'WordBoundary':
                words.append([ch['offset'] / 1e7, (ch['offset'] + ch['duration']) / 1e7, ch['text']])
        open(base + '.mp3', 'wb').write(audio)
        ff('-i', base + '.mp3', '-ac', '1', '-ar', str(SR), base + '.wav')
        return dict(words=words, dur=len(sf.read(base + '.wav')[0]) / SR, say=text)

    async def main():
        return {sid: await synth(sid, SAY.get(sid, ITEMS[sid][1]), '-14%' if sid == 'M' else RATE) for sid in ITEMS}
    return asyncio.run(main())


if ENGINE == 'gemini':
    res = {}
    for g in TTS_GROUPS:
        res.update(gemini_group(g))
    assert set(res) == set(ITEMS), set(ITEMS) ^ set(res)
else:
    res = edge_all()
idx = {}
for sid, (scene, text, pause) in ITEMS.items():
    r = res[sid]
    idx[sid] = dict(scene=scene, text=text, say=r['say'], pause=pause, dur=r['dur'], words=r['words'], engine=ENGINE)
    if 'gap' in r: idx[sid]['gap'] = r['gap']
json.dump(idx, open(os.path.join(work, 'vo_index.json'), 'w'), ensure_ascii=False, indent=1)
print('engine', ENGINE, '·', len(idx), '句')
