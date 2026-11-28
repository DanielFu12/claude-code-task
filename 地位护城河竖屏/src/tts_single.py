"""整篇一次合成（单条录音，没有任何接缝）+ 多条候选择优 + 只修残余的小幅音高漂移。
为什么这样做：整篇一次合成语流最自然，但 Seed-TTS 长录音可能越讲越“紧”（音高上爬）。
漂移程度每次合成都不同，所以：
  1. 整篇合成 N 条完整录音（同音色、同语速，按候选号缓存）；
  2. 每条按逐字时间戳切句，逐句用 Praat 测音高，算 60 秒滑窗中位数的范围与线性斜率；同时看谐噪比、响度随时间的变化；
  3. 选漂移最小的一条；残余漂移只做 ≤1.5 个半音的平滑修正（PSOLA，修正量小时不损音质）；响度做慢速拉平（±2 dB 内）；
  4. 输出与 tts_take.py 相同的 WORK/vo/<id>.wav、WORK/vo.json，并写 WORK/vo_report.json（单段，供 voice_qc 使用）。
python3 src/tts_single.py WORK [N=6]
"""
import sys, os, json, hashlib, subprocess
from concurrent.futures import ThreadPoolExecutor
import numpy as np, soundfile as sf, parselmouth
from parselmouth.praat import call
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, SPEED
from tts import synth
from tts_chunks import split_lines, TXT

WORK = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 6
VO = os.path.join(WORK, 'vo'); TK = os.path.join(WORK, 'vo_takes'); os.makedirs(VO, exist_ok=True); os.makedirs(TK, exist_ok=True)
KC = float(os.environ.get('KC', '1.0')); CAP = float(os.environ.get('CAP', '2.0'))
SR = 48000; IDS = [l[0] for l in LINES]; TEXT = ''.join(TXT[i] for i in IDS)


def take(k):
    h = hashlib.md5((TEXT + '|%s|full|%d' % (SPEED, k)).encode()).hexdigest()[:12]
    mp3 = os.path.join(TK, h + '.mp3'); js = mp3.replace('.mp3', '.json'); wav = mp3.replace('.mp3', '.wav')
    def complete():
        if not (os.path.exists(js) and os.path.exists(mp3)): return False
        w = json.load(open(js)); got = sum(len(x[0]) for x in w)
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp3],
                                   capture_output=True, text=True).stdout or 0)
        return got >= 0.97 * len(TEXT) and dur > len(TEXT) / 9.0
    for _ in range(0 if os.environ.get('NOSYN') else 2):
        if complete(): break
        for f in (mp3, js, wav):
            if os.path.exists(f): os.remove(f)
        try: json.dump(synth(TEXT, mp3, voice_settings={'speed': SPEED}), open(js, 'w'), ensure_ascii=False)
        except Exception as e: print('retry', k, e, file=sys.stderr)
    if not complete():
        print('跳过不完整的 take #%d' % k, file=sys.stderr); return None
    if not os.path.exists(wav): subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', mp3, '-ac', '1', '-ar', str(SR), wav], check=True)
    return wav, json.load(open(js))


def line_pitch(seg, sr):
    """逐句音高：自相关法（70–260 Hz），取 20–80 分位之间的几何平均。
    （原来的 cc 法 + 中位数在对照测试里不可靠：整句移 −2 半音，测出来却是 +0.6）"""
    p = call(parselmouth.Sound(seg, sr), 'To Pitch', 0.01, 70, 260).selected_array['frequency']; p = p[p > 0]
    if len(p) < 10: return np.nan
    lo, hi = np.percentile(p, [20, 80]); return float(np.exp(np.mean(np.log(p[(p >= lo) & (p <= hi)]))))


def analyse(wav, words):
    y, sr = sf.read(wav); parts = split_lines(y, sr, words, IDS)
    t = 0.0; rows = []
    for lid in IDS:
        seg, meta = parts[lid]; rows.append((t + meta['dur'] / 2, line_pitch(seg, sr), float(np.sqrt(np.mean(seg ** 2)) + 1e-9))); t += meta['dur']
    T = np.array([r[0] for r in rows]); F = np.array([r[1] for r in rows]); R = np.array([r[2] for r in rows])
    st = 12 * np.log2(F / np.nanmedian(F))
    win = [np.nanmedian(st[(T >= a) & (T < a + 60)]) for a in np.arange(0, T[-1] - 20, 30)]
    ok = np.isfinite(st); slope = np.polyfit(T[ok] / 60, st[ok], 1)[0]
    snd = parselmouth.Sound(y, sr); dur = snd.duration
    hnr = [call(call(snd.extract_part(a, min(a + 60, dur)), 'To Harmonicity (cc)', 0.01, 75, 0.1, 1.0), 'Get mean', 0, 0) for a in np.arange(0, dur - 20, 60)]
    return dict(parts=parts, T=T, st=st, rms=R, range=float(np.nanmax(win) - np.nanmin(win)), slope=float(slope), hnr=hnr, f0=float(np.nanmedian(F)), dur=dur)


def smooth_correct(y, sr, T, st, k=0.9, cap=1.5):
    """按逐句音高的慢趋势（±40 秒滑动中位数）做 PSOLA 修正，单点修正量限制在 cap 个半音以内"""
    WN = float(os.environ.get('WIN', '40')); tr = np.array([np.nanmedian(st[(T >= x - WN) & (T <= x + WN)]) for x in T])
    corr = np.clip(-k * tr, -cap, cap)
    snd = parselmouth.Sound(y, sr); man = call(snd, 'To Manipulation', 0.01, 60, 300); pt = call(man, 'Extract pitch tier')
    n = call(pt, 'Get number of points'); pts = [(call(pt, 'Get time from index', i), call(pt, 'Get value at index', i)) for i in range(1, n + 1)]
    call(pt, 'Remove points between', 0, snd.duration + 1)
    for tt, f in pts: call(pt, 'Add point', tt, f * 2 ** (np.interp(tt, T, corr) / 12))
    call([man, pt], 'Replace pitch tier'); z = call(man, 'Get resynthesis (overlap-add)').values[0]
    return z * (np.sqrt(np.mean(y ** 2)) / (np.sqrt(np.mean(z ** 2)) + 1e-12)), float(np.max(np.abs(corr)))


def shift_line(y, sr, d):
    """一句话整体移 d 个半音（PSOLA，保持时长与响度）"""
    snd = parselmouth.Sound(y, sr); man = call(snd, 'To Manipulation', 0.01, 60, 300); pt = call(man, 'Extract pitch tier')
    call(pt, 'Multiply frequencies', 0, snd.duration + 1, 2 ** (d / 12))
    call([man, pt], 'Replace pitch tier'); z = call(man, 'Get resynthesis (overlap-add)').values[0]
    z = z[:len(y)] if len(z) >= len(y) else np.pad(z, (0, len(y) - len(z)))
    return z * (np.sqrt(np.mean(y ** 2)) / (np.sqrt(np.mean(z ** 2)) + 1e-12))


if __name__ == '__main__':
    with ThreadPoolExecutor(2) as ex: takes = [x for x in ex.map(take, range(N)) if x]
    N = len(takes); res = []
    for k, (wav, words) in enumerate(takes):
        a = analyse(wav, words); res.append(a)
        print('take %d  时长 %5.1fs  音高中位 %5.1f Hz  60秒窗范围 %.2f 半音  斜率 %+.2f 半音/分  HNR/分 %s' %
              (k, a['dur'], a['f0'], a['range'], a['slope'], ' '.join('%.1f' % h for h in a['hnr'])))
    def resid(a):
        # 预估修正后的残余：逐句音高加上（受 CAP 限制的）趋势修正量，再算 60 秒窗范围
        WN = float(os.environ.get('WIN', '40')); T_, st_ = a['T'], a['st']
        tr = np.array([np.nanmedian(st_[(T_ >= x - WN) & (T_ <= x + WN)]) for x in T_]); z = st_ + np.clip(-KC * tr, -CAP, CAP)
        w = [np.nanmedian(z[(T_ >= q) & (T_ < q + 60)]) for q in np.arange(0, T_[-1] - 20, 30)]
        return float(np.nanmax(w) - np.nanmin(w))
    for k in range(N): print('take %d 预估修正后范围 %.2f 半音' % (k, resid(res[k])))
    best = min(range(N), key=lambda k: resid(res[k]) + 0.3 * res[k]['range'] / 4 + 0.4 * (max(res[k]['hnr']) - min(res[k]['hnr'])))
    print('选用 take %d' % best)
    wav, words = takes[best]; y, sr = sf.read(wav); a = res[best]
    flat = wav.replace('.wav', '_c.wav')
    # 残余漂移：按逐句音高的慢趋势算出每句的修正量（≤CAP 半音），切句后逐句 PSOLA 移调
    # （整条近 10 分钟的录音一次做 Manipulation，后段的修正会失效，所以改为逐句做）
    WN = float(os.environ.get('WIN', '40'))
    tr = np.array([np.nanmedian(a['st'][(a['T'] >= x - WN) & (a['T'] <= x + WN)]) for x in a['T']])
    corr = np.clip(-KC * tr, -CAP, CAP) if a['range'] > 1.0 else np.zeros(len(IDS))
    print('残余漂移修正：最大 %.2f 半音' % float(np.max(np.abs(corr))))
    # 响度慢速拉平：逐句 RMS 的 ±40 秒趋势，修正限制在 ±2 dB
    db = 20 * np.log10(a['rms']); trd = np.array([np.median(db[(a['T'] >= x - 40) & (a['T'] <= x + 40)]) for x in a['T']])
    g = np.clip(np.median(db) - trd, -2, 2)
    tt = np.arange(len(y)) / sr; y = y * 10 ** (np.interp(tt, a['T'], g) / 20)
    parts = split_lines(y, sr, words, IDS); vo = {}
    for i, lid in enumerate(IDS):
        seg, meta = parts[lid]
        if abs(corr[i]) > 0.02: seg = shift_line(seg, sr, corr[i])
        sf.write(os.path.join(VO, lid + '.wav'), seg.astype(np.float32), sr); vo[lid] = meta
    json.dump(vo, open(os.path.join(WORK, 'vo.json'), 'w'), ensure_ascii=False, indent=0)
    json.dump(dict(mode='single', take=best, report=[[0, IDS[0], IDS[-1], best]]), open(os.path.join(WORK, 'vo_report.json'), 'w'), ensure_ascii=False)
    print('take %d：%.1f 秒，%d 字，%.2f 字/秒' % (best, len(y) / sr, len(TEXT), len(TEXT) / (len(y) / sr)))
