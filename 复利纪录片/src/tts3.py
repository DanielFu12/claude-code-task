"""旁白配音。

主引擎：Google Gemini TTS（gemini-3.8-flash-tts，声音见 story.VOICE），按段落成组合成，风格指令原样放在 speech_metadata.style。
        Gemini 不返回逐字时间，所以用 faster-whisper 对合成结果做强制对齐（识别结果只用来定时，字幕文字以稿子为准），
        再在句间能量最低处切成逐句片段，段内句间停顿保留模型自己的节奏。
只用 Gemini，不设备用引擎。出错时停止并报告（退出码 2），由人工介入：
  - 429 限流按 Retry-After / 指数退避重试（每次封顶 2 分钟），网络错误与 5xx 同样重试，8 次后仍失败即停止；
  - 认证、额度、参数等其他接口错误（4xx）立即停止；
  - 同一段重合成 3 次后稿子覆盖率仍 < 0.88，或仍把停顿标签念了出来，停止。
  不换引擎、不跳过该段、不用旧音频顶替。

改编自《伯克希尔股东大会投资智慧录》E02 的 tts.py（同一套声音链路），朗读稿与分组取自 story.py。
用法：python3 src/tts3.py WORK
输出：WORK/vo/<id>.wav（48kHz 单声道，逐句）、WORK/vo/<group>.mp3（整段原始合成，Gemini）、WORK/vo_index.json
vo_index.json 每句：text / say / dur / words[[t0, t1, 字]]，段内句子另有 gap（到下一句开口的秒数）。
"""
import base64, difflib, hashlib, json, os, re, ssl, subprocess, sys, time, urllib.error, urllib.request
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from story import vo_groups, SAY, TAGS, TEMPO, STYLE_BY_GROUP, VOICE_MATCH, TTS_LAYOUT, TTS_HIDDEN, TTS_MODEL as GEMINI_MODEL, VOICE as GEMINI_VOICE, STYLE as GEMINI_STYLE

GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/interactions'
# 合成分组：(缓存名, 分组 id, 句子)。默认一个成片段落一组；story.TTS_LAYOUT 可以把一个段落拆成几组合成
TTS_GROUPS = []
for _it in vo_groups():
    if _it[1] in TTS_LAYOUT:
        TTS_GROUPS += [(name, gid, tuple(ids)) for name, gid, ids in TTS_LAYOUT[_it[1]]]
    else:
        _ids = tuple(sid for sid, _ in _it[2])
        TTS_GROUPS.append(('G_' + '_'.join(_ids), _it[1], _ids))
GROUP_OF = {sid: gid for _n, gid, ids in TTS_GROUPS for sid in ids}

work = sys.argv[1]
VD = os.path.join(work, 'vo'); os.makedirs(VD, exist_ok=True)
CA = '/root/.ccr/ca-bundle.crt'
SR = 48000
ITEMS = {sid: (GROUP_OF.get(sid, it[1]), text, 0) for it in vo_groups() for sid, text in it[2]}
ITEMS.update({sid: (GROUP_OF[sid], text, 0) for sid, text in TTS_HIDDEN.items()})    # 只为保持缓存而合成、不进成片的旧稿
PUNCT = '，。；：？！、—…“”《》·（）,.;:?! '


def content(s):
    return [c for c in s if c not in PUNCT and not c.isspace()]


def ff(*args):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', *args], check=True)


# ------------------------------------------------------------------ Gemini
def gemini_request(text, style=None):
    body = {
        'model': GEMINI_MODEL,
        'input': [{'type': 'user_input', 'content': [{
            'type': 'text', 'text': text,
            'annotations': [{'type': 'speech_metadata', 'style': style or GEMINI_STYLE}]}]}],
        'response_format': {'type': 'audio'},
        'generation_config': {'speech_config': [{'voice': GEMINI_VOICE}]},
    }
    headers = {'Content-Type': 'application/json'}
    if os.environ.get('GEMINI_API_KEY'):          # 云环境里 key 以 Network secret 形式由出口代理注入，本地运行时用环境变量
        headers['x-goog-api-key'] = os.environ['GEMINI_API_KEY']
    req = urllib.request.Request(GEMINI_URL, data=json.dumps(body).encode(), method='POST', headers=headers)
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
                              initial_prompt='以下是普通话财经纪录片旁白，提到李录、巴菲特、芒格、伯克希尔、复利。')
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


def stop(gname, text, why):
    """Gemini 出错：不换引擎、不跳过、不用旧音频顶替——停下来，把出错段落和原因报告给人工处理"""
    print(f'\n[需要人工介入] Gemini TTS 在段落 {gname} 出错：{why}\n  朗读稿：{text}\n'
          f'  已完成的段落已缓存在 {VD}，处理后重新运行本脚本会从出错段落继续。', file=sys.stderr, flush=True)
    raise SystemExit(2)


def gemini_group(gname, ids):
    say = {sid: SAY.get(sid, ITEMS[sid][1]) for sid in ids}
    text = ''.join((TAGS[sid] + ' ' if sid in TAGS else '') + say[sid] for sid in ids)
    plain = ''.join(say[sid] for sid in ids)
    base = os.path.join(VD, gname)
    style = STYLE_BY_GROUP.get(ITEMS[ids[0]][0], GEMINI_STYLE)
    key = hashlib.md5(f'{GEMINI_MODEL}|{GEMINI_VOICE}|{style}|{text}'.encode()).hexdigest()[:12]
    meta_p = base + '.json'
    gid = ITEMS[ids[0]][0]
    vm = VOICE_MATCH.get(gid)
    ntake = vm['takes'] if vm else 0
    take_keys = None
    if ntake:
        base_key = key
        key = hashlib.md5((f'{key}|takes{ntake}|ref{"+".join(vm["ref"])}' + (f'|m{vm["metric"]}' if vm.get('metric', 1) > 1 else '')).encode()).hexdigest()[:12]
        # 候选条的缓存只取决于朗读稿、声音与风格（第五版早期的候选条用的是 m2 键，同样认）
        take_keys = (base_key,) + tuple(hashlib.md5(f'{base_key}|takes{n}|ref{"+".join(vm["ref"])}|m2'.encode()).hexdigest()[:12] for n in range(1, 13))
    if os.path.exists(meta_p) and json.load(open(meta_p)).get('key') == key:
        meta = json.load(open(meta_p)); x, _ = sf.read(base + '.wav')
    elif ntake and vm.get('metric', 1) > 1:
        meta, x = takes_group2(gname, base, text, plain, style, key, vm, take_keys)
    elif ntake:
        meta, x = takes_group(gname, base, text, plain, style, key, ntake, vm['ref'])
    else:
        raw, mime, rec = synth(gname, text, plain, style, base)
        x = to_wav48(raw, mime, base)
        meta = dict(key=key, text=text, rec=rec, dur=len(x) / SR)
        json.dump(meta, open(meta_p, 'w'), ensure_ascii=False)
    return split_group(gname, ids, say, plain, meta, x)


def synth(gname, text, plain, style, base):
    """合成一条并做识别比对；不达标就重合成（最多 3 次）。返回 (raw, mime, rec)"""
    best = None
    for attempt in range(3):            # 识别比对不过关（漏读、误读、把标签念出来）就重新合成，最多 3 次
        last = None
        for k in range(8):                 # 429 / 网络错误 / 5xx：按 Retry-After 或指数退避重试
            try:
                raw, mime = gemini_request(text, style); break
            except urllib.error.HTTPError as e:
                body = e.read().decode('utf-8', 'replace')[:300] if hasattr(e, 'read') else ''
                last = f'HTTP {e.code} {e.reason} {body}'
                if e.code != 429 and e.code < 500:  # 认证 / 额度 / 参数错误：重试无用，立即停止
                    stop(gname, text, last)
                ra = e.headers.get('Retry-After') if e.headers else None
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                last, ra = f'{type(e).__name__}: {e}', None
            wait = min(float(ra), 120) if ra and str(ra).replace('.', '').isdigit() else min(15 * 2 ** k, 120)   # Retry-After 偶尔给出离谱的大值，封顶 2 分钟
            print('  retry', gname, last[:120], f'等待 {wait:.0f}s', flush=True); time.sleep(wait)
        else:
            stop(gname, text, f'退避重试 8 次后仍失败：{last}')
        x = to_wav48(raw, mime, base)
        rec = asr_chars(x, plain)
        rtxt = ''.join(c for c, _, _ in rec)
        num = set('0123456789零一二三四五六七八九十百千万亿两点分之倍%.')   # 数字写法（10% / 百分之十、17.4 / 十七点四）不算错
        sim = coverage([c for c in content(plain) if c not in num], [c for c in rtxt if c not in num])
        tag_read = bool(re.search(r'pause|breath|停顿|呼吸', rtxt, re.I))
        print(f'  {gname} try {attempt + 1}: {len(x) / SR:.1f}s  稿子覆盖率 {sim:.2f}{"  [念出了标签]" if tag_read else ""}')
        score = sim - (0.5 if tag_read else 0)
        if best is None or score > best[0]:
            best = (score, raw, mime, rec)
        if sim >= 0.88 and not tag_read: break
    else:
        stop(gname, text, f'重合成 3 次后仍不达标（最好一次的稿子覆盖率得分 {best[0]:.2f}，要求 ≥ 0.88 且不念出停顿标签）')
    _, raw, mime, rec = best
    return raw, mime, rec


def group_wav(gid):
    return os.path.join(VD, next(name for name, g, _ in TTS_GROUPS if g == gid) + '.wav')


def ref_voice(refs):
    """参照段的声纹与基频分布（第四版：G1 + G2）"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
    import voice_sim as VS
    ps = [group_wav(g) for g in refs]
    return VS, VS.embed(ps), VS.stats(ps)


def takes_group(gname, base, text, plain, style, key, ntake, refs):
    """同一 voice、同一 style 合成 ntake 条（基频分布偏离参照 > 6% 时最多再补 3 条），
    按「声纹余弦相似度 − 1.5 × 基频偏离」取与参照段最接近的一条。每条都缓存，重跑不重复调用接口"""
    VS, ref_e, ref_s = ref_voice(refs)
    cands = []
    for k in range(ntake + 3):
        if k >= ntake and min(c['df0'] for c in cands) <= 0.06: break
        xb = f'{base}.take{k + 1}'
        tj = xb + '.json'
        if os.path.exists(tj) and json.load(open(tj)).get('key') == key:
            rec = [tuple(r) for r in json.load(open(tj))['rec']]
        elif os.path.exists(xb + '.wav') and not os.path.exists(tj):   # 已合成、只缺对齐信息的一条：本地重新对齐，不再调用接口
            rec = asr_chars(sf.read(xb + '.wav')[0], plain)
            json.dump(dict(key=key, rec=rec), open(tj, 'w'), ensure_ascii=False)
        else:
            raw, mime, rec = synth(gname, text, plain, style, base)
            to_wav48(raw, mime, xb)
            json.dump(dict(key=key, rec=rec), open(tj, 'w'), ensure_ascii=False)
        st = VS.stats(xb + '.wav')
        c = dict(take=k + 1, sim=VS.sim(ref_e, VS.embed(xb + '.wav')), f0=st['f0'], centroid=st['centroid'],
                 df0=VS.f0_dev(st, ref_s), rec=rec)
        c['score'] = c['sim'] - 1.5 * c['df0']
        cands.append(c)
        print(f"  {gname} take {k + 1}: 声纹相似度 {c['sim']:.3f}  F0 {c['f0']:.0f}Hz（参照 {ref_s['f0']:.0f}Hz，分布偏离 {c['df0']:.0%}）  得分 {c['score']:.3f}", flush=True)
    best = max(cands, key=lambda c: c['score'])
    for ext in ('.src.wav', '.wav', '.mp3'):
        subprocess.run(['cp', f'{base}.take{best["take"]}{ext}', base + ext], check=True)
    x, _ = sf.read(base + '.wav')
    meta = dict(key=key, text=text, rec=best['rec'], dur=len(x) / SR, take=best['take'],
                takes=[{k: round(v, 4) if isinstance(v, float) else v for k, v in c.items() if k != 'rec'} for c in cands],
                ref=dict(groups=list(refs), f0_q=[round(v, 1) for v in ref_s['f0_q']]))
    json.dump(meta, open(base + '.json', 'w'), ensure_ascii=False)
    print(f'  {gname}: 选用 take {best["take"]}', flush=True)
    return meta, x


TRIM = 1.08                                   # 语速微调上限（±8%：配合整体 1.04 的提速，听感仍自然）


def take_audio(gname, base, text, plain, style, keys, k):
    """第 k 条候选（已缓存就直接用）：返回 (wav 路径, rec)"""
    key = keys[0]
    xb = f'{base}.take{k}'
    tj = xb + '.json'
    if os.path.exists(tj) and json.load(open(tj)).get('key') in keys:
        return xb, [tuple(r) for r in json.load(open(tj))['rec']]
    if os.environ.get('TTS_CACHE_ONLY'):              # 只用已缓存的候选条重新挑选，不调用接口
        return None, None
    raw, mime, rec = synth(gname, text, plain, style, base)
    to_wav48(raw, mime, xb)
    json.dump(dict(key=key, rec=rec), open(tj, 'w'), ensure_ascii=False)
    return xb, rec


def takes_group2(gname, base, text, plain, style, key, vm, take_keys):
    """第五版的挑选：与参照段比声纹、音色（MFCC）、基频分布、语速、亮度的综合距离（tools/voice_sim.py: distance）。
    超过 20 秒的长段按时间切成两半分别比，取较差的一半（防止段内后半截跑调）。
    至少合成 4 条；最好一条距离 ≤ 5（相当于现有段落里最一致的几段）就停，否则合成到 takes 条，仍 > 7 时最多再补 3 条。
    选中后，语速与参照差几个百分点的，用 rubberband 再微调（±8% 以内）；比较语速时按微调后的值算。"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
    import voice_sim as VS
    refs = vm['ref']
    ref_text = ''.join(SAY.get(sid, ITEMS[sid][1]) for _n, g, ids in TTS_GROUPS if g in refs for sid in ids)   # 参照音频实际念的稿子
    R = VS.profile([group_wav(g) for g in refs], ref_text)
    cands = []
    for k in range(1, vm['takes'] + 4):
        best = min((c['d'] for c in cands), default=99)
        if (k > 4 and best <= 5.0) or (k > vm['takes'] and best <= 7.0): break
        xb, rec = take_audio(gname, base, text, plain, style, take_keys, k)
        if xb is None: break
        y, _ = sf.read(xb + '.wav')
        parts = [(xb + '.wav', plain)]
        if len(y) / SR > 20:                     # 长段：按识别出的逐字时间在中点切开，两半分别比
            mid = len(y) / SR / 2
            j = min(range(len(rec)), key=lambda i: abs(rec[i][1] - mid))
            for nm, seg, txt in (('a', y[:int(rec[j][2] * SR)], ''.join(c for c, _, _ in rec[:j + 1])),
                                 ('b', y[int(rec[j][2] * SR):], ''.join(c for c, _, _ in rec[j + 1:]))):
                sf.write(f'{xb}.{nm}.wav', seg, SR); parts.append((f'{xb}.{nm}.wav', txt))
            parts = parts[1:]
        P = VS.profile(xb + '.wav', plain)
        adj = float(np.clip(R['rate'] / P['rate'], 1 / TRIM, TRIM))       # 选中后会做的语速微调，按微调后的语速比
        ds = []
        for pp, tx in parts:
            Q = VS.profile(pp, tx); Q['rate'] *= adj
            ds.append(VS.distance(Q, R, 0.5 if vm.get('metric', 1) >= 4 else 0.8))
        D, det = max(ds, key=lambda z: z[0])
        c = dict(take=k, d=round(D, 2), parts=[round(z[0], 2) for z in ds], rate=round(P['rate'], 2), ref_rate=round(R['rate'], 2),
                 pitch=round(float(P['st'][1]), 2), ref_pitch=round(float(R['st'][1]), 2), detail={a: round(b, 2) for a, b in det.items()}, rec=rec)
        cands.append(c)
        print(f"  {gname} take {k}: 综合距离 {D:.2f}（分段 {c['parts']}）  语速 {c['rate']}/{c['ref_rate']} 字/秒  中位音高 {c['pitch']:+.1f}/{c['ref_pitch']:+.1f} 半音  "
              + ' '.join(f'{a}={b:.1f}' for a, b in det.items()), flush=True)
    best = min(cands, key=lambda c: c['d'])
    for ext in ('.src.wav', '.wav', '.mp3'):
        subprocess.run(['cp', f'{base}.take{best["take"]}{ext}', base + ext], check=True)
    x, _ = sf.read(base + '.wav')
    adj = float(np.clip(best['ref_rate'] / best['rate'], 1 / TRIM, TRIM))
    meta = dict(key=key, text=text, rec=best['rec'], dur=len(x) / SR, take=best['take'], tempo_adj=round(adj, 4),
                takes=[{k: v for k, v in c.items() if k != 'rec'} for c in cands], ref=dict(groups=list(refs), metric=2))
    json.dump(meta, open(base + '.json', 'w'), ensure_ascii=False)
    print(f'  {gname}: 选用 take {best["take"]}（综合距离 {best["d"]}），语速微调 ×{adj:.3f}', flush=True)
    return meta, x


def split_group(gname, ids, say, plain, meta, x):
    tempo = TEMPO * meta.get('tempo_adj', 1.0)          # 第五版：选中条与参照的语速差在 ±8% 内微调
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
        p = os.path.join(VD, sid + '.wav')
        sf.write(p + '.raw.wav', x[a:b], SR)
        # 整体提速（rubberband：保留音高与共振峰），时间信息同比缩放
        ff('-i', p + '.raw.wav', '-af', f'rubberband=tempo={tempo}:pitchq=quality:formant=preserved:transients=smooth', p)
        os.remove(p + '.raw.wav')
        s0, s1 = spans[i]
        words = [[round((tt[j][0] - a / SR) / tempo, 3), round((tt[j][1] - a / SR) / tempo, 3), sc[j]] for j in range(s0, s1 + 1)]
        d = dict(words=words, dur=len(sf.read(p)[0]) / SR, say=say[sid])
        if i < len(ids) - 1:
            d['gap'] = round((ext[i + 1][0] - ext[i][1]) / SR / tempo, 3)
        out[sid] = d
    print(f'{gname}: {len(x) / SR:5.1f}s  对齐覆盖率 {ratio:.2f}  ' + ' '.join(f'{sid}={out[sid]["dur"]:.1f}s' for sid in ids))
    return out


res = {}
only = sys.argv[2:]                    # 可只合成指定段落（例如 G1），用于试音
for name, gid, g in TTS_GROUPS:
    if only and not any(sid in only for sid in g) and name not in only:
        continue
    res.update(gemini_group(name, g))
if only:                               # 只合成了部分段落：把这些句子并入已有的 vo_index.json（其余句子不动）
    ip = os.path.join(work, 'vo_index.json')
    idx = json.load(open(ip)) if os.path.exists(ip) else {}
    for sid, r in res.items():
        idx[sid] = dict(group=ITEMS[sid][0], text=ITEMS[sid][1], say=r['say'], dur=r['dur'], words=r['words'], engine=GEMINI_MODEL, voice=GEMINI_VOICE)
        if 'gap' in r: idx[sid]['gap'] = r['gap']
    json.dump(idx, open(ip, 'w'), ensure_ascii=False, indent=1)
    print('partial run:', list(res)); raise SystemExit(0)
assert set(res) == set(ITEMS), set(ITEMS) ^ set(res)
idx = {}
for sid, (scene, text, pause) in ITEMS.items():
    r = res[sid]
    idx[sid] = dict(group=scene, text=text, say=r['say'], dur=r['dur'], words=r['words'], engine=GEMINI_MODEL, voice=GEMINI_VOICE)
    if 'gap' in r: idx[sid]['gap'] = r['gap']
json.dump(idx, open(os.path.join(work, 'vo_index.json'), 'w'), ensure_ascii=False, indent=1)
print('Gemini TTS ·', len(idx), '句')
