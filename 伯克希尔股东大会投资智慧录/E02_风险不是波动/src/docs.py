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
      '本片为节选，省略了：' + '；'.join(tl['qa']['omitted']) + '。省略处在画面上用一道“玻璃快门”和“· 节选 ·”标出。以下为保留部分。', '',
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
    (0, tl['t_title'], '冷开场', '三维玻璃世界：1994 年原始录像作为一块发光的影像平面悬在暗处，一根三棱玻璃柱与一根细玻璃棒缓缓从画面前滑过，影像在玻璃里折射、色散；条形灯扫过；原声波形与中英字幕',
     '巴菲特原声 A19：“金融界在风险的衡量上，已经乱了套”', 'Hiding Your Reality 暗色铺底淡入；片名前低频膨胀'),
    (tl['t_title'], V['S1']['t0'], '片名', '七块玻璃从空中飞来，在重拍上精确合拢成一块厚玻璃铭牌，金色“风险不是波动”嵌在玻璃里；合拢瞬间条形灯扫过、地面焦散光环扩散', '—', 'Hiding Your Reality 整体进入 + 低沉冲击'),
    (V['S1']['t0'], V['S2']['t1'], '一年跌掉 25%', '一根玻璃价格管从左向右生长，光脉冲沿管内流动；下跌段染成暖红，“−25%”砸入；“更危险？/更便宜？”两块玻璃卡片；S2 镜头拉远，“β ↑ ＝ 风险 ↑ → 更危险”',
     'S1–S2', 'Hiding Your Reality（压低），段落开口踩拍'),
    (V['S3']['t0'], tl['ctx']['t0'], '1994 年的提问', '1994 年大会原始录像透过滑过的玻璃棱柱；问题“你们说的风险，到底是什么？”逐句砸入', 'S3', '同上'),
    (tl['ctx']['t0'], tl['qa']['t0'] + 1.2, '背景卡', '玻璃卡片：1994 年 4 月 25 日 · 奥马哈 · 上午场；CNBC 第 50 章；说明“原始录像节选，省略处以玻璃快门标出”', '—', '低频下潜；音乐停止'),
]
desc = {'ask': '股东提问：问题要点卡片（您的风险观 ≠ 传统风险观；β 是否自相矛盾）',
        'define': '“受到伤害或损失的可能性”金色大字 + 英文原话；“与持有期限密不可分”',
        'horizon': '一天的价格折线：11:30 买入 → 收盘前卖出，“50% 的概率受损”',
        'coke': '同一只可口可乐：长期持有“风险≈0” vs 今早买明早卖“高风险”两张玻璃卡',
        'beta': '“风险 ＝ 波动”被红线划去 →“对我们来说，不是风险的衡量”',
        'absurd': '柱状对比：投资 A 每年 +20%～+80%（从不亏钱），投资 B 每年稳定 +5%；“A 的风险更高？”；haywire / 乱了套',
        'expect': '单笔交易可以亏（金/红小圆点）→ 一组同类独立交易的期望值必须为正',
        'munger': '费马 · 帕斯卡；镜头缓缓推向芒格'}
for sc in ('ask', 'define', 'horizon', 'coke', 'beta', 'absurd', 'expect', 'munger'):
    s = Q[sc]
    shots.append((s['t0'], s['t1'], f'原声·{sc}', desc[sc] + '；上方玻璃边框里是 1994 年原始录像，下方中英字幕', '原始录像原声', '无音乐'))
shots += [
    (tl['insight']['t_card'], V['I1']['t0'], '投资启示标题卡', '两块玻璃碑从地面升起；“投资启示 · 本片解读，非巴菲特或芒格原话”', '—', 'Nerves 安静的开头 + 低沉冲击'),
    (V['I1']['t0'], V['I2']['t0'], '两种定义', '左碑里是剧烈抖动的冷蓝价格波形（教科书：波动 β），右碑里是稳定的金色内核（巴菲特：损失的可能性）', 'I1', 'Nerves（压低）'),
    (V['I2']['t0'], V['I3']['t0'], '持有期', '横向玻璃时间管：光脉冲上下抖动着从“买入”走到“持有期结束”的玻璃环，环在“购买力”处点亮；1993 年信原文', 'I2', '同上'),
    (V['I3']['t0'], V['I4']['t0'], '玻璃海', '第一次出现玻璃海与悬浮玻璃球（金核 = 生意的内在价值）；“风险，是钱还在不在”时镜头推进到金核', 'I3', '同上'),
    (V['I4']['t0'], V['I7']['t0'], '华盛顿邮报：风暴', '配乐大段落进入的重拍上玻璃海掀起风暴，球被抛进浪谷（$1,060 万 → $800 万，−25%，β 理论“更危险”）；生意增长时金核变大变亮，球随巨浪升起：> $4 亿', 'I4–I6', 'Nerves 大段落进入（28.5s）对准 I4 开口 + 低沉冲击'),
    (V['I7']['t0'], V['I9']['t0'], '德克斯特：平静', '海面变成镜面，球一动不动；“全资收购 · 没有股价 · 波动 ＝ 0”', 'I7–I8', 'Nerves 回落段'),
    (V['I9']['t0'], V['I11']['t0'], '德克斯特：裂开', '球体内部从一点开始长出发光裂纹，金核变暗；“价值归零”时碎成 16 块玻璃并下沉；所付股票 2014 年值 $57 亿；2007 年信原话', 'I9–I10', 'Nerves 激增（62.3s）+ 低频下潜'),
    (V['I11']['t0'], V['I12']['t0'], '杠杆', '一条暗红发光的锁链把球拴向海底（借来的钱）；浪谷来临时被拉进海里、裂开：暂时的下跌 → 永久的损失', 'I11', 'Nerves 高段'),
    (V['I12']['t0'], V['I13']['t0'], '今天', '磨砂玻璃手机屏上的回撤曲线（示意），镜头穿过屏幕；“这门生意还在吗？/ 我会被迫卖出吗？”', 'I12', '同上'),
    (V['I13']['t0'], tl['summary']['t0'], '收尾', '俯瞰一片悬浮的玻璃球，暖金天光从地平线扫来；整句大字逐句显现', 'I13', 'Nerves 留白段（99.6s 起）'),
    (tl['summary']['t0'], E['t_particles'], '一句话总结', '三片玻璃透镜在高潮重拍上合拢，光束聚焦；金色大字“波动不是风险，永久损失才是。”+ 流光', 'M', 'Nerves 高潮（108.3s）+ 低频下潜'),
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
L += ['', '原始问答期间不放音乐。口播期间音乐按人声包络侧链压低 11dB（提前 0.15 秒）。画面在强重拍上推镜 4%、闪光并做色散，在小节强拍上轻微脉动。', '',
      '## 转场音效（全部为正弦合成，4 阶 180Hz 低通，无噪声源）', '', '| 片内时间 | 类型 | 电平 |', '|---|---|---|']
names = {'swell': '低频膨胀（Bass Swell）', 'impact': '低沉冲击（Deep Impact）+ 低频空间混响', 'subdrop': '低频下潜（Sub Drop）+ 低频空间混响'}
for e in tl['sfx']:
    L.append(f"| {tc(e['t'])} | {names[e['kind']]} | {e['gain']} dBFS 峰值 |")
L += ['', '## 三维玻璃场景（本集新增）', '',
      '- 渲染：`src/glass.py` 用 GLSL 光线步进（moderngl + Mesa llvmpipe，CPU 渲染），1.25 倍超采样后缩小。',
      '- 材质：菲涅尔反射；光线穿过玻璃真实厚度的折射（内部最多 3 次全反射）；RGB 三通道不同折射率的棱镜色散；按光程的冰蓝吸收；玻璃内部的金色内核 / 光脉冲为体积发光。',
      '- 环境：深色无限空间 + 缓慢扫过的竖直条形灯、侧面条灯、暖金轮廓灯与顶部柔光箱；深色微光泽地面带反射、接触阴影与扩散的焦散光环。',
      '- 后期（`src/post.py`）：按深度的景深、HDR 泛光与横向光晕、ACES 色调映射、冷色暗部、暗角与细颗粒。',
      '- 场景（`src/scenes_gl.py`）：玻璃海与悬浮玻璃球（风暴 / 镜面 / 裂纹 / 16 块碎裂 / 锁链 / 球阵）、价格玻璃管、七块拼合的玻璃铭牌、玻璃棱柱与影像平面、两块玻璃碑、持有期时间管、透镜组、磨砂玻璃屏。']
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
     '- 三维玻璃场景、图表与文字动画均为本片根据下列公开资料制作；“账户回撤”屏幕是示意图，不代表任何真实账户。', '',
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
