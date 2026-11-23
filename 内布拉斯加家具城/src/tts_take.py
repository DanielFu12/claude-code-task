"""旁白合成（docs/旁白一致性与自然衔接.md）：整篇一次合成、一条录完；另外逐句合成“参考音频”，只用于对齐和校验，不进成片。

豆包语音合成 2.0（火山引擎 HTTP 单向流式接口，seed-tts-2.0），刘飞音色。API Key 由会话网络代理注入（X-Api-Key 请求头），代码里不保存任何密钥。
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

URL = 'https://openspeech.bytedance.com/api/v3/tts/unidirectional'
RESOURCE = 'seed-tts-2.0'
SPEAKER = 'zh_male_liufei_uranus_bigtts'          # 刘飞 2.0（系列统一音色）
SPEECH_RATE = 15                                   # 实测整篇约 5.3 字/秒（含停顿）；docs 中 25 档在本音色上偏快（约 6.2 字/秒）
CONTEXT = ('你是一位做了几十年投资的老派讲述人，在给一位朋友讲一个真实的商业传奇：一位没上过学的移民老太太，和巴菲特的一次握手。'
           '情绪真实饱满，讲到她吃苦创业时带着敬意，讲到数字和道理时清楚笃定，讲到转折时语气一顿再加重，讲到结尾时温暖有力；'
           '口语化，有呼吸感，不播音腔，语速偏快、干脆利落，全程同一个人、同一种状态')
SR = 48000


def spoken(l): return l[3] or l[2]


def key(text):
    return hashlib.sha1(json.dumps([RESOURCE, SPEAKER, SPEECH_RATE, CONTEXT, text], ensure_ascii=False).encode()).hexdigest()[:12]


def synth(text, out_wav):
    """一次请求 → out_wav（PCM16 48k 单声道）+ 同名 .json（[{text, words:[{word,startTime,endTime}]}]）"""
    add = {'context_texts': [CONTEXT], 'disable_markdown_filter': True, 'explicit_language': 'zh-cn'}
    body = {'user': {'uid': 'bamang-value'},
            'req_params': {'text': text, 'speaker': SPEAKER,
                           'audio_params': {'format': 'pcm', 'sample_rate': SR, 'speech_rate': SPEECH_RATE,
                                            'loudness_rate': 0, 'enable_subtitle': True},
                           'additions': json.dumps(add, ensure_ascii=False)}}
    for attempt in range(6):
        try:
            req = urllib.request.Request(URL, data=json.dumps(body).encode(), method='POST',
                                         headers={'Content-Type': 'application/json', 'X-Api-Resource-Id': RESOURCE,
                                                  'X-Api-Request-Id': str(uuid.uuid4()), 'X-Api-Key': 'proxy-injected'})
            raw = urllib.request.urlopen(req, timeout=600).read().decode()
            dec = json.JSONDecoder(); i = 0; audio = []; words = []
            while i < len(raw):
                while i < len(raw) and raw[i] in ' \r\n': i += 1
                if i >= len(raw): break
                o, i = dec.raw_decode(raw, i)
                if o.get('code') not in (0, 20000000, None): raise RuntimeError(str(o)[:300])
                if o.get('data'): audio.append(base64.b64decode(o['data']))
                s = o.get('sentence')
                if isinstance(s, dict) and s.get('words'): words.append(dict(text=s.get('text'), words=s['words']))
            if not audio: raise RuntimeError('empty audio')
            break
        except Exception as e:                       # 接口偶尔 502：重试
            print('  retry', attempt, str(e)[:120], flush=True); time.sleep(4 * (attempt + 1))
    else:
        raise RuntimeError('doubao tts failed')
    pcm = np.frombuffer(b''.join(audio), np.int16)
    tmp = out_wav + '.part.wav'
    sf.write(tmp, pcm, SR, subtype='PCM_16'); os.replace(tmp, out_wav)
    json.dump(words, open(out_wav[:-4] + '.json', 'w'), ensure_ascii=False)
    return out_wav


def take_text():
    return '\n'.join(spoken(l) for l in LINES)


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
        if not os.path.exists(p): jobs.append((take_text(), p))
    if '--take-only' not in args:
        jobs += [(spoken(l), ref_path(work, l)) for l in LINES if not os.path.exists(ref_path(work, l))]
    print(f'{len(jobs)} requests (take {len(take_text())} chars)', flush=True)
    t0 = time.time()
    with cf.ThreadPoolExecutor(4) as ex:
        for w in ex.map(lambda j: synth(*j), jobs):
            d = sf.info(w).duration
            print(f'done {os.path.basename(w)} {d:.1f}s  ({time.time() - t0:.0f}s)', flush=True)
