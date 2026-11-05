"""生成 docs/SOURCES.md：逐句旁白的出处（含片中时间戳）、屏幕原话、数据口径与影像素材授权。时间戳取自 work/timeline.json。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, QUOTES, TEASE, CHAPTERS

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
work = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work')
TL = json.load(open(os.path.join(work, 'timeline.json')))
C = json.load(open(os.path.join(ROOT, 'data', 'calc.json')))
CRP = os.path.join(ROOT, 'assets', 'media', 'credits.json')
CR = json.load(open(CRP)) if os.path.exists(CRP) else {}
SEG = {s['id']: s for s in TL['segs']}


def ts(sec):
    d = int(round(sec * 10)); return f'{d // 600}:{(d % 600) / 10:04.1f}'


out = []; w = out.append
w('# 《十年苹果——巴菲特为什么卖掉了大半》资料来源、引语出处与素材授权\n')
w(f'成片时长 {ts(TL["total"])}。时间戳为该句旁白在成片中开始的时刻（由 `work/timeline.json` 自动生成）。'
  f'行情与持仓数据截至 {C["asof"]} 收盘（AAPL ${C["close"]:.2f}；历史最高收盘 {C["ath"]["date"]} ${C["ath"]["close"]:.2f}）。\n')
w('## 1. 数据口径\n')
w('- **持股**：伯克希尔 SEC 13F（CIK 1067983），2016Q1–2026Q2，按 2020 年 1 拆 4 调整。')
w('- **买入/卖出金额（估算）**：各季度持股变动 × 该季度 AAPL 日均收盘价（`data/calc.py`），税前；伯克希尔从未逐笔披露成交价。')
w('- **股息（估算）**：每股股息 × 除息日前一季末持股。')
w(f'- **总账**：买入约 ${C["est_buys"] / 1e8:,.0f} 亿；卖出所得约 ${C["est_sells"] / 1e8:,.0f} 亿；股息约 ${C["cum_dividends_est"] / 1e8:,.0f} 亿；'
  f'剩余 {C["shares_now"] / 1e8:.2f} 亿股 × ${C["close"]:.2f} ≈ ${C["value_now"] / 1e8:,.0f} 亿；合计约为投入的 {C["total_multiple_est"]:.1f} 倍。')
w('- **年化回报**：按每季度买卖与股息的实际时间计算的内部收益率，约 29.2%；同额同期买入标普 500 全收益指数（^SP500TR）并持有至今约 $1394 亿，年化约 14.8%（`research/stories.md` D 节）。')
w('- **市盈率**：季度日均价 ÷ 上一财年摊薄每股收益（苹果 10-K，拆股调整）。\n')
w('## 2. 逐句出处\n')
cur = None
names = {c[0]: (c[1] or '开场') for c in CHAPTERS}
for l in LINES:
    if l[1] != cur:
        cur = l[1]; w(f'\n### {names[cur]}\n')
    t = ts(SEG[l[0]]['start']) if l[0] in SEG else '—'
    src = l[5] or '本片叙述'
    w(f'- `{t}` {l[2]}  \n  出处：{src}')
w(f'- `{ts(SEG["tease"]["start"])}` {TEASE[0]}  \n  出处：{TEASE[2]}\n')
w('## 3. 屏幕上的原话（只用已核实的文字记录）\n')
for k, (en, cn, who) in QUOTES.items():
    w(f'- **{who}**：{("“" + en + "”") if en else ""} {cn}')
w('\n更完整的核实记录见 `research/meeting_quotes.md`、`research/letters_apple.md`、`research/stories.md`。'
  '本片不使用任何 AI 模仿的巴菲特、芒格或段永平的声音；旁白为 Gemini TTS（音色 Charon）。\n')
w('## 4. 影像素材授权（Wikimedia Commons）\n')
w('片中照片与视频均为公有领域或知识共享授权素材，已按授权要求署名；画面中另有小字署名。“示意”标注的画面仅表现时代或场景，并非事件现场。\n')
for k, c in sorted(CR.items()):
    w(f'- `{k}` — [{c["title"]}]({c["page"]}) · 作者：{(c.get("artist") or "—").strip()} · 授权：{c.get("license") or "—"}')
IAP = os.path.join(ROOT, 'assets', 'media', 'ia_clips.json')
if os.path.exists(IAP):
    w('\n### 视频片段（Internet Archive 公开存档；按用户要求选用高清现代影像，版权归原权利人）\n')
    seen = set()
    for k, v in json.load(open(IAP)).items():
        w(f'- `{k}` — {v["source"]}（{v["ia"]}，原片 {v["start"]}s 起 {v["dur"]}s）')
w('\n## 5. 配乐与品牌\n')
w('- 配乐：Lyria（lyria-3-pro-preview）为本片生成的原创配乐，同一调性与主题动机，经节拍对位剪辑（`src/score.py`）。')
w('- 品牌角标与片尾 logo：仓库 `brand/` 目录官方资产。')
os.makedirs(os.path.join(ROOT, 'docs'), exist_ok=True)
open(os.path.join(ROOT, 'docs', 'SOURCES.md'), 'w').write('\n'.join(out) + '\n')
print('docs/SOURCES.md', len(out), 'lines')
