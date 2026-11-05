"""从 Internet Archive 的原片里按时间段远程截取高清片段（不整片下载）→ work_clips/<name>.mp4（2560×1440，30fps，无音轨）。
片源与时间码记录在 assets/media/ia_clips.json，供片尾与 SOURCES 署名。
python3 src/fetch_ia.py
"""
import os, json, subprocess, urllib.parse, concurrent.futures as cf
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'work_clips'); os.makedirs(OUT, exist_ok=True)
SRC = {
    'wwdc24': ('wwdc24', 'Apple WWDC24 Keynote.mp4', 'Apple WWDC24 Keynote（Apple, 2024）'),
    'park': ('youtube-VbeM8Lf7s5A', 'VbeM8Lf7s5A.webm', 'The Genius Design of Apple Park（Polyphonic / Nebula, 2023）'),
    'bwb': ('youtube-pKWN0YFf_14', 'pKWN0YFf_14.mkv', 'Becoming Warren Buffett（HBO, 2017）片段'),
    'bwbi': ('youtube-cd-w9H0G6nQ', 'cd-w9H0G6nQ.webm', 'Becoming Warren Buffett 访谈（HBO, 2017）'),
    'i6s': ('IPhone6SLaunchUnboxing4k', 'iPhone 6S Launch & Unboxing 4k.mov', 'iPhone 6S Launch & Unboxing（Gear Live, 2015）'),
    'jobs07': ('macworld-san-francisco-2007-keynote-address-steve-jobs-introduces-i-phone-4-k-ai-upscale', None, 'Macworld 2007 Keynote（Apple, 2007；4K AI 修复版）'),
}
CLIPS = {   # 名称: (片源, 起点秒, 时长)
    'x_park_top': ('wwdc24', 78, 12), 'x_cook_roof': ('wwdc24', 98, 14), 'x_park_green': ('wwdc24', 858, 10),
    'x_iphones_wall': ('wwdc24', 898, 10), 'x_iphone_hand': ('wwdc24', 938, 10),
    'x_park_ring1': ('park', 432, 14), 'x_park_ring2': ('park', 612, 16), 'x_park_ring3': ('park', 703, 18),
    'x_park_ring4': ('park', 958, 12), 'x_park_theater': ('park', 733, 10), 'x_jobs_council': ('park', 148, 18),
    'x_bwb_cherrycoke': ('bwb', 166, 7), 'x_bwb_cokestore': ('bwb', 190, 6), 'x_bwb_walk': ('bwb', 184, 6),
    'x_bwb_desk': ('bwb', 262, 12), 'x_bwb_office': ('bwb', 310, 12), 'x_bwb_meeting': ('bwb', 346, 30),
    'x_bwb_arena': ('bwb', 424, 6), 'x_bwbi_a': ('bwbi', 598, 20), 'x_bwbi_b': ('bwbi', 1618, 20), 'x_bwbi_c': ('bwbi', 2338, 20),
    'x_i6s_store': ('i6s', 110, 36), 'x_i6s_unbox': ('i6s', 168, 32),
    'x_jobs07_stage': ('jobs07', 1398, 14), 'x_jobs07_wave': ('jobs07', 2196, 10), 'x_jobs07_hand': ('jobs07', 1518, 10),
}


def grab(name):
    src, t0, d = CLIPS[name]
    ident, fn, _ = SRC[src]
    if fn is None:                                       # 文件名含特殊字符：从元数据里取最高分辨率的 mp4
        import json as _j, urllib.request as _u
        md = _j.load(_u.urlopen(f'https://archive.org/metadata/{ident}', timeout=60))
        fn = max((f for f in md['files'] if f['name'].endswith('.mp4')), key=lambda f: int(f.get('height') or 0))['name']
    out = os.path.join(OUT, name + '.mp4')
    if os.path.exists(out) and os.path.getsize(out) > 100000: return name, 'cached'
    url = f'https://archive.org/download/{ident}/' + urllib.parse.quote(fn)
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', str(t0), '-i', url, '-t', str(d), '-an', '-r', '30',
                        '-vf', "scale='if(gt(iw,ih),-2,1440)':'if(gt(iw,ih),1440,-2)':flags=lanczos", '-c:v', 'libx264', '-preset', 'fast',
                        '-crf', '15', '-g', '30', '-pix_fmt', 'yuv420p', out], capture_output=True, text=True, timeout=1800)
    return name, ('ok' if r.returncode == 0 else 'FAIL ' + r.stderr[-200:])


if __name__ == '__main__':
    meta = {k: dict(source=SRC[v[0]][2], ia='https://archive.org/details/' + SRC[v[0]][0], start=v[1], dur=v[2]) for k, v in CLIPS.items()}
    json.dump(meta, open(os.path.join(ROOT, 'assets', 'media', 'ia_clips.json'), 'w'), ensure_ascii=False, indent=1)
    with cf.ThreadPoolExecutor(4) as ex:
        for name, st in ex.map(grab, CLIPS): print(name, st, flush=True)
