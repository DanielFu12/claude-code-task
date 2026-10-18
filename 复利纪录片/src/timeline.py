"""时间轴：所有画面/旁白的时间点都锚定在配乐的实测节点上（见 assets/music/README）。

配乐 = main（0–156.4s 使用 mainA 0–156.4）+ climax（climA，从 C0 开始）。
"""
import json, os
import soundfile as sf
from script import NARRATION

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
VOICE = os.path.join(ROOT, 'assets', 'voice')

C0 = 156.4                      # 高潮配乐起点
BEAT = 60 / 90                  # 90 BPM
A = dict(                       # 配乐节点（秒，成片时间）
    drop=32.0,                  # 片头重拍：标题
    calm=42.75,                 # 沉静段（李录）
    build=85.4,                 # 推进段（巴菲特 / 芒格）
    build2=112.1,
    suspense=138.7,             # 第一性原理
    climax=C0,
    year0=C0 + 0.40,            # 30 年塔楼：每拍一年
    crash=C0 + 20.80,           # 崩塌（−50%）
    rebuild=C0 + 24.10,
    epic=C0 + 45.20,            # 人生复利
    final=C0 + 67.00,           # 最后一个重拍 → 品牌
    brand_hit=C0 + 69.44,       # 「巴芒价值」随此拍出现
    end=C0 + 80.46,
)
DUR = A['end']

# 旁白起点（秒）。每条的可用时长 = 到下一条起点（或 slot_end）为止
START = {
    'N01': 0.7, 'N02': 5.8, 'N03': 12.9, 'N04': 22.3,
    'N05': 43.3, 'N06': 60.3, 'N07': 69.0,
    'N08': 80.0, 'N09': 93.6, 'N10': 101.4, 'N11': 108.2,
    'N12': 114.8, 'N13': 123.4, 'N14': 130.3,
    'N16': 140.3, 'N17': 148.3,
    'N18': C0 + 4.0, 'N19': C0 + 24.6, 'N20': C0 + 34.6,
    'N21': C0 + 46.0, 'N22': C0 + 53.0, 'N23': C0 + 62.1,
}
SLOT_END = {'N04': 31.8, 'N08': 93.3, 'N17': C0 + 0.3, 'N18': A['crash'] - 0.3, 'N20': A['epic'] - 0.4, 'N23': A['final'] + 0.4}


def est(nid):
    return len(NARRATION[nid]) / 4.1 + 0.3


def dur(nid):
    p = os.path.join(VOICE, f'{nid}.wav')
    if os.path.exists(p):
        return sf.info(p).duration
    return est(nid)


def lines():
    """[(id, start, end)]，按时间排序"""
    ids = sorted(START, key=START.get)
    return [(i, START[i], START[i] + dur(i)) for i in ids]


def check():
    ids = sorted(START, key=START.get)
    ok = True
    for k, i in enumerate(ids):
        lim = SLOT_END.get(i, START[ids[k + 1]] - 0.25 if k + 1 < len(ids) else DUR)
        e = START[i] + dur(i)
        flag = 'OVER' if e > lim else ''
        if flag: ok = False
        src = 'wav' if os.path.exists(os.path.join(VOICE, f'{i}.wav')) else 'est'
        print(f'{i} {START[i]:7.2f} → {e:7.2f}  limit {lim:7.2f}  ({src}) {flag}')
    return ok


if __name__ == '__main__':
    print('ok' if check() else 'OVERLAPS')
