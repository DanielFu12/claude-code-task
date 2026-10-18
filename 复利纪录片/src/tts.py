"""旁白生成：只使用 Gemini TTS `gemini-3.8-flash-tts`。

每条旁白生成后，用 Gemini 做一次语音转写，与原文逐字比对；读错、漏读、把提示词读出来都会重试。
用法：python3 src/tts.py [VOICE] [ids...]     输出 assets/voice/Nxx.wav（24kHz 单声道）
"""
import base64, concurrent.futures as cf, difflib, json, os, re, sys, time, urllib.request, wave
import numpy as np, soundfile as sf

sys.path.insert(0, os.path.dirname(__file__))
from script import NARRATION

TTS_MODEL = 'gemini-3.8-flash-tts'
ASR_MODEL = 'gemini-3.8-flash'
API = 'https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent'
OUT = os.path.join(os.path.dirname(__file__), '..', 'assets', 'voice')
STYLE = ('# AUDIO PROFILE: 纪录片旁白（男声）\n'
         '### DIRECTOR\'S NOTES\n'
         'Style: low, calm, warm, restrained and confident Mandarin documentary narration.\n'
         'Pacing: natural and steady, about 4.5 Chinese characters per second; brief pauses only at punctuation.\n'
         'Read ONLY the transcript below, nothing else.\n'
         '#### TRANSCRIPT\n')
BUDGET = int(os.environ.get('TTS_BUDGET', '60'))     # 每次运行最多请求次数（gemini-3.8-flash-tts 每日配额 100 次）
_used = [0]


def call(model, body, timeout=300):
    for attempt in range(6):
        try:
            req = urllib.request.Request(API.format(model), data=json.dumps(body).encode(),
                                         headers={'Content-Type': 'application/json'})
            return json.load(urllib.request.urlopen(req, timeout=timeout))
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors='ignore')
            if e.code == 429 and 'per_day' in msg:
                raise RuntimeError(f'{model} 每日配额已用完：' + msg[:300])
            print('  retry', model, e.code, file=sys.stderr); time.sleep(8 * (attempt + 1))
        except Exception as e:
            print('  retry', model, e, file=sys.stderr); time.sleep(5 * (attempt + 1))
    raise RuntimeError('API failed')


def synth(text, voice, path):
    if _used[0] >= BUDGET: raise RuntimeError('TTS budget exhausted')
    _used[0] += 1
    d = call(TTS_MODEL, {'contents': [{'parts': [{'text': f'{STYLE}{text}'}]}],
                         'generationConfig': {'responseModalities': ['AUDIO'],
                                              'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice}}}}})
    assert d.get('modelVersion', TTS_MODEL).startswith(TTS_MODEL), d.get('modelVersion')
    raw = base64.b64decode(d['candidates'][0]['content']['parts'][0]['inlineData']['data'])
    if raw[:4] == b'RIFF':
        open(path, 'wb').write(raw)
    else:
        w = wave.open(path, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(raw); w.close()


def transcribe(path):
    d = call(ASR_MODEL, {'contents': [{'parts': [
        {'inline_data': {'mime_type': 'audio/wav', 'data': base64.b64encode(open(path, 'rb').read()).decode()}},
        {'text': 'Transcribe ALL speech in this audio verbatim, including any English words (output only the transcript).'}]}], 'generationConfig': {'temperature': 0}})
    return ''.join(p.get('text', '') for p in d['candidates'][0]['content']['parts'])


def norm(s):
    s = s.replace('AI', '爱').replace('ai', '爱')
    return re.sub(r'[^一-鿿爱]', '', s)


def trim(path, pad=0.08):
    y, sr = sf.read(path)
    env = np.abs(y) > 10 ** (-42 / 20)
    idx = np.where(env)[0]
    a, b = max(idx[0] - int(pad * sr), 0), min(idx[-1] + int(pad * 2 * sr), len(y))
    sf.write(path, y[a:b], sr)
    return (b - a) / sr


def make(nid, voice):
    text = NARRATION[nid]
    path = os.path.join(OUT, f'{nid}.wav')
    best = None
    for k in range(6):
        tmp = path + f'.try{k}.wav'
        synth(text, voice, tmp)
        dur = trim(tmp)
        heard = transcribe(tmp)
        sim = difflib.SequenceMatcher(None, norm(text), norm(heard)).ratio()
        cps = len(norm(text)) / dur
        print(f'{nid} try{k} sim={sim:.3f} dur={dur:.2f}s cps={cps:.2f} heard={heard.strip()[:60]}')
        ok = 3.3 < cps < 6.5
        if not ok: sim *= 0.5          # 时长异常（常见原因：把提示词也读了出来）
        if best is None or sim > best[0]: best = (sim, tmp, dur)
        if sim >= 0.96 and ok: break
    os.replace(best[1], path)
    for f in os.listdir(OUT):
        if f.startswith(nid + '.wav.try'): os.remove(os.path.join(OUT, f))
    return nid, best[0], best[2]


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    voice = sys.argv[1] if len(sys.argv) > 1 else 'Orus'
    ids = sys.argv[2:] or list(NARRATION)
    with cf.ThreadPoolExecutor(2) as ex:
        res = list(ex.map(lambda i: make(i, voice), ids))
    meta_p = os.path.join(OUT, 'voice.json')
    meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {}
    for nid, sim, dur in res: meta[nid] = dict(sim=round(sim, 3), dur=round(dur, 3), voice=voice, model=TTS_MODEL)
    json.dump(meta, open(meta_p, 'w'), ensure_ascii=False, indent=1)
    print('total speech', round(sum(v['dur'] for v in meta.values()), 1), 's')
