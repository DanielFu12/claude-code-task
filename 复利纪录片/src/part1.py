"""上半场（0 – 156.4s）：李录 / 巴菲特 / 芒格的原始影像 + 文字卡串联。

时间点锚定在配乐节点上（timeline.A）：0–32 钩子，32 标题重拍，42.75 沉静段（李录），85.4 推进段（巴菲特、芒格）。
"""
import math
import numpy as np
from engine import *
from common import backdrop, put_text, gold_text, footnote, tag
from timeline import A, C0
import ftscene as FT

# ------------------------------------------------------------------ 片段排布（原声起点，成片时间）
# (片段, 起点) —— 起点为 None 时，排在上一段结束 + gap 之后
CHAIN = [('LA', 1.20, 0), ('LB', 9.90, 0), ('LC', 43.30, 0), ('LD', 53.90, 0),
         ('BA', None, 4.0), ('MB', None, 2.2), ('BB', None, 2.2), ('MU', None, 2.0)]
FT.SEQ[:] = []
for cid, t0, gap in CHAIN:
    if cid not in FT.CLIPS: continue
    if t0 is None:
        pc, pt = FT.SEQ[-1]
        t0 = pt + FT.clip_len(pc) + gap
    FT.SEQ.append((cid, t0))
T = {cid: t0 for cid, t0 in FT.SEQ}
END = {cid: t0 + FT.clip_len(cid) for cid, t0 in FT.SEQ}
assert END.get('MU', 0) < C0 - 0.4, f"上半场超时：MU 结束于 {END.get('MU')}"

# 每个片段上方的标题（显示在窗口之上）
HEAD = {
    'LA': ('李录 · 2026 年 10 月最新演讲', '「这一波 AI，和以往任何一波都不同」'),
    'LB': ('李录', '「今天学到的，明天就没用了」'),
    'LC': ('李录', '知识的复利 → 资本的复利'),
    'LD': ('李录', '复利的基本理念：不要失去'),
    'BA': ('巴菲特 · 1999 年股东大会', '「你只需要富一次」'),
    'MB': ('芒格 · BBC 专访', '「下跌 50%，你能心平气和吗？」'),
    'BB': ('巴菲特 · 1999 年股东大会', '复利就像滚雪球'),
    'MU': ('芒格 · 南加州大学毕业演讲', '「每晚睡前，都比早上更聪明一点」'),
}

# 文字卡：(起, 止, [(相对出现时间, 文字, 样式)])
CARDS = [
    (END['LB'] + 0.3, A['drop'] - 0.05, [(0.2, 'AI 正在让知识越来越快地「过期」', 'w'),
                                         (2.1, '那么，什么东西不会过期？', 'g')]),
    (END['LC'] + 0.35, T['LD'] - 0.3, [(0.0, '复利是什么？', 'w')]),
    (END['LD'] + 0.4, T['BA'] - 0.3, [(0.0, '「不要失去你已经拥有的」', 'G'),
                                      (1.3, '李录的导师芒格，和巴菲特，讲了一辈子', 's')]),
    (END['BA'] + 0.4, T['MB'] - 0.3, [(0.0, '可是，市场总会下跌', 'w')]),
    (END['MB'] + 0.4, T['BB'] - 0.3, [(0.0, '不被迫卖出，下跌就只是暂时的', 'w')]),
    (END['BB'] + 0.4, T['MU'] - 0.3, [(0.0, '雪球滚的，不只是钱', 'w')]),
]


def _card(F, t):
    for t0, t1, items in CARDS:
        if not (t0 <= t <= t1 + 0.4): continue
        out = 1 - smooth((t - t1) / 0.4)
        n = len(items)
        y0 = 900 - (n - 1) * 70
        for k, (dt, txt, st) in enumerate(items):
            u = t - t0 - dt
            if u < 0: continue
            a = smooth(u / 0.45) * out
            y = y0 + k * 140
            if st == 'G':
                gold_text(F, txt, W / 2, y, 76, 'serif', a, clamp01(u / 0.8), glow=0.4, sweep=(u - 0.9) / 1.3)
            elif st == 'g':
                gold_text(F, txt, W / 2, y, 64, 'serif', a, clamp01(u / 0.7), glow=0.3)
            elif st == 's':
                put_text(F, txt, W / 2, y - 30 * (k - 1), 36, 'serif_m', np.array([0.92, 0.9, 0.84]), a, 980, reveal=clamp01(u / 0.9), shadow=0.6)
            else:
                put_text(F, txt, W / 2, y, 58, 'serif_m', WHITE, a, 980, reveal=clamp01(u / 0.7), shadow=0.6, glow=0.08)


def _head(F, t):
    ac = FT.active(t)
    if not ac: return
    cid, u, a, _ = ac
    if cid not in HEAD: return
    small, big = HEAD[cid]
    x0, y0, w, h = FT.rect_of(cid)
    yb = min(y0 - 70, 270)
    if FT.CLIPS[cid].get('context'): yb = min(yb, y0 - 110)
    put_text(F, small, W / 2, yb - 64, 28, 'sans', GOLD_SUB * 1.15, a, 900, shadow=0.6, track=2)
    gold_text(F, big, W / 2, yb, 54, 'serif', a, clamp01((t - T[cid] + 0.2) / 0.6), glow=0.25)


def sc_part1(t):
    # 段落底色：钩子偏冷、李录段偏暖、巴菲特/芒格段中性
    if t < A['drop']:
        F = backdrop(t, c1=(0.01, 0.015, 0.035), c2=(0.02, 0.05, 0.12), neb=(0.06, 0.16, 0.38), neb_amt=0.4, drift=1.2)
    elif t < A['build']:
        F = backdrop(t, c1=(0.015, 0.013, 0.012), c2=(0.05, 0.04, 0.03), neb=(0.22, 0.16, 0.08), neb_amt=0.3, drift=0.5)
    else:
        F = backdrop(t, c1=(0.01, 0.012, 0.02), c2=(0.03, 0.035, 0.05), neb=(0.12, 0.14, 0.2), neb_amt=0.3, drift=0.6)
    FT.ft_bg(F, t)
    _head(F, t)
    _card(F, t)
    # 标题重拍前的坍缩（31–32s）
    if A['drop'] - 1.0 < t < A['drop']:
        F *= 1 - 0.85 * smooth((t - (A['drop'] - 1.0)) / 1.0)
    # 进入高潮前压暗
    if C0 - 0.8 < t < C0:
        F *= 1 - 0.9 * smooth((t - (C0 - 0.8)) / 0.8)
    return F


def overlay(F, t):
    FT.ft_overlay(F, t)
    if A['drop'] - 1.0 < t < A['drop']:
        F *= 1 - 0.85 * smooth((t - (A['drop'] - 1.0)) / 1.0)
    if C0 - 0.8 < t < C0:
        F *= 1 - 0.9 * smooth((t - (C0 - 0.8)) / 0.8)
