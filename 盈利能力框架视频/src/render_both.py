"""同时渲染横版与竖版的一个帧区间：python3 src/render_both.py f0 f1 out_h.mp4 out_v.mp4"""
import subprocess, sys, time
import video as V, vertical as VV
f0, f1, oh, ov = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
f1 = min(f1, V.NFR)
def enc(path, w, h):
    return subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}',
                             '-r', '30', '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14',
                             '-pix_fmt', 'yuv420p', '-tune', 'animation', path], stdin=subprocess.PIPE)
ph, pv = enc(oh, 1920, 1080), enc(ov, 1080, 1920)
t0 = time.time()
for f in range(f0, f1):
    ph.stdin.write(V.render(f / 30).tobytes())
    pv.stdin.write(VV.render_v(f / 30).tobytes())
    if (f - f0) % 300 == 0:
        print(f'{f - f0}/{f1 - f0} {(time.time() - t0) / max(f - f0, 1):.3f}s/f', flush=True)
ph.stdin.close(); pv.stdin.close(); ph.wait(); pv.wait()
