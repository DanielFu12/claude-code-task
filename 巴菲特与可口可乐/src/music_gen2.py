"""v5 配乐：按章节分别生成 6 段 Lyria 原创配乐（lyria-3-pro-preview，流式接口），统一 90 BPM、D 小调体系，
每段有明确的情绪弧线和高潮重拍；之后由 music_plan.py 按旁白关键节点逐帧对位（整小节剪辑 + 微小变速）。

python3 src/music_gen2.py WORK [cue ...] [--n 2]
"""
import sys, os, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from music_gen import gen as _gen, PROMPTS

PALETTE = ("Instrumental epic cinematic documentary score, no vocals except wordless choir where stated. "
           "Tempo exactly 90 BPM in 4/4 throughout (one bar = 2.667 s). Key D minor, resolving to D major at the end. "
           "Full hybrid orchestra: taiko ensemble and big orchestral drums, deep sub-bass, celli and basses, violins and violas, "
           "French horns and trombones, warm grand piano. Rich, warm and powerful, emotionally moving; big dynamic contrast between quiet and loud. "
           "Strictly NO white-noise risers, NO whooshes, NO cymbal crashes or swells, NO hi-hats, NO shakers, NO ticking, "
           "NO reverse swells, NO harsh or piercing high synths.")

CUES = {
    'H': """Structure (total 0:32):
0:00-0:22 dark suspense: low heartbeat-like taiko pulse on every beat, deep drones, a low piano motif; tension rises in waves, each wave stronger.
0:22-0:24 sudden near-silence (one held breath).
0:24 MASSIVE orchestral hit: taiko ensemble + full low brass chord + sub-bass boom, the main theme announced by horns, ringing out to 0:32.""",
    'C1': """Structure (total 0:50):
0:00-0:20 warm nostalgic Americana: solo grand piano melody with soft cello, gentle and intimate, like an old photograph.
0:20-0:36 the theme grows: strings join, a soft low pulse starts, hopeful.
0:36-0:46 resolute build: horns enter, the pulse becomes a confident march-like rhythm.
0:46-0:50 soft cadence and ring-out.""",
    'C2': """Structure (total 1:20):
0:00-0:10 curious and intelligent: pizzicato strings and a low piano ostinato in eighth notes, light and clever.
0:10-0:40 build layer by layer, one new layer every 2 bars (celli ostinato, low drums, horns, violins), growing excitement like a puzzle being solved.
0:40 BIG HIT: full orchestra + taiko, a triumphant statement of the main theme (the 'lollapalooza' moment), 0:40-0:55 powerful and wide.
0:55-1:14 confident propulsive drive: driving string ostinato and toms, majestic horns, a sense of an unstoppable global machine.
1:14 majestic final chord with taiko hit, ring-out to 1:20.""",
    'C3': """Structure (total 0:52):
0:00-0:08 quiet: a single low piano ostinato on eighth notes, counting, patient.
0:08-0:22 compounding build: every bar adds a layer (celli, basses, taiko pulse, horns, violins), relentless and rising.
0:22 HUGE TRIUMPHANT HIT: full orchestra + taiko + wordless choir, the main theme at full power, 0:22-0:36 soaring and glorious.
0:36-0:52 the energy pulls back to a sober, thoughtful low string pad with a soft piano line.""",
    'C4': """Structure (total 0:56):
0:00-0:06 dark, heavy tension: low drones and an uneasy pulse.
0:06 a deep low impact (a bubble bursting), then 0:06-0:24 sorrowful low strings and sparse piano, heavy and regretful.
0:24-0:30 a quiet questioning pause, very sparse.
0:30-0:56 resolute and firm: a steady determined low pulse with horns, growing strength and conviction.""",
    'C5': """Structure (total 1:00):
0:00-0:16 reflective: solo grand piano and cello, intimate, thoughtful.
0:16-0:28 emotional build: strings swell, taiko pulse enters, horns rise, wordless choir joins softly.
0:28 EPIC CLIMAX HIT: full orchestra + taiko + choir, the main theme in D major, deeply moving and triumphant, 0:28-0:44 soaring.
0:44 one final majestic hit (full orchestra + taiko + sub-bass), then 0:44-1:00 a glowing sustained D major chord slowly fading to silence.""",
}


def gen(cue, out):
    PROMPTS['_tmp_' + cue] = PALETTE + '\n' + CUES[cue]
    return _gen('_tmp_' + cue, out)


if __name__ == '__main__':
    work = sys.argv[1]; args = sys.argv[2:]
    n = 2
    if '--n' in args: i = args.index('--n'); n = int(args[i + 1]); args = args[:i] + args[i + 2:]
    cues = args or list(CUES)
    d = os.path.join(work, 'music2'); os.makedirs(d, exist_ok=True)
    jobs = [(c, os.path.join(d, f'{c}_{k}.mp3')) for c in cues for k in range(n)]
    jobs = [j for j in jobs if not os.path.exists(j[1])]
    with cf.ThreadPoolExecutor(2) as ex:
        for o in ex.map(lambda j: gen(*j), jobs): print('done', o, flush=True)
