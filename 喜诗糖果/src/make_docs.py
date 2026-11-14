"""生成 docs/SOURCES.md：逐句旁白的出处（含片中时间戳）、屏幕原话、数据口径、影像素材与配乐说明。时间戳取自 work/timeline.json。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, QUOTES, CHAPTERS, TEASE, SOTS, SOT_SRC, HBO_SRC
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
work = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work')
TL = json.load(open(os.path.join(work, 'timeline.json')))
IA = json.load(open(os.path.join(ROOT, 'assets', 'media', 'ia_clips.json')))
CR = json.load(open(os.path.join(ROOT, 'assets', 'media', 'credits.json')))
SEG = {s['id']: s for s in TL['segs']}
CHN = {c[0]: c[1] for c in CHAPTERS}


def ts(sec): return f'{int(sec // 60)}:{sec % 60:04.1f}'


out = []; w = out.append
w('# 《一盒糖的学费——芒格怎样改变了巴菲特》出处与口径\n')
w(f'片长 {ts(TL["total"])}。喜诗的全部数字取自伯克希尔致股东信原文（原文存 `research/raw/`，摘录见 `research/sees_passages*.txt`）；'
  '详细核实过程与口径见 `research/核实笔记.md`。\n')
w('**口径原则**：税前 / 税后、当年 / 累计分开写；信中不同年份说法有出入时，片中只用核实笔记标注的口径；'
  '2015–2025 年的致股东信未再披露喜诗利润，片中不推测近况。\n')
w('## 逐句旁白\n')
cur = None
for lid, ch, text, say, mood, src in LINES:
    if ch != cur:
        w(f'\n### {CHN.get(ch) or "开场"}\n'); cur = ch
    w(f'- `{ts(SEG[lid]["start"])}` {text}' + (f'\n  - 出处：{src}' if src else ''))
    for sid, so in SOTS.items():
        if so['after'] == lid:
            sg = SEG['sot_' + sid]
            who = '芒格' if so.get('who') == 'munger' else '巴菲特'
            w(f'- `{ts(sg["start"])}` 🔊 **{who}原声**：“{so["en"]}” —— ' + ''.join(c for _, c in so['ph']) +
              f'\n  - 出处：{so.get("srcname", SOT_SRC)}，{"访谈" if so.get("src") == "hbo_munger" else "专访"} {so["ts"]}（切点见 `src/cut_sot.py`、`work/sot/sot.json`）')
w(f'\n### 片尾\n\n- `{ts(SEG["tease"]["start"])}` {TEASE[0]}')
w('\n## 大师原声（SOT）\n')
w('片中 4 处直接播放公开采访里的真实原声：芒格 2 处（Kunhardt Film Foundation 公开发布的 HBO 纪录片《Becoming Warren Buffett》芒格完整访谈，'
  'https://archive.org/details/youtube-F6s2HAzMeL0 ，原 YouTube F6s2HAzMeL0），巴菲特 2 处（CNBC Squawk Box 2026-07-15 专访）。'
  '全部原速、不改词、不拼接；入出点切在自然停顿，经离线英文语音识别逐句核对（芒格访谈全文转写：`research/芒格HBO访谈_转写_whisper.txt`）；'
  '屏幕给出英文原话、中文翻译与出处。画面与声音同一入点（口型同步）；芒格访谈画面上烧录的时间码已抹去、片名水印已裁出画外。')
for sid, so in SOTS.items():
    sg = SEG['sot_' + sid]
    who = '芒格' if so.get('who') == 'munger' else '巴菲特'
    w(f'- `{ts(sg["start"])}` {who}（{"访谈" if so.get("src") == "hbo_munger" else "专访"} {so["ts"]}，{sg["len"]:.1f}s）“{so["en"]}”')
w('\n## 屏幕原话（英文原句 + 中文翻译）\n')
for k, (en, cn, who) in QUOTES.items():
    w(f'- **{who}**：“{en}” —— {cn}')
w('\n- 致股东信原文均可在 https://www.berkshirehathaway.com/letters/letters.html 查到；屏幕引语卡注明年份。')
w('- 1983 年信附录《商誉及其摊销》（Goodwill and its Amortization）是第二章的主要依据。')
w('\n## 数据口径\n')
w('- 1972–1984 年喜诗数据：1984 年致股东信原表（销售额、税后营业利润、售出磅数、年底门店）。每磅售价 1972 年约 $1.85 为本片按原表推算（$31,337,000 ÷ 16,954,000 磅）；1984 年 $5.49 为信中原数。')
w('- 美国物价：BLS CPI-U 年均值（1972 年 41.8、1975 年 53.8、1978 年 65.2、1981 年 90.9、1984 年 103.9）。')
w('- 收购价：卖方名义要价 $4000 万，含 $1000 万多余现金，实际要价 $3000 万；成交 $2500 万（1991、2007、2014 年信）。有形资产 1991 年信作 $700 万、其余各信作 $800 万，片中用约 $800 万。')
w('- 2007 年：销售 $3.83 亿、税前 $8200 万、经营所需资本 $4000 万；1972–2007 累计税前 $13.5 亿，其中 $3200 万再投入。2014 年：累计税前 $19 亿，追加投入 $4000 万。')
w('- “一般公司要投约 $4 亿”是巴菲特在 2007 年信中举的例子，不是统计数。')
w('- 2025 年：伯克希尔 2025 年 10-K——约 250 家门店（另有约 100 个季节性网点），主要在加州和美国西部；约一半年收入在第四季度。10-K 不单列喜诗利润。')
w('- 示意画面（美国西部门店分布、资金循环、储蓄罐、资金分枝、月度柱形状等）均在画面上标注“示意”，不代表真实数据；卓别林《寻子遇仙记》挑烟头的镜头为“烟蒂投资”的示意。')
w('- 1952 年《我爱露西》：依据喜诗官网大事记（“Lucy Loves See’s”）；片中画面为今日喜诗厨房实拍，不是剧集画面。')
w('\n## 影像素材\n')
for k, v in IA.items():
    w(f'- `{k}`：{v["source"]}（片源起点 {v["start"]}s，{v["dur"]}s）{("—— " + v["note"]) if v.get("note") else ""}')
w('\n影像只取画面、不用原声（原声段落除外），画面上逐镜署名。照片（Wikimedia Commons，已核授权）：')
for k, v in CR.items():
    w(f'- `{k}`：{v.get("title") or v.get("file")}，{v.get("artist", "")}，{v.get("license", "")}，{v["page"]}')
w('\n## 声音\n')
w('- 旁白：豆包语音合成 2.0（刘飞音色），逐段整读；离线中文识别逐句回听核对（`src/check_vo.py`、`src/check_lines.py`）。')
w('- 配乐：本期原创，程序作曲（`src/music.py`，以 F 大调为主、谈判与“做不到的事”转 D 小调，80 BPM，四音主题贯穿），'
  'FluidSynth + FluidR3 GM 音色库渲染；片名、“13.5 亿”、“芒格把我扳了过来”、片尾 logo 四处重拍；巴菲特原声下只留铺底。')
w('- 大师原声：采访原片音轨，80Hz 高通、整段响度对齐旁白，原声下配乐再压低 5 dB。除原声外，不模仿、不合成任何真实人物的声音。')
open(os.path.join(ROOT, 'docs', 'SOURCES.md'), 'w').write('\n'.join(out) + '\n')
print('docs/SOURCES.md', len(out), 'lines')
