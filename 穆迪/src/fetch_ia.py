"""第二季第一期（穆迪）实拍影像：Internet Archive 片源（只取画面，不用原声）→ work_clips/<name>.mp4（30fps，无音轨）。

片源先下到 work/src_dl/，再按下面的时间段切片：只用干净的时段（制作宪章 二.4），按镜头（ffmpeg scene 检测）的边界取，不跨剪辑点；
宣传片里一闪而过的快切（每个镜头不到 1 秒）整段取原剪辑，按原速播放，不单独放慢。
片源与时间码写进 assets/media/ia_clips.json。
python3 src/fetch_ia.py
"""
import os, json, subprocess, urllib.parse, urllib.request, concurrent.futures as cf
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'work_clips'); os.makedirs(OUT, exist_ok=True)
DL = os.path.join(ROOT, 'work', 'src_dl'); os.makedirs(DL, exist_ok=True)

# 片源: (archive.org 标识, 文件名, 本地文件, 署名)
SRC = {
    'freight': ('loc-film-00694211-freight-train', '00047124.ia.mp4', 'lc_freight.mp4', '《Freight Train》（爱迪生公司，1898，美国国会图书馆，公有领域）'),
    'helena': ('loc-film-00694263-overland-express-arriving-at-helena-mont', '01202782.ia.mp4', 'lc_helena.mp4',
               '《Overland Express Arriving at Helena, Mont.》（爱迪生公司，1897，美国国会图书馆，公有领域）'),
    'elev': ('loc-film-00694393-elevated-railroad-new-york', '01870081.ia.mp4', 'lc_elev.mp4', '《Elevated Railroad, New York》（1903，美国国会图书馆，公有领域）'),
    'cx': ('0552_Work_of_the_Stock_Exchange_10_39_27_00', '0552_Work_of_the_Stock_Exchange_10_39_27_00_3mb.mp4', 'nyse1941.mp4',
           '《Work of the Stock Exchange》（1941，芝加哥证券交易所，Prelinger Archives）'),
    'vista': ('0803_Vista_Stock_Shots_New_York_Stock_Exchange_13_00_55_00', '0803_Vista_Stock_Shots_New_York_Stock_Exchange_13_00_55_00.mp4', 'nyse_vista.mp4',
              '《Vista Stock Shots: New York Stock Exchange》（纽约证券交易所资料片，Prelinger Archives）'),
    'rail42': ('GreatRai1942', 'GreatRai1942.mp4', 'greatrail.mp4', '《A Great Railroad at Work》（1942，Prelinger Archives，公有领域）'),
}
OFFSET = {}
PART = {}
CROP = {'freight': (0.06, 0.0, 0.94, 1.0), 'helena': (0.06, 0.0, 0.94, 1.0), 'elev': (0.06, 0.0, 0.94, 1.0)}   # LOC 片源左右有黑边
CLIPS = {   # 名称: (片源, 起点秒, 时长, 画面)
    'rr_loco': ('freight', 13.2, 9.5, '蒸汽机车牵引货车（1898 年影片）'),
    'rr_cars': ('freight', 24.0, 22.0, '铁路货车（1898 年影片）'),
    'rr_station': ('helena', 13.5, 26.0, '火车进站（1897 年影片）'),
    'rr_elev': ('elev', 15.0, 40.0, '纽约高架铁路（1903 年影片）'),
    'db_book': ('cx', 546.4, 9.0, '邓白氏《参考手册》（1941 年影片）'),
    'bond_cert': ('cx', 266.0, 17.5, '债券凭证（1941 年影片）'),
    'cx_floor': ('cx', 704.0, 18.5, '交易所交易大厅（1941 年影片）'),
    'cx_board': ('cx', 723.0, 18.0, '交易所报价（1941 年影片）'),
    'cx_quote': ('cx', 741.4, 10.4, '交易所报价板（1941 年影片）'),
    'ny_floor': ('vista', 420.0, 80.0, '纽约证券交易所交易大厅（资料片）'),
    'ny_floor2': ('vista', 1130.6, 30.0, '纽约证券交易所交易大厅（资料片）'),
    'ny_ticker': ('vista', 1205.0, 30.0, '纽约证券交易所报价带（资料片）'),
}


def url(src):
    ident, fn = SRC[src][0], SRC[src][1]
    md = json.load(urllib.request.urlopen(f'https://archive.org/metadata/{ident}', timeout=60))
    return f"https://{md['server']}{md['dir']}/" + urllib.parse.quote(fn)


def ensure(src):
    p = os.path.join(DL, SRC[src][2])
    if not (os.path.exists(p) and os.path.getsize(p) > 100000):
        if src in PART:
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', str(PART[src][0]), '-i', url(src), '-t', str(PART[src][1]),
                            '-c', 'copy', '-f', 'mp4', p + '.part'], check=True)
        else:
            subprocess.run(['curl', '-sSL', '--retry', '4', '-o', p + '.part', url(src)], check=True)
        os.replace(p + '.part', p)
    return p


def grab(name, srcpath):
    src, t0, d, _ = CLIPS[name]
    out = os.path.join(OUT, name + '.mp4')
    if os.path.exists(out) and os.path.getsize(out) > 50000: return name, 'cached'
    x0, y0, x1, y1 = CROP.get(name, CROP.get(src, (0, 0, 1, 1)))
    vf = (f"crop=iw*{x1 - x0:.4f}:ih*{y1 - y0:.4f}:iw*{x0:.4f}:ih*{y0:.4f},"
          "scale='min(1920,iw*2)':-2:flags=lanczos,setsar=1")
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', str(t0), '-i', srcpath, '-t', str(d), '-an', '-r', '30',
                        '-vf', vf, '-c:v', 'libx264', '-preset', 'fast', '-crf', '15', '-pix_fmt', 'yuv420p', out],
                       capture_output=True, text=True, timeout=1800)
    return name, ('ok' if r.returncode == 0 else 'FAIL ' + r.stderr[-300:])


if __name__ == '__main__':
    paths = {s: ensure(s) for s in SRC}
    with cf.ThreadPoolExecutor(4) as ex:
        for name, st in ex.map(lambda n: grab(n, paths[CLIPS[n][0]]), CLIPS): print(name, st, flush=True)
    p = os.path.join(ROOT, 'assets', 'media', 'ia_clips.json')
    m = json.load(open(p)) if os.path.exists(p) else {}          # 合并：保留 cut_sot.py 写入的原声与 B-roll 条目
    for k, (src, t0, d, note) in CLIPS.items():
        m[k] = dict(source=SRC[src][3], ia='https://archive.org/details/' + SRC[src][0], start=round(t0 + OFFSET.get(src, 0), 2), dur=d, note=note)
    json.dump(m, open(p, 'w'), ensure_ascii=False, indent=1)
