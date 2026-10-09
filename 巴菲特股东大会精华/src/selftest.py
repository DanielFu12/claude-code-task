"""离线自检：用 ffmpeg 测试图 + 伪造的逐词转写稿，跑通「定位 → 剪辑 → 合成」整条流水线。

    BRK_WORK=/tmp/brk_test python3 src/selftest.py [--render] [--shorts c01]

只用于验证代码，产物是彩条测试画面，不是成片。真实素材流程见 README.md。
"""
import json, os, random, subprocess, sys
os.environ.setdefault('BRK_WORK', '/tmp/brk_selftest')
os.environ.setdefault('BRK_OUT', os.path.join(os.environ['BRK_WORK'], 'out'))
os.makedirs(os.environ['BRK_OUT'], exist_ok=True)
from common import load_json, wpath, norm_tokens

FILLER = ('well we have a question from the audience about insurance float and the economics of the business '
          'and i think charlie would agree that the long term picture matters a lot more than any one quarter').split()
DUR = 480


def fake_source(year, items):
    """items: [(clip, [(line_tokens…)])]，把每段的句子按顺序埋进一条 8 分钟的伪转写稿。"""
    rng = random.Random(int(year))
    events, t = [], 5.0
    slots = sorted(rng.sample(range(1, 7), len(items)))
    for k, (cid, lines) in enumerate(items):
        target = slots[k] * 62.0
        while t < target:                                      # 填充废话
            n = rng.randint(6, 14)
            ws = [rng.choice(FILLER) for _ in range(n)]
            events.append((t, ws)); t += n * 0.38 + rng.uniform(0.3, 1.0)
        for toks in lines:
            events.append((t, toks)); t += len(toks) * 0.36 + rng.uniform(0.5, 1.1)
    while t < DUR - 10:
        n = rng.randint(6, 14)
        events.append((t, [rng.choice(FILLER) for _ in range(n)])); t += n * 0.38 + 0.6
    ev = [{'tStartMs': int(t0 * 1000), 'dDurationMs': int(len(ws) * 360),
           'segs': [{'utf8': (' ' if i else '') + w, 'tOffsetMs': int(i * 360)} for i, w in enumerate(ws)]}
          for t0, ws in events]
    d = wpath('fake', year)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    mp4 = d + '.mp4'
    json.dump({'events': ev}, open(d + '.en.json3', 'w'))
    size = '640x480' if int(year) < 2010 else '1280x720'           # 老录像是 4:3 标清
    if not os.path.exists(mp4):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'testsrc2=size={size}:rate=30:duration={DUR}',
                        '-f', 'lavfi', '-i', f'sine=frequency={300 + int(year) % 50 * 10}:duration={DUR}',
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '30', '-c:a', 'aac', '-shortest', mp4], check=True)
    json.dump([{'kind': 'local', 'path': mp4, 'title': f'fake {year}'}],
              open(wpath('src', year, 'parts.json'), 'w'))


def main():
    cfg = load_json('clips.json')
    by_year = {}
    for c in cfg['coldopen'] + cfg['clips']:
        lines = [l['en'] for l in c['lines']]
        if c['id'] == 'c03':                                   # 模拟口语与原句略有出入
            lines[0] = lines[0].replace('$10,000', 'ten thousand dollars').replace('reinvested the dividends', 'reinvested dividends')
        by_year.setdefault(c['source'], []).append((c['id'], [norm_tokens(x) for x in lines]))
    for y, items in by_year.items():
        fake_source(y, items)
    import locate, fetch
    locate.main()
    fetch.cmd_media()
    if '--render' in sys.argv:
        import render
        render.main_long()
    if '--shorts' in sys.argv:
        import render
        render.main_shorts(set(sys.argv[sys.argv.index('--shorts') + 1:]))


if __name__ == '__main__':
    main()
