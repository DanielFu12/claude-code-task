"""合成成片。

    python3 src/render.py                 # 横版 1920×1080 精华长视频 -> 巴菲特股东大会精华.mp4 + 章节时间码.md
    python3 src/render.py shorts [c01 …]  # 竖版 1080×1920 短视频，每段一条 -> shorts/

依赖 work/located.json（locate.py）和 work/media.json（fetch.py media）。
画面：源视频（4:3 老录像两侧用模糊放大的画面补齐）+ 中英双语字幕 + 左上角届次/人物条 + 右上角「巴芒价值」角标（brand.Hud，带流光）。
"""
import json, math, os, re, subprocess, sys, zlib
from multiprocessing import Pool
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
from common import ROOT, REPO, W, H, FPS, load_json, wpath, font_path, fmt_tc, parse_tc, ffprobe_duration
from brand import Hud, load_logo, GOLD_STOPS, SUB_GOLD

BGM_SRC = os.path.join(REPO, 'opus5.5涌现.mp4')
OUT_DIR = os.environ.get('BRK_OUT', ROOT)
OUT_LONG = os.path.join(OUT_DIR, '巴菲特股东大会精华.mp4')
OUT_SHORTS = os.path.join(OUT_DIR, 'shorts')
CARD = dict(title=6.0, chapter=3.5, end=8.0)
XFADE = 0.25                     # 片段首尾淡入淡出
WHITE, GREY, GOLD_SOFT = (255, 255, 255), (214, 214, 214), SUB_GOLD


# ================================================================ 文字 → 预乘 RGBA 精灵
_fonts = {}


def F(name, px):
    k = (name, int(px))
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(font_path(name), int(px))
    return _fonts[k]


class Sprite:
    """预乘 alpha：p = rgb·a（float32），a ∈ [0,1]。"""
    def __init__(self, p, a):
        self.p, self.a = p.astype(np.float32), a.astype(np.float32)
        self.h, self.w = a.shape

    @staticmethod
    def empty(w, h):
        return Sprite(np.zeros((h, w, 3)), np.zeros((h, w)))

    def over(self, s, x, y, alpha=1.0):
        """把 s 叠到自己上面（原地）。"""
        x, y = int(round(x)), int(round(y))
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + s.w, self.w), min(y + s.h, self.h)
        if x1 <= x0 or y1 <= y0:
            return self
        sa = s.a[y0 - y:y1 - y, x0 - x:x1 - x] * alpha
        sp = s.p[y0 - y:y1 - y, x0 - x:x1 - x] * alpha
        self.p[y0:y1, x0:x1] = sp + self.p[y0:y1, x0:x1] * (1 - sa[..., None])
        self.a[y0:y1, x0:x1] = sa + self.a[y0:y1, x0:x1] * (1 - sa)
        return self


def blit(frame, s, x, y, alpha=1.0):
    """把精灵叠到 uint8 帧上（只换算重叠区域，速度快）。"""
    if alpha <= 0.003:
        return
    x, y = int(round(x)), int(round(y))
    fh, fw = frame.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + s.w, fw), min(y + s.h, fh)
    if x1 <= x0 or y1 <= y0:
        return
    sa = s.a[y0 - y:y1 - y, x0 - x:x1 - x, None] * alpha
    sp = s.p[y0 - y:y1 - y, x0 - x:x1 - x] * alpha
    reg = frame[y0:y1, x0:x1].astype(np.float32) * (1 / 255)
    frame[y0:y1, x0:x1] = np.clip((sp + reg * (1 - sa)) * 255 + 0.5, 0, 255).astype(np.uint8)


def _ramp(h, stops):
    y = np.linspace(0, 1, max(h, 2))
    return np.stack([np.interp(y, [s[0] for s in stops], [s[1][c] for s in stops]) for c in range(3)], 1) / 255.0


def text(s, font, px, color=WHITE, stroke=0, shadow=0.0, tracking=0.0, shadow_alpha=0.75):
    """渲染一行文字。color 为 RGB 元组或 'gold'（品牌金色竖向渐变）。"""
    f = F(font, px)
    pad = int(stroke + shadow * 3 + 4)
    widths = [f.getlength(c) for c in s]
    tw = int(sum(widths) + tracking * max(len(s) - 1, 0)) + 2
    asc, desc = f.getmetrics()
    th = asc + desc
    Wd, Hd = tw + 2 * pad, th + 2 * pad
    fill = Image.new('L', (Wd, Hd), 0)
    strk = Image.new('L', (Wd, Hd), 0)
    df, ds = ImageDraw.Draw(fill), ImageDraw.Draw(strk)
    if tracking:                                  # 逐字排（加字距）
        x = pad
        for c, cw in zip(s, widths):
            df.text((x, pad), c, font=f, fill=255)
            if stroke:
                ds.text((x, pad), c, font=f, fill=255, stroke_width=int(stroke), stroke_fill=255)
            x += cw + tracking
    else:                                         # 整串排，保留字偶间距
        tw = int(f.getlength(s)) + 2
        Wd = tw + 2 * pad
        fill, strk = Image.new('L', (Wd, Hd), 0), Image.new('L', (Wd, Hd), 0)
        ImageDraw.Draw(fill).text((pad, pad), s, font=f, fill=255)
        if stroke:
            ImageDraw.Draw(strk).text((pad, pad), s, font=f, fill=255, stroke_width=int(stroke), stroke_fill=255)
    fa = np.asarray(fill, np.float32) / 255
    sa = np.asarray(strk, np.float32) / 255 if stroke else np.zeros_like(fa)
    if color == 'gold':
        rgb = np.broadcast_to(_ramp(Hd, GOLD_STOPS)[:, None, :], (Hd, Wd, 3))
    else:
        rgb = np.broadcast_to(np.array(color, np.float32) / 255, (Hd, Wd, 3))
    a = np.maximum(fa, sa)
    p = rgb * fa[..., None]                       # 描边是黑色：只贡献 alpha
    out = Sprite(p, a)
    if shadow:
        base = np.maximum(fa, sa)
        sh = cv2.GaussianBlur(base, (0, 0), shadow) * shadow_alpha
        bg = Sprite(np.zeros((Hd, Wd, 3)), sh)
        bg.over(out, 0, 0)
        out = bg
    return out


def vstack(items, align='center', gap=0):
    """items: [(sprite, extra_gap_before)] 竖向排列。"""
    w = max(s.w for s, _ in items)
    h = sum(s.h + g for s, g in items) + gap * (len(items) - 1)
    c = Sprite.empty(w, h)
    y = 0
    for s, g in items:
        y += g
        x = {'center': (w - s.w) / 2, 'left': 0, 'right': w - s.w}[align]
        c.over(s, x, y)
        y += s.h + gap
    return c


def hstack(items, gap=0, valign='center'):
    h = max(s.h for s in items)
    w = sum(s.w for s in items) + gap * (len(items) - 1)
    c = Sprite.empty(w, h)
    x = 0
    for s in items:
        c.over(s, x, {'center': (h - s.h) / 2, 'top': 0, 'bottom': h - s.h}[valign])
        x += s.w + gap
    return c


def wrap(s, font, px, maxw):
    """中文按字、英文按词换行：动态规划求各行尽量等长，优先在标点后断，不让标点打头。"""
    f = F(font, px)
    if f.getlength(s) <= maxw:
        return [s]
    toks = re.findall(r"[A-Za-z0-9$%.,'’\-]+\s*|\s+|.", s)
    total = f.getlength(s)
    ideal = total / math.ceil(total / maxw)
    punct_end = re.compile(r'[，。、；：！？—,.;:!?」）]\s*$')
    punct_start = re.compile(r'^[，。、；：！？—,.;:!?」）%]')
    n = len(toks)
    best = [0.0] + [math.inf] * n                # best[j]：前 j 个 token 的最小代价
    prev = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(j - 1, -1, -1):
            line = ''.join(toks[i:j]).strip()
            w = f.getlength(line)
            if w > maxw and j - i > 1:
                break
            if best[i] == math.inf:
                continue
            cost = 60 * ((w - ideal) / ideal) ** 2 if j < n else (20 * ((w - ideal) / ideal) ** 2 if w > ideal else 0)
            if j < n:
                if punct_end.search(toks[j - 1]):
                    pass
                elif toks[j - 1].endswith(' ') or toks[j].startswith(' '):
                    cost += 2
                else:
                    cost += 12
                if punct_start.match(toks[j]):
                    cost += 1000
            cost += 25                               # 每多一行的代价
            if best[i] + cost < best[j]:
                best[j], prev[j] = best[i] + cost, i
    lines, j = [], n
    while j > 0:
        lines.append(''.join(toks[prev[j]:j]).strip()); j = prev[j]
    return lines[::-1]


# ================================================================ 组件
class Kit:
    def __init__(self, vertical=False):
        self.vertical = vertical
        self.fw, self.fh = (1080, 1920) if vertical else (W, H)
        self.hud = Hud(frame_w=520)               # 只在右上角 520×150 的区域里合成，省时
        self._cache = {}

    def draw_hud(self, frame, t):
        reg = frame[0:150, self.fw - 520:self.fw].astype(np.float32) / 255
        self.hud.draw(reg, t)
        frame[0:150, self.fw - 520:self.fw] = np.clip(reg * 255 + 0.5, 0, 255).astype(np.uint8)

    def cached(self, key, fn):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    # -------- 字幕
    def subtitle(self, zh, en, who=None, en_only=False):
        def build():
            v = self.vertical
            zpx, epx = (54, 30) if v else (50, 28)
            maxw = 960 if v else 1640
            rows = []
            if zh and not en_only:
                zl = wrap(zh, 'sans_bold', zpx, maxw - (zpx * 3 if who else 0))
                for k, l in enumerate(zl):
                    s = text(l, 'sans_bold', zpx, WHITE, stroke=3, shadow=4)
                    if who and k == 0:
                        s = hstack([text(who, 'sans_bold', zpx, GOLD_SOFT, stroke=3, shadow=4), s], gap=4)
                    rows.append((s, 0 if k == 0 else -40))
            if en:
                for k, l in enumerate(wrap(en, 'sans_med', epx, maxw)):
                    rows.append((text(l, 'sans_med', epx, (226, 226, 226) if not en_only else (240, 240, 240),
                                      stroke=2, shadow=3), -4 if (k == 0 and rows) else -16))
            return vstack(rows) if rows else Sprite.empty(1, 1)
        return self.cached(('sub', zh, en, who, en_only), build)

    # -------- 左上角：届次 / 人物
    def lower_third(self, year, speaker, speaker_en, topic):
        def build():
            yr = text(year, 'serif_black', 64, 'gold', shadow=3)
            l1 = hstack([text(speaker, 'sans_bold', 32, WHITE, shadow=3),
                         text(speaker_en, 'corm', 30, GOLD_SOFT, shadow=3)], gap=14, valign='bottom')
            l2 = text(f'伯克希尔·哈撒韦股东大会 · {topic}', 'sans_med', 24, (232, 224, 205), shadow=3)
            right = vstack([(l1, 0), (l2, 2)], align='left')
            bar = Sprite(np.broadcast_to(np.array(GOLD_SOFT, np.float32) / 255 * 0.9, (right.h - 10, 3, 3)).copy(),
                         np.full((right.h - 10, 3), 0.9))
            row = hstack([yr, bar, right], gap=20)
            # 背后一层向右渐隐的暗色衬底
            bw, bh = row.w + 120, row.h + 36
            grad = np.clip(1.15 - np.linspace(0, 1, bw) ** 1.6, 0, 1)[None, :] * np.ones((bh, 1))
            grad *= np.minimum(1, np.minimum(np.arange(bh), bh - 1 - np.arange(bh))[:, None] / 10)
            bg = Sprite(np.zeros((bh, bw, 3)), grad * 0.5)
            bg.over(row, 28, 18)
            return bg
        return self.cached(('lt', year, speaker, topic), build)

    def tag(self, chapter, year, speaker):
        return self.cached(('tag', chapter, year, speaker), lambda: hstack([
            text(chapter, 'serif_bold', 24, 'gold', shadow=3),
            text(f'{year} · {speaker}', 'sans_med', 22, (236, 236, 236), shadow=3)], gap=16))


# ================================================================ 卡片背景（深蓝夜空 + 金色微光粒子）
class CardBG:
    def __init__(self, fw, fh, seed=7):
        yy, xx = np.mgrid[0:fh, 0:fw].astype(np.float32)
        r = np.hypot((xx - fw / 2) / fw, (yy - fh * 0.46) / fh)
        top, bot = np.array([0.035, 0.05, 0.10]), np.array([0.008, 0.01, 0.025])
        self.base = (top * (1 - yy / fh)[..., None] + bot * (yy / fh)[..., None]).astype(np.float32)
        self.glow = np.exp(-(r / 0.42) ** 2)[..., None].astype(np.float32) * np.array([0.16, 0.12, 0.06], np.float32)
        self.vig = (1 - 0.55 * np.clip(r * 1.25, 0, 1) ** 2)[..., None].astype(np.float32)
        rng = np.random.default_rng(seed)
        n = 90
        self.pts = np.c_[rng.uniform(0, fw, n), rng.uniform(0, fh, n), rng.uniform(1.0, 2.6, n),
                         rng.uniform(4, 16, n), rng.uniform(0, 6.28, n), rng.uniform(0.15, 0.6, n)]
        self.fw, self.fh = fw, fh

    def frame(self, t):
        img = self.base + self.glow * (0.85 + 0.15 * math.sin(t * 1.3))
        dots = np.zeros((self.fh // 2, self.fw // 2), np.float32)
        for x, y, rad, sp, ph, br in self.pts:
            yy = (y - sp * t * 6) % self.fh
            xx = x + 14 * math.sin(t * 0.4 + ph)
            cv2.circle(dots, (int(xx / 2), int(yy / 2)), max(1, int(rad / 2 + 0.5)),
                       float(br * (0.6 + 0.4 * math.sin(t * 2 + ph))), -1, cv2.LINE_AA)
        dots = cv2.GaussianBlur(dots, (0, 0), 1.6)
        dots = cv2.resize(dots, (self.fw, self.fh), interpolation=cv2.INTER_LINEAR)[..., None]
        img = (img + dots * np.array([1.0, 0.8, 0.45], np.float32) * 0.5) * self.vig
        return np.clip(img * 255 + 0.5, 0, 255).astype(np.uint8)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def env(t, dur, fin=0.6, fout=0.5, delay=0.0):
    return min(ease((t - delay) / fin), ease((dur - t) / fout))


# ================================================================ 时间线
def plan(cfg, loc, media):
    """生成片段列表：冷开场 → 片名 → 各章（章节卡 + 片段）→ 片尾。"""
    segs = []
    for c in cfg['coldopen']:
        if c['id'] in loc:
            segs.append(dict(kind='clip', clip=c, cold=True))
    segs.append(dict(kind='title', dur=CARD['title']))
    chap = {c['id']: c for c in cfg['chapters']}
    cur = None
    for c in cfg['clips']:
        if c['id'] not in loc:
            print(f'  ! 跳过 {c["id"]}（未定位）'); continue
        if c['chapter'] != cur:
            cur = c['chapter']
            segs.append(dict(kind='chapter', dur=CARD['chapter'], chapter=chap[cur]))
        segs.append(dict(kind='clip', clip=c, chapter=chap[cur]))
    segs.append(dict(kind='end', dur=CARD['end']))
    t = 0.0
    for s in segs:
        if s['kind'] == 'clip':
            if s.get('cold'):
                s['clip'] = dict(s['clip'], fill_en=False)
            L = loc[s['clip']['id']]
            s['dur'] = round((L['end'] - L['start']) * FPS) / FPS
            s['loc'], s['media'] = L, media[s['clip']['id']]
        s['t0'] = t
        t += s['dur']
    return segs, t


def sub_cues(clip, L):
    """返回 [(t0, t1, zh, en, who, en_only)]，时间相对片段起点。"""
    srt = os.path.join(ROOT, 'subs', f'{clip["id"]}.srt')
    if os.path.exists(srt):                       # 人工/翻译好的完整双语字幕优先（每条：中文一行，英文一行）
        cues = []
        for blk in re.split(r'\n\s*\n', open(srt, encoding='utf-8').read().strip()):
            ls = blk.strip().splitlines()
            m = re.match(r'(\S+)\s*-->\s*(\S+)', ls[1] if len(ls) > 1 else '')
            if m:
                body = ls[2:]
                cues.append((parse_tc(m[1].replace(',', '.')), parse_tc(m[2].replace(',', '.')),
                             body[0] if body else '', ' '.join(body[1:]), None, False))
        return cues
    lines = [(l, r) for l, r in zip(clip['lines'], L['lines']) if r]
    lines.sort(key=lambda x: x[1]['t0'])
    multi = len({l.get('who') for l, _ in lines}) > 1
    cues = []
    for k, (l, r) in enumerate(lines):
        nxt = lines[k + 1][1]['t0'] if k + 1 < len(lines) else L['end'] - L['start']
        cues.append((max(0, r['t0'] - 0.12), min(max(r['t1'] + 0.5, r['t0'] + 1.6), nxt - 0.04),
                     l['zh'], l['en'], l.get('who') if multi else None, False))
    # 金句之间、之前（如提问）的话，用转写稿英文补上
    if not clip.get('fill_en', True):
        return cues
    busy = [(c[0] - 0.2, c[1] + 0.2) for c in cues]
    cur = []
    words = [w for w in L['words'] if not any(a <= w[1] <= b for a, b in busy)]
    for w in words + [None]:
        if cur and (w is None or w[1] - cur[-1][2] > 0.7 or len(cur) >= 12):
            cues.append((cur[0][1], cur[-1][2] + 0.3, '', ' '.join(x[0] for x in cur), None, True)); cur = []
        if w:
            cur.append(w)
    cues.sort(key=lambda c: c[0])
    return cues


# ================================================================ 渲染单个片段
def reader(media, start, dur, vertical):
    """ffmpeg 解码 → rgb24 帧流。横版：等比铺满 16:9，4:3 素材两侧补模糊画面；竖版：模糊背景 + 居中横画面。"""
    src = media['path']
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                            '-of', 'csv=p=0', src], capture_output=True, text=True, check=True).stdout.split(',')
    sw, sh = int(probe[0]), int(probe[1])
    sharpen = ',unsharp=5:5:0.7' if sh < 700 else ''
    if vertical:
        fg_h = int(round(1080 * sh / sw / 2) * 2)
        fy = int(1920 * 0.47 - fg_h / 2)
        vf = (f'[0:v]fps={FPS},split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,'
              f'gblur=sigma=28,eq=brightness=-0.3:saturation=0.7[bg];[b]scale=1080:{fg_h}:flags=lanczos{sharpen}[fg];'
              f'[bg][fg]overlay=0:{fy},format=rgb24')
        geo = dict(fg_y=fy, fg_h=fg_h)
    elif abs(sw / sh - 16 / 9) < 0.05:
        vf = f'[0:v]fps={FPS},scale={W}:{H}:flags=lanczos{sharpen},setsar=1,format=rgb24'
        geo = {}
    else:
        vf = (f'[0:v]fps={FPS},split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},'
              f'gblur=sigma=30,eq=brightness=-0.25:saturation=0.7[bg];[b]scale=-2:{H}:flags=lanczos{sharpen}[fg];'
              f'[bg][fg]overlay=(W-w)/2:0,format=rgb24')
        geo = {}
    fw, fh = (1080, 1920) if vertical else (W, H)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{start:.3f}', '-i', src, '-t', f'{dur:.3f}',
                          '-filter_complex', vf, '-frames:v', str(int(round(dur * FPS))),
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    return p, fw, fh, geo


def writer(out, fw, fh, dur, audio):
    """audio: ('clip', path, start) | ('bgm', offset, gain) """
    if audio[0] == 'clip':
        ain = ['-ss', f'{audio[2]:.3f}', '-t', f'{dur:.3f}', '-i', audio[1]]
        af = (f'loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,afade=t=in:d={XFADE},'
              f'afade=t=out:st={max(0, dur - XFADE - 0.1):.3f}:d={XFADE}')
    else:
        ain = ['-ss', f'{audio[1]:.3f}', '-t', f'{dur:.3f}', '-i', wpath('bgm.wav')]
        af = f'volume={audio[2]},afade=t=in:d=0.6,afade=t=out:st={max(0, dur - 0.9):.3f}:d=0.9,aresample=48000'
    return subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{fw}x{fh}',
                             '-r', str(FPS), '-i', '-'] + ain +
                            ['-map', '0:v', '-map', '1:a', '-af', af + ',aformat=channel_layouts=stereo',
                             '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
                             '-c:a', 'aac', '-b:a', '192k', '-t', f'{dur:.3f}', '-movflags', '+faststart', out],
                            stdin=subprocess.PIPE)


def render_clip(seg, out, kit, vertical=False, t_global=0.0):
    clip, L, M = seg['clip'], seg['loc'], seg['media']
    dur, cold = seg['dur'], seg.get('cold', False)
    start = L['start'] - M['t0']
    rd, fw, fh, geo = reader(M, start, dur, vertical)
    wr = writer(out, fw, fh, dur, ('clip', M['path'], start))
    cues = sub_cues(clip, L)
    year = clip['source']
    speaker = clip.get('speaker', '')
    chap = seg.get('chapter')
    nbytes = fw * fh * 3
    n = int(round(dur * FPS))
    last = np.zeros((fh, fw, 3), np.uint8)
    if vertical:
        title_rows = [(text(l, 'serif_black', 66, 'gold', shadow=5), 0 if k == 0 else -6)
                      for k, l in enumerate(wrap(clip['short_title'], 'serif_black', 66, 940))]
        title = vstack(title_rows)
        info = text(f'{year} 伯克希尔股东大会 · {speaker}', 'sans_med', 30, (236, 230, 215), shadow=3)
    for i in range(n):
        t = i / FPS
        buf = rd.stdout.read(nbytes)
        frame = np.frombuffer(buf, np.uint8).reshape(fh, fw, 3).copy() if len(buf) == nbytes else last.copy()
        last = frame
        # 字幕
        for c0, c1, zh, en, who, en_only in cues:
            if c0 <= t < c1:
                s = kit.subtitle(zh, en, who, en_only)
                a = min(1, (t - c0) / 0.12, (c1 - t) / 0.12)
                if vertical:
                    blit(frame, s, (fw - s.w) / 2, geo['fg_y'] + geo['fg_h'] + 46, a)
                else:
                    blit(frame, s, (fw - s.w) / 2, fh - 46 - s.h, a)
        if vertical:
            ty = geo['fg_y'] - 70 - title.h - info.h
            blit(frame, title, (fw - title.w) / 2, max(150, ty), ease(t / 0.5))
            blit(frame, info, (fw - info.w) / 2, geo['fg_y'] - 30 - info.h, ease((t - 0.2) / 0.5))
        elif cold:
            yt = kit.cached(('yr', year), lambda: text(year, 'serif_black', 54, 'gold', shadow=4))
            blit(frame, yt, 60, 40, env(t, dur, 0.15, 0.15))
        else:
            lt = kit.lower_third(year, speaker, clip.get('speaker_en', ''), clip['topic'])
            a = min(ease((t - 0.3) / 0.5), ease((6.3 - t) / 0.5))
            if a > 0:
                blit(frame, lt, 22 - 30 * (1 - a), 22, a)
            tg = kit.tag(f'{chap["no"]} · {chap["title"]}', year, speaker.split(' & ')[0].split('·')[-1])
            blit(frame, tg, 56, 40, 0.85 * ease((t - 6.3) / 0.6) * ease((dur - t) / 0.3))
        kit.draw_hud(frame, t_global + t)
        fade = min(1.0, (t + 0.5 / FPS) / XFADE, (dur - t) / XFADE) if not cold else min(1.0, (t + 0.5 / FPS) / 0.08, (dur - t) / 0.08)
        if fade < 1:
            frame = (frame.astype(np.float32) * max(fade, 0)).astype(np.uint8)
        wr.stdin.write(frame.tobytes())
    rd.stdout.close(); rd.wait()
    wr.stdin.close(); wr.wait()


def render_card(seg, out, kit, cfg, t_global, vertical=False):
    fw, fh = (1080, 1920) if vertical else (W, H)
    dur, kind = seg['dur'], seg['kind']
    bg = CardBG(fw, fh, seed=zlib.crc32(kind.encode()) % 1000)
    els = []                                       # (sprite, cx, cy, delay, rise)
    cy = fh * 0.46
    if kind == 'title':
        a = text(cfg['title'], 'serif_black', 132, 'gold', shadow=8)
        b = text(cfg['subtitle'], 'sans_med', 40, (238, 238, 238), tracking=6, shadow=4)
        c = text(cfg['tagline'], 'serif_bold', 32, GOLD_SOFT, tracking=10, shadow=4)
        els = [(a, fw / 2, cy - 70, 0.2, 24), (b, fw / 2, cy + 50, 0.7, 16), (c, fw / 2, cy + 112, 1.1, 12)]
        audio = ('bgm', 0.0, 0.55)
    elif kind == 'chapter':
        ch = seg['chapter']
        no = text(ch['no'], 'serif_black', 76, 'gold', shadow=5)
        ring = Sprite.empty(150, 150)
        m = np.zeros((150, 150), np.float32)
        cv2.circle(m, (75, 75), 66, 1.0, 2, cv2.LINE_AA)
        ring = Sprite(np.array(GOLD_SOFT, np.float32)[None, None] / 255 * m[..., None], m * 0.85)
        ring.over(no, (150 - no.w) / 2, (150 - no.h) / 2 - 4)
        t1 = text(ch['title'], 'serif_black', 92, WHITE, shadow=6)
        t2 = text(ch['subtitle'], 'sans_med', 32, (205, 205, 205), tracking=4, shadow=4)
        els = [(ring, fw / 2, cy - 120, 0.0, 10), (t1, fw / 2, cy + 30, 0.25, 18), (t2, fw / 2, cy + 112, 0.55, 12)]
        audio = ('bgm', 30.0 + zlib.crc32(ch['id'].encode()) % 40, 0.4)
    else:                                          # 片尾：大号 logo + 金色「巴芒价值」+ BUFFETT · MUNGER
        lrgb, la = load_logo(220)
        logo = Sprite(lrgb * la[..., None], la)
        glow_a = cv2.GaussianBlur(np.pad(la, 60), (0, 0), 26) * 0.35
        glow = Sprite(np.array([110, 175, 255], np.float32)[None, None] / 255 * glow_a[..., None], glow_a)
        glow.over(logo, 60, 60)
        name = text('巴芒价值', 'serif_black', 96, 'gold', shadow=6)
        sub = text('BUFFETT · MUNGER', 'corm', 36, GOLD_SOFT, shadow=3)
        trk = (name.w - 16 - sub.w) / (len('BUFFETT · MUNGER') - 1)
        sub = text('BUFFETT · MUNGER', 'corm', 36, GOLD_SOFT, shadow=3, tracking=trk)   # 与主标题等宽
        memo = text('谨以此片致敬查理·芒格（1924—2023）', 'sans_med', 26, (190, 190, 190), tracking=3, shadow=3)
        els = [(glow, fw / 2, cy - 150, 0.1, 10), (name, fw / 2, cy + 50, 0.5, 14), (sub, fw / 2, cy + 130, 0.8, 8),
               (memo, fw / 2, fh - 120 if not vertical else fh - 260, 1.4, 6)]
        audio = ('bgm', 95.0, 0.6)
    k = min(1.0, dur / 6)                          # 短片尾（竖版 2.5 秒）把入场节奏整体压缩
    wr = writer(out, fw, fh, dur, audio)
    for i in range(int(round(dur * FPS))):
        t = i / FPS
        frame = bg.frame(t_global + t)
        for s, x, y, d, rise in els:
            a = env(t, dur, 0.7 * k, 0.6 * k, delay=d * k)
            blit(frame, s, x - s.w / 2, y - s.h / 2 + rise * (1 - a), a)
        kit.draw_hud(frame, t_global + t)
        fade = min(1.0, (t + 0.5 / FPS) / 0.4, (dur - t) / 0.5)
        if fade < 1:
            frame = (frame.astype(np.float32) * max(fade, 0)).astype(np.uint8)
        wr.stdin.write(frame.tobytes())
    wr.stdin.close(); wr.wait()


# ================================================================ 入口
def _job(args):
    k, seg, cfg, vertical, out = args
    kit = Kit(vertical)
    if seg['kind'] == 'clip':
        render_clip(seg, out, kit, vertical, seg.get('t0', 0.0))
    else:
        render_card(seg, out, kit, cfg, seg.get('t0', 0.0), vertical)
    return k, out


def prep_bgm():
    if not os.path.exists(wpath('bgm.wav')):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', BGM_SRC, '-vn', '-ac', '2', '-ar', '48000', wpath('bgm.wav')], check=True)


def concat(files, out):
    lst = wpath('concat.txt')
    with open(lst, 'w') as f:
        f.writelines(f"file '{p}'\n" for p in files)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy',
                    '-movflags', '+faststart', out], check=True)


def main_long(jobs=4):
    cfg = load_json('clips.json')
    loc, media = json.load(open(wpath('located.json'))), json.load(open(wpath('media.json')))
    prep_bgm()
    segs, total = plan(cfg, loc, media)
    print(f'{len(segs)} 段，总时长 {fmt_tc(total)}（目标 {fmt_tc(cfg["target_seconds"])}）')
    tasks = [(k, s, cfg, False, wpath('seg', f'{k:02d}_{s["kind"]}.mp4')) for k, s in enumerate(segs)]
    with Pool(jobs) as pool:
        for k, out in pool.imap_unordered(_job, sorted(tasks, key=lambda x: -x[1]['dur'])):
            print(f'  ✓ {os.path.basename(out)}')
    concat([t[4] for t in tasks], OUT_LONG)
    write_chapters(cfg, segs, total)
    print(f'done -> {OUT_LONG}  ({fmt_tc(ffprobe_duration(OUT_LONG))})')


def write_chapters(cfg, segs, total):
    rows = ['# 章节时间码', '', f'成片：`巴菲特股东大会精华.mp4`，总长 {fmt_tc(total)}。每一段都可以单独切出来做短视频'
            '（也可以直接用 `python3 src/render.py shorts` 生成竖版）。', '',
            '| 成片时间 | 段落 | 届次 | 人物 | 内容 | 短视频标题建议 | 源视频时间 |', '|---|---|---|---|---|---|---|']
    for s in segs:
        a, b = fmt_tc(s['t0']), fmt_tc(s['t0'] + s['dur'])
        if s['kind'] == 'clip':
            c, L = s['clip'], s['loc']
            if s.get('cold'):
                rows.append(f'| {a}–{b} | 冷开场 | {c["source"]} | 芒格 | 「我没什么要补充的」 | — | {fmt_tc(L["start"])} |')
            else:
                rows.append(f'| {a}–{b} | {c["id"]} | {c["source"]} | {c["speaker"]} | {c["topic"]} | {c["short_title"]} | '
                            f'{fmt_tc(L["start"])}–{fmt_tc(L["end"])} |')
        else:
            name = {'title': '片名', 'end': '片尾'}.get(s['kind']) or f'第{s["chapter"]["no"]}章 · {s["chapter"]["title"]}'
            rows.append(f'| {a}–{b} | {name} | | | | | |')
    with open(os.path.join(OUT_DIR, '章节时间码.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(rows) + '\n')


def main_shorts(ids, jobs=4):
    """每段金句一条竖版短视频：钩子标题 + 画面 + 双语字幕 + 2.5 秒品牌片尾。"""
    cfg = load_json('clips.json')
    loc, media = json.load(open(wpath('located.json'))), json.load(open(wpath('media.json')))
    prep_bgm()
    os.makedirs(OUT_SHORTS, exist_ok=True)
    tasks, outs = [], []
    for c in cfg['clips']:
        if (ids and c['id'] not in ids) or c['id'] not in loc:
            continue
        L = loc[c['id']]
        seg = dict(kind='clip', clip=c, loc=L, media=media[c['id']], dur=round((L['end'] - L['start']) * FPS) / FPS, t0=0.0)
        end = dict(kind='end', dur=2.5, t0=seg['dur'])
        a, b = wpath('shorts', f'{c["id"]}_a.mp4'), wpath('shorts', f'{c["id"]}_b.mp4')
        tasks += [(c['id'], seg, cfg, True, a), (c['id'], end, cfg, True, b)]
        safe = re.sub(r'[\\/:*?"<>|\s]+', '', c['short_title'])
        outs.append(([a, b], os.path.join(OUT_SHORTS, f'{c["id"]}_{c["source"]}_{safe}.mp4')))
    with Pool(jobs) as pool:
        for _ in pool.imap_unordered(_job, tasks):
            pass
    for parts, out in outs:
        concat(parts, out)
        print(f'  ✓ {os.path.relpath(out, OUT_DIR)}  ({fmt_tc(ffprobe_duration(out))})')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'shorts':
        main_shorts(set(sys.argv[2:]))
    else:
        main_long()
