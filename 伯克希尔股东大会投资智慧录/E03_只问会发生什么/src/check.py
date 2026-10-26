"""成片质检：规格、黑场、静音、响度/峰值、低频转场、字幕与声音的识别比对、品牌角标、关键帧拼图。

用法：python3 src/check.py VIDEO WORK OUT_DIR
输出：OUT_DIR/质检报告.md、OUT_DIR/keyframes.jpg、OUT_DIR/waveform.png
"""
import difflib, json, os, re, subprocess, sys
import numpy as np, cv2, soundfile as sf
from scipy.signal import resample_poly
from PIL import Image, ImageDraw

video, work, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
tl = json.load(open(os.path.join(work, 'timeline.json')))
R = ['# 质检报告', '', f'文件：`{os.path.basename(video)}`', '']
ok_all = True


def item(name, ok, detail):
    global ok_all
    ok_all &= bool(ok)
    R.append(f"- {'✅' if ok else '❌'} **{name}**：{detail}")


# ---------------------------------------------------------------- 规格
pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', video],
                               capture_output=True, text=True).stdout)
v = next(s for s in pr['streams'] if s['codec_type'] == 'video')
a = next(s for s in pr['streams'] if s['codec_type'] == 'audio')
dur = float(pr['format']['duration']); size = int(pr['format']['size'])
R.append('## 规格')
item('分辨率', (v['width'], v['height']) == (1080, 1920), f"{v['width']}×{v['height']}（9:16）")
item('视频编码', v['codec_name'] == 'h264', f"{v['codec_name']} {v.get('profile', '')}，{v['pix_fmt']}，{v['r_frame_rate']} fps")
item('音频编码', a['codec_name'] == 'aac', f"{a['codec_name']} {a['sample_rate']}Hz {a['channels']} 声道")
item('时长', abs(dur - tl['dur']) < 0.5, f'{dur:.2f} 秒（时间线 {tl["dur"]:.2f} 秒）；文件 {size / 1e6:.1f} MB')

# ---------------------------------------------------------------- 黑场 / 冻结
R += ['', '## 画面']
bd = subprocess.run(['ffmpeg', '-i', video, '-vf', 'blackdetect=d=0.5:pix_th=0.04', '-an', '-f', 'null', '-'],
                    capture_output=True, text=True).stderr
blacks = re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', bd)
allowed = [(0, 1.2), (tl['t_title'] - 0.8, tl['t_title'] + 0.2), (tl['ctx']['t0'] - 2.0, tl['ctx']['t0'] + 0.6), (tl['dur'] - 2.5, tl['dur'] + 1)]
bad = [(float(s), float(e)) for s, e in blacks if not any(lo <= float(s) and float(e) <= hi for lo, hi in allowed)]
item('黑场', not bad, f"检测到 {len(blacks)} 段 ≥0.5 秒的暗场，均位于设计的转场/片尾处" if not bad else f'意外黑场：{bad}')

# ---------------------------------------------------------------- 音频
R += ['', '## 声音']
raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', video, '-ac', '2', '-ar', '48000', '-f', 'f32le', '-'], capture_output=True).stdout
x = np.frombuffer(raw, np.float32).reshape(-1, 2)
SR = 48000
eb = subprocess.run(['ffmpeg', '-nostats', '-i', video, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
I = float(re.search(r'I:\s+(-?[\d.]+) LUFS', eb.split('Summary')[-1]).group(1))
tp = float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', eb.split('Summary')[-1]).group(1))
item('整体响度', -17.5 <= I <= -14.5, f'{I:.1f} LUFS（目标 -16）')
item('真峰值', tp <= -1.0, f'{tp:.1f} dBTP')
clip = int((np.abs(x) > 0.999).sum())
item('削波', clip == 0, f'{clip} 个满幅采样点')
# 短时响度突变（3 秒窗）
st = []
for line in eb.splitlines():
    m = re.search(r't:\s*([\d.]+).*S:\s*(-?[\d.]+)', line)
    if m: st.append((float(m.group(1)), float(m.group(2))))
st = np.array([s for s in st if s[1] > -60])[::10]
d_ = np.diff(st[:, 1])
cont = d_[st[:-1, 1] > -27]                      # 连续内容中的上升（排除停顿后自然起声）
jump = float(cont.max()) if len(cont) else 0.0
onset = [f'{st[i, 0]:.0f}s(+{d_[i]:.1f})' for i in np.where((d_ > 8) & (st[:-1, 1] <= -27))[0]]
item('响度突变', jump < 8, f'连续内容中相邻 1 秒短时响度最大上升 {jump:.1f} LU；停顿后的自然起声：{onset or "无"}')
# 不应出现的长静音（片头前 1 秒与片尾淡出除外）
mono = x.mean(1); f = SR // 10
lev = 20 * np.log10(np.sqrt((mono[:len(mono) // f * f].reshape(-1, f) ** 2).mean(1)) + 1e-9)
sil, run_ = [], 0
for i, l in enumerate(lev):
    run_ = run_ + 1 if l < -65 else 0
    if run_ == 15: sil.append(i / 10 - 1.4)
sil = [s for s in sil if 1.2 < s < tl['dur'] - 2.5]
item('意外静音', not sil, '无 ≥1.5 秒、低于 -65dB 的静音（音频不中断；原声里的句间停顿保留现场底噪）' if not sil else f'静音起点：{sil}')
# 转场音效频谱
sfx_p = os.path.join(work, 'stems', 'sfx.wav')
if os.path.exists(sfx_p):
    s, _ = sf.read(sfx_p); s = s[:, 0]
    P = np.abs(np.fft.rfft(s)) ** 2; fr = np.fft.rfftfreq(len(s), 1 / SR)
    hi = P[fr > 200].sum() / P.sum() * 100
    item('转场音效频段', hi < 0.5, f'200Hz 以上能量占 {hi:.3f}%（主体在 200Hz 以下，无高频 whoosh / 噪声）')
# 原声段无音乐
mus_p = os.path.join(work, 'stems', 'music.wav')
if os.path.exists(mus_p):
    m, _ = sf.read(mus_p); m = m[:, 0]
    q0, q1 = int((tl['qa']['t0'] + 1) * SR), int((tl['qa']['t1'] - 1) * SR)
    mr = 20 * np.log10(np.sqrt((m[q0:q1] ** 2).mean()) + 1e-12)
    item('原始问答期间音乐', mr < -70, f'音乐电平 {mr:.0f} dBFS（原声段不垫音乐）')

# 波形图
img = Image.new('RGB', (2400, 400), (16, 16, 18)); d = ImageDraw.Draw(img)
cols = 2400; step = len(mono) // cols
for i in range(cols):
    seg = mono[i * step:(i + 1) * step]
    pk = float(np.abs(seg).max()) if len(seg) else 0
    d.line([(i, 200 - pk * 190), (i, 200 + pk * 190)], fill=(214, 178, 112))
for s in tl['sections']:
    xx = int(s['t0'] / dur * cols); d.line([(xx, 0), (xx, 400)], fill=(90, 90, 100)); d.text((xx + 3, 4), s['name'][:6], fill=(200, 200, 200))
img.save(os.path.join(out, 'waveform.png'))

# ---------------------------------------------------------------- 字幕 × 声音识别比对
R += ['', '## 字幕与声音同步（语音识别比对）']
try:
    from faster_whisper import WhisperModel
    en = WhisperModel('base.en', device='cpu', compute_type='int8')
    scores = []
    for sub in tl['qa']['subs']:
        a0, a1 = int((sub['t0'] - 0.1) * SR), int((sub['t1'] + 0.1) * SR)
        seg = mono[a0:a1].astype(np.float32)
        seg16 = resample_poly(seg, 1, 3).astype(np.float32)
        txt = ' '.join(s.text for s in en.transcribe(seg16, language='en', beam_size=1)[0])
        A = re.sub(r'[^a-z ]', '', sub['en'].lower()).split(); Bw = re.sub(r'[^a-z ]', '', txt.lower()).split()
        r = difflib.SequenceMatcher(None, A, Bw).ratio()
        scores.append((r, sub['id']))
    scores.sort()
    mean = np.mean([s for s, _ in scores])
    low = [f'{i}({s:.2f})' for s, i in scores if s < 0.5]
    item('原声英文字幕', mean > 0.75 and len(low) <= 3,
         f'{len(scores)} 条字幕在各自时间窗内识别，平均词序列相似度 {mean:.2f}；低于 0.5 的：{low or "无"}')
    zh = WhisperModel('small', device='cpu', compute_type='int8')
    zs, worst = [], []
    for part in ('intro', 'insight', 'summary'):
        for vo in tl[part]['vo']:
            seg = resample_poly(mono[int((vo['t0'] - 0.05) * SR):int((vo['t1'] + 0.1) * SR)], 1, 3).astype(np.float32)
            txt = ''.join(s.text for s in zh.transcribe(seg, language='zh', beam_size=1, initial_prompt='以下是普通话。')[0])
            clean = lambda s: re.sub(r'[^\u4e00-\u9fff0-9a-zA-Z]', '', s)
            r = difflib.SequenceMatcher(None, clean(vo['text']), clean(txt)).ratio()
            zs.append(r); worst.append((r, vo['id'], txt))
    worst.sort()
    item('中文口播识别', np.mean(zs) > 0.8, f'{len(zs)} 句口播平均字符相似度 {np.mean(zs):.2f}；最低 3 句：' +
         '；'.join(f'{i} {r:.2f}「{t[:24]}」' for r, i, t in worst[:3]))
except Exception as e:  # noqa
    item('语音识别比对', False, f'未能运行：{e}')

# ---------------------------------------------------------------- 品牌角标 + 关键帧
R += ['', '## 品牌与关键帧']
cap = cv2.VideoCapture(video)
times = [round(float(x), 1) for x in np.linspace(0.6, tl['end']['t_particles'] - 0.5, 30)] + \
        [tl['end']['t_particles'] + 1.5, tl['end']['t_brand'] + 0.3, tl['end']['t_brand'] + 2.0, tl['end']['t_fade0'] + 0.5]
thumbs, hud_ok = [], []
for t in times:
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); okf, fr_ = cap.read()
    if not okf: continue
    rgb = cv2.cvtColor(fr_, cv2.COLOR_BGR2RGB)
    hud = rgb[30:100, 800:1030].astype(np.float32)
    gold = ((hud[..., 0] > 150) & (hud[..., 0] > hud[..., 2] + 40)).sum()
    blue = ((hud[..., 2] > 150) & (hud[..., 2] > hud[..., 0] + 30)).sum()
    hud_ok.append(gold > 200 and blue > 80 if t < tl['end']['t_fade0'] else True)
    im = Image.fromarray(rgb).resize((270, 480)); ImageDraw.Draw(im).text((6, 460), f'{t:.1f}s', fill=(255, 80, 80))
    thumbs.append(im)
item('右上角品牌角标', all(hud_ok), f'{sum(hud_ok)}/{len(hud_ok)} 个抽样帧检测到金色字样 + 蓝色 logo')
cols_ = 9; rows = (len(thumbs) + cols_ - 1) // cols_
sheet = Image.new('RGB', (270 * cols_, 480 * rows))
for i, im in enumerate(thumbs): sheet.paste(im, ((i % cols_) * 270, (i // cols_) * 480))
sheet.save(os.path.join(out, 'keyframes.jpg'), quality=88)
R += ['', f'关键帧拼图：`keyframes.jpg`；波形：`waveform.png`', '', f"**结论：{'全部通过' if ok_all else '存在未通过项（见上）'}**"]
open(os.path.join(out, '质检报告.md'), 'w').write('\n'.join(R) + '\n')
print('\n'.join(R))
