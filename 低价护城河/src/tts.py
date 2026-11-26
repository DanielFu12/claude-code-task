"""豆包 Seed-TTS 3.0（voice.cn-beijing.volces.com，X-Api-Key 由环境代理注入）。
synth(text, mp3, **extra) → 返回逐字对齐 [(word, start, end), ...]（秒）"""
import json, sys, base64, urllib.request, time
VOICE = 'multi_male_liufei2_v3_uranus_bigtts'
URL = 'https://voice.cn-beijing.volces.com/api/v3/text-to-speech/%s/streaming'
def synth(text, mp3, voice=VOICE, tries=4, **extra):
    body = {"text": text, "model_id": "doubao-seed-tts-3.0", "enable_subtitle": True}
    body.update(extra)
    req = urllib.request.Request(URL % voice, json.dumps(body, ensure_ascii=False).encode(),
                                 {'Content-Type': 'application/json', 'X-Api-Key': 'proxy-injected'})
    for k in range(tries):
        try:
            raw = urllib.request.urlopen(req, timeout=600).read().decode(); break
        except Exception as e:
            print('retry', e, file=sys.stderr); time.sleep(5 * (k + 1))
    audio = b''; words = []; offs = 0.0
    for line in raw.splitlines():
        if not line.strip(): continue
        o = json.loads(line); ev = o.get('event')
        if ev == 'audio': audio += base64.b64decode(o['audio'])
        elif ev == 'alignment':
            for w in o.get('words', []): words.append((w['word'], w['startTime'], w['endTime']))
        elif ev == 'error': raise RuntimeError(o)
    open(mp3, 'wb').write(audio)
    return words
if __name__ == '__main__':
    w = synth(sys.argv[1], sys.argv[2], **(json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}))
    print(json.dumps(w, ensure_ascii=False))
