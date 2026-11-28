"""生成 docs/SOURCES.md：逐句旁白的出处（含片中时间戳）、原声、屏幕原话、数据口径、影像素材与配乐说明。时间戳取自 work/timeline.json。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, QUOTES, CHAPTERS, SOTS, SOT_SRC
WHO = {'buffett': '巴菲特（2010）'}
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
work = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work')
TL = json.load(open(os.path.join(work, 'timeline.json')))
IA = json.load(open(os.path.join(ROOT, 'assets', 'media', 'ia_clips.json')))
CR = json.load(open(os.path.join(ROOT, 'assets', 'media', 'credits.json')))
SEG = {s['id']: s for s in TL['segs']}
CHN = {c[0]: c[1] for c in CHAPTERS}


def ts(sec): return f'{int(sec // 60)}:{sec % 60:04.1f}'


def sot_line(sid, so):
    sg = SEG['sot_' + sid]
    return (f'- `{ts(sg["start"])}` 🔊 **{WHO[so["who"]]}原声**：“{so["en"]}” —— ' + ''.join(c for _, c in so['ph']) +
            f'\n  - 出处：{so.get("srcname", SOT_SRC)}' + (f'，片中 {so["ts"]}' if so.get('ts') else '') + '（切点见 `src/cut_sot.py`、`work/sot/sot.json`）')


out = []; w = out.append
TITLE_ = '《不情愿的顾客——巴菲特与穆迪》'
w(f'# {TITLE_}出处与口径\n')
w(f'第二季第一期。片长 {ts(TL["total"])}。一手来源：伯克希尔历年致股东信与 2025 年年报持股表、穆迪 2025 年全年业绩新闻稿（8-K 附件 99.1）、'
  'SEC 评级办公室 2025 年 1 月 NRSRO 年度报告、金融危机调查委员会（FCIC）最终报告与 2010-05-26 访谈巴菲特录音、美国司法部 2017 年新闻稿；核实过程见 `research/核实笔记.md`。\n')
w('**口径原则**：持股数字一律取伯克希尔年报持股表的年末数；“51 倍”是剩下这 2467 万股的成本对比 2025 年底市值（本片推算，不含已卖出部分与历年分红）；'
  '利润率是穆迪评级业务（MIS）2025 年的调整后营业利润率；市场份额取 SEC 报告（存续评级数为 2023 年底，收入份额为 2020–2023 财年）；'
  '2009 年卖出的原因只按 2009 年信原文写（为买陶氏化学、瑞士再保险与 BNSF 筹钱），不说成因丑闻卖出；巴菲特说的“错”是股价很高时没卖。\n')
w('## 逐句旁白\n')
cur = None
for lid, ch, text, say, mood, src in LINES:
    if ch != cur:
        w(f'\n### {CHN.get(ch) or "开场"}\n'); cur = ch
    w(f'- `{ts(SEG[lid]["start"])}` {text}' + (f'\n  - 出处：{src}' if src else ''))
w(f'\n### 片尾\n\n- `{ts(TL["chapters"]["end"][0])}` 无旁白：下期预告的落版字“下期 · BNSF”化作粒子，汇聚成「巴芒价值」logo（第二季起恢复下期预告）')
w('\n## 原声\n')
w('巴菲特真实原声 5 段，全部出自 FCIC 工作人员在奥马哈访谈巴菲特的录音（2010-05-26，2011 年 2 月公开，斯坦福法学院 FCIC 档案）：原速、不改词、不拼接，入出点切在自然停顿，'
  '经离线英文语音识别逐段核对（老录音音质一般，识别把 single 听成 second、terrible 听成 charitable 等，屏幕文字以 Santangel’s Review 整理的逐字稿为准，并与录音逐句对照）。'
  '录音没有画面：原声段落用同年的照片（白宫官方照片等）加录音响度驱动的声纹呈现，不配假口型。屏幕同时给出英文原话、中文翻译与出处。\n')
for sid, so in SOTS.items(): w(sot_line(sid, so))
w('')
w('## 屏幕原话（英文原句 + 中文翻译）\n')
for k, (en, cn, who) in QUOTES.items():
    w(f'- **{who}**：“{en}” —— {cn}')
w('- 另：开场屏幕引用伯克希尔 2025 年致股东信第 15 页原文；第三章屏幕引用 SEC 评级办公室 2025 年报告第 35–36 页原文。')
w('\n## 数据口径\n')
w('- 伯克希尔持股：2001 年底 2400 万股（2005 年一拆二前）、成本 4.99 亿美元；2007 年底 4800 万股、19.1%、市值 17.14 亿；2013 年底 24,669,778 股、11.5%、成本 2.48 亿；'
  '2025 年底股数不变、13.9%、成本 2.48 亿、市值 126.03 亿、当年分红 0.93 亿美元（各年持股表）。')
w('- 穆迪 2025 财年：总营收 77.18 亿美元；评级业务对外营收 41.19 亿、调整后营业利润率 63.6%；数据与分析 35.99 亿、经常性收入 96%；评级收入中交易性 67%（业绩新闻稿表 6）。')
w('- 市场份额：SEC 登记的 NRSRO 共 10 家（2024 年底）；三家大机构占存续评级 94.15%（标普 49.96%、穆迪 31.73%、惠誉 12.46%，2023 年底）；收入份额 2020–2023 年依次为 94.1%、93.2%、91.1%、91.9%，中型机构 5.1%、5.6%、7.3%、6.7%。')
w('- 危机：2000–2007 年穆迪给近 4.5 万只房贷相关证券评三A；2010 年初全美拿到三A 的私营公司 6 家；2006 年每个工作日 30 只；当年三A 的房贷证券最终 83% 被下调（FCIC 结论第 xxv 页）。')
w('- 股价：雅虎财经月线（按拆股调整），2007-02 最高 76.09 美元，2009-03 最低 15.57 美元（`assets/media/mco_monthly.csv`）。')
w('- 和解：2017-01-13，近 8.64 亿美元（美国司法部、21 个州与华盛顿特区），其中联邦民事罚款 4.375 亿；穆迪在事实陈述中承认了关键行为。')
w('- 1909 年：约翰·穆迪出版铁路证券手册，用字母等级给近 1300 只铁路债券评级；Poor’s 1916 年、Fitch 1924 年开始出售评级；约 1970 年代初转为发行人付费；1975 年 SEC 引入 NRSRO。')
w('- 示意画面（评级阶梯、流程图、评级章、价签）均为示意；自绘图形不使用任何公司的商标。')
w('\n## 影像素材\n')
for k, v in IA.items():
    w(f'- `{k}`：{v["source"]}（片源起点 {v["start"]}s，{v["dur"]}s）{("—— " + v["note"]) if v.get("note") else ""}，{v["ia"]}')
w('\n影像只取画面、不用原声，画面上逐镜署名；第一季回顾片段取自本系列成片（只取画面，裁掉原片角标）。照片：')
for k, v in CR.items():
    w(f'- `{k}`：{v.get("title") or v.get("file")}，{v.get("artist", "")}，{v.get("license", "")}，{v["page"]}')
w('\n照片来自维基共享资源（逐张核对授权，作者与协议见上表；`src/fetch_commons.py` 逐张间隔下载原图）。')
w('\n## 声音\n')
w('- 旁白：豆包语音合成 3.0（刘飞 3.0 音色 multi_male_liufei2_v3_uranus_bigtts），每章一条录完（段内不拼接），另逐句合成参考音频只用于对齐；拉平音高漂移、逐句 DTW 切句（`src/tts_take.py`、`src/voice_build.py`）。'
  '对齐校验全部通过；修正后每分钟音高中位数首尾差 1.1 个半音；有声语速 5.0–5.9 字/秒。逐句中文识别（`src/check_vo.py`）只剩同音字差异（穆迪/目的、它/他等）。')
w('- 巴菲特原声：单独一轨，响度对齐旁白；原声下配乐只留铺底。出点逐段核查最后 1.5 秒（`src/cut_sot.py`）。')
w('- 配乐（`src/score.py`，沿用第八期第四版引擎）：本片原创，程序作曲，MuseScore General 音色库；不用踩镲、沙锤、军鼓、镲片、噪声上扬与“刷”的转场音效。'
  '每章换调、换速度、换织体：开场先是承接第一季的温暖钢琴（F 大调），冲突处转 D 小调 96 脉冲 → 片名铜管 → 第一章 A 小调 84 温暖、规矩倒过来处转 C 大调律动 → 第二章 F 大调 92 拨弦'
  ' → 第三章 D 小调 108 驱动、“大家都认它”转 F 大调颂歌 → 第四章 C 小调 76 心跳 → 第五章降 E 大调 100 → 第六章 B 小调 88 脉冲 → 第七章 D 大调 100 颂歌，下期预告转 A 大调 112 驱动。'
  '卡点（先抽空再重拍）：“只有六家”“百分之八十三”“凭什么”“倒了过来”“两关”“百分之九十四”“大家都认它”“八成”“没有”“五十一倍”“下一期”与片尾 logo。')
w('- 混音（`src/audio_mix.py`）：旁白 70 Hz 高通、2.2:1 轻压缩、很淡的短混响与 −64 dBFS 噪底；配乐保留自身起伏（各章只做 ±3 dB 内的校平）；'
  '闪避放在最后一步（−9 dB，人声频段再 −3 dB，只有大重拍短暂放开），说话时旁白比配乐高约 11 LU；线性增益到 −14 LUFS 并限峰。'
  '旁白不模仿、不合成任何真实人物的声音。')
open(os.path.join(ROOT, 'docs', 'SOURCES.md'), 'w').write('\n'.join(out) + '\n')
print('docs/SOURCES.md', len(out), 'lines')


# ------------------------------------------------------------------ docs/脚本.md：旁白全文（含时间戳与原声）
o = []; w = o.append
w(f'# {TITLE_}旁白脚本（第二季第一期）\n')
w(f'片长 {ts(TL["total"])}。出处见 `docs/SOURCES.md`，核实过程与勘误见 `research/核实笔记.md`。旁白按章整录（docs/旁白一致性与自然衔接.md）。\n')
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
w('- 无旁白：下期预告的落版字化作粒子，汇聚成「巴芒价值」logo。')
open(os.path.join(ROOT, 'docs', '脚本.md'), 'w').write('\n'.join(o) + '\n')
print('docs/脚本.md', len(o), 'lines')
