"""渲染入口
  python3 run.py stills OUTDIR t1 t2 ...      输出若干静帧 PNG
  python3 run.py chunk  F0 F1 OUT.mp4          渲染帧区间 [F0, F1) 为无损中间片段
  python3 run.py qa     OUT.json F0 F1 STEP    记录文字越界信息
"""
import os, sys, json, subprocess, inspect
import numpy as np, cv2
import video
from engine import W, H, FPS, TEXT_LOG

ORDER = [l for l in open(video.__file__, encoding='utf8').read().split('\n') if l.startswith('def sc_')]
names = [l[4:l.index('(')] for l in ORDER]
video.SCENES[:] = [getattr(video, n) for n in names]

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'stills':
        out = sys.argv[2]; os.makedirs(out, exist_ok=True)
        for tt in sys.argv[3:]:
            img = video.render(int(round(float(tt) * FPS)))
            cv2.imwrite(os.path.join(out, 'f_%07.2f.png' % float(tt)), img[..., ::-1])
    elif mode == 'chunk':
        a, b, path = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
                              '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '14',
                              '-pix_fmt', 'yuv420p', path], stdin=subprocess.PIPE)
        for i in range(a, b):
            p.stdin.write(video.render(i).tobytes())
            if (i - a) % 300 == 0: print(path, i, flush=True)
        p.stdin.close(); p.wait()
    elif mode == 'qa':
        out, a, b, st = sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
        from fontTools.ttLib import TTFont
        from engine import FONTS
        cmaps = {k: set(TTFont(v).getBestCmap().keys()) for k, v in FONTS.items()}
        bad = []; miss = set()
        for i in range(a, b, st):
            TEXT_LOG.clear()
            video.render(i)
            for (t, s, x0, x1, y, fnt) in TEXT_LOG:
                if x0 < 40 or x1 > W - 40 or y < 40 or y > H - 40:
                    bad.append((round(t, 2), s, round(x0), round(x1), round(y)))
                for ch in s:
                    if ch != ' ' and ord(ch) not in cmaps[fnt]: miss.add((fnt, ch, s))
        bad += [('MISSING GLYPH',) + m for m in sorted(miss)]
        json.dump(bad, open(out, 'w'), ensure_ascii=False, indent=0)
        print(len(bad), 'issues')
