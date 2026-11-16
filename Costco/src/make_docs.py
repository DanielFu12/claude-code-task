"""生成 docs/SOURCES.md：逐句旁白的出处（含片中时间戳）、原声、屏幕原话、数据口径、影像素材与配乐说明。时间戳取自 work/timeline.json。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, QUOTES, CHAPTERS, TEASE, SOTS, SOT_SRC
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
work = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work')
TL = json.load(open(os.path.join(work, 'timeline.json')))
IA = json.load(open(os.path.join(ROOT, 'assets', 'media', 'ia_clips.json')))
CR = json.load(open(os.path.join(ROOT, 'assets', 'media', 'credits.json')))
SEG = {s['id']: s for s in TL['segs']}
CHN = {c[0]: c[1] for c in CHAPTERS}
WHO = {'munger': '芒格', 'buffett': '巴菲特', 'sinegal': '辛内格尔'}


def ts(sec): return f'{int(sec // 60)}:{sec % 60:04.1f}'


def sot_line(sid, so):
    sg = SEG['sot_' + sid]
    return (f'- `{ts(sg["start"])}` 🔊 **{WHO[so["who"]]}原声**：“{so["en"]}” —— ' + ''.join(c for _, c in so['ph']) +
            f'\n  - 出处：{so.get("srcname", SOT_SRC)}' + (f'，片中 {so["ts"]}' if so.get('ts') else '') + '（切点见 `src/cut_sot.py`、`work/sot/sot.json`）')


out = []; w = out.append
w('# 《一块五的热狗——芒格为什么最爱 Costco》出处与口径\n')
w(f'片长 {ts(TL["total"])}。Costco 财务数字取自 2026 财年 10-K（截至 2026-08-30，2026-10-07 提交）；伯克希尔原话取自致股东信原文；'
  '详细核实过程、每条数字的交叉来源与两版参考脚本的勘误见 `research/核实笔记.md`。\n')
w('**口径原则**：加价率与毛利率分开；会员费不等于全部利润；“付费会员”与“持卡人”分开；续费率分美加与全球；'
  '只查到单一来源或媒体转述的，旁白写“据报道 / 据多家媒体报道”。\n')
w('## 逐句旁白\n')
cur = None
for lid, ch, text, say, mood, src in LINES:
    if ch != cur:
        w(f'\n### {CHN.get(ch) or "开场"}\n'); cur = ch
    w(f'- `{ts(SEG[lid]["start"])}` {text}' + (f'\n  - 出处：{src}' if src else ''))
    for sid, so in SOTS.items():
        if so['after'] == lid: w(sot_line(sid, so))
w(f'\n### 片尾\n\n- `{ts(SEG["tease"]["start"])}` {TEASE[0]}：{TEASE[1]}' + (f'\n  - 出处：{TEASE[3]}' if len(TEASE) > 3 else ''))
for sid, so in SOTS.items():
    if so['after'] == 'tease': w(sot_line(sid, so))
w('\n## 原声（SOT）\n')
w('片中 7 处直接播放公开影像里的真实原声：芒格 5 处（2022-02-16《每日期刊》年度股东会答问，Becky Quick 代读提问；'
  '片源为第三方转载件 https://archive.org/details/youtube-A21VQ4AFV5M ，转载件在芒格答问中间插了图库镜头，这些时段画面换成本片的 Costco 档案画面，'
  '芒格出镜时段保持原片、口型同步；转载件烧录的字幕已裁出画外）；辛内格尔 1 处（ABC《20/20》2005 年报道，https://archive.org/details/youtube-f9Iv_vdO7sw）；'
  '巴菲特 1 处（CNBC Squawk Box 2026-07-15 专访，第四期已入库）。全部原速、不改词、不拼接；入出点切在自然停顿，'
  '经离线英文语音识别（sherpa-onnx whisper small.en，`src/asr_en.py`）逐句核对，转写稿在 `research/asr/`；屏幕给出英文原话、中文翻译与出处。\n')
w('2011 年股东大会的“劫机笑话”和 2024 年股东大会的“买、买、买”，原声在 CNBC 巴菲特档案与 YouTube，均无法合规取得（机器人拦截），片中只用屏幕引语卡。\n')
for sid, so in SOTS.items():
    sg = SEG['sot_' + sid]
    w(f'- `{ts(sg["start"])}` {WHO[so["who"]]}（{so["srcname"]}，{sg["len"]:.1f}s）“{so["en"]}”')
w('\n## 屏幕原话（英文原句 + 中文翻译）\n')
for k, (en, cn, who) in QUOTES.items():
    w(f'- **{who}**：“{en}” —— {cn}')
w('\n- 致股东信原文均可在 https://www.berkshirehathaway.com/letters/letters.html 查到；屏幕引语卡注明年份。')
w('\n## 数据口径\n')
w('- 2026 财年（截至 2026-08-30）：商品净销售额 $297,247M；会员费 $5,907M；商品毛利 $32,968M（毛利率 11.09%）；SG&A $27,190M；'
  '营业利润约 $11.7B（本片按 32,968 − 27,190 + 5,907 = 11,685 计算，未单列开业前费用）；净利润 $9,226M；付费会员 8410 万、持卡人 1.504 亿；'
  '续费率美加 92.3%、全球 89.8%；仓库 939 家；年末存货 $19,324M、应付账款 $22,591M（二手数据，两家来源一致）。')
w('- “会员费约占营业利润一半”：5,907 ÷ 11,685 ≈ 50.6%。SG&A 无法严格拆成“卖货的”和“会员的”，片中只说“毛利付完整个公司的开销，还有结余”。')
w('- 加价上限 14% / 15%：多家媒体报道，Costco 没有正式披露；片中注明“据多家媒体报道”。100 → 114 的毛利率为 12.28%。')
w('- 热狗套餐 $1.50：多数来源写 1985 年起，维基百科写 1984 年推出；片中用 1985 年。物价：BLS CPI-U 1985 年均 107.6、2025 年 12 月 326.0（约 3 倍）。')
w('- 内布拉斯加养鸡体系：弗里蒙特市长所说“超过 4.5 亿美元”包括饲料厂、孵化场与加工厂；2019 年投产。')
w('- YouGov：顾客中高收入家庭占比 Costco 18%、BJ’s 15%、山姆 12%；低收入家庭占比山姆 28%、Costco 18%（美国）。')
w('- 美国单店年销售（本片计算）：Costco 2026 财年美国净销售额约 $2,160 亿（72.7% × $297,247M）÷ 647 家 ≈ $3.3 亿；Walmart 2026 财年 Sam’s Club U.S. $930 亿 ÷ 601 家 ≈ $1.5 亿；两家财年截止月不同。MMCG 2026 研报约 2 倍。')
w('- 山姆中国：1996 年深圳首店；2026 年门店 67–69 家（媒体报道）；付费会员超 1070 万（媒体报道，沃尔玛未披露）；约 1 小时送达（多数城市）；小红书“山姆”相关笔记 22 万+ 篇（36kr，截至 2021-11）。Costco 中国首店：2019-08-27 上海闵行，在华 7 家（China Daily 2026-08）。')
w('- 伯克希尔 2020 年三季度卖出全部 4,333,363 股 Costco（13F）。市盈率：2026-08-29 约 47.6 倍、2026-11-02 约 50 倍（第三方数据），片中写“四十多倍到五十倍之间”。')
w('- 示意画面（物价曲线、方块数量、利润桥比例、飞轮、仓库/工厂/卡片线稿、市盈率仪表）均为示意或按上述数字绘制；自绘图形不使用任何公司的商标。')
w('\n## 影像素材\n')
for k, v in IA.items():
    w(f'- `{k}`：{v["source"]}（片源起点 {v["start"]}s，{v["dur"]}s）{("—— " + v["note"]) if v.get("note") else ""}')
w('\n影像只取画面、不用原声（原声段落除外），画面上逐镜署名。照片（Wikimedia Commons，已核授权）：')
for k, v in CR.items():
    w(f'- `{k}`：{v.get("title") or v.get("file")}，{v.get("artist", "")}，{v.get("license", "")}，{v["page"]}')
w('\n## 声音\n')
w('- 旁白：豆包语音合成 2.0（刘飞音色），逐段整读；离线中文识别逐句回听核对（`src/check_lines.py`），英文专名另用英文识别复核。')
w('- 配乐：本期原创，程序作曲（`src/music.py`），FluidSynth + FluidR3 GM 音色库渲染。全片统一小节网格：片名、“我就宰了你”、“规模经济共享”、'
  '“净利润九十二亿”、“买、买、买”、片尾“美国运通”与 logo 处卡点，每章要点卡期间上扬、章节号亮起时重拍；原声下只留铺底。')
w('- 原声：影像原片音轨，整段响度对齐旁白，原声下配乐再压低。除原声外，不模仿、不合成任何真实人物的声音。')
open(os.path.join(ROOT, 'docs', 'SOURCES.md'), 'w').write('\n'.join(out) + '\n')
print('docs/SOURCES.md', len(out), 'lines')


# ------------------------------------------------------------------ docs/脚本.md：旁白全文（含时间戳与原声）
SOT_NAME = {'cnbc': 'CNBC Squawk Box · Becky Quick 专访巴菲特 · 2026-07-15'}
o = []; w = o.append
w('# 《一块五的热狗——芒格为什么最爱 Costco》旁白脚本（第六期）\n')
w(f'片长 {ts(TL["total"])}。出处见 `docs/SOURCES.md`，核实过程与参考脚本勘误见 `research/核实笔记.md`。\n')
CHE = {c[0]: c for c in CHAPTERS}
cur = None
w(f'\n## 开场（0:00.0）\n')
for lid, ch, text, say, mood, src in LINES:
    if ch != cur and ch in CHE and CHE[ch][1]:
        c = CHE[ch]; en = c[2] if len(c) > 2 and isinstance(c[2], str) else ''
        st = TL['chapters'].get(ch, [SEG[lid]['start']])[0]
        w(f'\n## {c[1]}' + (f'  ·  {en}' if en else '') + f'（{ts(st)}）\n')
    cur = ch
    w(f'- `{ts(SEG[lid]["start"])}` {text}')
    for sid, so in SOTS.items():
        if so['after'] == lid: w(f'  - 🔊 原声（{so["srcname"]}）：“{so["en"]}”')
w(f'\n## 片尾预告（{ts(SEG["tease"]["start"])}）\n')
w(f'- {TEASE[1]}')
for sid, so in SOTS.items():
    if so['after'] == 'tease': w(f'  - 🔊 原声（{so["srcname"]}）：“{so["en"]}”')
w('- 系列片单：可口可乐 → 苹果 → 日本商社 → 谷歌 → 喜诗糖果 → Costco → 美国运通')
open(os.path.join(ROOT, 'docs', '脚本.md'), 'w').write('\n'.join(o) + '\n')
print('docs/脚本.md', len(o), 'lines')
