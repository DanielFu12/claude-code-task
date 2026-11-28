"""接口暂不可用时的逐句参考：从正式整篇录音里，按接口返回的逐字时间戳切出缺失句子的参考音频（+ 同名 json）。
用法：python3 src/refs_from_take.py WORK
说明：参考音频只用来给 DTW 定位句子边界；从整篇录音本身切出来，等于直接采用接口给的逐字时间，
之后照常跑 voice_build 的对齐校验和 check_vo 的逐句语音识别。"""
import os, sys, json
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tts_take as T
from script import LINES
import voice_build as VB

work = sys.argv[1]
tp = T.take_path(work)
y, sr = sf.read(tp, dtype='float32')
js = json.load(open(tp[:-4] + '.json'))
mw = VB.map_words(js)
# 接口逐字时间戳个别处偏差近 1 秒：这几处句界改用整篇录音里的停顿正中（离线识别逐段回听确认，见 docs/SOURCES.md 声音部分）
BOUNDS = {"c3z": 201.59, "c3m1": 215.84, "c3m2": 226.47, "c3d": 237.59, "c3g": 251.7, "c3n1": 261.18, "c3a": 268.79, "c3c": 287.64,
          "c3n3": 298.52, "c3n4": 308.38, "c3n5": 320.9, "c3n6": 330.55, "c3n7": 337.33, "c3h": 345.98, "c3n8": 357.87, "c3i": 363.95,
          "c7l": 545.05, "c7m": 555.57}          # src/find_bounds.py 的输出（整篇录音 take_aa06d5cb5c66）
_ord = [l[0] for l in LINES]
CUT = {}
for _i in _ord[1:]:
    _p = _ord[_ord.index(_i) - 1]
    if _p in BOUNDS or _i in BOUNDS: CUT[_i] = (BOUNDS[_p] + 0.03 if _p in BOUNDS else None, BOUNDS[_i] - 0.03 if _i in BOUNDS else None)
n = 0
order = [l[0] for l in LINES]
first = {k: [w for w in v if w[0] != 'miss'][0][1] for k, v in mw.items() if [w for w in v if w[0] != 'miss']}
last = {k: [w for w in v if w[0] != 'miss'][-1][2] for k, v in mw.items() if [w for w in v if w[0] != 'miss']}
for l in LINES:
    rp = T.ref_path(work, l)
    if os.path.exists(rp): continue
    ws = [w for w in mw[l[0]] if w[0] != 'miss']
    miss = [w for w in mw[l[0]] if w[0] == 'miss']
    assert ws and not miss, (l[0], miss)
    i = order.index(l[0])
    prev_end = last[order[i - 1]] if i > 0 else 0.0
    next_st = first[order[i + 1]] if i + 1 < len(order) else len(y) / sr
    a = max(ws[0][1] - 0.12, (prev_end + ws[0][1]) / 2, 0); b = min(ws[-1][2] + 0.12, (ws[-1][2] + next_st) / 2, len(y) / sr)   # 不越过相邻句
    if l[0] in CUT:
        a = CUT[l[0]][0] if CUT[l[0]][0] is not None else a
        b = CUT[l[0]][1] if CUT[l[0]][1] is not None else b
    sf.write(rp, y[int(a * sr):int(b * sr)], sr, subtype='PCM_16')
    s = T.spoken(l)
    words = [{'word': s[j:j + 1] if isinstance(j, int) else '', 'startTime': round(t0 - a, 4), 'endTime': round(t1 - a, 4)} for j, t0, t1 in ws]
    # 用原 json 里的词（英文词可能多字），按起点对回
    src_words = [w for x in js for w in x['words']]
    starts = {round(w['startTime'], 4): w for w in src_words}
    words = [{'word': starts.get(round(t0, 4), {'word': s[j]})['word'], 'startTime': round(t0 - a, 4), 'endTime': round(t1 - a, 4)} for j, t0, t1 in ws]
    json.dump([{'text': s, 'words': words}], open(rp[:-4] + '.json', 'w'), ensure_ascii=False)
    n += 1; print('ref ←', l[0], f'{a:.2f}–{b:.2f}')
print('made', n)
