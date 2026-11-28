"""生成 docs/SOURCES.md：逐句旁白的出处（含片中时间戳）、原声、屏幕原话、数据口径、影像素材与配乐说明。时间戳取自 work/timeline.json。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, QUOTES, CHAPTERS, SOTS, SOT_SRC
WHO = {'buffett': '巴菲特'}
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
TITLE_ = '《全押美国——巴菲特与 BNSF》'
w(f'# {TITLE_}出处与口径\n')
w(f'第二季第二期。片长 {ts(TL["total"])}。一手来源：伯克希尔历年致股东信与 2025 年年报（10-K）、BNSF 与伯克希尔 2009-11-03 联合新闻稿（SEC 8-K 附件 99.1）、'
  '联合太平洋 2025 年四季度业绩与 2026 年三季度 10-Q、美国地面运输委员会（STB）公告；核实过程见 `research/核实笔记.md`。\n')
w('**口径原则**：“345 亿美元”是阿贝尔 2025 年信写的 2010 年全部股权作价（含此前已持有的部分）；“约 440 亿美元”是新闻稿口径，含 100 亿美元 BNSF 债务；'
  '“5000 亿美元、几十年”是巴菲特在 2023 年信里的估计（“my guess”）；利润率是 BNSF 营业利润率（100% − 运营比率）；'
  '“累计约 620 亿美元分红”= 截至 2020 年底的 418 亿 + 2021–2025 年平均每年 41 亿 × 5，为本片推算；“差约 13 亿美元”= 约 5.7 个百分点 × 每个百分点 2.3 亿，为本片推算；'
  '联合太平洋—诺福克南方合并截至 2026 年 11 月尚未获批，只说“提议”。\n')
w('## 逐句旁白\n')
cur = None
for lid, ch, text, say, mood, src in LINES:
    if ch != cur:
        w(f'\n### {CHN.get(ch) or "开场"}\n'); cur = ch
    w(f'- `{ts(SEG[lid]["start"])}` {text}' + (f'\n  - 出处：{src}' if src else ''))
w(f'\n### 片尾\n\n- `{ts(TL["chapters"]["end"][0])}` 无旁白：下期预告的落版字“下期 · 台积电”化作粒子，汇聚成「巴芒价值」logo')
w('\n## 原声\n')
w('巴菲特真实原声 1 段，出自 CNBC Squawk Box 2026-07-15 Becky Quick 专访（本系列谷歌一期已用的同一条片源）：原速、不改词、不拼接，入出点切在自然停顿，经离线英文语音识别核对；'
  '出点单独核查最后 1.5 秒（语音识别 + 基频），原候选出点 96.32 s 的结尾混进了主持人“Okay, so you’re”，改收在 95.8 s“…worth far more money.”之后。屏幕同时给出英文原话、中文翻译与出处。\n')
for sid, so in SOTS.items(): w(sot_line(sid, so))
w('')
w('## 屏幕原话（英文原句 + 中文翻译）\n')
for k, (en, cn, who) in QUOTES.items():
    w(f'- **{who}**：“{en}” —— {cn}')
w('- 另：开场与第四章屏幕引用伯克希尔 2023 年致股东信原文（“…$22 billion or more than $1½ billion annually. Ouch!”）。')
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
w('\n影像只取画面、不用原声，画面上逐镜署名；回顾片段 `s1_japan` 取自本系列《东京下注——巴菲特与日本五大商社》成片（只取画面，画面标「回顾 · 日本商社」）。1942 年影片只取不带其他公司字样的镜头。照片：')
for k, v in CR.items():
    w(f'- `{k}`：{v.get("title") or v.get("file")}，{v.get("artist", "")}，{v.get("license", "")}，{v["page"]}')
w('\n照片来自维基共享资源（逐张核对授权，作者与协议见上表；`src/fetch_commons.py` 逐张间隔下载原图）。')
w('\n## 声音\n')
w('- 旁白：豆包语音合成 3.0（刘飞 3.0 音色 multi_male_liufei2_v3_uranus_bigtts），每章一条录完（段内不拼接），另逐句合成参考音频只用于对齐；拉平音高漂移、逐句 DTW 切句（`src/tts_take.py`、`src/voice_build.py`）。'
  '对齐校验全部通过；第三章、第七章录音整体偏高（比开场高 1.6、2.15 个半音），用 `src/pitch_level.py` 按章平移（−1.20、−1.75 个半音，不改共振峰与时长），之后各章与开场相差都在约 1 个半音内；有声语速 4.7–5.6 字/秒。逐句中文识别（`src/check_vo.py`）最低相似度 0.92，差异为同音字与数字写法。')
w('- 巴菲特原声：单独一轨，响度对齐旁白；原声下配乐只留铺底。出点逐段核查最后 1.5 秒（`src/cut_sot.py`）。')
w('- 成片：竖版 1080×1920 与横版 1920×1080 两条（同一次渲染、同一条音轨；横版按区域重新排版，见 `src/film.py` 的 landscape）。不再输出预览版，成片不入库。')
# 配乐：授权音乐按叙事剪辑卡点（src/score_cues.py）
import score_cues as SC
SC.CUES.clear(); SC.HITS.clear(); SC.plan()
_hn = [('h2', '五千亿', '“五千亿”'), ('h3', '三百四十五亿', '“三百四十五亿”'), ('h5', '他说', 'h5 进入（“吃资本”）'), ('h6', '巴菲特为什么还说', '设问“为什么还说”'),
       ('c1e', '十一天后', '“十一天后”宣布交易'), ('c2c', '九百六十万', '“九百六十万车”'), ('c3e', '两关都过了', '“两关都过了”'),
       ('c4b', '哎哟', '“哎哟”'), ('c5d', '六百二十亿', '“累计约六百二十亿”'), ('c6d', '变局', '“变局也来了”'), ('c7e', '一百年后', '“一百年后”')]
HITNAME = {round(SC.WT(i, w_), 3): lab for i, w_, lab in _hn}
HITNAME.update({round(TL['chapters']['title'][0], 3): '片名', round(TL['logo'], 3): '片尾 logo'})
HITNAME.update({round(TL['chapters'][c][0], 3): '第' + '一二三四五六七'[int(c[2]) - 1] + '章章节卡' for c in ('ch2', 'ch3', 'ch4', 'ch5', 'ch6', 'ch7')})
HITNAME.update({round(SC.S('h5'), 3): 'h5 进入（“吃资本”）', round(SC.S('c5f'), 3): '“买在恐慌里”（Achilles 终段）', round(SC.S('c7c'), 3): '“第二”（台阶 2）', round(SC.S('c7d'), 3): '“第三”（台阶 3）'})
used = sorted({c['name'] for c in SC.CUES})
w('- 配乐（`src/score_cues.py`，沿用第一期第二版的做法）：用高质量授权音乐按旁白剪辑、卡点。按你的要求本期直接做全片，未出小样。曲目全部出自 **Kevin MacLeod（incompetech.com），授权 CC BY 4.0**（可商用，需署名；片尾已署名）：'
  + '、'.join('《' + SC.TRACKS[n][0][:-4] + '》' for n in used) + '。')
w('  - 做法：每段把曲子的某一段放到时间线上；两个锚点之间最多变速 ±3%（ffmpeg atempo），让曲子里的齐奏或段落进入正好落在关键词、章节卡和片尾 logo 上；'
  '重拍前留 0.4–0.6 秒真正的静默；设问处整段静默；原声、芒格语录和回顾段落下只留钢琴（《Blue Feather》每次取不同段落）；开场的《Industrial Cinematic》在第六章“变局”处以乐队全开的后段再现，第一章的《Hiding Your Reality》在下期预告再现；同一首曲子的同一段不重复使用。')
w('  - 自检：全片配乐按 2 秒窗口统计能量，没有连续 20 秒起伏小于 2 dB 的平直段（`docs/配乐能量曲线.png`）；说话时旁白比配乐高约 10 LU。')
w('\n### 配乐分段表\n')
w('| 时间线 | 曲目 | 曲中段落 | 变速 |'); w('|---|---|---|---|')
for c in SC.CUES:
    w(f"| {ts(c['Ta'])}–{ts(c['Tb'])} | {SC.TRACKS[c['name']][0][:-4]} | {c['ta']:.1f}–{c['tb']:.1f} s | {(c['rate'] - 1) * 100:+.1f}% |")
w('\n### 卡点表（重拍与画面同帧）\n')
w('| 时间 | 落点 |'); w('|---|---|')
for h in sorted(set(SC.HITS)):
    w(f'| {ts(h)} | {HITNAME.get(round(h, 3), "")} |')
w('')
w('- 混音（`src/audio_mix.py`）：旁白 70 Hz 高通、2.2:1 轻压缩、很淡的短混响与 −64 dBFS 噪底；配乐保留自身起伏（各章只做 ±3 dB 内的校平）；'
  '闪避放在最后一步（−9 dB，人声频段再 −3 dB，只有大重拍短暂放开），说话时旁白比配乐高约 10 LU（实测 9.7 LU）；线性增益到 −14 LUFS 并限峰。'
  '旁白不模仿、不合成任何真实人物的声音。')
open(os.path.join(ROOT, 'docs', 'SOURCES.md'), 'w').write('\n'.join(out) + '\n')
print('docs/SOURCES.md', len(out), 'lines')


# ------------------------------------------------------------------ docs/脚本.md：旁白全文（含时间戳与原声）
o = []; w = o.append
w(f'# {TITLE_}旁白脚本（第二季第二期）\n')
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


# ------------------------------------------------------------------ 配乐能量曲线（制作宪章 三.3：自检要量化）
import numpy as np, soundfile as sf
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
m, sr = sf.read(os.path.join(work, 'music', 'score_raw.wav')); m = m.mean(1) if m.ndim > 1 else m
tt = np.arange(0, len(m) / sr - 2, 1.0)
db = [20 * np.log10(np.sqrt(np.mean(m[int(t * sr):int((t + 2) * sr)] ** 2)) + 1e-6) for t in tt]
fig, ax = plt.subplots(figsize=(14, 3.2), dpi=120)
ax.plot(tt, db, color='#d9a441', lw=1.4)
for h in sorted(set(SC.HITS)): ax.axvline(h, color='#c0392b', lw=0.8, alpha=0.6)
for k, (a_, b_) in TL['chapters'].items():
    ax.axvspan(a_, a_ + 0.01, color='#555'); ax.text(a_ + 1, max(db) + 1, k, fontsize=7, color='#333')
ax.set_xlim(0, tt[-1]); ax.set_ylim(-45, max(db) + 4); ax.set_xlabel('s'); ax.set_ylabel('dB (2 s RMS)')
ax.set_title('Music energy curve (red lines = hit points)')
fig.tight_layout(); fig.savefig(os.path.join(ROOT, 'docs', '配乐能量曲线.png')); print('docs/配乐能量曲线.png')
