"""第二季第二期（BNSF）实拍影像：Internet Archive 片源（只取画面，不用原声）→ work_clips/<name>.mp4（30fps，无音轨）。

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
    'cx': ('0552_Work_of_the_Stock_Exchange_10_39_27_00', '0552_Work_of_the_Stock_Exchange_10_39_27_00_3mb.mp4', 'nyse1941.mp4',
           '《Work of the Stock Exchange》（1941，芝加哥证券交易所，Prelinger Archives）'),
    'vista': ('0803_Vista_Stock_Shots_New_York_Stock_Exchange_13_00_55_00', '0803_Vista_Stock_Shots_New_York_Stock_Exchange_13_00_55_00.mp4', 'nyse_vista.mp4',
              '《Vista Stock Shots: New York Stock Exchange》（纽约证券交易所资料片，Prelinger Archives）'),
    'rail42': ('GreatRai1942', 'GreatRai1942.mp4', 'greatrail.mp4', '《A Great Railroad at Work》（1942，Prelinger Archives，公有领域）'),
}
LOCAL = {   # 本系列成片（回顾片段）：(本地路径, 署名)
    'jp': ('../日本五大商社/东京下注_巴菲特与日本五大商社_预览版.mp4', '本系列《东京下注——巴菲特与日本五大商社》成片（需 git lfs pull）'),
}
OFFSET = {}
PART = {}
CROP = {'freight': (0.06, 0.0, 0.94, 1.0), 'helena': (0.06, 0.0, 0.94, 1.0),
        'rail42': (0.02, 0.02, 0.98, 0.97)}          # 1942 年影片：裁掉边缘的胶片磨损
CLIPS = {   # 名称: (片源, 起点秒, 时长, 画面)。1942 年影片只取不带“New Haven”字样的镜头
    'rr_loco': ('freight', 13.2, 9.5, '蒸汽机车牵引货车（1898 年影片）'),
    'rr_cars': ('freight', 24.0, 22.0, '铁路货车（1898 年影片）'),
    'rr_station': ('helena', 13.5, 26.0, '列车驶进蒙大拿州海伦娜（1897 年影片）'),
    'cx_floor': ('cx', 704.0, 18.5, '交易所交易大厅（1941 年影片）'),
    'cx_quote': ('cx', 741.4, 10.4, '交易所报价板（1941 年影片）'),
    'ny_floor': ('vista', 420.0, 80.0, '纽约证券交易所交易大厅（资料片）'),
    'ny_ticker': ('vista', 1205.0, 30.0, '纽约证券交易所报价带（资料片）'),
    'g_smoke': ('rail42', 431.3, 14.0, '编组场里冒烟的蒸汽机车（1942 年影片）'),
    'g_switch': ('rail42', 467.2, 12.2, '一片道岔（1942 年影片）'),
    'g_signal': ('rail42', 797.2, 6.2, '臂板信号机（1942 年影片）'),
    'g_tower': ('rail42', 805.0, 6.5, '列车驶近信号楼（1942 年影片）'),
    'g_pass': ('rail42', 812.6, 5.8, '列车疾驰而过（1942 年影片）'),
    'g_yard': ('rail42', 957.3, 5.4, '编组场（1942 年影片）'),
    'g_yard2': ('rail42', 963.2, 6.8, '编组场里的机车（1942 年影片）'),
    'g_bogie': ('rail42', 993.2, 6.2, '货车转向架（1942 年影片）'),
    'g_yard3': ('rail42', 1047.2, 6.2, '编组场里的货车（1942 年影片）'),
    'g_freight': ('rail42', 1081.0, 19.4, '货运站里堆满的货物（1942 年影片）'),
    'g_shop': ('rail42', 1135.0, 30.0, '机车检修车间（1942 年影片）'),
    'g_wheel': ('rail42', 1235.2, 15.2, '吊装机车动轮（1942 年影片）'),
    'g_wheels2': ('rail42', 1260.2, 7.6, '检修中的机车动轮（1942 年影片）'),
    'g_drive': ('rail42', 1301.0, 7.4, '转动的机车动轮（1942 年影片）'),
    'g_loco': ('rail42', 1310.2, 15.2, '修好的机车驶出车间（1942 年影片）'),
    'g_ballast': ('rail42', 1349.2, 12.2, '铺道砟（1942 年影片）'),
    'g_ties': ('rail42', 1391.2, 17.2, '吊运枕木（1942 年影片）'),
    'g_rails': ('rail42', 1409.2, 6.2, '堆放的枕木（1942 年影片）'),
    'g_diesel': ('rail42', 1473.6, 9.4, '内燃机车牵引货车疾驰（1942 年影片）'),
    's1_japan': ('jp', 432.0, 17.5, '本系列成片片段（日本五大商社：生意分三等）'),
}


def url(src):
    ident, fn = SRC[src][0], SRC[src][1]
    md = json.load(urllib.request.urlopen(f'https://archive.org/metadata/{ident}', timeout=60))
    return f"https://{md['server']}{md['dir']}/" + urllib.parse.quote(fn)


def ensure(src):
    if src in LOCAL: return os.path.join(ROOT, LOCAL[src][0])
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
    paths = {s: ensure(s) for s in list(SRC) + list(LOCAL)}
    with cf.ThreadPoolExecutor(4) as ex:
        for name, st in ex.map(lambda n: grab(n, paths[CLIPS[n][0]]), CLIPS): print(name, st, flush=True)
    p = os.path.join(ROOT, 'assets', 'media', 'ia_clips.json')
    m = json.load(open(p)) if os.path.exists(p) else {}          # 合并：保留 cut_sot.py 写入的原声与 B-roll 条目
    for k, (src, t0, d, note) in CLIPS.items():
        if src in LOCAL: m[k] = dict(source=LOCAL[src][1], ia='', start=t0, dur=d, note=note); continue
        m[k] = dict(source=SRC[src][3], ia='https://archive.org/details/' + SRC[src][0], start=round(t0 + OFFSET.get(src, 0), 2), dur=d, note=note)
    json.dump(m, open(p, 'w'), ensure_ascii=False, indent=1)
