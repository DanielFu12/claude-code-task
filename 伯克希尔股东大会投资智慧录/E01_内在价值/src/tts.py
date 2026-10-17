"""AI 口播：微软 Edge 神经网络语音（云健），逐句合成并取逐词边界。

用法：python3 src/tts.py WORK
输出：WORK/vo/<id>.wav（48kHz 单声道）、WORK/vo/<id>.json（逐词时间）、WORK/vo_index.json
逐句合成，句间停顿由 script.py 控制；同一句内部保持完整语调（不拆开合成）。
edge-tts 用 certifi 的证书，这里改指向代理的 CA（见 /root/.ccr/README.md）。
"""
import asyncio, hashlib, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import INTRO, INSIGHT, SUMMARY, SAY, VOICE, RATE, PITCH

CA = '/root/.ccr/ca-bundle.crt'
if os.path.exists(CA):
    import certifi
    certifi.where = lambda: CA
import edge_tts

work = sys.argv[1]
os.makedirs(os.path.join(work, 'vo'), exist_ok=True)


async def synth(sid, text, rate=RATE, pitch=PITCH):
    key = hashlib.md5(f'{VOICE}|{rate}|{pitch}|{text}'.encode()).hexdigest()[:10]
    base = os.path.join(work, 'vo', sid)
    meta_p = base + '.json'
    if os.path.exists(meta_p) and json.load(open(meta_p)).get('key') == key:
        return json.load(open(meta_p))
    for attempt in range(4):
        try:
            c = edge_tts.Communicate(text, VOICE, rate=rate, pitch=pitch, boundary='WordBoundary')
            audio, words = bytearray(), []
            async for ch in c.stream():
                if ch['type'] == 'audio':
                    audio += ch['data']
                elif ch['type'] == 'WordBoundary':
                    words.append([ch['offset'] / 1e7, (ch['offset'] + ch['duration']) / 1e7, ch['text']])
            break
        except Exception as e:  # 网络偶发失败：退避重试
            print('retry', sid, e); await asyncio.sleep(2 ** attempt)
    open(base + '.mp3', 'wb').write(audio)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', base + '.mp3', '-ac', '1', '-ar', '48000', base + '.wav'], check=True)
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', base + '.wav'],
                               capture_output=True, text=True).stdout)
    meta = dict(id=sid, key=key, text=text, words=words, dur=dur)
    json.dump(meta, open(meta_p, 'w'), ensure_ascii=False)
    return meta


async def main():
    idx = {}
    for sid, scene, text, pause in INTRO + INSIGHT + [SUMMARY]:
        rate = '-14%' if sid == 'M' else RATE          # 总结句放慢
        m = await synth(sid, SAY.get(sid, text), rate=rate)
        idx[sid] = dict(scene=scene, text=text, say=SAY.get(sid, text), pause=pause, dur=m['dur'], words=m['words'])
        print(f'{sid:4s} {m["dur"]:5.2f}s  {len(text)/m["dur"]:.2f} 字/秒  {text[:28]}')
    json.dump(idx, open(os.path.join(work, 'vo_index.json'), 'w'), ensure_ascii=False, indent=1)

asyncio.run(main())
