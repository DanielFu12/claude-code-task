"""旁白合成（docs/旁白一致性与自然衔接.md）：整篇一次合成、一条录完；另外逐句合成“参考音频”，只用于对齐和校验，不进成片。

豆包语音合成（v4 起 3.0 流式接口，刘飞 3.0 音色；见下方常量）。API Key 由会话网络代理注入（X-Api-Key 请求头），代码里不保存任何密钥。
  · 整篇：全部旁白按顺序用换行连接，一次请求 → WORK/vo_take/take_<hash>.wav（PCM 48k）+ .json（逐字时间戳，接口返回时）
  · 参考：每句单独请求（同音色、同语速、同一条语气提示）→ WORK/vo_ref/<id>.wav
  · 按“文本 + 语气 + 语速”哈希缓存，改了哪句只重做哪句的参考；整篇只要有一句改动就整条重录（不拼接）。
python3 src/tts_take.py WORK [--refs-only | --take-only]
"""
import sys, os, json, base64, time, uuid, hashlib, subprocess, concurrent.futures as cf
import urllib.request
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES

# v4 起：豆包语音合成 3.0（火山引擎 voice.cn-beijing.volces.com 流式接口，doubao-seed-tts-3.0），刘飞 3.0 音色（用户指定）。
# 原 2.0 接口（openspeech.bytedance.com, seed-tts-2.0）自 2026-11-26 起返回 45000030 “requested resource not granted”。
URL = 'https://voice.cn-beijing.volces.com/api/v3/text-to-speech/%s/streaming'
RESOURCE = 'doubao-seed-tts-3.0'
SPEAKER = 'multi_male_liufei2_v3_uranus_bigtts'    # 刘飞 3.0
SPEECH_RATE = 1.06                                 # voice_settings.speed；实测默认语速有声部分约 5.8–6.1 字/秒，与 2.0 档 2（5.76）相当
CONTEXT = ('纪录片旁白，像在给朋友讲一个真实的投资故事：沉稳、自然、口语化，语气有起伏，重点处稍作停顿，不夸张、不播音腔。'
           '全程同一个人、同一种状态。')            # 前几期原句 + 一句一致性要求（整篇一条录完）
SR = 48000


def spoken(l): return l[3] or l[2]


def key(text):
    return hashlib.sha1(json.dumps([RESOURCE, SPEAKER, SPEECH_RATE, CONTEXT, text], ensure_ascii=False).encode()).hexdigest()[:12]


def synth(text, out_wav):
    """一次请求 → out_wav（PCM16 48k 单声道，由接口返回的 MP3 解码）+ 同名 .json（[{text, words:[{word,startTime,endTime}]}]，时间为整条录音内的绝对时间）"""
    body = {'text': text, 'model_id': RESOURCE, 'enable_subtitle': True, 'voice_settings': {'speed': SPEECH_RATE}}
    for attempt in range(6):
        try:
            req = urllib.request.Request(URL % SPEAKER, data=json.dumps(body, ensure_ascii=False).encode(), method='POST',
                                         headers={'Content-Type': 'application/json', 'X-Api-Key': 'proxy-injected'})
            raw = urllib.request.urlopen(req, timeout=900).read().decode()
            audio, words = [], []
            for line in raw.splitlines():
                if not line.strip(): continue
                o = json.loads(line)
                if o.get('event') == 'error': raise RuntimeError(str(o)[:300])
                if o.get('audio'): audio.append(base64.b64decode(o['audio']))
                if o.get('words'): words.append(dict(text=o.get('text'), words=[dict(word=w['word'], startTime=w['startTime'], endTime=w['endTime']) for w in o['words']]))
            if not audio: raise RuntimeError('empty audio')
            break
        except Exception as e:                       # 接口偶尔 5xx：重试
            print('  retry', attempt, str(e)[:160], flush=True); time.sleep(5 * (attempt + 1))
    else:
        raise RuntimeError('doubao tts failed')
    mp3 = out_wav + '.part.mp3'; tmp = out_wav + '.part.wav'
    open(mp3, 'wb').write(b''.join(audio))
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', mp3, '-ar', str(SR), '-ac', '1', '-c:a', 'pcm_s16le', tmp], check=True)
    os.replace(tmp, out_wav); os.remove(mp3)
    json.dump(words, open(out_wav[:-4] + '.json', 'w'), ensure_ascii=False)
    return out_wav


def take_text():
    return '\n'.join(spoken(l) for l in LINES)


# v4：3.0 音色在长文本里音高一路上扬（整篇一条录完，十分钟内升 5–8 个半音，前 2–3 分钟稳定），
# 改为“每章一条录完”：每段仍是一次请求、段内不拼接；段与段只在章节卡处相接（中间本来就有章节卡与配乐）。
# 第三章较长，在“但要分清”（c3n1）处分成两条。
CHUNK_START = {'c3n1'}


def take_chunks():
    out, cur, prev = [], [], None
    for l in LINES:
        if cur and (l[1] != prev or l[0] in CHUNK_START): out.append(cur); cur = []
        cur.append(l); prev = l[1]
    if cur: out.append(cur)
    return out


CHUNK_GAP = 1.0      # 段间静音（秒），对齐时就是天然句界


def synth_take(out_wav):
    """按章分段合成 → 拼成一条 take（段间 CHUNK_GAP 秒静音），逐字时间戳平移到整条时间轴"""
    ys, words, t = [], [], 0.0
    for k, ch in enumerate(take_chunks()):
        part = out_wav[:-4] + f'.chunk{k}.wav'
        if not os.path.exists(part): synth('\n'.join(spoken(l) for l in ch), part)
        y, _ = sf.read(part, dtype='float32')
        js = json.load(open(part[:-4] + '.json'))
        for s_ in js:
            words.append(dict(text=s_['text'], words=[dict(word=w['word'], startTime=w['startTime'] + t, endTime=w['endTime'] + t) for w in s_['words']]))
        ys += [y, np.zeros(int(CHUNK_GAP * SR), np.float32)]; t += len(y) / SR + CHUNK_GAP
        print(f'  chunk {k}: {ch[0][0]}…{ch[-1][0]}  {len(y) / SR:.1f}s', flush=True)
    sf.write(out_wav, np.concatenate(ys), SR, subtype='PCM_16')
    json.dump(words, open(out_wav[:-4] + '.json', 'w'), ensure_ascii=False)
    return out_wav


def take_path(work):
    return os.path.join(work, 'vo_take', 'take_%s.wav' % key(take_text()))


def ref_path(work, l):
    return os.path.join(work, 'vo_ref', '%s_%s.wav' % (l[0], key(spoken(l))))


if __name__ == '__main__':
    work = sys.argv[1]; args = sys.argv[2:]
    os.makedirs(os.path.join(work, 'vo_take'), exist_ok=True); os.makedirs(os.path.join(work, 'vo_ref'), exist_ok=True)
    jobs = []
    if '--refs-only' not in args:
        p = take_path(work)
        if not os.path.exists(p): synth_take(p)
    if '--take-only' not in args:
        jobs += [(spoken(l), ref_path(work, l)) for l in LINES if not os.path.exists(ref_path(work, l))]
    print(f'{len(jobs)} requests (take {len(take_text())} chars)', flush=True)
    t0 = time.time()
    with cf.ThreadPoolExecutor(2) as ex:
        for w in ex.map(lambda j: synth(*j), jobs):
            d = sf.info(w).duration
            print(f'done {os.path.basename(w)} {d:.1f}s  ({time.time() - t0:.0f}s)', flush=True)
