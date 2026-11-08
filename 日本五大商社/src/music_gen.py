"""用 Lyria（lyria-3-pro-preview，流式接口）生成两段原创配乐，结构时间点对齐 work/timeline.json。

python3 src/music_gen.py WORK A 3     # 生成 A 段 3 个候选：work/music/A_0.mp3 ...
python3 src/music_gen.py WORK B 3
"""
import sys, os, json, base64, time, urllib.request, concurrent.futures as cf

API = 'https://generativelanguage.googleapis.com/v1beta/models/lyria-3-pro-preview:streamGenerateContent?alt=sse'

PALETTE = ("Instrumental cinematic documentary score (no vocals, no choir). Key D minor, steady tempo 84 BPM. "
           "Hybrid orchestral palette: deep sub-bass, low taiko and orchestral toms, low strings (celli, basses, violas), "
           "French horns and low brass, warm felt piano. Energy lives below 2 kHz; soft, dark top end. "
           "Strictly NO white-noise risers, NO whooshes, NO cymbal swells, NO hi-hats, NO shakers, NO ticking clocks, "
           "NO synth arpeggios in high register, NO reverse swells.")

PROMPTS = {
    'A': PALETTE + """
Exact structure (timestamps matter, total length 3:04):
0:00-0:26 dark suspense intro: low sub-bass drone, slow heartbeat-like low pulse every beat, sparse low piano notes; tension rises slowly.
0:26 one bar of near-silence.
0:27.5 massive low orchestral impact with a deep brass chord, ringing out until 0:32.
0:32-1:11 warm, nostalgic chapter: felt piano melody with soft cello; at 0:52 the theme brightens with a gentle low rhythmic pulse.
1:11 low impact. 1:11-2:09 intelligent, propulsive chapter: low string ostinato in eighth notes, steady toms, horns state the main theme; grows majestic toward 2:00.
2:09 low impact, then 2:09-3:04 compounding build: string ostinato and drums add layer after layer, rising to a powerful triumphant climax at 2:45-3:00; final huge hit at 3:02 and a short ring-out.""",
    'B': PALETTE + """
Exact structure (timestamps matter, total length 1:45):
0:00-0:29 dark tension: deep low drones, slow uneasy pulses, sparse low piano; feels like a long, heavy wait after a bubble bursts.
0:29-0:53 resolute: steady low pulse returns with horns; quiet determination.
0:53-1:14 reflective: solo felt piano and cello, intimate and warm (D minor moving toward F major).
1:14-1:29 emotional swell: strings and horns build to an epic, uplifting climax.
1:29 one final majestic low hit, then 1:29-1:45 a sustained glowing D major chord slowly fading to silence.""",
}


def gen(kind, out):
    body = {"contents": [{"parts": [{"text": PROMPTS[kind]}]}]}
    for k in range(5):
        try:
            req = urllib.request.Request(API, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
            parts = []
            with urllib.request.urlopen(req, timeout=900) as r:
                for line in r:
                    line = line.decode().strip()
                    if not line.startswith('data:'): continue
                    j = json.loads(line[5:])
                    for p in j['candidates'][0]['content'].get('parts', []):
                        if 'inlineData' in p: parts.append(base64.b64decode(p['inlineData']['data']))
            if parts:
                open(out, 'wb').write(b''.join(parts)); return out
        except Exception as e:
            print('retry', k, e, flush=True); time.sleep(6 * (k + 1))
    raise RuntimeError('lyria failed')


if __name__ == '__main__':
    work, kind, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
    d = os.path.join(work, 'music'); os.makedirs(d, exist_ok=True)
    start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    with cf.ThreadPoolExecutor(3) as ex:
        for o in ex.map(lambda i: gen(kind, os.path.join(d, f'{kind}_{i}.mp3')), range(start, start + n)):
            print('done', o, flush=True)
