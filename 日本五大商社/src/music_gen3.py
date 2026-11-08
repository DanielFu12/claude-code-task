"""第三期配乐：同一调性、同一速度、同一主题动机的三大段连续原创配乐（Lyria lyria-3-pro-preview）。
与第一期同一方法（统一音乐语言贯穿全片），气质更现代、清澈：钢琴 + 弦乐 + 柔和电子脉冲铺底。
v5 的问题是 8 段素材风格/速度/调性各异、章节处“收气”切换，听感突兀不连贯；
v6 用一套统一的音乐语言贯穿全片，只在少数关键节点由配乐自身的高潮点燃。

python3 src/music_gen3.py WORK [part ...] [--n 2]      # 输出 work/music3/P1_0.mp3 ...
"""
import sys, os, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from music_gen import gen as _gen, PROMPTS

PALETTE = ("Instrumental cinematic documentary score for a premium finance documentary about Warren Buffett investing in Japan, one continuous musical language, no vocals except soft wordless choir where stated. "
           "Tempo exactly 84 BPM in 4/4 throughout, never changes. Key D minor, moving to D major only where stated. "
           "One recurring main theme: a clear, elegant 4-note piano motif (D–A–F–E) that returns throughout in different orchestrations. "
           "Instruments: crisp grand piano, string orchestra (celli, basses, violins, violas), French horns, soft timpani, a very soft warm low pulse for a modern feel, "
           "and occasionally a delicate koto pluck doubling the piano motif as a subtle Japanese color (tasteful, never a pentatonic cliche). "
           "Smooth and coherent; transitions are gradual crescendos and diminuendos, never abrupt stops. "
           "Strictly NO white-noise risers, NO whooshes, NO cymbal crashes or swells, NO hi-hats, NO reverse effects, NO bright lead synths, NO electronic drum beats.")

PARTS = {
    'P1': """Structure (total 2:08):
0:00-0:55 suspenseful and intriguing, like a riddle about money: a low string ostinato, a soft heartbeat-like timpani pulse, the main motif hinted by low piano and a single koto pluck, slowly and steadily growing in intensity.
0:55 a powerful statement of the main theme by horns and full low strings with taiko (the title), 0:55-1:00 broad and noble.
1:00-1:28 melancholic and nostalgic, like looking back at a lost decade: solo piano and cello, slow descending lines.
1:28-2:08 curious and warm forward motion: light pizzicato strings and piano, the motif in a gentle major-leaning color, ending on a calm sustained chord.""",
    'S2': """Structure (total 1:30):
0:00-0:30 intelligent and curious: light pizzicato and piano, like discovering something surprising in the numbers.
0:30 a bright, confident accent of the main theme (strings and horn), 0:30-0:36.
0:36-1:02 patient and stealthy: a quiet, steady string ostinato in eighth notes, soft low pulse, like buying patiently in silence, slowly accumulating.
1:02 a warm, triumphant full statement of the main theme (horns, strings, timpani), 1:02-1:12.
1:12-1:30 an uneasy turn: low strings, the motif in minor, a question left hanging, ending suspended.""",
    'S3': """Structure (total 1:30):
0:00-0:24 uneasy and tense: low strings, sparse piano, a slow pulse.
0:24-1:02 clever and light, an elegant solution: piano arpeggios, pizzicato, the motif passed between piano, koto and cello, steadily building with growing confidence.
1:02 a bright, joyful full statement of the main theme (full strings, horns, soft timpani), 1:02-1:14.
1:14-1:30 a thoughtful, questioning close: solo piano over a soft string pad.""",
    'S4': """Structure (total 2:30):
0:00-0:44 serious and analytical: measured string ostinato and piano chords, the motif in minor, like weighing a business carefully.
0:44-0:58 darker and heavy: low strings and timpani, a short sorrowful passage.
0:58-1:38 constructive and building: four rising steps, each adding a layer (horns, celli, pulse), steadily gaining strength.
1:38 a firm, confident arrival of the main theme (horns and strings), 1:38-1:48.
1:48-2:20 reflective and wise: piano and cello, calm and thoughtful.
2:20-2:30 suspended and expectant: soft sustained strings, unresolved.""",
    'S5': """Structure (total 1:10):
0:00-0:40 warm and respectful, a journey to Tokyo: piano and koto play the main motif gently over soft strings, dignified and human.
0:40-0:48 a gentle swell.
0:48 a noble, uplifting statement of the main theme (strings and horns), 0:48-0:58.
0:58-1:10 settling to a calm, warm sustained chord.""",
    'P6': """Structure (total 2:08):
0:00-0:30 steady, confident build like adding up a ledger: string ostinato, piano, gradually adding horns and timpani.
0:30 the biggest majestic statement of the main theme (full orchestra, taiko, soft wordless choir), 0:30-0:42, glorious and certain.
0:42-1:00 confident and broad, slowly calming.
1:00-1:22 reflective and wise: solo piano and cello, quiet.
1:22-1:47 gentle, steadily rising warmth: strings join one by one, the motif moves to D major.
1:47 an emotional, uplifting climax: full orchestra and soft wordless choir, the main theme in its fullest form in D major, 1:47-1:59.
1:59-2:00 a brief breath.
2:00 one final majestic D major chord (full orchestra, timpani), ringing and slowly fading out until 2:08.""",
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
