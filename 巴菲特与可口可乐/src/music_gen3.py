"""v6 配乐：同一调性、同一速度、同一主题动机的三大段连续原创配乐（Lyria lyria-3-pro-preview）。
v5 的问题是 8 段素材风格/速度/调性各异、章节处“收气”切换，听感突兀不连贯；
v6 用一套统一的音乐语言贯穿全片，只在少数关键节点由配乐自身的高潮点燃。

python3 src/music_gen3.py WORK [part ...] [--n 2]      # 输出 work/music3/P1_0.mp3 ...
"""
import sys, os, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from music_gen import gen as _gen, PROMPTS

PALETTE = ("Instrumental cinematic documentary score, one continuous piece, no vocals except soft wordless choir where stated. "
           "Tempo exactly 84 BPM in 4/4 throughout, never changes. Key D minor, moving to D major only at the very end. "
           "One recurring main theme: a noble, warm 4-note rising horn motif (D–A–F–E) that returns throughout in different orchestrations. "
           "Orchestra: warm grand piano, celli and basses, violins and violas, French horns, low brass, soft timpani and taiko. "
           "Smooth, flowing, coherent; transitions between sections are gradual crescendos and diminuendos, never abrupt stops or sudden cuts. "
           "Strictly NO white-noise risers, NO whooshes, NO cymbal crashes or swells, NO hi-hats, NO reverse effects, NO synths, NO electronic beats.")

PARTS = {
    'P1': """Structure (total 1:20):
0:00-0:24 dark, suspenseful: low string ostinato and a soft heartbeat-like timpani pulse, the main motif hinted by low piano, slowly growing.
0:24 a powerful statement of the main theme by horns and full low strings with taiko (the title), 0:24-0:32 broad and noble.
0:32-1:20 warm and nostalgic: the main theme on solo piano with cello, intimate; strings gently join around 0:55 and the music swells softly to a warm, hopeful peak at about 1:05, then settles.""",
    'P2': """Structure (total 2:05):
0:00-0:37 intelligent and curious: light string ostinato in eighth notes, piano, gradually adding layers (celli, horns, soft drums), the main motif in fragments.
0:37 a majestic full statement of the main theme (horns, strings, timpani), 0:37-0:55 broad and confident.
0:55-1:13 steady, driving momentum, slightly calmer.
1:13-1:37 a relentless, rising build like compound interest: each bar adds intensity.
1:37 the biggest triumphant statement of the main theme: full orchestra, taiko, soft wordless choir, 1:37-1:52 glorious.
1:52-2:05 gently subsiding to a calm, thoughtful pad.""",
    'P3': """Structure (total 1:45):
0:00-0:30 dark and heavy: low strings, sparse piano, a slow uneasy pulse, sorrowful, the main motif in a minor, broken form.
0:30 the theme returns with resolve: firm horns and steady timpani, 0:30-0:48 determined and strong.
0:48-1:13 reflective and warm: piano and cello play the main theme intimately, strings slowly building.
1:13 an emotional, uplifting climax: full orchestra and soft wordless choir, the main theme in its fullest form, 1:13-1:26.
1:26-1:34 suspended, quiet and expectant: soft sustained strings.
1:34 one final majestic chord (full orchestra, timpani) resolving to D major, ringing and slowly fading out until 1:45.""",
}


def gen(part, out):
    PROMPTS['_p3_' + part] = PALETTE + '\n' + PARTS[part]
    return _gen('_p3_' + part, out)


if __name__ == '__main__':
    work = sys.argv[1]; args = sys.argv[2:]
    n = 2
    if '--n' in args: i = args.index('--n'); n = int(args[i + 1]); args = args[:i] + args[i + 2:]
    parts = args or list(PARTS)
    d = os.path.join(work, 'music3'); os.makedirs(d, exist_ok=True)
    jobs = [(p, os.path.join(d, f'{p}_{k}.mp3')) for p in parts for k in range(n)]
    jobs = [j for j in jobs if not os.path.exists(j[1])]
    with cf.ThreadPoolExecutor(3) as ex:
        for o in ex.map(lambda j: gen(*j), jobs): print('done', o, flush=True)
