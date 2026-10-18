"""用 Gemini TTS（gemini-3.8-flash-tts，音色 Alnilam）逐条生成旁白，并用 Gemini 转写回听校对。

python3 src/tts_gen.py WORK [ids...]      # 生成（已存在的跳过；指定 id 则强制重做）
python3 src/tts_gen.py WORK --check       # 转写所有旁白，与字幕文本比对
API key 由运行环境的代理注入（generativelanguage.googleapis.com）。
"""
import sys, os, json, base64, time, urllib.request, concurrent.futures as cf, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES

MODEL = 'gemini-3.8-flash-tts'
VOICE = 'Alnilam'
API = 'https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent'

PROFILE = """# AUDIO PROFILE: 资深中文纪录片旁白（男声，标准普通话）
## THE SCENE: 一部关于巴菲特与可口可乐 38 年投资的顶级金融纪录片。
### DIRECTOR'S NOTES
Style: 低沉、浑厚、沉稳、克制，有电影感；不夸张、不播音腔。本句情绪：{mood}。
Pace: 中等偏快的纪录片语速，吐字清晰，句中自然停顿，不拖沓。
#### TRANSCRIPT
{text}"""


def post(model, body, timeout=300):
    for k in range(6):
        try:
            req = urllib.request.Request(API.format(model), data=json.dumps(body).encode(),
                                         headers={'Content-Type': 'application/json'})
            return json.load(urllib.request.urlopen(req, timeout=timeout))
        except Exception as e:
            msg = getattr(e, 'read', lambda: b'')()[:200]
            print('  retry', k, e, msg, flush=True); time.sleep(4 * (k + 1))
    raise RuntimeError('API failed')


def gen(line, out):
    lid, ch, text, say, mood, src = line
    body = {"contents": [{"parts": [{"text": PROFILE.format(mood=mood, text=say or text)}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}}}}
    d = post(MODEL, body)
    p = d['candidates'][0]['content']['parts'][0]['inlineData']
    raw = base64.b64decode(p['data'])
    open(out, 'wb').write(raw)
    return out


def transcribe(path):
    body = {"contents": [{"parts": [
        {"inlineData": {"mimeType": "audio/wav", "data": base64.b64encode(open(path, 'rb').read()).decode()}},
        {"text": "逐字转写这段中文音频，只输出转写文本，数字用阿拉伯数字。"}]}]}
    d = post('gemini-3.8-flash', body)
    return ''.join(p.get('text', '') for p in d['candidates'][0]['content']['parts']).strip()


def norm(s):
    return re.sub(r'[\s，。、：；！？“”"\'—…·,.:;!?()（）-]', '', s)


if __name__ == '__main__':
    work = sys.argv[1]; d = os.path.join(work, 'tts'); os.makedirs(d, exist_ok=True)
    args = sys.argv[2:]
    if args and args[0] == '--check':
        res = {}
        with cf.ThreadPoolExecutor(4) as ex:
            futs = {ex.submit(transcribe, os.path.join(d, l[0] + '.wav')): l for l in LINES}
            for f in cf.as_completed(futs):
                l = futs[f]; tr = f.result(); res[l[0]] = tr
                ok = norm(tr) == norm(l[2])
                print(('OK  ' if ok else 'DIFF'), l[0], '|', l[2], '|', tr, flush=True)
        json.dump(res, open(os.path.join(d, 'transcripts.json'), 'w'), ensure_ascii=False, indent=1)
        sys.exit()
    todo = [l for l in LINES if (l[0] in args) or (not args and not os.path.exists(os.path.join(d, l[0] + '.wav')))]
    with cf.ThreadPoolExecutor(4) as ex:
        for out in ex.map(lambda l: gen(l, os.path.join(d, l[0] + '.wav')), todo):
            print('done', out, flush=True)
