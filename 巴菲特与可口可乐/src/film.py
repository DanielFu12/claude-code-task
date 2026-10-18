"""《38年，一股未卖——巴菲特与可口可乐》渲染入口。

python3 src/film.py WORK frame 12.5s,40s out_#.jpg   # 渲染单帧（调试；# 替换为时间）
python3 src/film.py WORK chunk 0 900 seg0.mp4         # 渲染帧区间
"""
import sys, os, subprocess, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *          # noqa
# ------------------------------------------------------------------ 章节镜头（见 film_ch*.py）
from film_ch1 import shot_ch1
from film_ch2 import shot_ch2
from film_ch3 import shot_ch3
from film_ch4 import shot_ch4
from film_ch5 import shot_ch5


def render(i):
    t = i / FPS
    cv = Canvas(t, background(t))
    if t < CH['title'][0] + 0.1: shot_hook(cv, t)
    if CH['title'][0] - 0.1 <= t < CH['ch1'][0] + 0.8: shot_title(cv, t)
    if CH['ch1'][0] <= t < CH['ch2'][0] + 0.8: shot_ch1(cv, t)
    if CH['ch2'][0] <= t < CH['ch3'][0] + 0.8: shot_ch2(cv, t)
    if CH['ch3'][0] <= t < CH['ch4'][0] + 0.8: shot_ch3(cv, t)
    if CH['ch4'][0] <= t < CH['ch5'][0] + 0.8: shot_ch4(cv, t)
    if CH['ch5'][0] <= t < CH['end'][0] + 0.8: shot_ch5(cv, t)
    if t >= CH['end'][0] - 0.6: shot_end(cv, t)
    # 镜头呼吸：极缓的推拉与漂移，让静态排版也有摄影机的生命感（字幕/角标不受影响）
    z = 1.012 + 0.012 * math.sin(t * 0.37)
    dx, dy = 6 * math.sin(t * 0.23), 8 * math.sin(t * 0.29 + 1)
    M = np.array([[z, 0, (1 - z) * W / 2 + dx], [0, z, (1 - z) * H / 2 + dy]], np.float32)
    cv.img = cv2.warpAffine(cv.img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    cv.glow = cv2.warpAffine(cv.glow, M, (W, H), flags=cv2.INTER_LINEAR)
    if cv.U.any(): cv.U = cv2.warpAffine(cv.U, M, (W, H), flags=cv2.INTER_LINEAR)
    chapter_card(cv, t)
    chapter_label(cv, t)
    subtitles(cv, t)
    fade = 1.0
    if t > TOTAL - 1.8: fade = eio((TOTAL - t) / 1.8)          # 整体淡出（含角标）
    if t < 0.4: fade = eio(t / 0.4)
    return finish(cv, i, bloom_k=1.0, fade=fade)


if __name__ == '__main__':
    mode = sys.argv[2]
    if mode == 'frame':
        for k in sys.argv[3].split(','):
            fi = int(round(float(k.rstrip('s')) * FPS)) if k.endswith('s') else int(k)
            out = render(fi)
            path = sys.argv[4].replace('#', k)
            cv2.imwrite(path, out[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 92])
    elif mode == 'chunk':
        a, b, path = int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
        b = min(b, NFRAMES)
        p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                              '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium',
                              '-crf', '14', '-pix_fmt', 'yuv420p', path], stdin=subprocess.PIPE)
        for i in range(a, b):
            p.stdin.write(render(i).tobytes())
            if (i - a) % 150 == 0: print(path, i, flush=True)
        p.stdin.close(); p.wait()
