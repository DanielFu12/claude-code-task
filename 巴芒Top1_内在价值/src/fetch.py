"""下载原始录音：从 archive.org 的 1994 年股东大会全场录像里只取需要的 280 秒音频。

用法：python3 src/fetch.py WORK
输出：WORK/orig48.wav（48kHz 立体声，成片用）、WORK/orig16.wav（16kHz 单声道，识别用）
ffmpeg 不读 HTTPS_PROXY，需要显式传 -http_proxy；archive.org 支持按区间读取，不必下载整片 1.5GB。
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import ARCHIVE_URL, CLIP_IN, CLIP_LEN

work = sys.argv[1]
proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
base = ['ffmpeg', '-loglevel', 'error', '-y'] + (['-http_proxy', proxy] if proxy else [])
src = os.path.join(work, 'orig_src.m4a')
if not os.path.exists(src):
    subprocess.run(base + ['-ss', str(CLIP_IN), '-i', ARCHIVE_URL, '-t', str(CLIP_LEN), '-vn', '-c:a', 'copy', src], check=True)
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', src, '-ac', '2', '-ar', '48000', os.path.join(work, 'orig48.wav')], check=True)
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', src, '-ac', '1', '-ar', '16000', os.path.join(work, 'orig16.wav')], check=True)
print('fetched', src)
