"""火山引擎 Seed-TTS 2.0 合成（鉴权由环境代理注入）。用法: tts.py speaker "文本" out.mp3 [out.json] [extra_json]"""
import json, sys, base64, urllib.request
URL = 'https://openspeech.bytedance.com/api/v3/tts/unidirectional'
def synth(speaker, text, mp3, js=None, extra=None, rate=0, ctx=None):
    ap = {"format": "mp3", "sample_rate": 48000, "speech_rate": rate, "enable_timestamp": True}
    rp = {"text": text, "speaker": speaker, "audio_params": ap}
    add = {"disable_markdown_filter": True}
    if ctx: add["context_texts"] = [ctx]
    rp["additions"] = json.dumps(add, ensure_ascii=False)
    if extra: rp.update(extra)
    body = json.dumps({"user": {"uid": "baman"}, "req_params": rp}, ensure_ascii=False).encode()
    req = urllib.request.Request(URL, body, {'Content-Type': 'application/json', 'X-Api-App-Id': 'dummy',
                                 'X-Api-Access-Key': 'dummy', 'X-Api-Resource-Id': 'seed-tts-2.0'})
    audio = b''; words = []; raw = urllib.request.urlopen(req, timeout=120).read().decode()
    dec = json.JSONDecoder(); i = 0
    while i < len(raw):
        while i < len(raw) and raw[i] in ' \r\n': i += 1
        if i >= len(raw): break
        o, i = dec.raw_decode(raw, i)
        if o.get('data'): audio += base64.b64decode(o['data'])
        if o.get('sentence'): words.append(o['sentence'])
        if o.get('code') not in (0, 20000000, None): print('ERR', o, file=sys.stderr)
    open(mp3, 'wb').write(audio)
    if js: json.dump(words, open(js, 'w'), ensure_ascii=False, indent=0)
    return words
if __name__ == '__main__':
    a = sys.argv
    synth(a[1], a[2], a[3], a[4] if len(a) > 4 else None, json.loads(a[5]) if len(a) > 5 else None)
