"""局部重渲染：只重画改动过的时间段，拼回已渲染好的分段（work/seg*.mp4），省去整片重渲染。
python3 src/patch_render.py WORK 117.0-143.6 228-257 …     # 时间段（秒）；随后运行 SKIP_RENDER=1 bash render.sh 重新合成成片
每段拆成 4 份并行渲染（竖版、横版同时出）；分段里没改动的部分按帧号截出（重新编码 CRF 17），与新渲染的部分用 concat 无缝拼接。"""
import sys, os, json, subprocess
WORK = sys.argv[1]
FPS, P = 30, 4
N = int(round(json.load(open(os.path.join(WORK, 'timeline.json')))['total'] * FPS)); STEP = (N + P - 1) // P
rngs = sorted((int(float(a) * FPS), int(float(b) * FPS)) for a, b in (r.split('-') for r in sys.argv[2:]))
jobs = []; cmds = []
for i, (a, b) in enumerate(rngs):
    sub = [(a + (b - a) * j // 4, a + (b - a) * (j + 1) // 4) for j in range(4)]
    for j, (x, y) in enumerate(sub):
        out = os.path.join(WORK, f'patch_{i}_{j}.mp4'); jobs.append((i, out))
        cmds.append(['python3', 'src/film.py', WORK, 'chunk', str(x), str(y), out])
running = []                                   # 同时最多 4 个渲染进程（每个进程内存占用大）
for c in cmds:
    while len(running) >= 4:
        for p in running[:]:
            if p.poll() is not None: assert p.returncode == 0; running.remove(p)
        if len(running) >= 4: import time; time.sleep(0.5)
    running.append(subprocess.Popen(c, stdout=subprocess.DEVNULL))
for p in running: assert p.wait() == 0
def enc(src, fa, fb, out):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', src, '-vf', f'trim=start_frame={fa}:end_frame={fb},setpts=PTS-STARTPTS',
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p', out], check=True)
for k, V in [(k, V) for V in ('', '_h') for k in range(P)]:                 # 竖版与横版分段各自拼接
    s0, s1 = k * STEP, min((k + 1) * STEP, N)
    mine = [(i, a, b) for i, (a, b) in enumerate(rngs) if a < s1 and b > s0]
    if not mine: continue
    seg = os.path.join(WORK, f'seg{k}{V}.mp4'); pieces = []; cur = s0
    if not os.path.exists(seg): continue
    for i, a, b in mine:
        assert s0 <= a and b <= s1, '改动段不能跨分段边界'
        if a > cur:
            o = os.path.join(WORK, f'keep_{k}_{cur}{V}.mp4'); enc(seg, cur - s0, a - s0, o); pieces.append(o)
        pieces += [o[:-4] + V + '.mp4' for ii, o in jobs if ii == i]; cur = b
    if cur < s1:
        o = os.path.join(WORK, f'keep_{k}_{cur}{V}.mp4'); enc(seg, cur - s0, s1 - s0, o); pieces.append(o)
    lst = os.path.join(WORK, f'patch_list_{k}{V}.txt')
    open(lst, 'w').write(''.join(f"file '{os.path.abspath(p)}'\n" for p in pieces))
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', seg + '.new.mp4'], check=True)
    n = int(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames',
                            '-of', 'csv=p=0', seg + '.new.mp4'], capture_output=True, text=True).stdout)
    assert n == s1 - s0, (k, n, s1 - s0)
    os.replace(seg + '.new.mp4', seg); print('seg', k, V or '竖版', 'patched', [(a / FPS, b / FPS) for _, a, b in mine], flush=True)
