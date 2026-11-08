"""生成 docs/SOURCES.md：逐句旁白的出处（含片中时间戳）、屏幕原话、数据口径与影像素材来源。时间戳取自 work/timeline.json。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, QUOTES, CHAPTERS
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
work = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work')
TL = json.load(open(os.path.join(work, 'timeline.json')))
C = json.load(open(os.path.join(ROOT, 'data', 'calc.json')))
IA = json.load(open(os.path.join(ROOT, 'assets', 'media', 'ia_clips.json')))
SEG = {s['id']: s for s in TL['segs']}
CHN = {c[0]: c[1] for c in CHAPTERS}


def ts(sec): return f'{int(sec // 60)}:{sec % 60:04.1f}'


out = []
w = out.append
w('# 《东京下注——巴菲特与日本五大商社》出处与口径\n')
w(f'片长 {ts(TL["total"])}。数字截至 {C["close_day"]} 东京收盘；详细核实过程见 `research/核实笔记.md`，伯克希尔原文摘录见 `research/letters_japan.md`。\n')
w('## 逐句旁白\n')
cur = None
for lid, ch, text, say, mood, src in LINES:
    if ch != cur:
        w(f'\n### {CHN.get(ch) or "开场"}\n'); cur = ch
    t = ts(SEG[lid]['start']) if lid in SEG else '—'
    w(f'- `{t}` {text}' + (f'\n  - 出处：{src}' if src else ''))
w('\n## 屏幕原话（英文原句 + 中文翻译）\n')
for k, (en, cn, who) in QUOTES.items():
    w(f'- **{who}**：“{en}” —— {cn}')
w('\n## 数据口径\n')
m = C['mult']
w(f'- 股价倍数：Yahoo Finance 日线收盘价（拆股调整、日元计、不含分红），{C["base"]} → {C["close_day"]}：'
  + '、'.join(f'{n} ×{m[k]:.2f}' for k, n in (('marubeni', '丸红'), ('mitsubishi', '三菱商事'), ('mitsui', '三井物产'),
                                             ('sumitomo', '住友商事'), ('itochu', '伊藤忠'), ('n225', '日经 225')))
  + f'；五家简单平均 ×{C["avg5"]:.2f}。')
w(f'- 汇率：USD/JPY 2020-08-31 约 {C["fx0"]:.1f}，{C["close_day"]} 约 {C["fx1"]:.1f}。')
w(f'- 伯克希尔 2025 年致股东信持仓表：成本 ${C["cost"] / 100:.2f} 亿、2025 年底市值 ${C["mv2025"] / 100:.2f} 亿、2025 年分红 ${C["div2025"] / 100:.2f} 亿；'
  f'日元借款平均利率 1.2%，资产负债表日元债 ${C["yen_debt"] / 100:.2f} 亿；年利息约 ${C["yen_debt"] * C["yen_rate"] / 100:.1f} 亿为估算。')
w('- “花 100 块每年赚回约 14 块”：巴菲特估算的 earnings yield 约 14%（CNBC 2023-04）；100 ÷ 14 ≈ 7.1 年。')
w('- 第四章“护城河四段”“三等生意的归类”为本片解读，依据巴菲特 1991、2007 年致股东信的标准。')
w('\n## 影像素材\n')
for k, v in IA.items():
    w(f'- `{k}`：{v["source"]}，{v["ia"]}（起点 {v["start"]}s，{v["dur"]}s）')
w('\n配乐：本频道第二期原创配乐素材（Lyria 生成）重新剪辑对位。旁白：豆包语音合成 2.0（刘飞音色）。大师原话只以屏幕文字呈现，不模仿任何人的声音。')
os.makedirs(os.path.join(ROOT, 'docs'), exist_ok=True)
open(os.path.join(ROOT, 'docs', 'SOURCES.md'), 'w').write('\n'.join(out) + '\n')
print('docs/SOURCES.md', len(out), 'lines')
