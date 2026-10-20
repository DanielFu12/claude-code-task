"""成片音轨：原声片段按时间线拼接 + 片头/章节卡/片尾配乐（配乐来源与重拍位置见 render_consts.py）。
用法: python3 audio.py <orig.mp4> <bgm.mp4> <out.wav>
"""
import subprocess, sys
import numpy as np
import edl, render_consts as RC

SR = 48000

def load(path, t0=None, dur=None):
    cmd = ['ffmpeg', '-loglevel', 'error']
    if t0 is not None: cmd += ['-ss', f'{t0:.4f}']
    cmd += ['-i', path]
    if dur is not None: cmd += ['-t', f'{dur:.4f}']
    cmd += ['-vn', '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).reshape(-1, 2)

def ramp(x, fi, fo):
    n = len(x); x = x.copy()
    a, b = int(fi * SR), int(fo * SR)
    if a: x[:a] *= np.linspace(0, 1, a)[:, None] ** 2
    if b: x[n - b:] *= np.linspace(1, 0, b)[:, None] ** 2
    return x

def rms_db(x): return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)

def main(orig, bgm_path, out):
    items, _, total = edl.load(edl.ASR_DEFAULT)
    buf = np.zeros((int(total * SR) + SR, 2), np.float32)
    speech = []
    for it in items:
        if it['kind'] != 'clip': continue
        x = ramp(load(orig, it['src0'], it['src1'] - it['src0']), 0.012, 0.03)
        i = int(round(it['f0'] / edl.FPS * SR))
        buf[i:i + len(x)] += x; speech.append(x)
    sp_db = rms_db(np.concatenate(speech[:3]))
    bgm = load(bgm_path)
    bg_db = rms_db(bgm[int(100 * SR):int(240 * SR)])      # 配乐主体段的平均响度

    def bed(src_t, dur, at, rel_db, fi, fo):
        x = bgm[int(src_t * SR):int((src_t + dur) * SR)]
        g = 10 ** ((sp_db + rel_db - bg_db) / 20)
        x = ramp(x * g, fi, fo)
        i = int(at * SR); buf[i:i + len(x)] += x

    for it in items:
        if it['kind'] == 'intro':
            bed(RC.HIT_INTRO - 0.35, edl.INTRO, it['t0'], -3, 0.05, 1.4)
        elif it['kind'] == 'card':
            bed(RC.HIT_CARD - 0.24, edl.CARD, it['t0'], -7, 0.02, 1.0)
        elif it['kind'] == 'outro':
            bed(RC.HIT_OUTRO - RC.OUTRO_HIT, edl.OUTRO, it['t0'], -2, 0.9, 1.6)
    buf = buf[:int(total * SR)]
    import soundfile as sf
    sf.write(out, buf, SR, subtype='FLOAT')
    print('speech', round(sp_db, 1), 'dB  bgm', round(bg_db, 1), 'dB  len', round(len(buf) / SR, 2))

if __name__ == '__main__':
    main(*sys.argv[1:4])
