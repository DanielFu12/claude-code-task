"""公共工具：路径、字体、转写稿解析、时间码。"""
import json, os, re, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 巴菲特股东大会精华/
REPO = os.path.dirname(ROOT)
WORK = os.environ.get('BRK_WORK', os.path.join(ROOT, 'work'))
FONTS = os.path.join(ROOT, 'fonts')
sys.path.insert(0, os.path.join(REPO, 'brand'))                       # from brand import Hud（规范见 brand/BRAND.md）

W, H, FPS = 1920, 1080, 30


def load_json(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as f:
        return json.load(f)


def wpath(*p):
    path = os.path.join(WORK, *p)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def run(cmd, **kw):
    kw.setdefault('check', True)
    return subprocess.run(cmd, **kw)


def ffprobe_duration(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def parse_tc(v):
    """'1:02:03.5' / '62:03' / 3723.5 -> 秒"""
    if v is None or isinstance(v, (int, float)):
        return v
    s = 0.0
    for part in str(v).split(':'):
        s = s * 60 + float(part)
    return s


def fmt_tc(s, ms=False):
    s = max(0.0, s)
    h, m, sec = int(s // 3600), int(s % 3600 // 60), s % 60
    return f'{h}:{m:02d}:{sec:06.3f}' if ms else (f'{h}:{m:02d}:{int(sec):02d}' if h else f'{m}:{int(sec):02d}')


# ---------------------------------------------------------------- 字体（Google Fonts）
FONT_SPECS = {
    'sans_med': ('Noto+Sans+SC', 500), 'sans_bold': ('Noto+Sans+SC', 700), 'sans_black': ('Noto+Sans+SC', 900),
    'serif_bold': ('Noto+Serif+SC', 700), 'serif_black': ('Noto+Serif+SC', 900),
    'corm': ('Cormorant+Garamond', 600), 'corm_it': ('Cormorant+Garamond', '1,500'),
}


def font_path(name):
    os.makedirs(FONTS, exist_ok=True)
    p = os.path.join(FONTS, name + '.ttf')
    if not os.path.exists(p):
        fam, w = FONT_SPECS[name]
        axis = f'ital,wght@{w}' if ',' in str(w) else f'wght@{w}'
        css = urllib.request.urlopen(urllib.request.Request(
            f'https://fonts.googleapis.com/css2?family={fam}:{axis}', headers={'User-Agent': 'curl'})).read().decode()
        urllib.request.urlretrieve(re.search(r'https://[^)]+\.ttf', css).group(0), p)
    return p


# ---------------------------------------------------------------- 转写稿 → 带时间的单词序列
_NUM = re.compile(r'(?<=\d),(?=\d{3})')


def norm_tokens(text):
    """小写、去标点、'$10,000' -> '10000'，便于模糊匹配。"""
    text = _NUM.sub('', text.lower().replace('’', "'"))
    text = re.sub(r"[^a-z0-9' ]+", ' ', text.replace('-', ' '))
    return [t.strip("'") for t in text.split() if t.strip("'")]


def _spread(words, t0, t1):
    """一个字幕事件里没有逐词时间时，按字符数把时间均分给每个词。"""
    n = sum(len(w) + 1 for w in words) or 1
    out, acc = [], 0
    for w in words:
        a = t0 + (t1 - t0) * acc / n
        acc += len(w) + 1
        out.append((w, a, t0 + (t1 - t0) * acc / n))
    return out


def load_json3(path, offset=0.0):
    """YouTube json3 字幕（自动字幕带逐词时间）。"""
    ev = json.load(open(path, encoding='utf-8')).get('events', [])
    words = []
    for i, e in enumerate(ev):
        segs = e.get('segs')
        if not segs or 'tStartMs' not in e:
            continue
        t0 = e['tStartMs'] / 1000
        t1 = t0 + e.get('dDurationMs', 0) / 1000
        if any('tOffsetMs' in s for s in segs[1:]) or len(segs) > 1:
            marks = [(s.get('utf8', ''), t0 + s.get('tOffsetMs', 0) / 1000) for s in segs]
            for k, (txt, ts) in enumerate(marks):
                te = marks[k + 1][1] if k + 1 < len(marks) else min(t1, ts + 0.8)
                for w, a, b in _spread(norm_tokens(txt), ts, max(te, ts + 0.05)):
                    words.append((w, a + offset, b + offset))
        else:
            for w, a, b in _spread(norm_tokens(''.join(s.get('utf8', '') for s in segs)), t0, t1):
                words.append((w, a + offset, b + offset))
    words.sort(key=lambda x: x[1])
    return words


_TC = re.compile(r'(\d+:)?(\d+):(\d+)[.,](\d+)\s*-->\s*(\d+:)?(\d+):(\d+)[.,](\d+)')


def _tc(h, m, s, f):
    return int((h or '0:')[:-1]) * 3600 + int(m) * 60 + int(s) + int(f) / 10 ** len(f)


def load_vtt(path, offset=0.0):
    """WebVTT / SRT（Whisper 或手工字幕）。YouTube 自动字幕的 <00:00:01.234> 逐词标记也会解析。"""
    words, cue_t, prev = [], None, None
    for line in open(path, encoding='utf-8', errors='ignore'):
        line = line.strip()
        m = _TC.search(line)
        if m:
            g = m.groups()
            cue_t = (_tc(*g[:4]), _tc(*g[4:]))
            continue
        if not line or cue_t is None or line.isdigit() or line.startswith(('WEBVTT', 'NOTE', 'Kind:', 'Language:')):
            continue
        if re.search(r'<\d+:\d+:\d+\.\d+>', line):                 # 逐词标记
            parts = re.split(r'<(\d+:\d+:\d+\.\d+)>', re.sub(r'</?c[^>]*>', '', line))
            t = cue_t[0]
            for k in range(0, len(parts), 2):
                nxt = _tc(*re.match(r'(\d+:)?(\d+):(\d+)\.(\d+)', parts[k + 1]).groups()) \
                    if k + 1 < len(parts) else cue_t[1]
                for w, a, b in _spread(norm_tokens(parts[k]), t, max(nxt, t + 0.05)):
                    words.append((w, a + offset, b + offset))
                t = nxt
            prev = None
            continue
        clean = re.sub(r'<[^>]+>', '', line)
        if clean == prev:                                     # YouTube 滚动字幕的重复行
            continue
        prev = clean
        for w, a, b in _spread(norm_tokens(clean), *cue_t):
            words.append((w, a + offset, b + offset))
    words.sort(key=lambda x: x[1])
    return words


def load_transcript(path, offset=0.0):
    if path.endswith('.json3'):
        return load_json3(path, offset)
    if path.endswith('.words.json'):                          # whisper 逐词输出：[[word, start, end], ...]
        return [(w, a + offset, b + offset) for t, a, b in json.load(open(path)) for w in norm_tokens(t)]
    return load_vtt(path, offset)
