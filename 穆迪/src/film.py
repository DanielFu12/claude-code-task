"""第八期《一张支票，换一句话——巴菲特与内布拉斯加家具城》渲染入口。

python3 src/film.py WORK frame 12.5s,40s out_#.jpg   # 渲染单帧（调试；# 替换为时间）
python3 src/film.py WORK chunk 0 900 seg0.mp4         # 渲染帧区间
"""
import sys, os, subprocess, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *          # noqa
# ------------------------------------------------------------------ 章节镜头（见 film_ch*.py）
from sot import sot_layer
from gg import shot_hook, shot_title, shot_ch1, shot_ch2, shot_ch3, shot_ch4, shot_ch5, shot_ch6, shot_ch7   # 第八期全部镜头


import media as MEDIA
_LAST = [-10]
_ZONE = None


def _zone():
    """氛围背景的明暗：上方画窗一带亮一些，中下部（解读图表、字幕）压得更暗，四角再收一点"""
    global _ZONE
    if _ZONE is None:
        y = np.linspace(0, 1, H)[:, None]; x = np.linspace(-1, 1, W)[None, :]
        v = np.interp(y, [0, 0.10, 0.42, 0.50, 0.78, 1.0], [0.16, 0.34, 0.34, 0.20, 0.17, 0.12])
        _ZONE = (v * (1 - 0.35 * x ** 2)).astype(np.float32)[..., None]
    return _ZONE


def underlay(cv, items):
    for small, al in items:
        b = cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR)
        g = b @ np.array([0.3, 0.59, 0.11], np.float32)
        b = (b * 0.7 + g[..., None] * 0.3) * np.array([1.04, 0.98, 0.90], np.float32) * _zone()
        cv.over(b, np.full((H, W), min(al, 1.0) * 0.92, np.float32), 0, 0)


def render(i, warm=False):
    if not warm and _LAST[0] != i - 1 and i > 0: render(i - 1, warm=True)     # 块首帧：先空跑上一帧，拿到它登记的背景
    _LAST[0] = i
    t = i / FPS
    bd = list(MEDIA.BD); MEDIA.BD.clear()
    cv = Canvas(t, background(t))
    underlay(cv, bd)
    if t < CH['title'][0] + 0.1: shot_hook(cv, t)
    if CH['title'][0] - 0.1 <= t < CH['ch1'][0] + 0.8: shot_title(cv, t)
    if CH['ch1'][0] <= t < CH['ch2'][0] + 0.8: shot_ch1(cv, t)
    if CH['ch2'][0] <= t < CH['ch3'][0] + 0.8: shot_ch2(cv, t)
    if CH['ch3'][0] <= t < CH['ch4'][0] + 0.8: shot_ch3(cv, t)
    if CH['ch4'][0] <= t < CH['ch5'][0] + 0.8: shot_ch4(cv, t)
    if CH['ch5'][0] <= t < CH['ch6'][0] + 0.8: shot_ch5(cv, t)
    if CH['ch6'][0] <= t < CH['ch7'][0] + 0.8: shot_ch6(cv, t)
    if CH['ch7'][0] <= t < CH['end'][0] + 0.8: shot_ch7(cv, t)
    if t >= CH['end'][0] - 0.6: shot_end(cv, t)
    if CH['ch1'][0] <= t < CH['end'][0]:
        import fx
        fx.dust(cv, t, 0.35, seed=9)
    sot_layer(cv, t)                      # 巴菲特原声段落：整屏转入采访现场
    # 镜头呼吸：极缓的推拉与漂移，让静态排版也有摄影机的生命感（字幕/角标不受影响）
    z = 1.012 + 0.012 * math.sin(t * 0.37)
    dx, dy = 6 * math.sin(t * 0.23), 8 * math.sin(t * 0.29 + 1)
    M = np.array([[z, 0, (1 - z) * W / 2 + dx], [0, z, (1 - z) * H / 2 + dy]], np.float32)
    cv.img = cv2.warpAffine(cv.img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    cv.glow = cv2.warpAffine(cv.glow, M, (W, H), flags=cv2.INTER_LINEAR)
    if cv.U.any(): cv.U = cv2.warpAffine(cv.U, M, (W, H), flags=cv2.INTER_LINEAR)
    interlude_dim(cv, t)                  # 幕间：要点卡 → 章节卡连续压暗（v3）
    takeaway(cv, t)
    chapter_card(cv, t)
    nav(cv, t)
    follow_pill(cv, t)
    subtitles(cv, t)
    fade = 1.0
    if t > TOTAL - 1.8: fade = eio((TOTAL - t) / 1.8)          # 整体淡出（含角标）
    if t < 0.4: fade = eio(t / 0.4)
    if warm: return None
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
                              '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'fast',
                              '-crf', '17', '-pix_fmt', 'yuv420p', '-threads', '1', path], stdin=subprocess.PIPE)
        for i in range(a, b):
            p.stdin.write(render(i).tobytes())
            if (i - a) % 150 == 0: print(path, i, flush=True)
        p.stdin.close(); p.wait()
