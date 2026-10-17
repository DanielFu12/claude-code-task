"""从 timeline.json 导出中英双语 SRT（与画面字幕同一时间轴）。用法：python3 src/srt.py WORK OUT.srt"""
import json, sys


def ts(x):
    ms = int(round(x * 1000))
    return '%02d:%02d:%02d,%03d' % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


items = json.load(open(sys.argv[1] + '/timeline.json'))['items']
out = []
for k, it in enumerate(items):
    nxt = items[k + 1]['start'] if k + 1 < len(items) else 1e9
    end = nxt - 0.06 if nxt - it['end'] < 1.3 else it['end'] + 0.45
    out.append('%d\n%s --> %s\n%s\n%s\n' % (k + 1, ts(it['start']), ts(end), it['zh'], it['en']))
open(sys.argv[2], 'w', encoding='utf-8').write('\n'.join(out))
print(sys.argv[2], len(out), 'cues')
