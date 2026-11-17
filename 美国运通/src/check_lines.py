"""逐句回听（切分后的 work/vo/<id>.wav），只报“脚本有、录音里没有”的连续两字以上缺失——豆包偶尔会漏读半句。
ASR_DIR 同 check_vo.py。 python3 src/check_lines.py WORK
"""
import sys, os, re, difflib, subprocess, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tts_passage import PASSAGES, TEASE_P, spoken
from cnnum import to_reading
SIM = {'它': '他', '她': '他', '得': '的', '地': '的'}


def norm(s):
    s = re.sub(r'[^一-鿿a-z]', '', to_reading(s).lower())
    return ''.join(SIM.get(c, c) for c in s)


if __name__ == '__main__':
    import sherpa_onnx
    D = os.environ['ASR_DIR'].rstrip('/') + '/'
    rec = sherpa_onnx.OfflineRecognizer.from_paraformer(paraformer=D + 'model.int8.onnx', tokens=D + 'tokens.txt', num_threads=4)
    work = sys.argv[1]; bad = []
    for pid, ids, _ in PASSAGES + [TEASE_P]:
        for i in ids:
            y = np.frombuffer(subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', os.path.join(work, 'vo', i + '.wav'), '-f', 'f32le',
                                              '-ac', '1', '-ar', '16000', '-'], capture_output=True).stdout, np.float32)
            s = rec.create_stream(); s.accept_waveform(16000, y); rec.decode_stream(s)
            ref, hyp = norm(spoken(i)), norm(s.result.text)
            sm = difflib.SequenceMatcher(None, ref, hyp, autojunk=False)
            miss = [ref[a:b] for op, a, b, c, d in sm.get_opcodes() if op in ('delete', 'replace') and b - a >= 2 and (op == 'delete' or b - a > d - c + 1)]
            flag = '  ⚠ 缺：' + '、'.join(miss) if miss else ''
            print(f'{i}: {sm.ratio():.3f}{flag}')
            if miss: bad.append(i)
    print('需复听：', bad)
