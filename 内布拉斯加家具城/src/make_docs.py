"""生成 docs/SOURCES.md：逐句旁白的出处（含片中时间戳）、原声、屏幕原话、数据口径、影像素材与配乐说明。时间戳取自 work/timeline.json。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, QUOTES, CHAPTERS, SOTS, SOT_SRC
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
w('# 《银行赚 13%，它凭什么赚 30%？——巴菲特持有三十年的美国运通》出处与口径\n')
w(f'片长 {ts(TL["total"])}。美国运通财务数字取自 2025 年度报告（含 2025 Form 10-K）与 2025 年第四季度财报附表（Exhibit 99.2）；'
  '伯克希尔数字与原话取自致股东信原文；详细核实过程与参考脚本的勘误见 `research/核实笔记.md`。\n')
w('**口径原则**：营收为“扣除利息支出后”；非利息收入不等于“不占用资本”；1.7 亿是受理点而非直接签约商户；'
  '银行业对比用 FDIC 的资产回报率与美联储的信用卡核销率（同为 2025 年）；“13%–14%”是巴菲特的口头说法；'
  '只查到媒体转述或第三方测算的，旁白写“据报道 / 有媒体估算”。\n')
w('## 逐句旁白\n')
cur = None
for lid, ch, text, say, mood, src in LINES:
    if ch != cur:
        w(f'\n### {CHN.get(ch) or "开场"}\n'); cur = ch
    w(f'- `{ts(SEG[lid]["start"])}` {text}' + (f'\n  - 出处：{src}' if src else ''))
    for sid, so in SOTS.items():
        if so['after'] == lid: w(sot_line(sid, so))
w(f'\n### 片尾\n\n- `{ts(TL["chapters"]["end"][0])}` 无旁白：落版字“六十年，看的是同一件事”化作粒子，汇聚成「巴芒价值」logo（本期起不再预告下一期）')
w('\n## 原声（SOT）\n')
w('片中 2 处直接播放巴菲特的真实原声，都来自 CNBC Squawk Box 2026-07-15 专访（第四期已入库的原片），是同一段回答里前后相接的两句，'
  '在片中分开播放（开场与第七章），各自原速、不改词、不拼接；入出点切在自然停顿，经离线英文语音识别（sherpa-onnx whisper small.en，`src/asr_en.py`）逐句核对；'
  '屏幕给出英文原话、中文翻译与出处。致股东信、年报、采访转述等文字材料只用屏幕引语卡。\n')
for sid, so in SOTS.items():
    sg = SEG['sot_' + sid]
    w(f'- `{ts(sg["start"])}` {WHO[so["who"]]}（{so["srcname"]}，{sg["len"]:.1f}s）“{so["en"]}”')
w('\n## 屏幕原话（英文原句 + 中文翻译）\n')
for k, (en, cn, who) in QUOTES.items():
    w(f'- **{who}**：“{en}” —— {cn}')
w('\n- 致股东信原文均可在 https://www.berkshirehathaway.com/letters/letters.html 查到；屏幕引语卡注明年份。')
w('\n## 数据口径\n')
w('- 伯克希尔（2025-12-31）：持股 22.1%；成本 $1,287M；市值 $56,088M；2025 年分红 $479M。1995 年“基本完成”买入（1998 年仍有少量增持），2023 年信：二十多年未买卖。')
w('- 运通 2025 年：营收（扣除利息支出后）$72,229M；商户折扣收入 $37,401M（51.8%）；净卡费 $9,993M（+18%）；服务费及其他 $7,471M；净利息收入 $17,364M（24.0%）；'
  '非利息收入合计 $54,865M（76.0%）；积分 $18,409M + 持卡人服务 $6,057M = $24,466M（约营收 34%，同比 +14%）；净利润 $10,833M；ROE 33.9%（2024 年 34.6%，2023 年 31.5%）。')
w('- 资产回报率：运通 10,833 ÷ 平均总资产 (271,461 + 300,052) / 2 ≈ 3.8%（本片计算）；FDIC 全美投保银行业 2025 年 ROA 1.20%。运通股东权益 / 总资产 = 33,474 / 300,052 ≈ 11%。')
w('- 核销率：运通卡贷款净核销率（仅本金）2.2%；美联储 FRED CORCCACBS 全美商业银行信用卡核销率 2025 年各季 4.43%、4.18%、4.18%、4.11%（季调、年化）。')
w('- 规模：自营卡 8,660 万张、刷卡额 $1.67 万亿；第三方发卡 6,620 万张；受理点 1.7 亿以上（含第三方收单、支付机构、数字钱包，含中国约 3,700 万）。每卡消费约为 Visa、万事达卡的三倍（运通口径，注 6）。')
w('- 年费收入：2018 年 $3,441M（2019Q4 财报附表）→ 2025 年 $9,993M。2025 年新发自营卡 1,250 万张，七成以上新账户为收年费的卡；年轻客群 65% / 75%；新客户平均 33 岁（白金卡）、29 岁（金卡）。')
w('- 色拉油丑闻：损失超过 1.8 亿美元；运通代为和解 6,000 万美元；股价约 65 → 37 美元（1963-10 → 1964-01，多家来源）；巴菲特合伙基金约 40% 资金、5% 以上股权、1,300 万美元（1994 年信）。')
w('- Costco：1999 年起独家、2004 年起联名卡；2015-02-12 宣布不续约；Costco 联名卡约占运通全球卡贷款 20%、流通卡 10%；Costco 受理成本约 0.6%（Bloomberg 2015-10-15）。')
w('- 白金卡：$695 → $895（2025-09）；“$3,500 权益”为运通口径，需用满各项额度；第三方测算多数持卡人约 $1,500–2,500。百夫长卡现行收费为媒体报道。')
w('- 风险：卡贷款 + 应收账款 $213,863M（2025 年末）；达美联名卡约占刷卡额 13%、卡贷款 21%，协议到 2029 年底；商户费率承压（10-K 风险因素原文）。')
w('- 示意画面（油罐剖面、四方/闭环/飞轮图、硬币与方块、卡片线稿）均为示意或按上述数字绘制；自绘图形不使用任何公司的商标。')
w('\n## 影像素材\n')
for k, v in IA.items():
    w(f'- `{k}`：{v["source"]}（片源起点 {v["start"]}s，{v["dur"]}s）{("—— " + v["note"]) if v.get("note") else ""}')
w('\n影像只取画面、不用原声（原声段落除外），画面上逐镜署名。照片（Wikimedia Commons，已核授权）：')
for k, v in CR.items():
    w(f'- `{k}`：{v.get("title") or v.get("file")}，{v.get("artist", "")}，{v.get("license", "")}，{v["page"]}')
w('\n## 声音\n')
w('- 旁白：豆包语音合成 2.0（刘飞音色），逐段整读；离线中文识别逐句回听核对（`src/check_lines.py`），英文专名另用英文识别复核。')
w('- 配乐：本期原创，程序作曲（`src/music.py`），FluidSynth + FluidR3 GM 音色库渲染。全片统一小节网格：片名、股价跌到“三十七美元”、“闭环”、'
  '“三点八美元”、“不再续约”、“里子把人留下来”与片尾 logo 处卡点，每章要点卡期间上扬、章节号亮起时重拍；原声下只留铺底。')
w('- 原声：影像原片音轨，整段响度对齐旁白，原声下配乐再压低。除原声外，不模仿、不合成任何真实人物的声音。')
open(os.path.join(ROOT, 'docs', 'SOURCES.md'), 'w').write('\n'.join(out) + '\n')
print('docs/SOURCES.md', len(out), 'lines')


# ------------------------------------------------------------------ docs/脚本.md：旁白全文（含时间戳与原声）
SOT_NAME = {'cnbc': 'CNBC Squawk Box · Becky Quick 专访巴菲特 · 2026-07-15'}
o = []; w = o.append
w('# 《银行赚 13%，它凭什么赚 30%？——巴菲特持有三十年的美国运通》旁白脚本（第七期）\n')
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
w(f'\n## 片尾（{ts(TL["chapters"]["end"][0])}）\n')
w('- 无旁白：落版字化作粒子，汇聚成「巴芒价值」logo。')
open(os.path.join(ROOT, 'docs', '脚本.md'), 'w').write('\n'.join(o) + '\n')
print('docs/脚本.md', len(o), 'lines')
