"""豆包语音合成 2.0 旁白（v4 起取 PCM：mp3 分块拼接解码会丢帧，导致逐字时间戳与音频错位）（火山引擎 HTTP 单向流式接口）。
API Key 由会话网络代理注入（X-Api-Key 请求头），代码里不保存任何密钥。
按段落（tts_passage.PASSAGES）整段合成：同一段一次读完，句间衔接自然；返回逐字时间戳一并保存。

python3 src/tts_doubao.py WORK [pid ...] [--takes N]     # → work/tts_db/<pid>_<k>.mp3 / .wav / .json
"""
import sys, os, json, base64, time, uuid, subprocess, concurrent.futures as cf
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tts_passage import PASSAGES, TEASE_P, spoken

URL = 'https://openspeech.bytedance.com/api/v3/tts/unidirectional'
RESOURCE = 'volc.seedtts.default'                 # 账号开通的豆包语音合成 2.0 资源
SPEAKER = 'zh_male_liufei_uranus_bigtts'      # 刘飞 2.0（用户试听后选定）
CONTEXT = '像在给朋友讲一个真实的投资故事：沉稳、自然、口语化，有悬念感，不夸张。'
SPEECH_RATE = 5
SILENCE = 150


def synth(text, out_mp3, speech_rate=None):
    speech_rate = SPEECH_RATE if speech_rate is None else speech_rate
    body = {'user': {'uid': 'bamang-value'},
            'req_params': {'text': text, 'speaker': SPEAKER,
                           'audio_params': {'format': 'pcm', 'sample_rate': 48000, 'speech_rate': speech_rate,
                                            'loudness_rate': 0, 'enable_subtitle': True},
                           'context_texts': [CONTEXT], 'post_process': {'pitch': 0},
                           'additions': json.dumps({'silence_duration': SILENCE, 'disable_markdown_filter': True,
                                                    'disable_emoji_filter': True, 'explicit_language': 'zh-cn'})}}
    for attempt in range(6):
        try:
            req = urllib.request.Request(URL, data=json.dumps(body).encode(), method='POST',
                                         headers={'Content-Type': 'application/json', 'X-Api-Resource-Id': RESOURCE,
                                                  'X-Api-Request-Id': str(uuid.uuid4()), 'X-Api-Key': 'proxy-injected'})
            raw = urllib.request.urlopen(req, timeout=300).read().decode()
            break
        except Exception as e:
            print('  retry', attempt, e, flush=True); time.sleep(3 * (attempt + 1))
    else:
        raise RuntimeError('doubao tts failed')
    dec = json.JSONDecoder(); i = 0; audio = []; words = []
    while i < len(raw):
        while i < len(raw) and raw[i] in ' \r\n': i += 1
        if i >= len(raw): break
        o, i = dec.raw_decode(raw, i)
        if o.get('code') not in (0, 20000000, None): raise RuntimeError(o)
        if o.get('data'): audio.append(base64.b64decode(o['data']))
        s = o.get('sentence')
        if isinstance(s, dict) and s.get('words'): words.append(dict(text=s.get('text'), words=s['words']))
    import numpy as np, soundfile as sf
    pcm = np.frombuffer(b''.join(audio), np.int16)                 # PCM s16le 单声道 48k：不经 mp3 编解码，时间戳与音频逐样本对齐
    wav = out_mp3[:-4] + '.wav'
    sf.write(wav, pcm, 48000, subtype='PCM_16')
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', wav, '-b:a', '160k', out_mp3], check=True)   # mp3 仅作入库备份
    json.dump(words, open(out_mp3[:-4] + '.json', 'w'), ensure_ascii=False)
    return wav


if __name__ == '__main__':
    work = sys.argv[1]; args = sys.argv[2:]
    takes = 1
    if '--takes' in args: k = args.index('--takes'); takes = int(args[k + 1]); args = args[:k] + args[k + 2:]
    d = os.path.join(work, 'tts_db'); os.makedirs(d, exist_ok=True)
    ps = [p for p in PASSAGES + [TEASE_P] if not args or p[0] in args]
    jobs = [(p, os.path.join(d, f'{p[0]}_{k}.mp3')) for p in ps for k in range(takes)]
    jobs = [j for j in jobs if not os.path.exists(j[1][:-4] + '.wav')]
    def run(j):
        p, out = j
        return synth('\n'.join(spoken(i) for i in p[1]), out)
    with cf.ThreadPoolExecutor(3) as ex:
        for w in ex.map(run, jobs): print('done', w, flush=True)
