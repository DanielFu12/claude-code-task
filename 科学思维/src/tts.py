"""旁白配音：Kokoro v1.1-zh（sherpa-onnx，离线），逐句合成并用 SenseVoice 语音识别回听校对。

用法：python3 src/tts.py work/ [speaker_id] [speed]
输出：work/vo/<id>.wav（24 kHz 单声道）与 work/vo.json（每句时长、识别结果、字错率）
模型目录由环境变量 TTS_DIR / ASR_DIR 指定（build.sh 会自动下载）。
"""
import difflib
import json
import os
import sys

import numpy as np
import soundfile as sf
import sherpa_onnx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import SECTIONS, tts_text  # noqa: E402

WORK = sys.argv[1]
SID = int(sys.argv[2]) if len(sys.argv) > 2 else 72
SPEED = float(sys.argv[3]) if len(sys.argv) > 3 else 1.08
TTS_DIR = os.environ.get("TTS_DIR", "models/kokoro-multi-lang-v1_1") + "/"
ASR_DIR = os.environ.get("ASR_DIR", "models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09") + "/"
ONLY = set(os.environ.get("ONLY", "").split(",")) - {""}

d = TTS_DIR
tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(
    model=sherpa_onnx.OfflineTtsModelConfig(kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
        model=d + "model.onnx", voices=d + "voices.bin", tokens=d + "tokens.txt",
        data_dir=d + "espeak-ng-data", dict_dir=d + "dict",
        lexicon=d + "lexicon-us-en.txt," + d + "lexicon-zh.txt"), num_threads=4),
    rule_fsts=d + "date-zh.fst," + d + "number-zh.fst"))
rec = sherpa_onnx.OfflineRecognizer.from_sense_voice(
    model=ASR_DIR + "model.int8.onnx", tokens=ASR_DIR + "tokens.txt", use_itn=False, language="zh", num_threads=4)

os.makedirs(os.path.join(WORK, "vo"), exist_ok=True)
meta_p = os.path.join(WORK, "vo.json")
meta = json.load(open(meta_p)) if os.path.exists(meta_p) and ONLY else {}


def han(s):
    return "".join(c for c in s if "一" <= c <= "鿿")


def trim(x, sr, thr=0.012):
    """去掉首尾静音，各留 30 ms。"""
    a = np.abs(x)
    idx = np.nonzero(a > thr)[0]
    if not len(idx):
        return x
    pad = int(0.03 * sr)
    return x[max(0, idx[0] - pad):min(len(x), idx[-1] + pad)]


for sec in SECTIONS:
    for lid, text, _sub, _p in sec[3]:
        if not text or (ONLY and lid not in ONLY):
            continue
        g = tts.generate(tts_text(text), sid=SID, speed=SPEED)
        x = trim(np.asarray(g.samples, np.float32), g.sample_rate)
        sf.write(os.path.join(WORK, "vo", lid + ".wav"), x, g.sample_rate)
        # 回听：16 kHz 识别，算字错率（数字按汉字读法比较时会有出入，人工核对）
        import librosa
        y = librosa.resample(x, orig_sr=g.sample_rate, target_sr=16000)
        s = rec.create_stream()
        s.accept_waveform(16000, y)
        rec.decode_stream(s)
        hyp = s.result.text
        cer = 1 - difflib.SequenceMatcher(None, han(tts_text(text)), han(hyp)).ratio()
        meta[lid] = dict(dur=round(len(x) / g.sample_rate, 3), asr=hyp, cer=round(cer, 3))
        print(f"{lid:4s} {meta[lid]['dur']:6.2f}s cer={cer:.2f} {hyp}", flush=True)

meta["_voice"] = dict(sid=SID, speed=SPEED)
json.dump(meta, open(meta_p, "w"), ensure_ascii=False, indent=1)
print("total speech", round(sum(v["dur"] for k, v in meta.items() if not k.startswith("_")), 1))
