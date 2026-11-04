"""把下载好的视频素材（assets/media/v_*.webm）转成渲染用的 30fps H.264（work_clips/<name>.mp4，长边不超过 1920，去掉音轨）。
python3 src/prep_media.py
"""
import os, glob, subprocess
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
src = os.path.join(ROOT, 'assets', 'media'); dst = os.path.join(ROOT, 'work_clips'); os.makedirs(dst, exist_ok=True)
for f in sorted(glob.glob(os.path.join(src, 'v_*.webm'))):
    name = os.path.basename(f)[:-5]; out = os.path.join(dst, name + '.mp4')
    if os.path.exists(out) and os.path.getmtime(out) > os.path.getmtime(f): continue
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', f, '-an', '-r', '30',
                    '-vf', "scale='if(gt(iw,ih),min(1920,iw),-2)':'if(gt(iw,ih),-2,min(1920,ih))'",
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '16', '-g', '30', '-pix_fmt', 'yuv420p', out], check=True)
    print('ok', name, flush=True)
