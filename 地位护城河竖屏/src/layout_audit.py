"""版面审计：读 video.py audit 的记录，找 ① 两段可见文字互相重叠；② 文字跨在卡片边界上（半在卡内半在卡外）；③ 文字超出画面安全区。
python3 src/layout_audit.py audit0.json audit1.json ..."""
import sys, json, collections
import os
W, H = (1920, 1080) if os.environ.get('ORIENT') == 'h' else (1080, 1920)
def inter(a, b):
    x0, y0 = max(a[1], b[1]), max(a[2], b[2]); x1, y1 = min(a[3], b[3]), min(a[4], b[4])
    return max(0, x1 - x0) * max(0, y1 - y0)
def area(a): return max(1, (a[3] - a[1]) * (a[4] - a[2]))
issues = collections.defaultdict(list)
# 有意的叠加：删除线、划掉的价格
ALLOW = {'贵', '“敬畏自然”', '一笔订单'}   # 有意的删除线 / 裂痕
for f in sys.argv[1:]:
    for t, recs in json.load(open(f)):
        texts = [r for r in recs if r[0] == 'text' and r[6] >= 0.35]; cards = [r for r in recs if r[0] == 'card' and r[6] >= 0.35]
        for r in recs:
            if r[0] == 'onGraphic' and r[1] not in ALLOW: issues[('压在线条/图形上', r[1])].append(t)
        for i in range(len(texts)):
            a = texts[i]
            if a[1] < 20 or a[3] > W - 20 or a[2] < 0 or a[4] > H: issues[('出界', a[5])].append(t)
            for b in texts[i + 1:]:
                ov = inter(a, b)
                if ov >= 40 and ov >= 0.04 * min(area(a), area(b)):
                    issues[('文字重叠', *sorted((a[5], b[5])))].append(t)
            for c in cards:
                ov = inter(a, c)
                if ov > 0 and ov < 0.97 * area(a) and not (a[1] >= c[1] - 4 and a[3] <= c[3] + 4 and a[2] >= c[2] - 4 and a[4] <= c[4] + 4):
                    if ov >= 0.03 * area(a): issues[('跨卡片边', a[5], 'card@%d,%d' % (c[1], c[2]))].append(t)
out = []
for k, ts in issues.items():
    ts = sorted(ts); groups = [[ts[0]]]
    for x in ts[1:]:
        (groups[-1].append(x) if x - groups[-1][-1] <= 0.41 else groups.append([x]))
    for g in groups: out.append((g[0], g[-1], k))
for a, b, k in sorted(out):
    print('%6.1f–%6.1f  %s' % (a, b, ' | '.join(str(x)[:26] for x in k)))
print('共 %d 处' % len(out))
