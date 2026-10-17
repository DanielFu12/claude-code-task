"""离线 TTS：按 script.LINES 逐句合成，拼成旁白音轨，并写出时间轴 timeline.json。

用法：python3 src/tts.py WORK MODEL_DIR
MODEL_DIR = sherpa-onnx 的 kokoro-multi-lang-v1_0 目录。
旁白从 START 秒开始；英文原话从 ANSWER_AT（音乐第一个重拍）开始。
"""
import json, os, sys
import numpy as np, soundfile as sf
import sherpa_onnx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, VOICE, SPEED

SR = 24000
START = 1.6          # 第一句旁白
ANSWER_AT = 17.10    # 原曲第一个重拍（见 audio.py），巴菲特原话从这里开始
LEAD = 0.25          # 段落切换时在下一段前多留的空隙


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
    a, b = max(idx[0] - int(pad * SR), 0), min(idx[-1] + int(pad * SR), len(x))
    return x[a:b]


def main():
    work, model = sys.argv[1], sys.argv[2]
    os.makedirs(os.path.join(work, 'vo'), exist_ok=True)
    tts = engine(model)
    clips = []
    for i, (part, lang, en, zh, pause, say) in enumerate(LINES):
        text = say or (zh if lang == 'zh' else en)
        text = text.replace('’', "'").replace('“', '"').replace('”', '"')
        a = tts.generate(text, sid=VOICE[lang], speed=SPEED[lang])
        x = trim(np.asarray(a.samples, np.float32))
        sf.write(os.path.join(work, 'vo', '%02d.wav' % i), x, SR)
        clips.append(x)
        print('%02d %-6s %5.2fs  %s' % (i, part, len(x) / SR, text[:60]), flush=True)
    # 排时间轴
    t = START
    items = []
    for i, ((part, lang, en, zh, pause, say), x) in enumerate(zip(LINES, clips)):
        if i and part != LINES[i - 1][0]:
            t += LEAD
        if lang == 'en' and LINES[i - 1][1] == 'zh':
            assert t <= ANSWER_AT - 0.3, '开场旁白太长：%.2f' % t
            t = ANSWER_AT + 0.35
        d = len(x) / SR
        items.append(dict(i=i, part=part, lang=lang, en=en, zh=zh, start=round(t, 3), end=round(t + d, 3)))
        t += d + pause
    total = int((t + 30) * SR)
    vo = np.zeros(total, np.float32)
    for it, x in zip(items, clips):
        s = int(it['start'] * SR); vo[s:s + len(x)] += x
    peak = np.abs(vo).max()
    vo *= 0.89 / peak
    sf.write(os.path.join(work, 'vo.wav'), vo, SR)
    json.dump(dict(items=items, vo_end=round(t, 3)), open(os.path.join(work, 'timeline.json'), 'w'),
              ensure_ascii=False, indent=1)
    print('narration ends at %.2fs' % t)


if __name__ == '__main__':
    main()
