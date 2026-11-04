"""离线二选一听辨：用 MMS_FA 声学模型分别计算“正确说法 / 可疑说法”整句文本的 CTC 负对数似然，低者为实际读法。
python3 src/ab_local.py WORK [wav_dir]
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from align import model, normalize, romanize
from script import LINES
from ab_check import CHECKS

SAY = {l[0]: (l[3] or l[2]) for l in LINES}


def nll(em, text, tok, torch):
    words = romanize(normalize(text)[0])
    ids = [i for w in tok(words) for i in w]
    lp = torch.log_softmax(em[0], -1)
    tgt = torch.tensor([ids])
    return float(torch.nn.functional.ctc_loss(lp[:, None, :], tgt, torch.tensor([lp.shape[0]]), torch.tensor([len(ids)]),
                                              blank=0, reduction='sum'))


def judge(path, ref, good, bad):
    m, tok, aligner, sr, torch, ta = model()
    y, r = ta.load(path); y = y.mean(0, keepdim=True)
    if r != sr: y = ta.functional.resample(y, r, sr)
    with torch.inference_mode():
        em, _ = m(y)
    a = nll(em, ref, tok, torch); b = nll(em, ref.replace(good, bad, 1), tok, torch)
    return a, b


if __name__ == '__main__':
    work = sys.argv[1]; vdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(work, 'vo')
    for i, good, bad in CHECKS:
        ref = SAY[i]
        if good not in ref: print('skip', i, good); continue
        a, b = judge(os.path.join(vdir, f'{i}.wav'), ref, good, bad)
        print('OK ' if a < b else 'BAD', i, f'{good} {a:.1f}  vs  {bad} {b:.1f}  (差 {b - a:+.1f})', flush=True)
