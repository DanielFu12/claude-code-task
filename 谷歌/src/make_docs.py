"""生成 docs/SOURCES.md：逐句旁白的出处（含片中时间戳）、屏幕原话、数据口径、影像素材与配乐说明。时间戳取自 work/timeline.json。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, QUOTES, CHAPTERS, TEASE
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
work = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work')
TL = json.load(open(os.path.join(work, 'timeline.json')))
IA = json.load(open(os.path.join(ROOT, 'assets', 'media', 'ia_clips.json')))
CR = json.load(open(os.path.join(ROOT, 'assets', 'media', 'credits.json')))
SEG = {s['id']: s for s in TL['segs']}
CHN = {c[0]: c[1] for c in CHAPTERS}


def ts(sec): return f'{int(sec // 60)}:{sec % 60:04.1f}'


out = []; w = out.append
w('# 《二十年后的补票——巴菲特为什么出手谷歌》出处与口径\n')
w(f'片长 {ts(TL["total"])}。股价截至 2026-11-09 收盘；持股取自 SEC 13F 原件；详细核实过程见 `research/核实笔记.md`，'
  'CNBC 专访的带时间码转写见 `research/CNBC专访_20260715_转写.md`。\n')
w('**口径原则**：每个关于谷歌的投资判断，只用谷歌自身的数据或明确对应谷歌的交易证据（13F 的 Alphabet 行、Alphabet 的公告与财报、当事人谈谷歌的原话）；'
  '伯克希尔整个股票组合的买卖额等数据不用于谷歌叙事（核实笔记第零节）。\n')
w('## 逐句旁白\n')
cur = None
for lid, ch, text, say, mood, src in LINES:
    if ch != cur:
        w(f'\n### {CHN.get(ch) or "开场"}\n'); cur = ch
    w(f'- `{ts(SEG[lid]["start"])}` {text}' + (f'\n  - 出处：{src}' if src else ''))
w(f'\n### 片尾\n\n- `{ts(SEG["tease"]["start"])}` {TEASE[0]}')
w('\n## 屏幕原话（英文原句 + 中文翻译）\n')
for k, (en, cn, who) in QUOTES.items():
    w(f'- **{who}**：“{en}” —— {cn}')
w('\n- 芒格 2009 年“从没见过这么宽的护城河”只见二手报道，片中只做转述，不做引语卡。')
w('- CNBC 2026-07-15 专访的原话，已在仓库内原片里逐句定位（见转写文件时间码）；英文以 CNBC 官方摘录为准。')
w('\n## 数据口径\n')
w('- 持股：SEC 13F 原件（2025-09-30 起逐季）；两期之差记作“净增 / 净买入”。市场净买入约 7,741 万股 = 2026-06-30 合计 10,598 万股 − 定增 2,857 万股。')
w('- 定增：Alphabet 2026-06-01 公告、6-02 定价公告、8-K / 424B5（A 14,212,035 股 @ $351.81，C 14,359,656 股 @ $348.20，6-04 完成）；'
  '公开发行价 A $355.1982、C $351.8018（Alphabet 三季度 10-Q）；差幅为本片计算。')
w('- 融资总额 $847.5 亿为计划额，含 $400 亿 ATM（主要用于员工股权奖励缴税，不是 AI 融资）；公开发行与定增所得用于包括 AI 基础设施与算力在内的公司用途。')
w('- 股价：Yahoo Finance 日线收盘价（GOOGL，拆股调整）。')
w('- 示意画面（搜索框、股权结构、搜索引擎此消彼长、竞争曲线、服务器机柜、天平等）均在画面上标注“示意”，不代表真实数据。')
w('\n## 影像素材\n')
for k, v in IA.items():
    w(f'- `{k}`：{v["source"]}（片源起点 {v["start"]}s，{v["dur"]}s）{("—— " + v["note"]) if v.get("note") else ""}')
w('\n照片（Wikimedia Commons，第二期已核授权）：')
for k, v in CR.items():
    w(f'- `{k}`：{v["title"]}，{v.get("artist", "")}，{v.get("license", "")}，{v["page"]}')
w('\n## 声音\n')
w('- 旁白：豆包语音合成 2.0（刘飞音色），逐段整读；离线中文识别逐句回听核对（`src/check_vo.py`、`src/check_lines.py`）。')
w('- 配乐：本期原创，程序作曲（`src/music.py`，D 小调 / D 大调，80 BPM，四音主题贯穿），FluidSynth + FluidR3 GM 音色库渲染；'
  '片名、“是我发起的”、片尾 logo 三处重拍。大师原话只以屏幕文字呈现，不模仿任何人的声音。')
open(os.path.join(ROOT, 'docs', 'SOURCES.md'), 'w').write('\n'.join(out) + '\n')
print('docs/SOURCES.md', len(out), 'lines')
