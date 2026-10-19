"""整段生成旁白：同一段落的多句话放在一次 Gemini TTS 调用里连续朗读（gemini-3.8-flash-tts，音色 Charon），
句与句之间的语气、换气、停顿由模型自然衔接；再按停顿 + 转写把整段切回逐句，供字幕与画面对位。

python3 src/tts_passage.py WORK gen [pid ...] [--takes N]   # 生成（每段 N 个候选：work/tts_p/<pid>_<k>.wav）
"""
import sys, os, json, base64, time, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, TEASE, DROPPED
from tts_gen import post, MODEL, VOICE

# 段落：一次 TTS 调用读完的若干句（按叙事段落划分，段落之间才是“换场”）
PASSAGES = [
    ('hook', ['s01', 's03', 's04', 's05'],
     '开场悬念。第一句像一条刚刚发生的新闻，干脆有力；接着压低声音讲那位股东，数字有分量；最后“为什么？”放慢、留住悬念'),
    ('ch1', ['s07', 's08', 's09', 's10', 's11', 's12'],
     '回到过去讲一个真实的故事，温暖、怀旧、娓娓道来；讲到 1988 年的数字时转为笃定'),
    ('ch2a', ['s14', 's15', 's16', 's17a', 's17b', 's17c', 's17d'],
     '带着好奇抛出问题，然后像在拆解一道谜题，一步一步讲清芒格的思想实验；三种心理力量逐条递进，最后一句豁然开朗'),
    ('ch2b', ['s18', 's19', 's20', 's21', 's22', 's23'],
     '冷静、有洞察的商业分析，节奏紧凑；“真正的钱，在糖浆里”略带会心；最后一句“护城河”沉稳收束'),
    ('ch3', ['s25', 's26', 's27', 's28', 's29', 's30', 's30b', 's31'],
     '翻开账本，从平静逐渐推向震撼：数字一个比一个大，语气层层上扬；讲到“就是复利”时放慢、意味深长；最后一句冷静地拆解'),
    ('ch4a', ['s34', 's35', 's37', 's38'],
     '语气沉下来，讲一段不平坦的往事；泡沫与回本带着凝重，巴菲特的自省坦诚，机会成本冷静客观'),
    ('ch4b', ['s39', 's40', 's41', 's42'],
     '先抛出问题，再给出坚定的理由；最后一句提醒持有并非无条件，郑重'),
    ('ch5', ['s43', 's44', 's45', 's46', 's47', 's48'],
     '反思与升华：先冷静地列出风险，再缓缓说出核心道理；倒数第二句是全片主题，饱满、有力量；最后一句温暖、余韵悠长'),
]
TEASE_P = ('tease', ['tease'], '片尾预告，温和而有悬念，像在讲下一个故事的开头')

PROFILE = """# AUDIO PROFILE: 资深中文纪录片旁白（男声，标准普通话）
## THE SCENE: 一部关于巴菲特与可口可乐 38 年投资的高端金融纪录片，这是其中一个完整段落，一口气讲下来。
### DIRECTOR'S NOTES
Style: 低沉、温暖、有颗粒感的真人讲述，像一位资深纪录片讲述者在给观众讲一个真实的故事，不是播音腔、不是广告口播、不是逐句朗读。
本段情绪：{mood}。
Flow: 句与句之间要连贯，前一句的语气自然引出后一句；不要每一句都重新起调，也不要每一句末尾都用同样的下沉收尾。
句号处自然换气、稍作停顿（约半秒）；段落转折处停得更久一些；逗号、破折号处轻轻带过。
Pace: 纪录片讲述的语速，紧凑而从容，略快于播音（约每秒五个字），重要的数字和关键词放慢、加重。
#### TRANSCRIPT
{text}"""


# 提示词变体（盲听比较后选定）
PROFILES = {
    'zh': PROFILE,
    'en': """# AUDIO PROFILE: Seasoned Mandarin documentary narrator (male, standard Putonghua)
## THE SCENE: A late-night recording booth. He is telling a true story about Warren Buffett and Coca-Cola to one listener sitting across from him — a premium finance documentary, not an advertisement.
### DIRECTOR'S NOTES
Style: Warm, low, intimate, slightly gravelly; a real human storyteller, never a newsreader. He thinks while he talks: some phrases lean forward, some settle back; pitch moves naturally with meaning instead of repeating one contour per sentence.
Mood of this passage: {mood}
Flow: Read it as one continuous passage. Each sentence grows out of the previous one; do not reset the intonation at every full stop and do not drop every sentence ending the same way. Natural breaths between sentences, a slightly longer pause only where the thought turns.
Pace: Natural, unhurried conversational pace; linger a little on key numbers and key words.
#### TRANSCRIPT
{text}""",
    'zh2': """# AUDIO PROFILE: 资深中文纪录片讲述者（男声，标准普通话）
## THE SCENE: 高端金融纪录片《巴菲特与可口可乐》。录音棚里，他面对一位听众，把一段真实的故事一口气讲下来。
### DIRECTOR'S NOTES
Style: 低沉、温暖、略带颗粒感的真人讲述；像在讲故事，不像在念稿；不是播音腔，也不是广告口播。
本段整体：{mood}。
逐句表演提示（只是提示，不要读出来）：
{cues}
Flow: 整段连贯——前一句的情绪自然带出下一句，不要每句都重新起调，句尾不要千篇一律地下沉；句号处像真人一样换气，思路转折处多停半拍。
Pace: 自然的讲述语速，有快有慢：铺垫处轻快，关键数字和关键词放慢、加重。
#### TRANSCRIPT
{text}""",
    'min': """用真人纪录片讲述者的语气，自然、连贯地讲出下面这段话（{mood}）：
{text}""",
}


def spoken(lid):
    if lid == 'tease': return TEASE[1]
    if lid in DROPPED: return DROPPED[lid]
    l = next(l for l in LINES if l[0] == lid)
    return l[3] or l[2]


def cue(lid):
    if lid == 'tease': return '温和而有悬念'
    if lid in DROPPED: return '叙述'
    return next(l for l in LINES if l[0] == lid)[4]


def gen(p, out, variant='zh', temp=None):
    pid, ids, mood = p
    text = '\n'.join(spoken(i) for i in ids)
    cues = '\n'.join(f'{k + 1}.「{spoken(i)[:8]}……」{cue(i)}' for k, i in enumerate(ids))
    body = {"contents": [{"parts": [{"text": PROFILES[variant].format(mood=mood, text=text, cues=cues)}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}}}}
    if temp is not None: body['generationConfig']['temperature'] = temp
    d = post(MODEL, body, timeout=600)
    raw = base64.b64decode(d['candidates'][0]['content']['parts'][0]['inlineData']['data'])
    if raw[:4] == b'RIFF':
        open(out, 'wb').write(raw)
    else:                                                    # 裸 PCM（24kHz s16le）
        import numpy as np, soundfile as sf
        sf.write(out, np.frombuffer(raw, np.int16).astype(np.float32) / 32768, 24000)
    return out


if __name__ == '__main__':
    work = sys.argv[1]; d = os.path.join(work, 'tts_p'); os.makedirs(d, exist_ok=True)
    args = sys.argv[2:]
    takes = 1; variant = 'zh'
    if '--takes' in args: i = args.index('--takes'); takes = int(args[i + 1]); args = args[:i] + args[i + 2:]
    if '--variant' in args: i = args.index('--variant'); variant = args[i + 1]; args = args[:i] + args[i + 2:]
    if args and args[0] == 'gen':
        want = args[1:]
        selp = os.path.join(d, 'select.json')
        done = json.load(open(selp)) if os.path.exists(selp) and not want else {}   # 已选定录音的段落不再生成
        ps = [p for p in PASSAGES + [TEASE_P] if (not want or p[0] in want) and p[0] not in done]
        tag = '' if variant == 'zh' else variant + '-'
        jobs = [(p, os.path.join(d, f'{p[0]}_{tag}{k}.wav')) for p in ps for k in range(takes)]
        jobs = [j for j in jobs if not os.path.exists(j[1])]
        with cf.ThreadPoolExecutor(2) as ex:
            for out in ex.map(lambda j: gen(*j, variant), jobs): print('done', out, flush=True)
