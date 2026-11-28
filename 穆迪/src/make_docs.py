"""生成 docs/SOURCES.md：逐句旁白的出处（含片中时间戳）、原声、屏幕原话、数据口径、影像素材与配乐说明。时间戳取自 work/timeline.json。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, QUOTES, CHAPTERS, SOTS, SOT_SRC
WHO = {'buffett': '巴菲特', 'buffett94': '巴菲特（1994）'}
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
TITLE_ = '《一张支票，换一句话——巴菲特与内布拉斯加家具城》'
w(f'# {TITLE_}出处与口径\n')
w(f'片长 {ts(TL["total"])}。一手来源：伯克希尔历年致股东信原文、伯克希尔 2013 年年报所附 1983-08-30 收购提议书与 NFM 1946 年报表原件、'
  '伯克希尔 2025 年年报（Form 10-K）；详细核实过程与流行说法的勘误见 `research/核实笔记.md`。\n')
w('**口径原则**：凡巴菲特信里有原话的一律以原信为准；“握手成交、一页纸合同”这类流行说法改为原件所示的“一页多纸的提议书、五位股东签字”；'
  '500 美元与 1937 年按 1983–2011 年历封信（2020 年信另记作 1936 年、2500 美元，见核实笔记）；NFM 近年的营收与利润伯克希尔不单独披露，片中不报（只引用 1984–1990 年信利润表里列出的 NFM 税前利润）；'
  '四家家具零售商合计营收为业界媒体估算，不说成 NFM 一家。\n')
w('## 逐句旁白\n')
cur = None
for lid, ch, text, say, mood, src in LINES:
    if ch != cur:
        w(f'\n### {CHN.get(ch) or "开场"}\n'); cur = ch
    w(f'- `{ts(SEG[lid]["start"])}` {text}' + (f'\n  - 出处：{src}' if src else ''))
w(f'\n### 片尾\n\n- `{ts(TL["chapters"]["end"][0])}` 无旁白：落版字“一张支票，换一句话”化作粒子，汇聚成「巴芒价值」logo（第七期起不再预告下一期）')
w('\n## 原声\n')
w('巴菲特真实原声 3 段：原速、不改词、不拼接，入出点切在自然停顿，经离线英文语音识别逐句核对（核对记录见 `research/核实笔记.md` 第八节）。屏幕同时给出英文原话、中文翻译与出处。\n')
for sid, so in SOTS.items(): w(sot_line(sid, so))
w('- 1994 年股东会一段：转载件中 32.5–34.5 秒（片源秒数）有一句听不清的插话，原样保留，屏幕记作“……”；画面裁掉了转载水印与烧录字幕。')
w('- 引出原声的旁白下面用同一场 CNBC 专访的无声双人景（不与原声画面重复）。\n')
w('## 屏幕原话（英文原句 + 中文翻译）\n')
for k, (en, cn, who) in QUOTES.items():
    w(f'- **{who}**：“{en}” —— {cn}')
w('- 另：第四章屏幕引用 1992 年信“having been incautious on this point when she was 89”；第六章屏幕引用伯克希尔 2025 年 10-K'
  '“With the exception of NFM, our retailing businesses generated flat or lower earnings in 2025 compared to the prior year.”；'
  '第七章屏幕引用 1999 年信“My thanks go to Louie, Ron and Irv Blumkin for getting me started in the furniture business.”')
w('\n- 致股东信原文均可在 https://www.berkshirehathaway.com/letters/letters.html 查到；收购提议书与 1946 年报表见 https://www.berkshirehathaway.com/2013ar/2013ar.pdf 第 114–117 页。')
w('\n## 数据口径\n')
w('- 1983 年收购：提议书日期 1983-08-30（巴菲特 53 岁生日）；买下 90%，现金 $55,350,000（手写金额）；其余 10% 由路易与儿子们保留；五位股东各 20%；1984 年信“a check for $55 million”；2020 年信：整体估值 $6000 万。')
w('- 没有审计：1984 年信（没审计、没盘点、没核对应收账款、没查产权）；1993 年信（没有经审计的报表、没查不动产记录、没有任何担保）。')
w('- 1946 年：现金 $50.00；年末合伙人资本 $72,264.41；全年销售 $575,096.47，毛利率 17.77%，净利 $29,884.42（报表原件）。')
w('- “好价钱”：NFM 全公司税前利润（千美元）1984 14,511；1985 12,686；1986 17,685；1987 16,837；1988 18,439；1989 17,070；1990 17,248（各年信利润表）；'
  '七年合计约 $1.14 亿（本片加总）。作价按 2020 年信整体估值 $6000 万：约为 1984 年税前利润的 4.1 倍；七年合计约为作价的 1.9 倍。均为全公司、税前口径。')
w('- 1983 年：一家约 20 万平方英尺的店，年销售一亿多美元，超过奥马哈所有同行之和（1983 年信）。')
w('- Levitz 对比（1984 年信，引 Levitz 1984 财年 10-K）：Levitz 毛利率 44.4%，NFM“not much more than half”；营业费用率 NFM 约 16.5%，Levitz 35.6%；NFM 每年至少替顾客省 $3000 万。片中 NFM 毛利率柱长为示意。')
w('- 得梅因调查（1990 年信）：服务该市的 20 家家具零售商中 NFM 人气第 3，另 19 家在本地，NFM 在 130 英里外。')
w('- 1989 年：5 月辞职（95 岁）；过去三年其他部门 +24%、地毯 −17%；在隔壁自有大楼开新店。1992 年底：大楼与土地卖给 NFM，99 岁签竞业禁止。工作到 103 岁，1998-08-09 去世，享年 104 岁。')
w('- 扩张：堪萨斯城店 2003 年开业（45 万平方英尺零售面积，25 英亩停车场）；2007 年奥马哈、堪萨斯城各约 $4 亿；2011 年利润创纪录、超过 1983 年十倍；'
  '达拉斯北郊 The Colony 店 2015 年开业，一个屋顶下卖场加仓库 180 万平方英尺（片中“约 23 个标准足球场”按 105×68 米折算）；2020 年三家店均创纪录（疫情关店六周多）。')
w('- 股东会那一周：2016 年奥马哈店一周 $4550 万；平时一周约 $900 万（2014、2015 年信）。')
w('- 今天：四个零售园区近 450 万平方英尺（零售、仓储、办公），在各自市场都是最大的家居零售商（2025 年 10-K）；奥斯汀 Cedar Park 园区预计 2027 年春开业（NFM 官网）。')
w('- 风险：伯克希尔家居零售收入 2024 年 −6.4%（销量下降、价格竞争加剧）；2025 年零售板块中除 NFM 外利润持平或下降（2025 年 10-K）。')
w('- 一家牵出一家：R.C. Willey（1995，经 Irv Blumkin）、Star Furniture（1997，两小时谈定）、Jordan’s（1999）；四家 2025 年合计营收约 $33.4 亿（Home News Now 2026-06-22，业界媒体估算）。')
w('- 示意画面（书、支票、店面方盒子、价签、飞轮、手机比价、地图）均为示意；自绘图形不使用任何公司的商标。')
w('\n## 影像素材\n')
for k, v in IA.items():
    w(f'- `{k}`：{v["source"]}（片源起点 {v["start"]}s，{v["dur"]}s）{("—— " + v["note"]) if v.get("note") else ""}，{v["ia"]}')
w('\n影像只取画面、不用原声，画面上逐镜署名。1921 年教育片为搬演画面，只用于“离开俄国、去美国”的气氛，画面上注明“搬演”。照片与文件影像：')
for k, v in CR.items():
    w(f'- `{k}`：{v.get("title") or v.get("file")}，{v.get("artist", "")}，{v.get("license", "")}，{v["page"]}')
w('\n照片来自美国国会图书馆（公有领域：FSA/OWI、普罗库金-戈尔斯基、Detroit Publishing Co.、Carol M. Highsmith）与维基共享资源（逐张核对授权，作者与协议见上表；维基共享资源对本环境限流，`src/fetch_commons.py` 逐张间隔下载原图）。')
w('\n## 声音\n')
w('- 旁白（第四版）：豆包语音合成 3.0（doubao-seed-tts-3.0，刘飞 3.0 音色 multi_male_liufei2_v3_uranus_bigtts，用户指定；原 2.0 接口自 2026-11-26 起不可用），`src/tts_take.py`。'
  '3.0 音色在长文本里音高一路上扬（整篇一条录完的三条试录，十分钟内升 5–8 个半音），改为**每章一条录完**（第三章分两条）：每段仍是一次请求、段内不拼接，段与段只在章节卡处相接。'
  '另逐句合成参考音频，只用于对齐与校验。拉平剩余音高漂移（pYIN 估趋势 + Praat PSOLA），逐句子序列 DTW 切句并在停顿正中下刀，分段处直接用段间静音（`src/voice_build.py`）；'
  '段内首尾相接不插停顿，只在引语卡、原声、揭晓与数字之后留白（`src/timeline.py` 的 STORY / QUOTE_HOLD）。对齐校验全部通过；修正后每分钟音高中位数首尾差 1.2 个半音；有声语速 5.0–5.7 字/秒，与前几期相当。'
  '逐句中文识别（`src/check_vo.py`）只剩同音字与识别器的写法差异（“这一家”读作“zhèi 家”的连读、个别“事儿”的儿化）。')
w('- 巴菲特原声：单独一轨，80 Hz 高通，不压缩、不加混响，响度对齐旁白；原声下配乐再压 4 dB。出点逐段核查最后 1.5 秒（单独识别 + 基频查有没有混入主持人），见 `src/cut_sot.py`。')
w('- 配乐（第四版，`src/score.py`）：本片原创，程序作曲，MuseScore General 音色库；按用户要求**去掉一切沙沙声**——不用踩镲、沙锤、军鼓、镲片、噪声上扬与“刷”的转场音效；'
  '上扬改用弦乐音阶爬升 + 定音鼓滚奏 + 铜管渐强，重拍只留次低频与乐队和弦；旋律放在小提琴、圆号的中高音区；均衡去闷（320 Hz −3 dB）、提亮（2.7 kHz +2.5 dB）、10 kHz 以上滚降，混响变干。'
  '实测：500 Hz–6 kHz 能量占比由 22.5% 升到约 42%，6 kHz 以上的噪声成分降到原来的约 1/15。'
  '每章换调、换速度、换织体：开场 D 小调 92 的紧张脉冲 → 片名 F 大调铜管主题 → 第一章 A 小调 84 温暖钢琴（官司全赢处转 C 大调）'
  ' → 第二章 F 大调 100 律动 → 第三章：五条打法处 F 大调 108 明亮律动、飞轮全速、规模经济分享处重拍，两关处转 D 小调 112 驱动弦乐，“差距反而拉大了”转 F 大调颂歌 → 第四章 C 小调 76 心跳、隔壁新店处降 E 大调拨弦、九十九岁处转降 A 大调'
  ' → 第五章 D 大调 118 颂歌 → 第六章 B 小调 88 脉冲 → 第七章 D 大调 100 层层推进。同一条主题旋律换配器出现（钢琴、铜管、钟琴、圆号、合唱）。'
  '卡点（先抽空再重拍）：“六年后”“现金只有五十美元”“一个字没改”“将近两倍”“百分之十六点五”“倒贴”“反而拉大了”“辞职走了”“一百八十万”“三十三亿”与片尾 logo；章节号亮起时重拍。')
w('- 混音（`src/audio_mix.py`）：旁白 70 Hz 高通、2.2:1 轻压缩、很淡的短混响与 −64 dBFS 噪底；配乐保留自身起伏（各章只做 ±3 dB 内的校平）；'
  '闪避放在最后一步（−9 dB，人声频段再 −3 dB，只有大重拍短暂放开），说话时旁白比配乐高约 11 LU；线性增益到 −14 LUFS 并限峰。'
  '旁白不模仿、不合成任何真实人物的声音。')
open(os.path.join(ROOT, 'docs', 'SOURCES.md'), 'w').write('\n'.join(out) + '\n')
print('docs/SOURCES.md', len(out), 'lines')


# ------------------------------------------------------------------ docs/脚本.md：旁白全文（含时间戳与原声）
o = []; w = o.append
w(f'# {TITLE_}旁白脚本（第八期）\n')
w(f'片长 {ts(TL["total"])}。出处见 `docs/SOURCES.md`，核实过程与勘误见 `research/核实笔记.md`。旁白整篇一次合成（docs/旁白一致性与自然衔接.md）。\n')
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
