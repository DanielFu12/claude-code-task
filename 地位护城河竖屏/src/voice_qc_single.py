"""整条录音旁白的一致性验收：逐句 Praat 音高 → 60 秒滑窗（步长 30 秒）中位数；同时给出每分钟谐噪比、逐句响度趋势。
python3 src/voice_qc_single.py WORK"""
import sys, os, numpy as np, soundfile as sf, parselmouth
from parselmouth.praat import call
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES
WORK = sys.argv[1]; ids = [l[0] for l in LINES]
T = []; F = []; D = []; ys = []; t = 0.0
for lid in ids:
    y, sr = sf.read(os.path.join(WORK, 'vo', lid + '.wav')); ys.append(y)
    p = call(parselmouth.Sound(y, sr), 'To Pitch (cc)', 0.01, 65, 15, 'no', 0.03, 0.45, 0.01, 0.35, 0.14, 240).selected_array['frequency']
    T.append(t + len(y) / sr / 2); F.append(np.median(p[p > 0])); D.append(20 * np.log10(np.sqrt(np.mean(y ** 2)))); t += len(y) / sr
T, F, D = map(np.array, (T, F, D)); st = 12 * np.log2(F / np.median(F))
win = [(a, np.median(st[(T >= a) & (T < a + 60)]), np.median(D[(T >= a) & (T < a + 60)])) for a in np.arange(0, T[-1] - 20, 30)]
print('全片逐句音高中位数 %.1f Hz' % np.median(F))
print('窗口起点  音高st  响度dB')
for a, s, d in win: print('  %4.0fs   %+5.2f   %+5.2f' % (a, s, d - np.median(D)))
snd = parselmouth.Sound(np.concatenate(ys), sr)
hnr = [call(call(snd.extract_part(a, min(a + 60, snd.duration)), 'To Harmonicity (cc)', 0.01, 75, 0.1, 1.0), 'Get mean', 0, 0) for a in np.arange(0, snd.duration - 20, 60)]
s_ = [w[1] for w in win]; d_ = [w[2] for w in win]
print('60 秒窗音高范围 %.2f 半音；斜率 %+.2f 半音/分；窗响度范围 %.2f dB；HNR/分 %s' % (max(s_) - min(s_), np.polyfit(T / 60, st, 1)[0], max(d_) - min(d_), ' '.join('%.1f' % h for h in hnr)))
adj = np.abs(np.diff(st)); print('相邻句音高差：中位 %.2f、90%% 分位 %.2f 半音' % (np.median(adj), np.percentile(adj, 90)))
