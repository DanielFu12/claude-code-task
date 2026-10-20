"""成片字幕在场扫描：每 STEP 秒采样一次字幕带（y 1560–1860）亮度，统计正片段内的字幕空白。
用法: python3 check_subs.py <成片.mp4> [STEP=2]
判定：字幕带中亮度 >150 的像素超过 400 个即视为「有字幕」；片头、章节卡、片尾不计。
"""
import subprocess, sys
import numpy as np
import edl

def main(path, step=2.0):
    items, _, total = edl.load(edl.ASR_DEFAULT)
    clips = [(it['t0'], it['t1']) for it in items if it['kind'] == 'clip']
    Y0, HH = 1560, 300
    p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-i', path, '-vf', f'fps=1/{step}:round=down,crop=1080:{HH}:0:{Y0},format=gray',
                          '-f', 'rawvideo', '-'], stdout=subprocess.PIPE)
    n = 1080 * HH; k = 0; rows = []
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        t = k * step; k += 1
        lit = int((np.frombuffer(b, np.uint8) > 150).sum())
        inclip = any(a + 0.3 <= t <= z - 0.3 for a, z in clips)
        rows.append((t, lit, inclip))
    # 连续空白（只看正片段内的采样点）
    runs, cur = [], []
    for t, lit, inclip in rows:
        if inclip and lit < 400: cur.append(t)
        else:
            if cur: runs.append(cur); cur = []
    if cur: runs.append(cur)
    sampled = sum(1 for r in rows if r[2]); blank = sum(len(r) for r in runs)
    longest = max(runs, key=len) if runs else []
    print(f'采样 {len(rows)} 帧（每 {step:g}s），正片段内 {sampled} 帧，其中无字幕 {blank} 帧')
    print(f'最长连续空白：{len(longest)} 个采样点' + (f'（{longest[0]:.0f}s–{longest[-1]:.0f}s，约 {len(longest) * step:g}s 跨度）' if longest else ''))
    for r in runs: print(f'  空白 {r[0]:7.1f}s ×{len(r)}')
    ok = all(len(r) * step < 6 for r in runs)
    print('结论：', '通过（正片段内无 ≥6 秒的字幕空白）' if ok else '不通过')
    return ok

if __name__ == '__main__':
    sys.exit(0 if main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 2.0) else 1)
