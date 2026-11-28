"""分段合成 + 候选择优：保证全片旁白音色一致。
为什么不用整篇一次合成：Seed-TTS 长录音会越讲越“紧”——5 分钟后音高 +8 个半音、音色（MFCC）明显偏离开头，
后期 PSOLA 拉平音高修不了音色，大幅移调还会让谐噪比从 10.6 掉到 6.9 dB（前后听起来不像同一个人）。
实测每次请求的头 30 秒非常稳定，所以：
  1. 在章节起点和场景转换（句前留白 ≥0.8 秒）处切段，每段 ≤ 约 30 秒；过短的段并入前一段；
  2. 每段独立请求 N 个候选（同音色、同语速），每次都从同样的“起始状态”开口；
  3. 全部候选算音高中位数（三法一致）、音色（MFCC 均值）、语速、谐噪比，选最接近全片基准的一条；
  4. 残余音高偏差只做整体微调（≤1 个半音，PSOLA 常数比例，不改共振峰）；有声部分响度对齐；
  5. 按逐字时间戳切句，输出与 tts_take.py 相同的 WORK/vo/<id>.wav 与 WORK/vo.json。
python3 src/tts_chunks.py WORK [N=3]
"""
import sys, os, json, hashlib, subprocess
from concurrent.futures import ThreadPoolExecutor
import numpy as np, soundfile as sf, librosa, parselmouth
from parselmouth.praat import call
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, BREAK, SPEED
from timeline import CHAPTERS
from tts import synth
from detrend import consensus_f0

WORK = sys.argv[1]; NC = int(sys.argv[2]) if len(sys.argv) > 2 else 3
VO = os.path.join(WORK, 'vo'); CK = os.path.join(WORK, 'vo_chunks'); os.makedirs(VO, exist_ok=True); os.makedirs(CK, exist_ok=True)
SR = 48000
TXT = {l[0]: l[1] for l in LINES}; SUB = {l[0]: (l[2] or l[1]) for l in LINES}


def plan_chunks(maxlen=165, minlen=60):
    chap = {c[0] for c in CHAPTERS}; chunks = []; cur = []; n = 0
    for lid, t, *_ in LINES:
        brk = lid in chap or BREAK.get(lid, 0) >= 0.8
        if cur and (brk or n + len(t) > maxlen):
            chunks.append((cur, lid in chap)); cur = []; n = 0
        cur.append(lid); n += len(t)
    chunks.append((cur, False))
    out = []
    for c, chap_start in chunks:   # 过短的段并入前一段（不跨章节）
        n = sum(len(TXT[i]) for i in c)
        if out and n < minlen and not (c[0] in chap) and sum(len(TXT[i]) for i in out[-1]) + n <= maxlen + 40:
            out[-1] = out[-1] + c
        else: out.append(c)
    return out


def get_candidate(text, k):
    h = hashlib.md5((text + '|%s|%d' % (SPEED, k)).encode()).hexdigest()[:12]
    mp3 = os.path.join(CK, h + '.mp3'); js = mp3.replace('.mp3', '.json'); wav = mp3.replace('.mp3', '.wav')
    def complete():
        if not (os.path.exists(js) and os.path.exists(mp3)): return False
        w = json.load(open(js)); got = sum(len(x[0]) for x in w)
        if got < 0.97 * len(text): return False
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp3],
                                   capture_output=True, text=True).stdout or 0)
        return dur > 0.9 * w[-1][2] and dur > len(text) / 9.0      # 音频没有被截断
    for attempt in range(6):
        if complete(): break
        for f in (mp3, js, wav):
            if os.path.exists(f): os.remove(f)
        try:
            w = synth(text, mp3, voice_settings={'speed': SPEED}); json.dump(w, open(js, 'w'), ensure_ascii=False)
        except Exception as e: print('retry', e, file=sys.stderr)
    if not complete(): raise RuntimeError('候选合成不完整: ' + text[:20])
    if not os.path.exists(wav):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', mp3, '-ac', '1', '-ar', str(SR), wav], check=True)
    return wav, json.load(open(js))


def features(wav):
    cache = wav.replace('.wav', '.feat2.json')
    if os.path.exists(cache):
        d = json.load(open(cache)); d['mfcc'] = np.array(d['mfcc']); return d
    d = _features(wav); json.dump({**d, 'mfcc': d['mfcc'].tolist()}, open(cache, 'w')); return d


def _features(wav):
    y, sr = sf.read(wav); t, f = consensus_f0(y, sr)
    y16 = librosa.resample(y, orig_sr=sr, target_sr=16000)
    S = np.abs(librosa.stft(y16, n_fft=1024, hop_length=320)); rms = librosa.feature.rms(S=S, frame_length=1024)[0]
    v = rms > np.percentile(rms, 45)
    mf = librosa.feature.mfcc(S=librosa.power_to_db(librosa.feature.melspectrogram(S=S ** 2, sr=16000, n_mels=40)), n_mfcc=13)[1:, v].mean(1)
    snd = parselmouth.Sound(y16, 16000)
    hnr = call(call(snd, 'To Harmonicity (cc)', 0.01, 75, 0.1, 1.0), 'Get mean', 0, 0)
    f0 = np.nanmedian(f); hs = f[t < min(6, t[-1] / 3)]; head = np.nanmedian(hs) if np.isfinite(hs).any() else f0
    def med(sel): x = f[sel]; return float(np.nanmedian(x)) if np.isfinite(x).any() else float(f0)
    head3 = med(t < 3.0); tail3 = med((t > t[-1] - 3.4) & (t < t[-1] - 0.2))
    fr = librosa.fft_frequencies(sr=16000, n_fft=1024); P = (S ** 2)[:, v].mean(1)
    tilt = 10 * np.log10(P[(fr >= 60) & (fr < 1000)].sum() / (P[(fr >= 1000) & (fr < 4000)].sum() + 1e-12))   # 发声用力程度
    return dict(f0=float(f0), head=float(head), mfcc=mf, hnr=float(hnr), voiced=float(v.sum() * 0.02), vrms=float(np.median(rms[v])), tilt=float(tilt), head3=head3, tail3=tail3)


def pitch_shift(y, sr, semis):
    snd = parselmouth.Sound(y, sr)
    man = call(snd, 'To Manipulation', 0.01, 60, 300); pt = call(man, 'Extract pitch tier')
    call(pt, 'Multiply frequencies', 0, snd.duration + 1, 2 ** (semis / 12))
    call([man, pt], 'Replace pitch tier')
    z = call(man, 'Get resynthesis (overlap-add)').values[0]
    return z * (np.sqrt(np.mean(y ** 2)) / (np.sqrt(np.mean(z ** 2)) + 1e-12))


def voiced(ch): return ch not in '，。、：；？！“”·,.:;?! '


def split_lines(y, sr, words, lids):
    """按逐字时间戳把一段录音切成句（与 tts_take.py 相同的方法）"""
    text = ''.join(TXT[i] for i in lids)
    seq = []; off = 0.0; last = 0.0
    for w, a, b in words:
        if a + off < last - 0.5: off = last
        seq.append((w, a + off, b + off)); last = max(last, b + off)
    chars = []; k = 0
    for w, a, b in seq:
        for c in w:
            while k < len(text) and text[k] != c: k += 1
            if k < len(text): chars.append((k, c, a, b)); k += 1
    spans = {}; pos = 0
    for lid in lids:
        s, e = pos, pos + len(TXT[lid]); pos = e
        got = {k: (c, a, b) for (k, c, a, b) in chars if s <= k < e}
        cs = []; prev = None
        for kk in range(s, e):
            if kk in got: cs.append(got[kk]); prev = got[kk][2]
            else:
                nxt = next((got[j][1] for j in range(kk + 1, e) if j in got), prev)
                cs.append((text[kk], prev if prev is not None else nxt, prev if prev is not None else nxt))
        vs = [x for x in cs if voiced(x[0])]
        spans[lid] = (vs[0][1], vs[-1][2], cs)
    env = np.convolve(np.abs(y), np.ones(480) / 480, mode='same'); cuts = {}
    for i, lid in enumerate(lids):
        a, b, _ = spans[lid]
        start = max(0.0, a - 0.12) if i == 0 else cuts[lids[i - 1]][1]
        if i + 1 < len(lids):
            na = spans[lids[i + 1]][0]; lo, hi = int(b * sr), int(max(b + 0.02, na - 0.03) * sr)
            end = (lo + int(np.argmin(env[lo:hi]))) / sr if hi > lo else (b + na) / 2
        else: end = min(len(y) / sr, b + 0.45)
        cuts[lid] = (start, end)
    out = {}; fade = int(0.012 * sr)
    for lid in lids:
        s0, s1 = cuts[lid]; seg = y[int(s0 * sr):int(s1 * sr)].copy()
        seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
        a, b, cs = spans[lid]
        out[lid] = (seg, dict(dur=len(seg) / sr, speech=(a - s0, b - s0), text=TXT[lid], sub=SUB[lid],
                              chars=[(c, round(x - s0, 3), round(z - s0, 3)) for c, x, z in cs]))
    return out


if __name__ == '__main__':
    chunks = plan_chunks()
    print('%d chunks: %s' % (len(chunks), [len(''.join(TXT[i] for i in c)) for c in chunks]))
    def text_of(ci): return ''.join(TXT[i] for i in chunks[ci])
    def run(jobs):
        with ThreadPoolExecutor(2) as ex:
            res = list(ex.map(lambda j: get_candidate(text_of(j[0]), j[1]), jobs))
        for j, r in zip(jobs, res): cand[j] = r; feat[j] = features(r[0])
    cand, feat = {}, {}
    run([(ci, k) for ci in range(len(chunks)) for k in range(NC)])
    # 全片基准（第一轮全部候选的中位数，之后固定）：只用与文字内容无关的量
    f0_ref = np.median([feat[j]['f0'] for j in feat]); tilt_ref = np.median([feat[j]['tilt'] for j in feat])
    def rate(j): return sum(1 for c in text_of(j[0]) if voiced(c)) / max(1, feat[j]['voiced'])
    rate_ref = np.median([rate(j) for j in feat])
    def chunk_med(ci):   # 段内典型：同一段文字的全部候选的中位数
        js_ = [j for j in feat if j[0] == ci]
        return np.median([feat[j]['mfcc'] for j in js_], 0), np.median([rate(j) for j in js_])
    def metrics(j):
        F = feat[j]; mm, rm = chunk_med(j[0])
        return (12 * np.log2(F['f0'] / f0_ref), 12 * np.log2(F['head'] / f0_ref), F['tilt'] - tilt_ref,
                float(np.linalg.norm(F['mfcc'] - mm)), rate(j) / rm - 1, F['hnr'])
    def ok(j):
        st, hd, tl, md, rd, hnr = metrics(j)
        return abs(st) <= 0.8 and abs(hd) <= 1.5 and abs(tl) <= 1.5 and md <= 3.0 and abs(rd) <= 0.06
    def score(j):
        st, hd, tl, md, rd, hnr = metrics(j)
        return abs(st) + 0.5 * abs(hd) + 0.4 * abs(tl) + md / 2 + 10 * abs(rd) - 0.1 * hnr
    # 不达标的段继续加候选（最多 10 个）
    for rnd in range(3):
        need = [ci for ci in range(len(chunks)) if not any(ok(j) for j in feat if j[0] == ci)]
        if not need: break
        have = {ci: max(k for (c, k) in feat if c == ci) + 1 for ci in need}
        more = [(ci, have[ci] + k) for ci in need for k in range(2 if rnd < 2 else 1) if have[ci] + k < 10]
        if not more: break
        print('第 %d 轮补充候选：%s' % (rnd + 1, sorted(set(ci for ci, _ in more))))
        run(more)
    # 整体选择（动态规划）：单段得分 + 接缝罚分。接缝 = 本段开头 3 秒音高 − 上一段结尾 3 秒音高（按各自微调后计）
    def shift(j): return float(np.clip(12 * np.log2(f0_ref / feat[j]['f0']), -1.0, 1.0)) if abs(12 * np.log2(f0_ref / feat[j]['f0'])) > 0.35 else 0.0
    def seam(jp, j): return 12 * np.log2(feat[j]['head3'] / feat[jp]['tail3']) + shift(j) - shift(jp)
    def seam_pen(x): return 1.5 * max(0.0, abs(x - 2.0) - 3.0)          # 新段落起调 −1…+5 个半音视为自然
    C = [[j for j in feat if j[0] == ci] for ci in range(len(chunks))]
    def base(j): return score(j) + (0 if ok(j) else 2.0)
    stage = [{j: (base(j), None) for j in C[0]}]                     # stage[ci][j] = (累计代价, 上一段的选择)
    for ci in range(1, len(chunks)):
        prev = stage[-1]; cur = {}
        for j in C[ci]:
            jp = min(prev, key=lambda q: prev[q][0] + seam_pen(seam(q, j)))
            cur[j] = (prev[jp][0] + seam_pen(seam(jp, j)) + base(j), jp)
        stage.append(cur)
    j = min(stage[-1], key=lambda q: stage[-1][q][0]); pick = {}
    for ci in range(len(chunks) - 1, -1, -1):
        pick[ci] = j[1]; j = stage[ci][j][1]
    vr_ref = np.median([feat[(ci, pick[ci])]['vrms'] for ci in pick])
    vo = {}; report = []
    for ci, lids in enumerate(chunks):
        j = (ci, pick[ci]); wav, words = cand[j]; y, sr = sf.read(wav)
        d = 12 * np.log2(f0_ref / feat[j]['f0'])
        if abs(d) > 0.35: y = pitch_shift(y, sr, float(np.clip(d, -1.0, 1.0)))   # 只做 ≤1 个半音的整体微调
        y = y * (vr_ref / feat[j]['vrms'])                                         # 有声部分响度对齐
        for lid, (seg, meta) in split_lines(y, sr, words, lids).items():
            sf.write(os.path.join(VO, lid + '.wav'), seg.astype(np.float32), sr); vo[lid] = meta
        F = feat[j]
        st, hd, tl, md, rd, hnr = metrics(j)
        report.append((ci, lids[0], lids[-1], pick[ci], round(F['f0'], 1), round(st, 2), round(hd, 2), round(tl, 2), round(md, 2),
                       round(rate(j), 2), round(F['hnr'], 1), 'OK' if ok(j) else '未达标', sum(1 for x in feat if x[0] == ci)))
    json.dump({l[0]: vo[l[0]] for l in LINES}, open(os.path.join(WORK, 'vo.json'), 'w'), ensure_ascii=False, indent=0)
    json.dump(dict(f0_ref=float(f0_ref), rate_ref=float(rate_ref), report=report), open(os.path.join(WORK, 'vo_report.json'), 'w'), ensure_ascii=False, indent=1)
    print('ref f0 %.1f Hz, tilt %.1f dB, rate %.2f 字/秒（有声）' % (f0_ref, tilt_ref, rate_ref))
    print('段  起止        选  f0    音高st 开头st 倾斜dB 段内音色 语速  HNR  达标 候选')
    for r in report: print('%2d  %-4s-%-4s  %d  %5.1f  %+.2f  %+.2f  %+.2f  %5.2f  %4.2f  %4.1f  %s  %d' % r)
