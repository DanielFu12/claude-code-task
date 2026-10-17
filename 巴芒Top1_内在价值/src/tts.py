"""投资启示解说（离线 TTS）+ 整片时间轴。

用法：python3 src/tts.py WORK MODEL_DIR
MODEL_DIR = sherpa-onnx 的 kokoro-multi-lang-v1_1 目录（Kokoro v1.1-zh，中文更自然）。
输出：WORK/vo/*.wav（逐句解说）、WORK/timeline.json

时间轴：0–TITLE 片头标题 → 原始录音（股东提问 + 巴菲特回答）→ 音乐重拍进入“投资启示” → 金句。
"""
import json, os, sys
import numpy as np, soundfile as sf
import sherpa_onnx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import NARRATION, SAY, VOICE_ID, VOICE_SPEED

SR = 24000
TITLE = 5.0          # 片头标题时长；提问在其后 0.5 秒开始
ORIG_PAD = (0.5, 0.6)  # 原声片段在第一句前 / 最后一句后多留的时长
LESSON_GAP = 0.9     # 原声结束 → 音乐重拍（投资启示开始）
VO_DELAY = 0.9       # 音乐重拍 → 第一句解说


def engine(d):
    d = d.rstrip('/') + '/'
    k = sherpa_onnx.OfflineTtsKokoroModelConfig(
        model=d + 'model.onnx', voices=d + 'voices.bin', tokens=d + 'tokens.txt',
        data_dir=d + 'espeak-ng-data', dict_dir=d + 'dict',
        lexicon=d + 'lexicon-us-en.txt,' + d + 'lexicon-zh.txt')
    cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(kokoro=k, num_threads=4),
                                       rule_fsts=d + 'phone-zh.fst,' + d + 'date-zh.fst,' + d + 'number-zh.fst')
    return sherpa_onnx.OfflineTts(cfg)


def trim(x, thr=0.006, pad=0.03):
    """去掉首尾静音，保留 30ms"""
    env = np.convolve(np.abs(x), np.ones(240) / 240, 'same')
    idx = np.where(env > thr)[0]
    if not len(idx): return x
    return x[max(idx[0] - int(pad * SR), 0):min(idx[-1] + int(pad * SR), len(x))]


def main():
    work, model = sys.argv[1], sys.argv[2]
    os.makedirs(os.path.join(work, 'vo'), exist_ok=True)
    cues = json.load(open(os.path.join(work, 'orig_cues.json')))
    clip_in, clip_out = cues[0]['s'] - ORIG_PAD[0], cues[-1]['e'] + ORIG_PAD[1]
    off = TITLE + 0.5 - cues[0]['s']                   # 片段时间 + off = 成片时间
    items = [dict(id=c['id'], part=c['part'], lang='orig', en=c['en'], zh=c['zh'],
                  start=round(c['s'] + off, 3), end=round(c['e'] + off, 3)) for c in cues]
    orig_end = clip_out + off
    lesson_at = orig_end + LESSON_GAP
    tts = engine(model)
    t = lesson_at + VO_DELAY
    for cid, part, zh, en, pause in NARRATION:
        text = SAY.get(cid, zh).replace('“', '').replace('”', '')
        x = trim(np.asarray(tts.generate(text, sid=VOICE_ID, speed=VOICE_SPEED).samples, np.float32))
        sf.write(os.path.join(work, 'vo', cid + '.wav'), x, SR)
        d = len(x) / SR
        items.append(dict(id=cid, part=part, lang='zh', en=en, zh=zh, start=round(t, 3), end=round(t + d, 3)))
        print('%-3s %5.2fs  %s' % (cid, d, zh), flush=True)
        t += d + pause
    json.dump(dict(items=items, title_end=TITLE, clip_in=round(clip_in, 3), clip_out=round(clip_out, 3),
                   off=round(off, 3), orig_end=round(orig_end, 3), lesson_at=round(lesson_at, 3)),
              open(os.path.join(work, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
    print('original %.2f–%.2fs, lesson at %.2fs, narration ends %.2fs' % (TITLE + 0.5 - ORIG_PAD[0], orig_end, lesson_at, t))


if __name__ == '__main__':
    main()
