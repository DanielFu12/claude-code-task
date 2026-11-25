"""逐段语音识别核对整篇录音（本地 Whisper），找漏读、错读。"""
import json, os, sys, difflib
import numpy as np, soundfile as sf, librosa
from faster_whisper import WhisperModel
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work')
segs = json.load(open(os.path.join(WORK, 'vo', 'segments.json')))['segs']
m = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=4)
norm = lambda s: ''.join(c for c in s if c.isalnum())
bad = []
for s in segs:
    y, sr = sf.read(os.path.join(WORK, s['wav']))
    y16 = librosa.resample(y.astype(np.float32), orig_sr=sr, target_sr=16000)
    out, _ = m.transcribe(y16, language="zh", beam_size=5, initial_prompt="以下是普通话的句子，关于巴菲特、芒格和价值投资。")
    got = ''.join(o.text for o in out)
    a, b = norm(s['text']), norm(got)
    r = difflib.SequenceMatcher(None, a, b).ratio()
    miss = len(a) - sum(bl.size for bl in difflib.SequenceMatcher(None, a, b).get_matching_blocks())
    flag = r < 0.85 or miss > 4
    print(f"{s['i']:02d} {r:.2f} miss={miss} {'<<<' if flag else ''}\n  稿: {s['text']}\n  听: {got}")
    if flag: bad.append(s['i'])
print('SUSPECT', bad)
