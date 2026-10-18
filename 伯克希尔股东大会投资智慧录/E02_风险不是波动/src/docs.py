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
    (0, tl['t_title'], '冷开场', '与第一集同款：1994 年大会原始录像（巴菲特与芒格同框）放在宽银幕窗口里，同画面模糊补满；瞄准框、扫描线；窗口四周一层随原声能量乱跳的 3D 冰青粒子（“风险的衡量乱了套”）；中英字幕',
     '巴菲特原声 A19：“金融界在风险的衡量上，已经乱了套”', 'Hiding Your Reality 暗色铺底淡入；片名前低频膨胀'),
    (tl['t_title'], V['S1']['t0'], '片名', '与第一集同款的系列片名：巴菲特与芒格 / 伯克希尔股东大会 / 投资智慧录（金色擦除显现 + 流光）+「第二集 · 风险不是波动」；重拍上粒子爆开、冲击波扩散，金色微粒从景深里飘过', '—', 'Hiding Your Reality 整体进入 + 低沉冲击'),
    (V['S1']['t0'], V['S2']['t0'], '一年跌掉 25%', '上方是 1994 年大会实况；下方图表面板里一条发光的价格线从买入价出发，下跌段变成琥珀色并洒落火花（示意），“−25%”砸入；“更危险？/ 更便宜？”两张卡片砸入',
     'S1', 'Hiding Your Reality（压低），段落开口踩拍'),
    (V['S2']['t0'], V['S3']['t0'], '教科书的答案', '上方大会实况；下方“教科书 · 贝塔理论”面板：β 公式，大盘与这只股票两条波动曲线对比；“β↑ ＝ 风险↑”砸入，“更危险”琥珀色砸入', 'S2', '同上'),
    (V['S3']['t0'], tl['ctx']['t0'], '1994 年的提问', '上方大会实况；年份从 2026 飞速倒带回 1994 并爆开；“你们说的风险，到底是什么？”逐句砸入，冲击波', 'S3', '同上'),
    (tl['ctx']['t0'], tl['qa']['t0'], '背景卡', '与第一集同款：淡金大字 1994、1994 年 4 月 25 日 · 美国奥马哈、伯克希尔·哈撒韦年度股东大会 · 上午场；CNBC 第 50 章', '—', '低频下潜；音乐停止'),
]
desc = {'ask': '“股东的问题”面板：金融世界里的风险，您怎么看？→“您的风险观 ≠ 传统的风险观”两张卡片 → β 公式，“是否自相矛盾？”',
        'define': '金色大字“受到伤害或损失的可能性”+ 英文原话；“与打算持有多久密不可分”',
        'horizon': '一天里的价格折线：11:30 买入 → 收盘前卖出；一半赚、一半亏的两根柱子（50% / 50%），“风险非常高”',
        'coke': '同一只可口可乐两张卡片：以当初的买入价长期持有，风险 ≈ 0；今天上午买、明天上午卖，风险很高',
        'beta': '“风险 ＝ 波动”被一道琥珀线划去 →“对我们来说，根本不是风险的衡量”',
        'absurd': '柱状对比：投资 A 每年 +20%～+80%（从不亏钱），投资 B 每年稳定 +5%；“A 的风险更高”？→ 乱了套 · HAYWIRE（故障效果）',
        'expect': '一组金 / 琥珀小圆点代表单笔交易的盈亏 →“期望值必须为正”砸入',
        'munger': '“费马 · 帕斯卡”砸入，“像从没听说过现代金融理论那样，用概率思考”；镜头缓缓推向芒格'}
for sc in ('ask', 'define', 'horizon', 'coke', 'beta', 'absurd', 'expect', 'munger'):
    s = Q[sc]
    shots.append((s['t0'], s['t1'], f'原声·{sc}', desc[sc] + '；上方是 1994 年原始录像，说话人与原声波形，下方中英字幕', '原始录像原声', '无音乐'))
shots += [
    (tl['insight']['t_card'], V['I1']['t0'], '投资启示', '与第一集完全一致的标题转场：“投资启示”在重拍上砸入并爆开、HUD 圆环、INSIGHT、“以下为本片解读，非巴菲特或芒格原话”；之后整段解读的背景是透视网格 + 3D 金色微粒 + 漏光', '—', 'Nerves 安静的开头 + 低沉冲击'),
    (V['I1']['t0'], V['I2']['t0'], '两种定义', '上：“教科书的风险”面板，价格曲线上下剧烈波动（σ, β）；下：“巴菲特的风险”面板，持有期结束时各种结果的分布，落在本金线左侧的那一截是琥珀色——损失的可能性（示意）', 'I1', 'Nerves（压低）'),
    (V['I2']['t0'], V['I3']['t0'], '持有期', '“持有期”图表：价格从“买入”一路起伏，终点落在“当初的购买力”虚线之上，打勾、爆开；“拿回的钱 ≥ 当初的购买力”砸入，1993 年信原文打字机显现', 'I2', '同上'),
    (V['I3']['t0'], V['I4']['t0'], '波动与风险', '上：波动面板，正弦曲线 + 幅度标尺（价格摆动的幅度）；下：风险面板，一根完整的金色“本金”柱，火花上升（钱还在不在）', 'I3', '同上'),
    (V['I4']['t0'], V['I7']['t0'], '华盛顿邮报', '配乐大段落进入的重拍上冲击波扩散；“伯克希尔的持股市值”柱状图：1973 年买入成本 1,060 万 → 1974 年底 800 万（−25%，故障效果）；按贝塔理论“更危险”；生意一直在增长——1993 年 4.40 亿的柱子拔地而起，纵轴重新缩放，前两根被压成细条，光柱与火花，“≈ 41 倍”砸入', 'I4–I6', 'Nerves 大段落进入（28.5s）对准 I4 开口 + 低沉冲击'),
    (V['I7']['t0'], V['I11']['t0'], '德克斯特鞋业', '“伯克希尔付出的代价”柱状图：4.33 亿美元（以伯克希尔股票支付）；旁边一条完全平直的线（股价波动 ＝ 0）；海外竞争时柱子发颤，“价值归零”时碎裂、碎屑飞散、冲击波，只剩一个空框；当初付出的股票 2014 年值 57 亿美元——琥珀色柱子拔地而起，“≈ 13 倍”；2007 年信原话', 'I7–I10', 'Nerves 回落段 → 激增（62.3s）+ 低频下潜'),
    (V['I11']['t0'], V['I12']['t0'], '杠杆', '“同一段下跌”图表（示意）：价格跌到谷底又涨了回去；借了钱的人在谷底被迫卖出（✕、冲击波、故障），之后账户停在谷底——琥珀色的“永久的损失”；“暂时的下跌 ↓ 被锁定成 永久的损失”', 'I11', 'Nerves 高段'),
    (V['I12']['t0'], V['I13']['t0'], '今天', '“账户回撤”图表（示意，−35%）；“先问两个问题”：01 这门生意还在吗？02 我会被迫卖出吗？两张金框卡片依次砸入；Drawdown ≠ Permanent loss', 'I12', '同上'),
    (V['I13']['t0'], tl['summary']['t0'], '收尾 + 蓄力', '镜头在全片节点组成的 3D 星图里向前飞行，整句逐句显现（后半句金色）；之后越飞越快，星点拉成曲速拖尾；高潮前 0.4 秒纯黑', 'I13', 'Nerves 留白段（99.6s 起，配乐提升 6dB）'),
    (tl['summary']['t0'], E['t_particles'], '一句话总结', '重拍上整片星图同时亮起、冲击波扩散，再缓缓暗下；与第一集同款的总结版式：金色大字“波动不是风险，永久损失才是。”+ 流光', 'M', 'Nerves 高潮（108.3s）+ 低频下潜'),
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
L += ['', '原始问答期间不放音乐。口播期间音乐按人声包络侧链压低 11dB（提前 0.15 秒）。与第一集一致的后期：泛光、横向光晕，强重拍上推镜 4%、闪光并做色散，小节强拍轻微脉动（原声问答段减弱）。解读段内换镜为 0.5 秒暗下 + 0.45 秒亮起，不硬切。', '',
      '## 转场音效（全部为正弦合成，4 阶 180Hz 低通，无噪声源）', '', '| 片内时间 | 类型 | 电平 |', '|---|---|---|']
names = {'swell': '低频膨胀（Bass Swell）', 'impact': '低沉冲击（Deep Impact）+ 低频空间混响', 'subdrop': '低频下潜（Sub Drop）+ 低频空间混响'}
for e in tl['sfx']:
    L.append(f"| {tc(e['t'])} | {names[e['kind']]} | {e['gain']} dBFS 峰值 |")
L += ['', '## 画面风格（本集）', '',
      '- 系列一致：片头与第一集同款（1994 年大会原始录像 + 金色系列片名 + 背景卡），左上章节标签、字幕版式、“投资启示”标题转场、总结与品牌片尾都与第一集一致；后期同为泛光、横向光晕、重拍推镜 + 闪光 + 色散。',
      '- 直观的图表面板（不用玻璃）：深色实底 + 细边 + 发光的角标折线；发光曲线与渐变填充、上亮下暗的柱子、会重新缩放的纵轴、金色大数字与砸入的结论。示意性的图表都标注“示意”，真实数据只用致股东信里的数字。',
      '- 特效：冲击波、粒子爆开、碎裂与碎屑、光柱与上升火花、故障效果；收尾在 3D 星图里越飞越快，高潮时整片星图同时亮起。',
      '- 光色：金色 = 生意与本金（真正的风险看它在不在）；冰青 = 价格与波动；琥珀 = 亏损与付出去的。']
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
