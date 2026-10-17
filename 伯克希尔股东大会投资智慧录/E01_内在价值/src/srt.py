"""导出字幕文件（与画面烧录字幕同一时间轴）。

用法：python3 src/srt.py WORK OUT_DIR
输出：OUT_DIR/字幕_中英.srt（原声为中英双语，口播为中文）
"""
import json, os, sys

work, out = sys.argv[1], sys.argv[2]
tl = json.load(open(os.path.join(work, 'timeline.json')))


def ts(t):
    t = max(t, 0); ms = int(round(t * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


items = []
for s in tl['cold_subs']:
    items.append((s['t0'], s['t1'], f"{s['zh']}\n{s['en']}"))
for part in ('intro', 'insight', 'summary'):
    for s in tl[part]['subs']:
        items.append((s['t0'], s['t1'], s['text']))
for s in tl['qa']['subs']:
    items.append((s['t0'], s['t1'], f"{s['zh']}\n{s['en']}"))
items.append((tl['laugh']['t0'], tl['laugh']['t1'], '（现场笑声）'))
items.sort()
with open(os.path.join(out, '字幕_中英.srt'), 'w', encoding='utf-8') as f:
    for i, (a, b, s) in enumerate(items, 1):
        f.write(f'{i}\n{ts(a)} --> {ts(b)}\n{s}\n\n')
print('wrote', len(items), 'cues')
