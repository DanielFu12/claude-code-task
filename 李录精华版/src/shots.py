"""逐镜头分析：检测剪辑点 + 人脸位置 → 每个镜头的 1:1 裁切窗口（竖屏用）。
用法: python3 shots.py <orig.mp4> <yunet.onnx> <asr.json3>   → work/shots.json
原片 1440×1080，有效画面 1440×808（y=136 起，上下黑边）。裁切窗口 808×808，镜头内固定不动。
"""
import json, os, subprocess, sys
import numpy as np, cv2
import edl

AY, AH, AW = 136, 808, 1440          # 有效画面
SW, SH = 192, 108                    # 剪辑点检测用的小图
FW, FH = 640, 359                    # 人脸检测用的图

def frames(src, t0, t1, w, h, fps=None, gray=False):
    vf = f'crop={AW}:{AH}:0:{AY},scale={w}:{h}' + (f',fps={fps}' if fps else '')
    p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-ss', f'{t0:.3f}', '-i', src, '-t', f'{t1 - t0:.3f}',
                          '-vf', vf, '-f', 'rawvideo', '-pix_fmt', 'gray' if gray else 'bgr24', '-'], stdout=subprocess.PIPE)
    n = w * h * (1 if gray else 3)
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield np.frombuffer(b, np.uint8).reshape(h, w) if gray else np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.wait()

def analyze(src, det, t0, t1):
    # 1) 剪辑点：逐帧小图差分
    diffs, prev = [], None
    for f in frames(src, t0, t1, SW, SH, gray=True):
        f = f.astype(np.float32)
        diffs.append(0 if prev is None else float(np.abs(f - prev).mean())); prev = f
    d = np.array(diffs)
    med = np.median(d) + 1e-3
    cuts = [0] + [i for i in range(1, len(d)) if d[i] > max(14, 6 * med) and d[i] == d[max(0, i - 3):i + 4].max()] + [len(d)]
    # 2) 人脸：每秒 3 帧
    faces = []
    for k, f in enumerate(frames(src, t0, t1, FW, FH, fps=3)):
        det.setInputSize((FW, FH))
        r = det.detect(f)[1]
        if r is not None and len(r):
            x, y, w, h = max(r[:, :4].tolist(), key=lambda b: b[2] * b[3])
            faces.append((k / 3, (x + w / 2) * AW / FW, w * AW / FW))
    shots = []
    for a, b in zip(cuts, cuts[1:]):
        ta, tb = a / edl.FPS, b / edl.FPS
        fx = [c for t, c, w in faces if ta + 0.2 <= t < tb - 0.1] or [c for t, c, w in faces if ta <= t < tb]
        cx = float(np.median(fx)) if fx else None
        shots.append(dict(t=round(t0 + ta, 3), cx=cx))
    # 没检测到人脸的镜头沿用相邻镜头的位置（通常是同一机位），否则居中
    for i, s in enumerate(shots):
        if s['cx'] is None:
            near = [shots[j]['cx'] for j in (i - 1, i + 1) if 0 <= j < len(shots) and shots[j]['cx'] is not None]
            s['cx'] = near[0] if near else AW / 2
        s['x0'] = int(np.clip(round(s['cx'] - AH / 2), 0, AW - AH))
    return shots, [(round(t0 + t, 3), round(c, 1), round(w, 1)) for t, c, w in faces]

if __name__ == '__main__':
    src, model, asr = sys.argv[1:4]
    det = cv2.FaceDetectorYN.create(model, '', (FW, FH), 0.7)
    items, _, _ = edl.load(asr)
    out = []
    for it in items:
        if it['kind'] != 'clip': continue
        sh = analyze(src, det, it['src0'], it['src1'])
        out.append(dict(src0=it['src0'], src1=it['src1'], shots=sh[0], faces=sh[1]))
        print(it['ch'], it['src0'], len(sh[0]), 'shots', len(sh[1]), 'faces', flush=True)
    json.dump(out, open(os.path.join(edl.WORK, 'shots.json'), 'w'), indent=0)
