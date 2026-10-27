"""把整片渲染的分段与局部重渲的片段按帧精确拼成 video_master.mp4（局部修改后不必整片重渲）。

用法：python3 src/assemble.py WORK OUT.mp4 片段1.mp4:起始帧 片段2.mp4:起始帧 …
每个片段从“起始帧”开始覆盖时间线；排在后面的片段优先（用来覆盖前面的整片分段）。
片段的帧数由 ffprobe 读出；拼接用 trim 滤镜按帧切，再统一编码为 crf 14 的中间文件。
"""
import json, os, subprocess, sys

work, out = sys.argv[1], sys.argv[2]
tl = json.load(open(os.path.join(work, 'timeline.json')))
N = tl['nframes']
pieces = []
for arg in sys.argv[3:]:
    path, start = arg.rsplit(':', 1)
    n = int(subprocess.run(['ffprobe', '-v', 'error', '-count_packets', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_packets',
                            '-of', 'csv=p=0', path], capture_output=True, text=True).stdout.strip())
    pieces.append((path, int(start), n))
owner = [-1] * N                      # 每一帧来自哪个片段
for k, (p, s, n) in enumerate(pieces):
    for f in range(s, min(s + n, N)):
        owner[f] = k
assert all(o >= 0 for o in owner), '有帧没有被任何片段覆盖'
runs, f = [], 0
while f < N:
    k = owner[f]; g = f
    while g < N and owner[g] == k: g += 1
    runs.append((k, f, g)); f = g
args = ['ffmpeg', '-loglevel', 'error', '-y']
for p, s, n in pieces:
    args += ['-i', p]
fc = []
for i, (k, a, b) in enumerate(runs):
    s = pieces[k][1]
    fc.append(f'[{k}:v]trim=start_frame={a - s}:end_frame={b - s},setpts=PTS-STARTPTS[v{i}]')
fc.append(''.join(f'[v{i}]' for i in range(len(runs))) + f'concat=n={len(runs)}:v=1:a=0[out]')
args += ['-filter_complex', ';'.join(fc), '-map', '[out]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p', '-r', '30', out]
for k, a, b in runs:
    print(f'  帧 {a:6d}–{b:6d}  ← {os.path.basename(pieces[k][0])}')
subprocess.run(args, check=True)
print('wrote', out)
