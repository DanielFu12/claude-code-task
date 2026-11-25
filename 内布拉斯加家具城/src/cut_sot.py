"""大师原声（SOT）切片 → 带原声的画面 + 音频。两个片源：
  cnbc        —— 仓库内 CNBC 专访（Squawk Box，2026-07-15，Becky Quick 专访巴菲特），画面只取字幕条以上 1920×752；
  agm94       —— 1994 年伯克希尔股东会录像（archive.org 转载件），介绍经理人环节；裁掉转载水印、烧录字幕与节目条。

· 入出点先按本地语音识别定位（research/CNBC专访_20260715_转写.md），再在附近找能量最低的 60ms 切点，
  前后各留一点空气，0.12s 淡入淡出；画面与声音同一入点，口型同步，原速播放，不变速。
· 画面只取字幕条以上的 1920×752（去掉 CNBC 横条与台标，渲染时再按人物取景放大）。
· 原声只用真实录音，不做任何变声、合成或拼接改词；屏幕上同时给出英文原话与中文翻译。
输出：work_clips/sot_<id>.mp4（含音轨）、WORK/sot/<id>.wav（48k 单声道）、WORK/sot/sot.json（时长与分句时间）
python3 src/cut_sot.py WORK
"""
import os, sys, json, glob, subprocess
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import SOTS

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRCS = {   # 片源: (文件, 文件第 0 秒对应原片的秒数, 画面裁切, 署名, 链接)
    'cnbc': (glob.glob(os.path.join(ROOT, '..', '谷歌', '*CNBC专访*.mp4'))[0], 0.0, 'crop=1920:752:0:0',
             'CNBC Squawk Box：Becky Quick 专访巴菲特（2026-07-15）· 原声',
             'https://www.cnbc.com/2026/07/15/warren-buffett-tells-cnbc-he-initiated-berkshire-hathaways-investment-in-alphabet.html'),
    # 1994 年伯克希尔股东会录像（第三方转载件 archive.org youtube-A2J-_BNkqm8，只取 480–540s 到 work/src_dl/agm1994_480.mp4）：
    # 原始 4:3 画面在 x 195–1725；左上角转载水印、下方烧录字幕与节目条都裁掉，只取 y 170–780
    'agm94': (os.path.join(ROOT, 'work', 'src_dl', 'agm1994_480.mp4'), 480.0, 'crop=1530:610:195:170',
              '1994 年伯克希尔·哈撒韦股东大会录像 · 原声', 'https://archive.org/details/youtube-A2J-_BNkqm8'),
}
BROLL = {'cnbc_two1': (137.3, 9.8, 'CNBC 专访双人景（2026-07-15，无声）'), 'cnbc_two2': (277.7, 8.2, 'CNBC 专访双人景（2026-07-15，无声）')}
WORK = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work')
CLIPS = os.path.join(ROOT, 'work_clips')
SR = 48000


def quiet_point(x, t, span=0.3, win=0.06):
    """t 附近 ±span 内能量最低的 win 窗中心"""
    a, b = int((t - span) * SR), int((t + span) * SR); h = int(win * SR)
    seg = x[a:b]
    e = np.convolve(seg ** 2, np.ones(h) / h, 'valid')
    return (a + int(np.argmin(e)) + h // 2) / SR


def tail_check(sid, y):
    """出点核查（第八期教训）：整段识别会把结尾抢话的主持人吞掉，所以单独识别最后 1.5 秒，
    并看最后 1.2 秒里有没有明显高于讲话人的基频（女声主持人 170–300 Hz）。有问题直接报错，不往下走。"""
    import librosa
    tail = y[-int(1.5 * SR):]
    tmp = os.path.join(WORK, 'sot', f'_tail_{sid}.wav'); sf.write(tmp, tail, SR)
    txt = subprocess.run(['python3', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'asr_en.py'), tmp],
                         capture_output=True, text=True).stdout.strip().split('|')[-1].strip()
    y16 = librosa.resample(y, orig_sr=SR, target_sr=16000)
    f0, _, _ = librosa.pyin(y16, fmin=70, fmax=400, sr=16000, frame_length=1024, hop_length=160)
    body, end = f0[:-120], f0[-120:]
    med = np.nanmedian(body) if np.any(~np.isnan(body)) else 120
    v = end[~np.isnan(end)]; hi = float(np.mean(v > max(170, med * 1.6))) if len(v) else 0.0
    print(f'  出点核查 {sid}：最后 1.5 秒识别为「{txt}」；讲话人基频中位 {med:.0f} Hz，结尾高基频帧占比 {hi:.0%}', flush=True)
    assert hi < 0.25, f'{sid} 结尾疑似混入另一个人的声音（高基频帧 {hi:.0%}），请把出点前移'


if __name__ == '__main__':
    os.makedirs(os.path.join(WORK, 'sot'), exist_ok=True); os.makedirs(CLIPS, exist_ok=True)
    xs = {}
    meta = {}
    for sid, s in SOTS.items():
        SRC, off, crop, _, _ = SRCS[s.get('src', 'cnbc')]
        if SRC not in xs:
            tmp = os.path.join(WORK, 'sot', '_src48_%s.wav' % s.get('src', 'cnbc'))
            if not os.path.exists(tmp):
                subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', SRC, '-vn', '-ac', '1', '-ar', str(SR), tmp], check=True)
            xs[SRC] = sf.read(tmp, dtype='float32')[0]
        x = xs[SRC]
        sp = s.get('span', 0.3)
        a = quiet_point(x, s['in'] - off, sp) if sp > 0 else s['in'] - off
        b = quiet_point(x, s['out'] - off, sp) if sp > 0 else s['out'] - off
        y = x[int(a * SR):int(b * SR)].copy()
        f = int(s.get('fade', 0.12) * SR); y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f)
        sf.write(os.path.join(WORK, 'sot', sid + '.wav'), y, SR)
        # 有声起止（相对切片）
        h = int(0.02 * SR); e = np.array([np.sqrt(np.mean(y[i:i + h] ** 2)) for i in range(0, len(y) - h, h)])
        db = 20 * np.log10(e + 1e-9); on = np.nonzero(db > np.percentile(db, 95) - 30)[0]
        lead, end = on[0] * 0.02, (on[-1] + 1) * 0.02
        # 分句定时：按英文字数比例估计边界，再吸附到最近的停顿（≥80ms 静音）中点
        sil = db < np.percentile(db, 95) - 26; pauses = []; k = 0
        while k < len(sil):
            if sil[k]:
                j = k
                while j + 1 < len(sil) and sil[j + 1]: j += 1
                if (j - k + 1) * 0.02 >= 0.08 and lead < k * 0.02 < end: pauses.append((k + j + 1) / 2 * 0.02)
                k = j + 1
            else: k += 1
        L = [len(e) for e, _ in s['ph']]; cum = np.cumsum(L) / sum(L); bnd = [lead]
        for c in cum[:-1]:
            g = lead + c * (end - lead)
            near = [q for q in pauses if abs(q - g) < 0.7 and q > bnd[-1] + 0.3]
            bnd.append(min(near, key=lambda q: abs(q - g)) if near else g)
        bnd.append(end)
        if 'cuts' in s: bnd = [lead] + list(s['cuts']) + [end]
        phr = [[round(bnd[i], 3), round(bnd[i + 1], 3)] for i in range(len(L))]
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', f'{a:.3f}', '-i', SRC, '-t', f'{b - a:.3f}', '-r', '30',
                        '-vf', crop, '-c:v', 'libx264', '-crf', '14', '-preset', 'fast', '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', '-b:a', '192k', os.path.join(CLIPS, 'sot_' + sid + '.mp4')], check=True)
        meta[sid] = dict(src_in=round(a + off, 3), src_out=round(b + off, 3), len=round(b - a, 3), lead=round(lead, 3), dur=round(end - lead, 3), ph=phr)
        print(sid, meta[sid], flush=True)
        tail_check(sid, y)
    json.dump(meta, open(os.path.join(WORK, 'sot', 'sot.json'), 'w'), ensure_ascii=False, indent=1)
    p = os.path.join(ROOT, 'assets', 'media', 'ia_clips.json')
    m = json.load(open(p)) if os.path.exists(p) else {}
    for sid, v in meta.items():
        _, _, _, nm, url = SRCS[SOTS[sid].get('src', 'cnbc')]
        m['sot_' + sid] = dict(source=nm, ia=url, start=v['src_in'], dur=v['len'], shot='close', note=SOTS[sid]['en'])
    # 无声 B-roll：同一场专访的双人景（主持人在左、巴菲特在右），用在引出原声的旁白下面（不与原声画面重复）
    for nm, (st, d, note) in BROLL.items():
        out = os.path.join(CLIPS, nm + '.mp4')
        if not os.path.exists(out):
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', str(st), '-i', SRCS['cnbc'][0], '-t', str(d), '-an', '-r', '30',
                            '-vf', SRCS['cnbc'][2], '-c:v', 'libx264', '-crf', '15', '-preset', 'fast', '-pix_fmt', 'yuv420p', out], check=True)
        m[nm] = dict(source=SRCS['cnbc'][3].replace(' · 原声', ''), ia=SRCS['cnbc'][4], start=st, dur=d, note=note)
    json.dump(m, open(p, 'w'), ensure_ascii=False, indent=1)
