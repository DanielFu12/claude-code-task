"""由 timeline.json 生成文字交付物：口播脚本、原始问答清单、分镜与精确到秒的剪辑时间线、素材来源与事实核查。

用法：python3 src/docs.py WORK OUT_DIR
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import (ARCHIVE_ITEM, ARCHIVE_URL, CLIP_IN, CNBC_CHAPTER, CNBC_URL, FACTS, VOICE, RATE, PITCH, BROLL, STILL_T, PIC_BOX,
                    GEMINI_MODEL, GEMINI_VOICE, GEMINI_STYLE)

work, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
tl = json.load(open(os.path.join(work, 'timeline.json')))
AFTERNOON_START = 2 * 3600 + 31 * 60 + 47       # archive.org 全场录像中下午场的起点（录像简介标注 02:31:47）


def tc(t):
    t = max(t, 0)
    return f'{int(t // 60):d}:{t % 60:05.2f}'


def hms(t):
    return f'{int(t // 3600)}:{int(t // 60 % 60):02d}:{t % 60:05.2f}'


# ------------------------------------------------------------------ 口播脚本
ENGINE = next(iter(json.load(open(os.path.join(work, 'vo_index.json'))).values())).get('engine', 'edge')
if ENGINE == 'gemini':
    VOICE_NOTE = (f'配音：Google Gemini TTS（`{GEMINI_MODEL}`，声音 `{GEMINI_VOICE}`），风格指令原样放在 speech_metadata.style：'
                  f'“{GEMINI_STYLE}”。按段落成组合成，段内句间停顿保留模型自己的节奏，段落之间按语义设置停顿。')
else:
    VOICE_NOTE = f'配音：微软 Edge 神经网络语音 `{VOICE}`（男声），语速 {RATE}、音高 {PITCH}；逐句合成，句间停顿按语义设置。'
L = ['# 口播脚本 · 第一集《内在价值》', '',
     VOICE_NOTE, '',
     '> 标注说明：**【旁白】** 为本片撰写的解说；**【原声】** 为 1994 年股东大会原始录音。画面上同样区分：原声段标注“声音：下午场原始录音”，解读段标注“本片解读”。', '']
L += ['## 一、冷开场【原声】', '']
for s in tl['cold_subs']:
    L.append(f"- `{tc(s['t0'])}–{tc(s['t1'])}` {s['en']}  \n  {s['zh']}")
L += ['', '## 二、系列片头【旁白】', '']
for v in tl['intro']['vo']:
    L.append(f"- `{tc(v['t0'])}–{tc(v['t1'])}` {v['text']}")
L += ['', '## 三、原始问答【原声】', '',
      f"来源：{CNBC_CHAPTER}（1994 年伯克希尔股东大会下午场）。英文逐字取自 CNBC 逐字稿，只省略口头重起的半句；中文为本片翻译。", '',
      '本片为节选：' + '；'.join(tl['qa']['omitted']) + '。以下为保留部分。', '',
      '| 片内时间 | archive.org 录像时间 | 下午场时间（约） | 英文原话 | 中文字幕 |', '|---|---|---|---|---|']
for s in tl['qa']['subs']:
    src = s['t0'] - tl['qa']['t0'] + tl['qa']['src_in'] + CLIP_IN
    L.append(f"| {tc(s['t0'])} | {hms(src)} | {hms(src - AFTERNOON_START)} | {s['en']} | {s['zh']} |")
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
shots = [
    (0, tl['t_title'], '冷开场', '黑场中浮现 1994 年股东大会同日静帧（巴菲特托腮倾听，宽银幕窗口，模糊背景扩展）；原声波形；中英字幕', '巴菲特原声 A7–A8：“如果完全不知道未来现金流……就完全不知道它值多少”', '无音乐；结尾低频膨胀'),
    (tl['t_title'], V['S1']['t1'] + 0.3, '片名', '大鼓重拍上金色宋体片名“伯克希尔股东大会 / 投资智慧录”砸入 + 流光', 'S1', 'Undaunted 大鼓进入 + 低沉冲击'),
    (V['S2']['t0'], V['S2']['t1'], '1994 → 至今', '1994 年上午场真实影像；“1994—至今”与“估值 / 护城河 / 风险 / 人生智慧”逐词砸入、粒子爆开', 'S2', 'Undaunted（压低），段落开口踩拍'),
    (V['S3']['t0'], V['S3']['t1'], '每期结构', '巴菲特讲话影像；“01 原声 → 02 案例”卡片砸入；“说了什么”被划去，“为什么这样想”砸入', 'S3', '同上'),
    (V['S4']['t0'], V['S5']['t1'], '回到 1994', '年份从 2026 倒带到 1994（残影 + 粒子）；巴菲特与芒格同框影像；金色问题逐句砸入', 'S4–S5', '同上'),
    (tl['ctx']['t0'], tl['qa']['t0'] + 1.5, '背景卡', '1994 年 4 月 · 奥马哈 · 下午场；CNBC 第 22 章；说明“此段仅存原始录音、画面为同日上午场静帧”', '—', '低频下潜；音乐停止'),
]
for sc, desc in [('ask', '股东提问：画面为倾听静帧；面板写出问题要点'), ('open', '“1992 ANNUAL REPORT”卡片'),
                 ('dcf', '十年现金流柱逐年折现、汇入“现值”'), ('fog', '现金流柱抖动、出现问号，现值变成“？”'),
                 ('dissonance', '“今天的股价：自以为知道” vs “未来 20 年现金流：毫无概念” → 认知失调'),
                 ('range', '宽锥（看不清，放进太难）与窄带（高概率区间），再折现回今天'),
                 ('cert', '天平：确定性 ＞ 看起来便宜'), ('report', '财务报表 → 没有答案 / 只有指引 → 懂生意 ＞ 懂数学'),
                 ('check', '公寓楼 · 农场 · 小生意 → 四问清单')]:
    s = Q[sc]
    shots.append((s['t0'], s['t1'], f'原声·{sc}', desc + '；上方为同日静帧（回答段换成巴菲特讲话时的静帧），下方中英字幕', '原始录音（不剪）', '无音乐'))
shots += [
    (tl['insight']['t_card'], V['I1']['t0'], '投资启示标题卡', 'HUD 圆环展开 + 粒子爆开，“投资启示”砸入；注明“以下为本片解读，非巴菲特或芒格原话”', '—', 'The Escalation 渐强段进入 + 低沉冲击'),
    (V['I1']['t0'], V['I3']['t1'], '价值公式', '透视网格 + 3D 粒子场背景；V = Σ CFₜ/(1+r)ᵗ 各符号从景深飞入，HUD 圆环旋转；“分子”被瞄准框锁定并爆开；1938 书目打字机显现', 'I1–I3', 'The Escalation（压低）'),
    (V['I4']['t0'], V['I6']['t1'], '债券 vs 股票', '债券票息光柱整齐升起；股票“票息”问号柱抖动后故障化；1992 年信原文打字机显现', 'I4–I6', '同上'),
    (V['I7']['t0'], V['I9']['t1'], '看得清：喜诗糖果', '配乐大段落进入的重拍上推镜 + 闪光 + 粒子爆开；销量与利润滚动计数；13.5 亿光柱升起（竖向光束 + 火花），3200 万仅约 2.4%', 'I7–I9', '重拍对准“看得清” + 低沉冲击'),
    (V['I11']['t0'], V['I13']['t1'], '看不清：美国航空', '3.58 亿金柱；“1994.9 停付股息”红色警报闪烁 + 故障；减记时金柱碎裂下坠，只剩 25% 红柱；“$1 → 25¢”砸入；“a case of sloppy analysis”打字机', 'I11–I13', 'The Escalation 高段'),
    (V['I14']['t0'], V['I15']['t1'], '代价：错过', '2017 年芒格原话打字机显现；“错过＝少赚 / 看错＝永久亏损”两块卡片砸入，后者故障闪红', 'I14–I15', '配乐回落'),
    (V['I16']['t0'], V['I17']['t1'], '今天', '旋转的 3D 点阵球，只有 7 颗点亮并连线；“越来越少”砸入；“答案，在你对生意的理解里”', 'I16–I17', '配乐再起'),
    (tl['summary']['t0'], E['t_particles'], '一句话总结', '金色大字“先问看不看得清，再问便不便宜。”+ 流光', 'M', '低频下潜 + Impact Lento 段落重拍'),
    (E['t_particles'], E['t_logo'], '片尾·汇聚', '总结文字化为金色微粒，沿官方 logo 透明通道汇聚', '—', 'Impact Lento'),
    (E['t_logo'], E['t_brand'], '片尾·logo', '官方 logo_baman.png 清晰居中出现，背后淡蓝光晕', '—', '同上'),
    (E['t_brand'], E['t_fade0'], '片尾·品牌', '音乐重拍上浮现金色「巴芒价值」+「BUFFETT · MUNGER」（官方预渲染字样），随后流光扫过', '—', '低沉冲击（与重拍对齐）'),
    (E['t_fade0'], tl['dur'], '淡出', '整体（含右上角角标）缓慢淡出', '—', '音乐淡出'),
]
L = ['# 分镜与剪辑时间线 · 第一集《内在价值》', '',
     f"成片 1080×1920 · 30fps · 总长 {tl['dur']:.2f} 秒（{int(tl['dur'] // 60)}:{tl['dur'] % 60:05.2f}）。时间全部由 `src/timeline.py` 计算，与成片逐帧一致。", '',
     '## 段落', '', '| 起 | 止 | 段落 |', '|---|---|---|']
for s in tl['sections']:
    L.append(f"| {tc(s['t0'])} | {tc(s['t1'])} | {s['name']} |")
L += ['', '## 分镜（每个镜头的作用）', '', '| 起 | 止 | 镜头 | 画面 | 声音 | 音乐 / 音效 |', '|---|---|---|---|---|---|']
for a, b, n, d, v, m in shots:
    L.append(f'| {tc(a)} | {tc(b)} | {n} | {d} | {v} | {m} |')
L += ['', '## 原始素材剪辑点', '',
      f"- 冷开场原声：录像 {hms(CLIP_IN + tl['cold']['src_in'])}–{hms(CLIP_IN + tl['cold']['src_out'])} → 片内 {tc(tl['cold']['t0'])}–{tc(tl['cold']['t1'])}",
      f"- 问答原声（节选）：录像 {hms(CLIP_IN + tl['qa']['src_in'])}–{hms(CLIP_IN + tl['qa']['src_out'])}（下午场约 {hms(CLIP_IN + tl['qa']['src_in'] - AFTERNOON_START)}–{hms(CLIP_IN + tl['qa']['src_out'] - AFTERNOON_START)}）→ 片内 {tc(tl['qa']['t0'])}–{tc(tl['qa']['t1'])}，中间不剪。",
      '- 节选时省略：' + '；'.join(tl['qa']['omitted']) + '。核心问题与完整论证（从“经济价值就是未来现金流的现值”到“我们做的就是这些，只不过对象是大企业”）一字未剪。',
      f"- 历史影像（上午场，有画面）：录像 " + '、'.join(f'{hms(b)} 起 16 秒' for b in BROLL) + f"；静帧取自 {hms(STILL_T)} 与 {hms(6000)}。",
      f"- 画面只取源画面中 x {PIC_BOX[0]}–{PIC_BOX[2]}、y {PIC_BOX[1]}–{PIC_BOX[3]} 的干净区域（避开第三方水印和烧录字幕），等比缩放进 1080×438 宽银幕窗口，不拉伸；窗口外是同一画面的模糊放大背景。", '',
      '## 音乐', '', '| 片内起 | 片内止 | 曲目 | 曲内起点 | 用途 |', '|---|---|---|---|---|']
use = ['冷开场至系列介绍（大鼓进入对准片名；段落开口吸附到节拍）', '投资启示至片尾（大段落进入对准“看得清”，高潮重拍对准总结句，5 小节后的强拍对准「巴芒价值」）']
for m, u in zip(tl['music'], use):
    L.append(f"| {tc(m['t0'])} | {tc(m['t1'])} | Kevin MacLeod – {m['track']} | {m['src_in']:.2f}s | {u} |")
L += ['', '原始问答期间不放音乐。口播期间音乐按人声包络侧链压低 11dB（提前 0.15 秒，attack 80ms / release 650ms）。画面在强重拍上推镜 4%、闪光并做色散，在小节强拍上轻微脉动。', '',
      '## 转场音效（全部为正弦合成，4 阶 180Hz 低通，无噪声源）', '', '| 片内时间 | 类型 | 电平 |', '|---|---|---|']
names = {'swell': '低频膨胀（Bass Swell）', 'impact': '低沉冲击（Deep Impact）+ 低频空间混响', 'subdrop': '低频下潜（Sub Drop）+ 低频空间混响'}
for e in tl['sfx']:
    L.append(f"| {tc(e['t'])} | {names[e['kind']]} | {e['gain']} dBFS 峰值 |")
open(os.path.join(out, '分镜与剪辑时间线.md'), 'w').write('\n'.join(L) + '\n')

# ------------------------------------------------------------------ 素材来源与事实核查
L = ['# 素材来源、授权与事实核查', '', '## 原始问答', '',
     f'- 内容：1994 年伯克希尔·哈撒韦年度股东大会下午场，CNBC Warren Buffett Archive 第 22 章「{CNBC_CHAPTER.split(" · ")[1]}」。提问者 Sean Barry（加拿大里贾纳），回答者沃伦·巴菲特；芒格在场，本题未补充。',
     f'- CNBC 档案页：{CNBC_URL}（CNBC 档案中 1994 年下午场只有音频）',
     '- 逐字稿：CNBC 档案逐字稿（经 GitHub 镜像 `pzponge/Yestoday` 获取，文件 `Warren_Buffett/Berkshire_Hathaway_Annual_Meeting/1994_Annual_Meeting.md` 第 22 节）。',
     f'- 录音来源：archive.org 条目 `{ARCHIVE_ITEM}`（{ARCHIVE_URL}），为 YouTube 频道 Legendary Investor 上传的 1994 年全场录像（3:31:28），下午场在该录像中也是“Audio Only”卡片。只按区间读取需要的音频与画面，不下载整片。',
     '- 字幕时间：faster-whisper（medium.en）逐词时间戳与逐字稿做序列匹配，574 个单词中 563 个直接对上（98.1%），其余插值；识别结果只用于定时，字幕文字以逐字稿为准。',
     '- 使用性质：评论、教育与研究目的的引用；完整保留问答上下文，不改变原意。', '',
     '## 画面素材', '',
     '- 1994 年股东大会上午场真实影像（同一录像，有画面），用于片头与过场；原声段落用同日上午场的两张静帧作底图，画面上标明“画面：同日上午场静帧 ｜ 声音：下午场原始录音”。没有任何 AI 生成的“历史影像”。',
     '- 裁切时避开了第三方频道水印与其烧录字幕。',
     '- 图表、文字动画均为本片根据下列公开资料绘制。', '',
     '## 事实核查', '', '| 片中位置 | 事实 | 出处 |', '|---|---|---|']
for k, f, s in FACTS:
    L.append(f'| {k} | {f} | {s} |')
L += ['', '致股东信原文：https://www.berkshirehathaway.com/letters/1992.html 、 https://www.berkshirehathaway.com/letters/1994.html 、 https://www.berkshirehathaway.com/letters/2007ltr.pdf', '',
      '## 音乐（CC BY 4.0）', '',
      '- "Undaunted" Kevin MacLeod (incompetech.com) — Licensed under Creative Commons: By Attribution 4.0 License — http://creativecommons.org/licenses/by/4.0/',
      '- "The Escalation" Kevin MacLeod (incompetech.com) — Licensed under Creative Commons: By Attribution 4.0 License — http://creativecommons.org/licenses/by/4.0/',
      '- 发布时请在简介中保留以上署名。', '',
      '## 配音', '', (f'- Google Gemini TTS `{GEMINI_MODEL}`，声音 `{GEMINI_VOICE}`；字幕时间由 faster-whisper 对合成结果强制对齐得到。' if ENGINE == 'gemini' else f'- 微软 Edge 神经网络语音 `{VOICE}`，经 `edge-tts` 调用。'), '',
      '## 字体（SIL Open Font License）', '', '- 思源宋体 / 思源黑体（Noto Serif SC、Noto Sans SC）、Cormorant Garamond、EB Garamond、Inter，均来自 Google Fonts。', '',
      '## 品牌', '', '- 右上角角标：仓库 `brand/brand.py` 的 `Hud`（逐帧合成，含光晕与流光）。',
      '- 片尾 logo：`brand/logo_baman.png`（经 `brand.load_logo` 预乘 alpha 缩放）；片尾文字取自 `brand/hud_lockup@4x.png` 的官方预渲染文字区。']
open(os.path.join(out, '素材来源与事实核查.md'), 'w').write('\n'.join(L) + '\n')
print('docs written to', out)
