"""从 Internet Archive 的原片里按时间段远程截取高清片段（不整片下载）→ work_clips/<name>.mp4（2560×1440，30fps，无音轨）。
片源与时间码记录在 assets/media/ia_clips.json，供片尾与 SOURCES 署名。
python3 src/fetch_ia.py
"""
import os, json, subprocess, urllib.parse, concurrent.futures as cf
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'work_clips'); os.makedirs(OUT, exist_ok=True)
SRC = {
    't34': ('youtube-bIfPgSQiYtw', 'bIfPgSQiYtw.webm', "Tokyo's All 34 main areas in one complete video【4K】（YouTube 存档）"),
    'law': ('youtube-UXD5Tw4_NkM', 'UXD5Tw4_NkM.webm', 'Lawson Japan / Japanese Convenience Store Food in Asakusa（YouTube 存档）'),
    'lng': ('youtube-9KAUYI_eX24', '9KAUYI_eX24.webm', 'The truth about LNG（DW, YouTube 存档）'),
    'mung': ('youtube-F6s2HAzMeL0', 'F6s2HAzMeL0.webm', 'Becoming Warren Buffett：Charlie Munger 访谈（HBO, 2017）'),
    'cine': ('vimeo-160301271', '160301271.mp4', 'In Japan - 2015（Vimeo 存档）'),
    'tsn': ('youtube-wl-QL6jPZUc', 'wl-QL6jPZUc.webm', 'Tokyo, World’s busiest Station On a Rainy Night【4K】（YouTube 存档）'),
    'itc': ('youtube-PEogKMKPchs', 'PEogKMKPchs.webm', 'Negocios TV 2022 日本经济报道（YouTube 存档）'),
}
CLIPS = {   # 名称: (片源, 起点秒, 时长)
    'j_bay': ('t34', 12688, 14), 'j_aerial_river': ('t34', 16140, 12), 'j_aerial_city': ('t34', 16488, 12),
    'j_crossing': ('t34', 3912, 10), 'j_street': ('t34', 226, 10),
    'j_lawson': ('law', 64, 9), 'j_lng_ship': ('lng', 255, 6), 'j_lng_plant': ('lng', 135, 6),
    'x_bwbm_munger': ('mung', 566, 20), 'x_bwbm_munger2': ('mung', 1006, 20),
    'j_cine_aerial': ('cine', 10, 7), 'j_cine_konbini': ('cine', 74, 7), 'j_cine_city': ('cine', 90, 7),
    'j_cine_osaka': ('cine', 98, 7), 'j_cine_miyajima': ('cine', 161, 7), 'j_cine_skyline': ('cine', 178, 7), 'j_cine_train': ('cine', 18, 6),
    'j_night_crossing': ('tsn', 948, 10), 'j_night_towers': ('tsn', 1732, 10), 'j_night_street': ('tsn', 1508, 10), 'j_night_711': ('tsn', 1844, 8),
    'j_tower': ('itc', 47.5, 3.5), 'j_shinkansen': ('itc', 72.5, 4), 'j_commuters': ('itc', 55, 5.5), 'j_taxi': ('itc', 68.5, 3.5),
    'j_market': ('t34', 1610, 10), 'j_evening': ('t34', 5760, 10),
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
