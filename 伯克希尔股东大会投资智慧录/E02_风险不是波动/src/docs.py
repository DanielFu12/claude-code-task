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
L = ['# 口播脚本 · 第二集《风险不是波动》', '',
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
    (0, tl['t_title'], '冷开场', '近乎纯黑的画面中央，一团冰青点云在剧烈乱跳，中间一颗暖金节点静静呼吸；中英字幕；底部时间尺停在“序”',
     '巴菲特原声 A19：“金融界在风险的衡量上，已经乱了套”', 'Hiding Your Reality 暗色铺底淡入；片名前低频膨胀'),
    (tl['t_title'], V['S1']['t0'], '片名', '暗到黑后，衬线大字“风险不是波动”在重拍上亮起并呼吸，下方一行字距很宽的“RISK IS NOT VOLATILITY”和一排很淡的金点', '—', 'Hiding Your Reality 整体进入 + 低沉冲击'),
    (V['S1']['t0'], V['S2']['t0'], '一年跌掉 25%', '十二个冰青节点用细线连成一年的价格，最后一个节点变成带圆环的暖金点；节点卡“−25% / 一年 / One year”；右上读数 P₁/P₀ = 0.75；时间尺滑到“问”',
     'S1', 'Hiding Your Reality（压低），段落开口踩拍'),
    (V['S2']['t0'], V['S3']['t0'], '教科书的答案', '倾斜网格平面上的冰青点云，一条暖金分界线转到斜率 β；节点卡“β / 贝塔”；读数 β = Cov(r, rₘ)/Var(rₘ)、β↑ ⇒ 更危险', 'S2', '同上'),
    (V['S3']['t0'], tl['ctx']['t0'], '1994 年的提问', '细边框“展柜”里的 1994 年大会原始录像；节点卡“1994 / 伯克希尔股东大会”与股东的问题', 'S3', '同上'),
    (tl['ctx']['t0'], tl['qa']['t0'], '背景卡', '九条冰青细线扇入一个带圆环的金色节点；节点卡“1994 · 04 · 25 / 伯克希尔·哈撒韦年度股东大会”；时间尺滑到“1994”', '—', '低频下潜；音乐停止'),
]
desc = {'ask': '一颗金色节点（您的风险观）与一团抖动的冰青点云（传统的风险观）之间一条细线，“≠”；读数 β 公式、“自相矛盾？”',
        'define': '一圈 36 个冰青点中有 5 个变成琥珀色（受到伤害或损失的可能性），中心金色节点；下方长出一条持有期时间轴；读数 Risk = P(harm or injury) → Risk = f(T)',
        'horizon': '一天里的价格点线从 11:30 走到收盘，终点分叉成一金一琥珀两个节点；读数 P(loss) ≈ 50%',
        'coke': '上方：一串金点长期缓缓上行（以当初买入价长期持有，Risk ≈ 0）；下方：几颗冰青点在一夜里乱跳（Risk ≫ 0）',
        'beta': '倾斜网格平面与点云，分界线转到 β；读数 Risk ≡ σ → Risk ≠ σ',
        'absurd': '零线之上：投资 A 的冰青节点在 +20%～+80% 间大起大落，投资 B 的金色节点稳稳停在 +5%；读数 σ(A) > σ(B) ⇒ Risk(A) > Risk(B)? → haywire · 乱了套',
        'expect': '60 个交易节点逐个亮起（金 = 赚、琥珀 = 亏），再用细线汇向一个中心节点；计数 N；读数 E[ΣXₖ] > 0',
        'munger': 'Fermat · Pascal，三层的概率树逐层展开；读数 E = Σ pᵢxᵢ；镜头缓缓推向芒格'}
for sc in ('ask', 'define', 'horizon', 'coke', 'beta', 'absurd', 'expect', 'munger'):
    s = Q[sc]
    shots.append((s['t0'], s['t1'], f'原声·{sc}', desc[sc] + '；上方细边框里是 1994 年原始录像，一排细点随原声起伏，下方中英字幕', '原始录像原声', '无音乐'))
shots += [
    (tl['insight']['t_card'], V['I1']['t0'], '投资启示', '衬线“投资启示 · INSIGHT”；左上“III · INSIGHT / 本片解读，非巴菲特或芒格原话”；时间尺滑到“启示”', '—', 'Nerves 安静的开头 + 低沉冲击'),
    (V['I1']['t0'], V['I2']['t0'], '两种定义', '左上一团剧烈抖动的冰青点云（价格的波动 · σ, β），右下一颗稳定发光、带圆环的金色节点（损失的可能性）', 'I1', 'Nerves（压低）'),
    (V['I2']['t0'], V['I3']['t0'], '持有期', '一串冰青节点从“买入”起伏着走到“持有期结束”，终点金色节点高于“当初的购买力”细线；节点卡“1993 / 致股东信”与原文；读数 W(T)/P(T) ≥ W(0)/P(0)', 'I2', '同上'),
    (V['I3']['t0'], V['I4']['t0'], '波动与风险', '一排冰青节点上下乱跳（波动），下方一颗金色节点始终亮着（钱还在不在）；节点卡“≠ / 波动不是风险”', 'I3', '同上'),
    (V['I4']['t0'], V['I7']['t0'], '华盛顿邮报', '配乐大段落进入的重拍上亮起：金色点云（生意）在中央缓缓旋转、越长越大；下方价格节点 1973 → 1974 下跌 25%（琥珀）并在风暴里抖动，之后一路走到 1993；计数 $10,600,000 → $8,000,000 → $440,000,000；时间尺“1973”', 'I4–I6', 'Nerves 大段落进入（28.5s）对准 I4 开口 + 低沉冲击'),
    (V['I7']['t0'], V['I11']['t0'], '德克斯特鞋业', '一团完全静止的金色点云（没有股价）与一条平直的冰青线（σ = 0）；海外竞争时点云散成星尘（价值归零）；付出去的伯克希尔股票化作一团琥珀点云长大：$433,000,000 → $0，$5,700,000,000；2007 年信原话；时间尺“1993”', 'I7–I10', 'Nerves 回落段 → 激增（62.3s）+ 低频下潜'),
    (V['I11']['t0'], V['I12']['t0'], '杠杆', '金色节点骑在冰青的价格浪上，一根琥珀细线把它拴向下方（借来的钱）；被迫在低点卖出时被拉下去、熄灭；浪平了，它再也没回来；读数 temporary ⇒ permanent', 'I11', 'Nerves 高段'),
    (V['I12']['t0'], V['I13']['t0'], '今天', '一条回撤的点线上亮起两个带圆环的检查点；节点卡“2 / 先问两个问题”：这门生意还在吗？我会被迫卖出吗？', 'I12', '同上'),
    (V['I13']['t0'], tl['summary']['t0'], '收尾 + 蓄力', '整句逐句淡入；背后全片的节点一颗颗亮起、连成一张星图，越来越密', 'I13', 'Nerves 留白段（99.6s 起，配乐提升 6dB）'),
    (tl['summary']['t0'], E['t_particles'], '一句话总结', '高潮重拍前 0.4 秒纯黑，重拍上全屏节点同时亮起、连线暴涨，再缓缓暗下；金色衬线大字“波动不是风险，永久损失才是。”呼吸两次；时间尺走到“终”', 'M', 'Nerves 高潮（108.3s）+ 低频下潜'),
    (E['t_particles'], E['t_logo'], '片尾·汇聚', '总结文字化为金色微粒，沿官方 logo 透明通道汇聚', '—', 'Nerves'),
    (E['t_logo'], E['t_brand'], '片尾·logo', '官方 logo_baman.png 清晰居中出现，背后淡蓝光晕', '—', '同上'),
    (E['t_brand'], E['t_fade0'], '片尾·品牌', '重拍上浮现金色「巴芒价值」+「BUFFETT · MUNGER」（官方预渲染字样）、关注语，随后流光扫过', '—', '低沉冲击（与重拍对齐）'),
    (E['t_fade0'], tl['dur'], '淡出', '整体（含右上角角标）缓慢淡出', '—', '音乐淡出'),
]
L = ['# 分镜与剪辑时间线 · 第二集《风险不是波动》', '',
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
    L.append(f"- 问答原声 {sg['ids'][0]}–{sg['ids'][1]}：录像 {hms(CLIP_IN + sg['src_in'])}–{hms(CLIP_IN + sg['src_out'])} → 片内 {tc(sg['t0'])}–{tc(sg['t1'])}（剪点在句间静音处）")
L += ['- 节选时省略：' + '；'.join(tl['qa']['omitted']) + '。核心问题与论证主线（风险的定义 → 持有期 → 贝塔不是风险 → 传统度量的荒谬 → 期望值 → 芒格的补充）完整保留。',
      f"- 片头历史影像（上午场）：录像 " + '、'.join(f'{hms(b)} 起 16 秒' for b in BROLL) + '。',
      f"- 画面只取源画面中 x {PIC_BOX[0]}–{PIC_BOX[2]}、y {PIC_BOX[1]}–{PIC_BOX[3]} 的干净区域（避开第三方水印和烧录字幕），等比缩放，不拉伸。", '',
      '## 音乐', '', '| 片内起 | 片内止 | 曲目 | 曲内起点 | 用途 |', '|---|---|---|---|---|']
use = ['冷开场至开场口播（暗色铺底 → 9.01s 打击乐整体进入对准片名；段落开口吸附到节拍）',
       f"投资启示至片尾（28.48s 大段落进入对准华盛顿邮报，46.27s 回落对应德克斯特的平静，62.25s 激增对应裂开，99.64s 留白承接收尾句，108.26s 高潮对准总结，之后的强拍对准「巴芒价值」）"]
for m, u in zip(tl['music'], use):
    L.append(f"| {tc(m['t0'])} | {tc(m['t1'])} | Kevin MacLeod – {m['track']} | {m['src_in']:.2f}s | {u} |")
L += ['', '原始问答期间不放音乐。口播期间音乐按人声包络侧链压低 11dB（提前 0.15 秒）。画面没有一次硬切：场景之间先整体暗到黑（0.85 秒）、停 0.4 秒，再按“图解 → 排印卡 → 读数”错开 0.5 秒亮起；强重拍上节点整体亮一下。', '',
      '## 转场音效（全部为正弦合成，4 阶 180Hz 低通，无噪声源）', '', '| 片内时间 | 类型 | 电平 |', '|---|---|---|']
names = {'swell': '低频膨胀（Bass Swell）', 'impact': '低沉冲击（Deep Impact）+ 低频空间混响', 'subdrop': '低频下潜（Sub Drop）+ 低频空间混响'}
for e in tl['sfx']:
    L.append(f"| {tc(e['t'])} | {names[e['kind']]} | {e['gain']} dBFS 峰值 |")
L += ['', '## 画面风格：暗夜星图编年（本集新增）', '',
      '- 近乎纯黑的背景（#010204，中心略亮、四周暗角，极稀疏的暗星尘），画面主体只有发光的点和细线；阈值泛光只让点线溢光，2% 以内的颗粒。',
      '- 两套光色：暖金（核心 #FFD9A0、外晕 #E0A060）= 被点亮、被选中的（内在价值、真正的风险）；冰青 #6FC3DF = 数据（价格、波动）；雾蓝紫 #636D9A 用于远景连线；琥珀 #D97F5B 用于亏损与付出去的。',
      '- 底部常驻时间刻度尺：序 · 问 · 1994 · 启示 · 1973 · 1993 · 杠杆 · 今 · 终；走过的部分变亮，当前点是一颗带光晕的白点，切场时滑到下一个节点。',
      '- 节点卡与图解对角放置：灰白衬线大数字（不发光）→ 短横线 → 中文衬线名 → 英文斜体名 → 灰色说明；左上段落标签（罗马数字 · 全大写英文，字距 0.4em），右上衬线读数，右下等宽状态读数。',
      '- 图解：发光节点 + 细连线、扇入结构、倾斜网格平面 + 点云 + 转动的分界线、点云体积增长与散成星尘、概率树、全屏星图。',
      '- 本系列的硬性要求高于原风格：保留中英字幕（衬线、灰白、无底条）与 1994 年原始录像（放在细边框“展柜”里，降饱和）。']
open(os.path.join(out, '分镜与剪辑时间线.md'), 'w').write('\n'.join(L) + '\n')

# ------------------------------------------------------------------ 素材来源与事实核查
L = ['# 素材来源、授权与事实核查', '', '## 原始问答', '',
     f'- 内容：{MEETING_DATE} 伯克希尔·哈撒韦年度股东大会上午场，CNBC Warren Buffett Archive 第 50 章「{CNBC_CHAPTER.split(" · ")[1]}」。提问者为来自密歇根州安阿伯的股东（逐字稿记作 Charles Pyle，并标注为音译），回答者沃伦·巴菲特，查理·芒格补充。',
     f'- CNBC 档案页：{CNBC_URL}',
     '- 逐字稿：CNBC 档案逐字稿（经 GitHub 镜像 `pzponge/Yestoday` 获取，文件 `Warren_Buffett/Berkshire_Hathaway_Annual_Meeting/1994_Annual_Meeting.md` 第 50 节）。',
     f'- 录像来源：archive.org 条目 `{ARCHIVE_ITEM}`（{ARCHIVE_URL}），为 YouTube 频道 Legendary Investor 上传的 1994 年全场录像；本题在录像 1:53:48 起。只按区间读取需要的音频与画面，不下载整片。',
     '- 档案录像在芒格作答后的笑声中有一处硬切（数字静音），本片在硬切前收住。',
     '- 字幕时间：faster-whisper（medium.en）逐词时间戳与逐字稿做序列匹配，754 个单词中 739 个直接对上（98.0%），其余插值；识别结果只用于定时，字幕文字以逐字稿为准。',
     '- 使用性质：评论、教育与研究目的的引用；保留问答主线，不改变原意。', '',
     '## 画面素材', '',
     '- 原声段画面为同一题的 1994 年上午场原始录像（巴菲特与芒格同框），不是静帧、不是 AI 生成。',
     '- 裁切时避开了第三方频道水印与其烧录字幕。',
     '- 节点、点云、星图与文字动画均为本片根据下列公开资料制作的示意画面，不冒充历史影像。', '',
     '## 事实核查', '', '| 片中位置 | 事实 | 出处 |', '|---|---|---|']
for k, f, s in FACTS:
    L.append(f'| {k} | {f} | {s} |')
L += ['', '致股东信原文：https://www.berkshirehathaway.com/letters/1985.html 、 https://www.berkshirehathaway.com/letters/1993.html 、 '
      'https://www.berkshirehathaway.com/letters/2007ltr.pdf 、 https://www.berkshirehathaway.com/letters/2014ltr.pdf', '',
      '## 音乐（CC BY 4.0）', '',
      '- "Hiding Your Reality" Kevin MacLeod (incompetech.com) — Licensed under Creative Commons: By Attribution 4.0 License — http://creativecommons.org/licenses/by/4.0/',
      '- "Nerves" Kevin MacLeod (incompetech.com) — Licensed under Creative Commons: By Attribution 4.0 License — http://creativecommons.org/licenses/by/4.0/',
      '- 选曲：从 incompetech 曲库按 Dark / Epic / Intense / Driving 筛出 16 首，逐首做 librosa 能量曲线、低频占比、频谱与起音分析；'
      '“Nerves”有完整的渐进结构（安静开头 → 28.5s 大段落进入 → 46.3s 回落 → 62.3s 激增 → 99.6s 留白 → 108.3s 高潮），与本集论证节奏一一对应。',
      '- 发布时请在简介中保留以上署名。', '',
      '## 配音', '', f'- Google Gemini TTS `{GEMINI_MODEL}`，声音 `{GEMINI_VOICE}`；字幕时间由 faster-whisper 对合成结果强制对齐得到。',
      '- 含金额的句子另用 faster-whisper medium 逐句复核“美元”是否读出（Gemini 曾在长句里把“亿美元”读成“亿元”，已重新合成并复核）。', '',
      '## 字体（SIL Open Font License）', '', '- 思源宋体 / 思源黑体（Noto Serif SC、Noto Sans SC）、Cormorant Garamond、EB Garamond、Inter，均来自 Google Fonts。', '',
      '## 品牌', '', '- 右上角角标：仓库 `brand/brand.py` 的 `Hud`（逐帧合成，含光晕与流光）。',
      '- 片尾 logo：`brand/logo_baman.png`（经 `brand.load_logo` 预乘 alpha 缩放）；片尾文字取自 `brand/hud_lockup@4x.png` 的官方预渲染文字区。']
open(os.path.join(out, '素材来源与事实核查.md'), 'w').write('\n'.join(L) + '\n')
print('docs written to', out)
