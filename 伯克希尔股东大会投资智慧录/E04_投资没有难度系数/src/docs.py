"""由 timeline.json 生成文字交付物：口播脚本、原始问答清单、分镜与精确到秒的剪辑时间线、素材来源与事实核查。

用法：python3 src/docs.py WORK OUT_DIR
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import (ARCHIVE_ITEM, ARCHIVE_URL, CLIP_IN, CNBC_CHAPTER, CNBC_URL, FACTS, BROLL, PIC_BOX, MEETING_DATE,
                    GEMINI_MODEL, GEMINI_VOICE, GEMINI_STYLE)

work, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
tl = json.load(open(os.path.join(work, 'timeline.json')))
MORNING_START = 0.0          # archive.org 全场录像从上午场开场开始


def tc(t):
    t = max(t, 0)
    return f'{int(t // 60):d}:{t % 60:05.2f}'


def hms(t):
    return f'{int(t // 3600)}:{int(t // 60 % 60):02d}:{t % 60:05.2f}'


def src_of(t):
    for sg in tl['qa']['segs']:
        if sg['t0'] - 0.1 <= t <= sg['t1'] + 0.1:
            return sg['src_in'] + t - sg['t0'] + CLIP_IN
    return None


# ------------------------------------------------------------------ 口播脚本
VOICE_NOTE = (f'配音：Google Gemini TTS（`{GEMINI_MODEL}`，声音 `{GEMINI_VOICE}`），风格指令原样放在 speech_metadata.style：'
              f'“{GEMINI_STYLE}”。按段落成组合成，段内句间停顿保留模型自己的节奏，段落之间按语义设置停顿；整体提速 7%（保留音高）。')
L = ['# 口播脚本 · 第四集《投资没有难度系数》', '',
     VOICE_NOTE, '',
     '> 标注说明：**【旁白】** 为本片撰写的解说；**【原声】** 为 1994 年股东大会原始录像的声音。画面上同样区分：原声段标注“画面与声音：1994 年上午场原始录像”，解读段标注“本片解读，非巴菲特或芒格原话”。', '']
L += ['## 一、冷开场【原声】', '']
for s in tl['cold_subs']:
    L.append(f"- `{tc(s['t0'])}–{tc(s['t1'])}` {s['en']}  \n  {s['zh']}")
L += ['', '## 二、开场【旁白】', '']
for v in tl['intro']['vo']:
    L.append(f"- `{tc(v['t0'])}–{tc(v['t1'])}` {v['text']}")
L += ['', '## 三、原始问答【原声】', '',
      f"来源：{CNBC_CHAPTER}（1994 年伯克希尔股东大会上午场）。英文逐字取自 CNBC 逐字稿，只省略口头重起的半句；中文为本片翻译。", '',
      '本片为节选，省略了：' + '；'.join(tl['qa']['omitted']) + '。省略处画面先暗下去再亮起，并标出“· 节选 ·”。以下为保留部分。', '',
      '| 片内时间 | archive.org 录像时间 | 英文原话 | 中文字幕 |', '|---|---|---|---|']
for s in tl['qa']['subs']:
    src = src_of(s['t0'] + 0.1)
    L.append(f"| {tc(s['t0'])} | {hms(src) if src is not None else '—'} | {s['en']} | {s['zh']} |")
L += ['', '## 四、投资启示【旁白 · 本片解读，非巴菲特或芒格原话】', '']
for v in tl['insight']['vo']:
    L.append(f"- `{tc(v['t0'])}–{tc(v['t1'])}` {v['text']}")
L += ['', f"解读口播时长：{tl['insight']['t1'] - tl['insight']['t0']:.1f} 秒。", '', '## 五、一句话总结【旁白】', '']
for v in tl['summary']['vo']:
    L.append(f"- `{tc(v['t0'])}–{tc(v['t1'])}` {v['text']}")
open(os.path.join(out, '口播脚本.md'), 'w').write('\n'.join(L) + '\n')

# ------------------------------------------------------------------ 分镜与剪辑时间线
V = {v['id']: v for p in ('intro', 'insight', 'summary') for v in tl[p]['vo']}
Q = {s['scene']: s for s in tl['qa']['scenes']}
E = tl['end']
NV = tl['nerves']
shots = [
    (0, tl['t_title'], '开场钩子', '第 0 帧就是中文大字“研究得越复杂、模型越精密——就越能赚钱？”；下方“你的选股功课”示意图：模型曲线越堆越多、缠成一团，“研报＋ 模型＋ 变量＋”标签依次弹出；念到“巴菲特”时浮现“巴菲特的回答——也许会让你松一口气”。先共情、再给视角',
     'S1（中文口播）', 'Long Road Ahead B 第二乐句，钩子说完时淡出到几乎无声；低沉冲击'),
    (tl['t_title'], tl['cold']['t0'], '片名', '与前三集同款的系列片名：巴菲特与芒格 / 伯克希尔股东大会 / 投资智慧录（金色擦除显现 + 流光）+「第四集 · 投资没有难度系数」；重拍上粒子爆开、冲击波扩散', '—',
     'Long Road Ahead B 全奏进入（33.66s）+ 低沉冲击'),
    (tl['cold']['t0'], V['S2']['t0'], '巴菲特原声', '1994 年大会原始录像（巴菲特与芒格同框），瞄准框、扫描线、随原声能量跳动的冰青粒子；中英字幕', '巴菲特原声 A12B：“你不需要做非凡的事，也能取得非凡的结果。”', 'Long Road Ahead B（压低）'),
    (V['S2']['t0'], V['S3']['t0'], '1994 年春天', '上方大会实况；下方“1994 年 1–3 月 · 宝洁公司”面板：“固定利率 ⇄ 浮动利率”的掉期示意弧线，说到“复杂”时越缠越多，“两笔利率掉期 / 杠杆”标签；“−1.57 亿美元”砸入并故障，下方注明“税前 · 为两笔利率掉期平仓（宝洁 1994 年 1–3 月季度报告）”', 'S2', '同上'),
    (V['S3']['t0'], tl['ctx']['t0'], '1994 年的提问', '上方大会实况；“1994.04.25 · 奥马哈 · 伯克希尔股东大会”；“耐克、锐步这样的全球品牌，前景有哪些不确定性？”逐句砸入，NIKE / REEBOK 两个标签', 'S3', '同上'),
    (tl['ctx']['t0'], tl['qa']['t0'], '背景卡', '与前三集同款：淡金大字 1994、1994 年 4 月 25 日 · 美国奥马哈、伯克希尔·哈撒韦年度股东大会 · 上午场；CNBC 第 38–39 章', '—', '低频下潜；音乐停止'),
]
desc = {'ask': '“股东的问题”面板：伯克希尔偏爱的全球品牌 COCA-COLA / GILLETTE，制鞋业的全球品牌 NIKE / REEBOK →“它们有哪些不确定性？”',
        'nike': '“竞争地位能不能持续 10–20 年？”→ NIKE / REEBOK“看不清”（冰青）与 BROWN / DEXTER“看得懂”（金）两张卡片 →“对我们：更难理解，更难拿准”“对更懂那一行的人：也许更容易”',
        'pi': '“有些企业，比别的企业容易理解得多”→ 金色大字“× 3”与冰青的“× π = 3.14159…”（数字越滚越长）→“宁可乘以 3，也不乘以 π”（现场笑声）',
        'labels': '“雇一个头衔合适的人，就能做成很难的事？”→ 博士 / 顾问 / 专家 / 名校标签 →“最危险的想法之一”（琥珀）→“保持简单，就不必把思考外包”（金）；镜头缓缓推向芒格，巴菲特接话时拉回',
        'bar': '“不必做非凡的事，也能取得非凡的结果”→ 一尺与七尺两副栏架，上方两枚绶带：人们以为七尺的更大 →“在投资里，完全不是这样”时两枚变得一样大',
        'coke': '“这有什么复杂的？”可口可乐 →“+30 亿美元”滚动（税前 · 1993 年底持股成本 10.24 亿 → 市值 41.68 亿）→ 产品 / 分销体系 / 财务 →“几十万、几百万人都懂”→“他们只是什么也没做”',
        'report': '一摞越堆越厚的报告，“1,000 页”“博士 × N”→“10–15 年后，它会是什么样子？”与琥珀问号 →“可那说明不了什么”',
        'wrong': '金色大字“避免犯错”（现场笑声）→ 金句卡“最重要的，是避免犯错。”停留约 3 秒'}
for sc in ('ask', 'nike', 'pi', 'labels', 'bar', 'coke', 'report', 'wrong'):
    s = Q[sc]
    shots.append((s['t0'], s['t1'], f'原声·{sc}', desc[sc] + '；上方是 1994 年原始录像，说话人与原声波形，下方中英字幕', '原始录像原声', '无音乐'))
shots += [
    (tl['insight']['t_card'], V['I1']['t0'], '投资启示', '与前三集完全一致的标题转场：“投资启示”在重拍上砸入并爆开、HUD 圆环、INSIGHT、“以下为本片解读，非巴菲特或芒格原话”；之后整段解读的背景是透视网格 + 3D 金色微粒 + 漏光', '—', 'Impact Allegretto + 低沉冲击'),
    (V['I1']['t0'], V['I2']['t0'], '投资不按难度给分', '一尺（金）与七尺（冰青）两副栏架依次立起，上方两枚绶带之间砸入“＝”与“回报一样”；下方“一以贯之”：1989 年致股东信 “…one-foot hurdles that we could step over rather than … seven-footers.” 打字机显现，“1998、2005 年大会上，他又用奥运跳水的‘难度系数’讲了同一个道理”', 'I1', 'Impact Allegretto（压低）'),
    (V['I2']['t0'], V['I5']['t0'], '第一性原理', '全奏进入的重拍上冲击波扩散，“市场只为结果付钱”砸入 →“企业将来赚多少 / 你当初付多少”两张卡片 →“难度 ✗ 没有这一项”。下：“要同时猜对的环节越多”——十根柱子依次升起（0.9 的 1–10 次方：90% → 59% → 35%），上方一条十个环的链条；“十环全对：35%”琥珀砸入；标注“示意 · 0.9 的 n 次方（各环独立）”', 'I2–I3', '全奏进入（42.03s）对准 I2 开口 + 低沉冲击'),
    (V['I5']['t0'], V['I7']['t0'], '十年赌局', '“2008 → 2017”；左：巴菲特押“标普 500 指数基金 · 最简单的一跳”（金）；右：对手押“5 只母基金 → 两百多家对冲基金”（冰青，一团两百多个点）。下：2008–2017 十年累计（2007 年底 = 1），金色粗线为指数基金，五条冰青细线为母基金；终点 +125.8%，最好的 +87.7%，最差的 +2.8%；“2008 年五只母基金都跑赢指数；此后九年，每一年整体都落后”', 'I5–I6', 'Impact Allegretto 全奏'),
    (V['I7']['t0'], V['I10']['t0'], '代价：德克斯特鞋厂', '低音撤走的低谷上：“哪是一尺？哪是七尺？”两副横杆高度上下浮动、看不准；“1993 · 德克斯特鞋厂”“我自认为看得懂”+ 本段原声英文 →“海外竞争 → 竞争优势没几年就消失”砸入、碎裂；付出 25,203 股伯克希尔 A 股：1993 年 4.33 亿美元 → 2014 年约 57 亿美元（琥珀柱）；“最惨痛的错误”+ 2014 年信 “The most gruesome was Dexter Shoe.”', 'I7–I8', '低谷（88.04s）对准 I7 开口 + 低频下潜'),
    (V['I10']['t0'], V['I11']['t0'], '今天：三个问题', '“先问三个问题”：01 这门生意，我看得懂吗？/ 02 十年后，它大概什么样？/ 03 要猜对几件事才能赚钱？依次砸入；说到“答不上来”时第二张卡片缩小、掉进琥珀色的“太难 · TOO HARD”篮子', 'I10', '全奏回归（112.03s）对准 I10 开口'),
    (V['I11']['t0'], tl['summary']['t0'], '收尾 + 蓄力', '星图在身后升起，“宁愿把看得懂的范围，想得小一点”“少犯错，比做难事重要得多”（金）逐句显现；之后越飞越快，星点拉成曲速拖尾；高潮前 0.4 秒纯黑', 'I11', '只剩鼓的蓄力段（配乐抬高 4dB）+ 低频膨胀'),
    (tl['summary']['t0'], E['t_particles'], '一句话总结', '重拍上整片星图同时亮起、冲击波扩散，再缓缓暗下；与前三集同款的总结版式：金色大字“投资没有难度系数：跨过一尺的栏，就够了。”+ 流光', 'M', 'Impact Allegretto 全奏高潮（144.03s）+ 低频下潜'),
    (E['t_particles'], E['t_logo'], '片尾·汇聚', '总结文字化为金色微粒，沿官方 logo 透明通道汇聚', '—', '同上'),
    (E['t_logo'], E['t_brand'], '片尾·logo', '官方 logo_baman.png 清晰居中出现，背后淡蓝光晕', '—', '同上'),
    (E['t_brand'], E['t_fade0'], '片尾·品牌', '重拍上浮现金色「巴芒价值」+「BUFFETT · MUNGER」（官方预渲染字样）、关注语，随后流光扫过', '—', '高潮段里的小节强拍（156.04s）+ 低沉冲击'),
    (E['t_fade0'], tl['dur'], '淡出', '整体（含右上角角标）缓慢淡出', '—', '音乐淡出'),
]
L = ['# 分镜与剪辑时间线 · 第四集《投资没有难度系数》', '',
     f"成片 1080×1920 · 30fps · 总长 {tl['dur']:.2f} 秒（{int(tl['dur'] // 60)}:{tl['dur'] % 60:05.2f}）。时间全部由 `src/timeline.py` 计算，与成片逐帧一致。", '',
     '## 段落', '', '| 起 | 止 | 段落 |', '|---|---|---|']
for s in tl['sections']:
    L.append(f"| {tc(s['t0'])} | {tc(s['t1'])} | {s['name']} |")
L += ['', '## 分镜（每个镜头的作用）', '', '| 起 | 止 | 镜头 | 画面 | 声音 | 音乐 / 音效 |', '|---|---|---|---|---|---|']
for a, b, n, d, v, m in shots:
    L.append(f'| {tc(a)} | {tc(b)} | {n} | {d} | {v} | {m} |')
L += ['', '## 原始素材剪辑点', '',
      f"- 冷开场原声：录像 {hms(CLIP_IN + tl['cold']['src_in'])}–{hms(CLIP_IN + tl['cold']['src_out'])} → 片内 {tc(tl['cold']['t0'])}–{tc(tl['cold']['t1'])}"]
for sg in tl['qa']['segs']:
    L.append(f"- 问答原声 {sg['ids'][0]}–{sg['ids'][1]}：录像 {hms(CLIP_IN + sg['src_in'])}–{hms(CLIP_IN + sg['src_out'])} → 片内 {tc(sg['t0'])}–{tc(sg['t1'])}（剪点在句间能量最低处）")
L += ['- 节选时省略：' + '；'.join(tl['qa']['omitted']) + '。核心问题与论证主线（耐克、锐步的不确定性 → 看不清它们 10–20 年的竞争地位，看得懂布朗与德克斯特 → 宁可乘以 3 → 芒格：头衔不能替你思考，保持简单 → 不必做非凡的事 → 一尺与七尺的栏 → 可口可乐 30 亿美元 → 一千页的报告 → 避免犯错）完整保留。',
      '- 档案录像本身有几处数字静音，用同一录音的底噪补齐；每段节选内用慢速电平跟随抹平现场轻重差异。',
      f"- 片头历史影像（上午场）：录像 " + '、'.join(f'{hms(b)} 起 16 秒' for b in BROLL) + '。',
      f"- 画面只取源画面中 x {PIC_BOX[0]}–{PIC_BOX[2]}、y {PIC_BOX[1]}–{PIC_BOX[3]} 的干净区域（避开第三方水印和烧录字幕），等比缩放，不拉伸。", '',
      '## 音乐', '', '| 片内起 | 片内止 | 曲目 | 曲内起点 | 用途 |', '|---|---|---|---|---|']
use = ['开场钩子至开场口播（第二乐句铺在钩子下面，钩子说完时淡出到几乎无声 → 33.66s 全奏进入对准片名；段落开口吸附到节拍）',
       '投资启示至片尾（42.03s 全奏进入对准第一性原理 I2；88.04s 低音撤走的低谷对准“代价：德克斯特”I7；112.03s 全奏回归对准“今天”I10；136–143s 只剩鼓的蓄力托住收尾；144.03s 全奏高潮对准一句话总结；156.04s 小节强拍对准「巴芒价值」）']
for m, u in zip(tl['music'], use):
    L.append(f"| {tc(m['t0'])} | {tc(m['t1'])} | Kevin MacLeod – {m['track']} | {m['src_in']:.2f}s | {u} |")
L += ['', '原始问答期间不放音乐。口播期间音乐按人声包络侧链压低 11dB（提前 0.15 秒）。与前三集一致的后期：泛光、横向光晕，强重拍上推镜 4%、闪光并做色散，小节强拍轻微脉动（原声问答段减弱）。解读段内换镜为 0.5 秒暗下 + 0.45 秒亮起，不硬切。', '',
      '## 转场音效（全部为正弦合成，4 阶 180Hz 低通，无噪声源）', '', '| 片内时间 | 类型 | 电平 |', '|---|---|---|']
names = {'swell': '低频膨胀（Bass Swell）', 'impact': '低沉冲击（Deep Impact）+ 低频空间混响', 'subdrop': '低频下潜（Sub Drop）+ 低频空间混响'}
for e in tl['sfx']:
    L.append(f"| {tc(e['t'])} | {names[e['kind']]} | {e['gain']} dBFS 峰值 |")
L += ['', '## 画面风格（本集）', '',
      '- 系列一致：第 0 秒中文钩子、片头 1994 年大会原始录像 + 金色系列片名 + 背景卡、左上章节标签、字幕版式、问答收尾的金句卡、“投资启示”标题转场、总结与品牌片尾都与前三集一致；后期同为泛光、横向光晕、重拍推镜 + 闪光 + 色散。',
      '- 本集的视觉母题是“栏架”：一尺（金）与七尺（冰青）的横杆贯穿问答、概括与代价三处；每个论点一张直观的图：宝洁的利率掉期、环节越多越容易错的概率柱、十年赌局的真实收益曲线、德克斯特付出的股票价值。示意图（钩子里的模型曲线、利率掉期弧线、概率柱）标注“示意”。',
      '- 原声问答段克制：原始录像窗口 + 原声波形 + 关键观点面板，不做卡点特效。',
      '- 光色：金色 = 简单、看得懂、长期回报；冰青 = 复杂、价格与数据；琥珀 = 错误、风险与代价。']
open(os.path.join(out, '分镜与剪辑时间线.md'), 'w').write('\n'.join(L) + '\n')

# ------------------------------------------------------------------ 素材来源与事实核查
L = ['# 素材来源、授权与事实核查', '', '## 原始问答', '',
     f'- 内容：{MEETING_DATE} 伯克希尔·哈撒韦年度股东大会上午场，CNBC Warren Buffett Archive 第 38 章「Nike and Reebok」与第 39 章「“You don’t have to do exceptional things to get exceptional results”」（同一个问答）。提问者为来自纽约市的股东（逐字稿记作 Mike Assail，并标注为音译），回答者沃伦·巴菲特，查理·芒格补充。',
     f'- CNBC 档案页：{CNBC_URL}',
     '- 逐字稿：CNBC 档案逐字稿（经 GitHub 镜像 `pzponge/Yestoday` 获取，文件 `Warren_Buffett/Berkshire_Hathaway_Annual_Meeting/1994_Annual_Meeting.md` 第 38–39 节）。',
     f'- 录像来源：archive.org 条目 `{ARCHIVE_ITEM}`（{ARCHIVE_URL}），为 YouTube 频道 Legendary Investor 上传的 1994 年全场录像；本题从录像 1:19:08（“Zone 2.”）开始，巴菲特在 1:23:38 说完“The big thing to do is avoid being wrong.”。只按区间读取需要的音频与画面，不下载整片。',
     '- 字幕时间：faster-whisper（medium.en）逐词时间戳与逐字稿做序列匹配，669 个单词中 644 个直接对上（96.3%），其余插值；识别结果只用于定时，字幕文字以逐字稿为准。',
     '- 使用性质：评论、教育与研究目的的引用；保留问答主线，不改变原意。', '',
     '## 画面素材', '',
     '- 原声段画面为同一题的 1994 年上午场原始录像（巴菲特与芒格同框），不是静帧、不是 AI 生成。巴菲特说“这个有什么复杂的？”时，可口可乐不在镜头里；“this”指可口可乐依据 CNBC 逐字稿的中文译文与 1993 年持股表。',
     '- 裁切时避开了第三方频道水印与其烧录字幕。',
     '- 图表与文字动画均为本片根据下列公开资料制作的数据可视化，不冒充历史影像。', '',
     '## 事实核查', '', '| 片中位置 | 事实 | 出处 |', '|---|---|---|']
for k, f, s in FACTS:
    L.append(f'| {k} | {f} | {s} |')
L += ['', '致股东信原文：https://www.berkshirehathaway.com/letters/1989.html 、 https://www.berkshirehathaway.com/letters/1993.html 、 '
      'https://www.berkshirehathaway.com/letters/1994.html 、 https://www.berkshirehathaway.com/letters/2007ltr.pdf 、 '
      'https://www.berkshirehathaway.com/letters/2014ltr.pdf 、 https://www.berkshirehathaway.com/letters/2017ltr.pdf', '',
      '宝洁季度报告：SEC EDGAR，Procter & Gamble Form 10-Q（截至 1994 年 3 月 31 日），https://www.sec.gov/Archives/edgar/data/0000080424/000008042494000012/0000080424-94-000012.txt 。'
      '十年赌局的逐年数据存于 `src/script.py` 的 `BET`（照录 2017 年致股东信的记分表）。', '',
      '## 音乐（CC BY 4.0）', '',
      '- "Long Road Ahead B" Kevin MacLeod (incompetech.com) — Licensed under Creative Commons: By Attribution 4.0 License — http://creativecommons.org/licenses/by/4.0/',
      '- "Impact Allegretto" Kevin MacLeod (incompetech.com) — Licensed under Creative Commons: By Attribution 4.0 License — http://creativecommons.org/licenses/by/4.0/',
      '- 选曲：本集从 incompetech 曲库新筛 28 首候选（避开前三集用过的 6 首），逐首做 librosa 能量曲线、低频占比、节拍与起音分析。'
      '“Long Road Ahead B”的第二个乐句会淡出到几乎无声，33.66s 全奏进入，正好接在第 0 秒钩子的末尾、落在片名上；'
      '“Impact Allegretto”（120 BPM）结构清楚：42.03s 全奏进入 → 88.04s 低音撤走的低谷 → 112.03s 全奏回归 → 136–143s 只剩鼓的蓄力 → 144.03s 全奏高潮，与解读的“第一性原理与案例 → 代价 → 今天 → 总结”一一对应。',
      '- 发布时请在简介中保留以上署名。', '',
      '## 配音', '', f'- Google Gemini TTS `{GEMINI_MODEL}`，声音 `{GEMINI_VOICE}`；字幕时间由 faster-whisper 对合成结果强制对齐得到。', '',
      '## 字体（SIL Open Font License）', '', '- 思源宋体 / 思源黑体（Noto Serif SC、Noto Sans SC）、Cormorant Garamond、EB Garamond、Inter、JetBrains Mono，均来自 Google Fonts。', '',
      '## 品牌', '', '- 右上角角标：仓库 `brand/brand.py` 的 `Hud`（逐帧合成，含光晕与流光）。',
      '- 片尾 logo：`brand/logo_baman.png`（经 `brand.load_logo` 预乘 alpha 缩放）；片尾文字取自 `brand/hud_lockup@4x.png` 的官方预渲染文字区。']
open(os.path.join(out, '素材来源与事实核查.md'), 'w').write('\n'.join(L) + '\n')
print('docs written to', out)
