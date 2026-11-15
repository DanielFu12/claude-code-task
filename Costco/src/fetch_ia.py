"""第六期实拍影像：Internet Archive 片源（只取画面，不用原声；原声另由 src/cut_sot.py 切）→ work_clips/<name>.mp4（30fps，无音轨）。

片源先下到 work/src_dl/（archive.org 下载会跳转到 dn*.archive.org 存储服务器，会话网络需放行对应主机），
再按下面的时间段切片：只用干净的时段（制作宪章 二.4），按镜头（ffmpeg scene 检测）的边界取，不跨剪辑点；
CROP 裁掉 4:3 画面两侧的黑边、台标、转载水印与字幕条（像素坐标按 1920×1080 片源，低分辨率片源按比例换算）。
片源与时间码写进 assets/media/ia_clips.json。
python3 src/fetch_ia.py
"""
import os, json, subprocess, urllib.parse, urllib.request, concurrent.futures as cf
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'work_clips'); os.makedirs(OUT, exist_ok=True)
DL = os.path.join(ROOT, 'work', 'src_dl'); os.makedirs(DL, exist_ok=True)
ENV = dict(os.environ, http_proxy=os.environ.get('HTTPS_PROXY', os.environ.get('https_proxy', '')))

# 片源: (archive.org 标识, 文件名, 本地文件, 署名)
SRC = {
    'abc': ('youtube-f9Iv_vdO7sw', 'f9Iv_vdO7sw.mp4', '2020_2005.mp4', 'ABC News《20/20》：James Sinegal 与 Costco（2005）'),
    'sol82': ('youtube-3Ui_sFvSgDI', '3Ui_sFvSgDI.webm', 'sol1982.webm', 'CBS 8 圣地亚哥（KFMB News 8）：FedMart 倒闭，记者 Gene Cubbison 采访索尔·普莱斯（1982-04-29）'),
    'fm82': ('youtube-3N94uTwddHE', '3N94uTwddHE.mkv', 'fedmart1982.mkv', 'CBS 8 圣地亚哥：FedMart 奥申赛德店最后几天（1982 年 6 月）'),
    'sol66': ('youtube-7Dwhpeivpes', '7Dwhpeivpes.mp4', 'sol1966.mp4', 'CBS 8 圣地亚哥：索尔·普莱斯接受 Harold Keen 采访（1966-11-07）'),
    'wh91': ('discount-warehouse-stores-report-boston-ma-usa-1991', '1991 Warehouse Stores Report (USA) [Raw].mp4', 'wh1991.mp4',
             'WBZ-TV 波士顿：仓储会员店报道（1991，Costco 段落）'),
    'dj22': ('youtube-A21VQ4AFV5M', 'A21VQ4AFV5M.webm', 'a21v.webm', '2022 年《每日期刊》年度股东会芒格答问（转载片段，只取芒格出镜画面）'),
}
# 裁切（像素，基于 1920×1080）：4:3 画面在 x 240–1680；去掉台标/水印
CROP = {'abc': (250, 0, 1670, 850), 'sol82': (240, 235, 1680, 1080), 'fm82': (240, 235, 1680, 1080), 'sol66': (240, 235, 1680, 1080),
        'wh91': (250, 20, 1670, 1060), 'dj22': (0, 0, 1920, 840)}
CROPC = {'sol_int1': (240, 0, 1490, 1080), 'sol_int2': (240, 0, 1490, 1080), 'sol_int3': (240, 0, 1490, 1080),
         'sol66_cu': (240, 0, 1490, 1080), 'sol66_two': (240, 0, 1490, 1080)}
CLIPS = {   # 名称: (片源, 起点秒, 时长, 画面)
    # ABC 20/20（2005）：Costco 卖场与辛内格尔
    'a_open': ('abc', 24.0, 6.6, '新店开业，辛内格尔在人群里'), 'a_crowd': ('abc', 37.0, 8.0, '开业人潮与购物车'),
    'a_greet': ('abc', 58.2, 8.8, '辛内格尔和员工打招呼'), 'a_tag': ('abc', 90.3, 2.8, '名牌：JIM'),
    'a_phone': ('abc', 100.6, 5.5, '辛内格尔自己接电话'), 'a_hall': ('abc', 115.0, 9.0, '总部走廊'),
    'a_entrance': ('abc', 142.5, 3.6, '仓库入口'), 'a_floor': ('abc', 150.7, 3.1, '仓库全景'),
    'a_bakery': ('abc', 154.6, 2.5, '海鲜区'), 'a_sign': ('abc', 179.9, 2.8, 'Costco 招牌'), 'a_walk': ('abc', 183.0, 2.7, '辛内格尔巡店'),
    'a_lot': ('abc', 187.7, 5.8, '停车场推车'), 'a_aisle': ('abc', 193.8, 3.8, '通道与购物车'), 'a_walk2': ('abc', 208.4, 2.7, '辛内格尔巡店'),
    'a_cans': ('abc', 211.4, 6.4, '整托盘罐头'), 'a_chicken': ('abc', 221.0, 2.3, '烤鸡'), 'a_wine': ('abc', 223.6, 3.4, '葡萄酒'),
    'a_pies': ('abc', 227.3, 6.0, '南瓜派'), 'a_shelf': ('abc', 259.4, 5.3, '辛内格尔检查货架'), 'a_meat': ('abc', 265.0, 5.9, '肉品区'),
    'a_fork': ('abc', 271.2, 6.2, '叉车与整托盘'), 'a_fork2': ('abc', 287.8, 2.0, '叉车'), 'a_bake2': ('abc', 306.6, 8.0, '烘焙员工'),
    'a_office': ('abc', 346.4, 10.0, '朴素的总部办公室'), 'a_fax': ('abc', 356.8, 3.3, '自己发传真'), 'a_desk': ('abc', 360.4, 12.8, '办公桌前打电话'),
    # 1982 圣地亚哥：FedMart 倒闭、对面的 Price Club、索尔·普莱斯
    'fm_ext': ('sol82', 0.3, 5.3, 'FedMart 门店（1982）'), 'fm_ext2': ('sol82', 7.9, 4.5, 'FedMart 停车场（1982）'),
    'pc_int1': ('sol82', 18.5, 2.2, 'Price Club 卖场（1982）'), 'pc_int2': ('sol82', 22.1, 2.3, 'Price Club 卖场（1982）'),
    'pc_int3': ('sol82', 24.6, 2.2, 'Price Club 货架（1982）'),
    'sol_int1': ('sol82', 38.4, 12.0, '索尔·普莱斯（1982）'), 'sol_int2': ('sol82', 96.4, 11.6, '索尔·普莱斯（1982）'),
    'sol_int3': ('sol82', 110.2, 10.2, '索尔·普莱斯（1982）'),
    'fm_check': ('fm82', 8.2, 5.8, 'FedMart 收银台（1982）'), 'fm_front': ('fm82', 2.2, 4.4, 'FedMart 门店（1982）'),
    'fm_bag': ('fm82', 16.2, 5.0, 'FedMart 收银员（1982）'),
    'sol66_cu': ('sol66', 240.0, 14.0, '索尔·普莱斯（1966）'), 'sol66_two': ('sol66', 22.0, 10.0, '索尔·普莱斯接受采访（1966）'),
    # 1991 Costco（波士顿地区；同一报道也拍了 BJ's，只取 Costco 外景之后的段落）
    'w_ext': ('wh91', 124.5, 5.0, 'Costco 仓库外景（1991）'), 'w_aisle': ('wh91', 129.9, 2.2, 'Costco 通道（1991）'),
    'w_bakery': ('wh91', 132.4, 3.5, 'Costco 烘焙区（1991）'), 'w_bake2': ('wh91', 141.9, 3.8, 'Costco 烘焙（1991）'),
    'w_stock': ('wh91', 146.0, 4.2, 'Costco 理货（1991）'),
    # 芒格（2022，只取出镜画面）
    'm_dj1': ('dj22', 15.0, 3.6, '芒格（2022）'), 'm_dj2': ('dj22', 133.5, 9.0, '芒格（2022）'), 'm_dj3': ('dj22', 50.3, 5.0, '芒格（2022）'),
}


def url(src):
    ident, fn = SRC[src][0], SRC[src][1]
    md = json.load(urllib.request.urlopen(f'https://archive.org/metadata/{ident}', timeout=60))
    return f"https://{md['server']}{md['dir']}/" + urllib.parse.quote(fn)


def ensure(src):
    loc = SRC[src][2]
    if loc is None: return url(src)
    p = os.path.join(DL, loc)
    if not (os.path.exists(p) and os.path.getsize(p) > 100000):
        subprocess.run(['curl', '-sSL', '--retry', '4', '-o', p + '.part', url(src)], check=True); os.replace(p + '.part', p)
    return p


def grab(name, srcpath):
    src, t0, d, _ = CLIPS[name]
    out = os.path.join(OUT, name + '.mp4')
    if os.path.exists(out) and os.path.getsize(out) > 50000: return name, 'cached'
    x0, y0, x1, y1 = CROPC.get(name, CROP[src])
    vf = (f"crop=iw*{(x1 - x0) / 1920:.4f}:ih*{(y1 - y0) / 1080:.4f}:iw*{x0 / 1920:.4f}:ih*{y0 / 1080:.4f},"
          "scale='min(1920,iw*2)':-2:flags=lanczos,setsar=1")
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', str(t0), '-i', srcpath, '-t', str(d), '-an', '-r', '30',
                        '-vf', vf, '-c:v', 'libx264', '-preset', 'fast', '-crf', '15', '-pix_fmt', 'yuv420p', out],
                       capture_output=True, text=True, timeout=1800, env=ENV)
    return name, ('ok' if r.returncode == 0 else 'FAIL ' + r.stderr[-300:])


if __name__ == '__main__':
    paths = {s: ensure(s) for s in SRC}
    with cf.ThreadPoolExecutor(4) as ex:
        for name, st in ex.map(lambda n: grab(n, paths[CLIPS[n][0]]), CLIPS): print(name, st, flush=True)
    p = os.path.join(ROOT, 'assets', 'media', 'ia_clips.json')
    m = json.load(open(p)) if os.path.exists(p) else {}
    for k, (src, t0, d, note) in CLIPS.items():
        m[k] = dict(source=SRC[src][3], ia='https://archive.org/details/' + SRC[src][0], start=t0, dur=d, note=note)
    json.dump(m, open(p, 'w'), ensure_ascii=False, indent=1)
