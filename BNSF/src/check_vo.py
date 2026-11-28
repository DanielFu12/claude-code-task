"""逐句核对录音与脚本（制作宪章 三.4）：离线中文识别（sherpa-onnx Paraformer）回听切好的每一句 WORK/vo/<id>.wav，
把识别文本和脚本朗读文本都转成汉字读音后逐字比对，列出差异处（同音字、英文专名的差异需人工判断）。
ASR_DIR 默认 work/asr/sherpa-onnx-paraformer-zh-small-2024-03-09（GitHub k2-fsa/sherpa-onnx releases）。
python3 src/check_vo.py WORK
"""
import sys, os, re, difflib, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES
from cnnum import to_reading


def norm(s):
    s = to_reading(s)
    return re.sub(r'[^一-鿿a-z]', '', s.lower())


if __name__ == '__main__':
    import sherpa_onnx
    work = sys.argv[1]
    D = os.environ.get('ASR_DIR', os.path.join(work, 'asr', 'sherpa-onnx-paraformer-zh-small-2024-03-09')).rstrip('/') + '/'
    rec = sherpa_onnx.OfflineRecognizer.from_paraformer(paraformer=D + 'model.int8.onnx', tokens=D + 'tokens.txt', num_threads=4)
    tot = 0; worst = []
    for l in LINES:
        wav = os.path.join(work, 'vo', l[0] + '.wav')
        x = np.frombuffer(subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', wav, '-f', 'f32le', '-ac', '1', '-ar', '16000', '-'],
                                         capture_output=True).stdout, np.float32)
        s = rec.create_stream(); s.accept_waveform(16000, x); rec.decode_stream(s)
        ref = norm(l[3] or l[2]); h = norm(s.result.text)
        sm = difflib.SequenceMatcher(None, ref, h, autojunk=False)
        diffs = [(ref[a:b], h[c:d]) for op, a, b, c, d in sm.get_opcodes() if op != 'equal']
        tot += len(diffs); worst.append((sm.ratio(), l[0]))
        print(f'{l[0]}: 相似度 {sm.ratio():.3f}  差异 {len(diffs)}' + ''.join(f'\n    脚本「{r}」 识别「{hh}」' for r, hh in diffs))
    worst.sort()
    print('差异合计', tot, '；最低相似度', ', '.join(f'{i} {r:.3f}' for r, i in worst[:5]))
