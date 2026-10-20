"""剪辑时间线：片头 → [章节卡 → 本章片段]×9 → 片尾。所有时间单位为秒，成片 30fps。

需要 work/ 下的 align.json（align.py 输出）和 cues.json（build_cues.py 输出）。
"""
import json, os
from align import words_asr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.environ.get('LILU_WORK', os.path.join(ROOT, 'work'))
FPS = 30
ASR_DEFAULT = os.path.join(HERE, "youtube_asr.en.json3")
INTRO, CARD, OUTRO = 6.0, 3.0, 11.5

CHAPTERS = {   # 编号: (中文标题, 英文标题)
    1: ('价值投资的六大原则', 'Six Timeless Principles of Value Investing'),
    2: ('AI 的本质、边界与红线', 'What AI Is, Where It Stops, and the Red Line'),
    3: ('AI 狂热下的资本市场', 'The Market in an AI Frenzy'),
    4: ('投资中国：看清目标与代价', 'Investing in China: Objective or Cost'),
    5: ('全球共同市场里的投资机会', 'Opportunity in One Global Common Market'),
    6: ('中国股市：是目标还是代价', 'China\'s Stock Market: Objective or Cost'),
    7: ('一切聪明的投资都是价值投资', 'All Intelligent Investing Is Value Investing'),
    8: ('业绩落后时，如何坚守价值投资', 'When Value Investing Lags Behind'),
    9: ('下行保护与复利人生', 'Downside Protection and a Compounding Life'),
}

def load(src_json3):
    A = json.load(open(os.path.join(WORK, 'align.json')))
    cues = json.load(open(os.path.join(WORK, 'cues.json')))
    W = words_asr(src_json3)
    starts = [w[1] for w in W]
    clips = []
    for g in A['segments']:
        # 起止各留一点余量，但不吃进前后不要的词
        prev_end = max([w[2] for w in W if w[2] <= g['t0'] + 1e-3] or [0])
        next_start = min([s for s in starts if s >= g['t1'] - 1e-3] or [g['t1'] + 1])
        s0 = g['t0'] - max(0.04, min(0.18, g['t0'] - prev_end - 0.03))
        s1 = g['t1'] + max(0.10, min(0.40, next_start - g['t1'] - 0.03))
        clips.append(dict(ch=g['ch'], src0=round(s0, 3), src1=round(s1, 3)))
    # 时间线
    items, t = [dict(kind='intro', t0=0.0, t1=INTRO)], INTRO
    for ch in sorted(CHAPTERS):
        items.append(dict(kind='card', ch=ch, t0=t, t1=t + CARD)); t += CARD
        for c in [c for c in clips if c['ch'] == ch]:
            d = c['src1'] - c['src0']
            items.append(dict(kind='clip', ch=ch, t0=t, t1=t + d, src0=c['src0'], src1=c['src1'])); t += d
    items.append(dict(kind='outro', t0=t, t1=t + OUTRO)); t += OUTRO
    # 帧对齐：每段起点取整到帧
    for it in items:
        it['f0'], it['f1'] = int(round(it['t0'] * FPS)), int(round(it['t1'] * FPS))
    # 字幕映射到成片时间
    out_cues = []
    for c in cues:
        for it in items:
            if it['kind'] == 'clip' and it['ch'] == c['ch'] and it['src0'] - 0.5 <= c['t0'] < it['src1']:
                a = max(c['t0'], it['src0']); b = min(c['t1'], it['src1'] - 0.05)
                if b - a > 0.2:
                    out_cues.append(dict(c, o0=it['t0'] + a - it['src0'], o1=it['t0'] + b - it['src0']))
                break
    # 片段首尾：首条字幕不晚于片段开头 1 秒内出现，末条字幕延续到片段结束（原话常有简短复述）
    for it in items:
        if it['kind'] != 'clip': continue
        cs = [c for c in out_cues if it['t0'] <= c['o0'] < it['t1']]
        if not cs: continue
        if 0 < cs[0]['o0'] - it['t0'] < 1.0: cs[0]['o0'] = it['t0'] + 0.05
        if 0 < it['t1'] - cs[-1]['o1'] < 8.0: cs[-1]['o1'] = it['t1'] - 0.1
    return items, out_cues, t

if __name__ == '__main__':
    import sys
    items, cues, total = load(sys.argv[1])
    for it in items:
        print(it['kind'], it.get('ch', ''), round(it['t0'], 2), round(it['t1'] - it['t0'], 2), it.get('src0', ''), it.get('src1', ''))
    print('cues', len(cues), 'total', round(total, 2), 's =', f'{int(total//60)}:{total%60:05.2f}')
