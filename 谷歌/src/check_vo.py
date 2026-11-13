"""逐段核对录音与脚本（制作宪章 三.3）：离线中文识别（sherpa-onnx Paraformer）回听每段豆包录音，
把识别文本和脚本朗读文本都转成汉字读音后逐字比对，列出差异处。
ASR_DIR 指向 sherpa-onnx-paraformer-zh-small 模型目录（GitHub k2-fsa/sherpa-onnx releases）。
python3 src/check_vo.py WORK
"""
import sys, os, re, difflib, subprocess
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tts_passage import PASSAGES, TEASE_P, spoken
from cnnum import to_reading


def norm(s):
    s = to_reading(s)
    return re.sub(r'[^一-鿿a-z]', '', s.lower())


if __name__ == '__main__':
    import sherpa_onnx
    D = os.environ['ASR_DIR'].rstrip('/') + '/'
    rec = sherpa_onnx.OfflineRecognizer.from_paraformer(paraformer=D + 'model.int8.onnx', tokens=D + 'tokens.txt', num_threads=4)
    work = sys.argv[1]; bad = 0
    for pid, ids, _ in PASSAGES + [TEASE_P]:
        wav = os.path.join(work, 'tts_db', f'{pid}_0.wav')
        y = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', wav, '-f', 'f32le', '-ac', '1', '-ar', '16000', '-'], capture_output=True).stdout
        x = np.frombuffer(y, np.float32)
        hyp = ''
        for k in range(0, len(x), 16000 * 25):          # 25 秒一段送识别
            s = rec.create_stream(); s.accept_waveform(16000, x[k:k + 16000 * 26]); rec.decode_stream(s); hyp += s.result.text
        ref = norm(''.join(spoken(i) for i in ids)); h = norm(hyp)
        sm = difflib.SequenceMatcher(None, ref, h, autojunk=False)
        diffs = [(ref[a:b], h[c:d]) for op, a, b, c, d in sm.get_opcodes() if op != 'equal']
        print(f'{pid}: 相似度 {sm.ratio():.3f}  差异 {len(diffs)}')
        for r, hh in diffs: print('    脚本「%s」 识别「%s」' % (r, hh))
