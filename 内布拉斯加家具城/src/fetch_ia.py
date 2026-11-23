"""第七期实拍影像：Internet Archive 片源（只取画面，不用原声；原声另由 src/cut_sot.py 切）→ work_clips/<name>.mp4（30fps，无音轨）。

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
    'bb58': ('0730_Big_Board_The_17_01_01_00', '0730_Big_Board_The_17_01_01_00.mp4', '0730_Big_Board_The_17_01_01_00.mp4',
             '纽约证券交易所宣传片《The Big Board》（1958，Prelinger Archives）'),
    'tc60a': ('dmbb09710', 'dmbb09710.mp4', 'dmbb09710.mp4', '美国运通旅行支票电视广告（1960 年代，Duke University Libraries 广告档案）'),
    'tc60b': ('dmbb09715', 'dmbb09715.mp4', 'dmbb09715.mp4', '美国运通电视广告（1960 年代，Duke University Libraries 广告档案）'),
    'abc': ('youtube-f9Iv_vdO7sw', 'f9Iv_vdO7sw.mp4', '2020_2005.mp4', 'ABC News《20/20》：James Sinegal 与 Costco（2005）'),
    'wh91': ('discount-warehouse-stores-report-boston-ma-usa-1991', '1991 Warehouse Stores Report (USA) [Raw].mp4', 'wh1991.mp4',
             'WBZ-TV 波士顿：仓储会员店报道（1991，Costco 段落）'),
    'tc60c': ('dmbb09713', 'dmbb09713.mp4', 'dmbb09713.mp4', '美国运通旅行支票电视广告（1960 年代，Duke University Libraries 广告档案）'),
    'tc60d': ('dmbb09704', 'dmbb09704.mp4', 'dmbb09704.mp4', '美国运通旅行支票电视广告（1960 年代，Duke University Libraries 广告档案）'),
    'ad88': ('youtube-DGPhXpECU0M', 'DGPhXpECU0M.mp4', 'youtube-DGPhXpECU0M.mp4', '美国运通卡电视广告（1988）'),
    'ad89': ('CLE-B26_396316-397252', '396316_American-Express-Gold-Card-Ad-A&E_1989-07-20.mp4', 'CLE-B26_396316-397252.mp4',
             '美国运通金卡电视广告（A&E，1989-07-20）'),
    'lounge': ('Centurion_Lounge_Opens_at_DFW_Airport', 'Centurion_Lounge_Opens_at_DFW_Airport.HD.mov', 'Centurion_Lounge_Opens_at_DFW_Airport.mov',
               '达拉斯–沃思堡机场电视台（ICTN）：百夫长贵宾厅开业（2018）'),
    'delta': ('Delta_Air_Lines_Debuts_A220_Flights_at_DFW_Airport', 'Delta_Air_Lines_Debuts_A220_Flights_at_DFW_Airport.HD.mov',
              'Delta_Air_Lines_Debuts_A220_Flights_at_DFW_Airport.mov', '达拉斯–沃思堡机场电视台（ICTN）：达美航空 A220 首航（2019）'),
}
# 裁切（像素，基于 1920×1080）：4:3 画面在 x 240–1680；去掉台标/水印
CROP = {'abc': (250, 0, 1670, 850), 'wh91': (250, 20, 1670, 1060), 'tc60c': (0, 0, 1920, 1080), 'tc60d': (0, 0, 1920, 1080), 'bb58': (0, 0, 1920, 1080), 'tc60a': (0, 0, 1920, 1080), 'tc60b': (0, 0, 1920, 1080), 'ad88': (240, 0, 1680, 1080),
        'ad89': (240, 0, 1680, 1080), 'lounge': (0, 0, 1920, 1080), 'delta': (0, 0, 1920, 1080)}
CROPC = {}
CLIPS = {   # 名称: (片源, 起点秒, 时长, 画面)
    'nyse1': ('bb58', 42.1, 6.0, '纽约证券交易所交易大厅（1958）'), 'nyse2': ('bb58', 80.3, 7.9, '交易大厅俯瞰（1958）'),
    'nyse3': ('bb58', 192.0, 4.0, '交易员（1958）'), 'nyse4': ('bb58', 346.2, 3.8, '交易大厅（1958）'),
    'nyse5': ('bb58', 647.0, 6.4, '交易大厅（1958）'), 'nyse_tick': ('bb58', 715.7, 3.3, '报价牌（1958）'),
    'tc_bank': ('tc60a', 11.2, 8.4, '旅行支票广告动画（1960 年代）'), 'tc_sign': ('tc60a', 19.9, 3.0, '旅行支票柜台牌（1960 年代）'),
    'tc_write': ('tc60a', 30.4, 5.8, '在旅行支票上签名（1960 年代）'), 'tc_cheque': ('tc60a', 47.6, 3.3, '旅行支票（1960 年代）'),
    'tc_beach': ('tc60b', 0.5, 10.3, '运通广告动画（1960 年代）'), 'ax_logo60': ('tc60b', 11.2, 2.6, '运通标志（1960 年代广告）'),
    'tc_pisa': ('tc60b', 14.3, 13.3, '运通广告动画：比萨斜塔（1960 年代）'), 'tc_ship': ('tc60b', 27.9, 10.8, '运通广告动画：邮轮（1960 年代）'),
    'ad88_desk': ('ad88', 1.5, 4.5, '机场柜台与运通卡（1988 年广告）'), 'ad88_card': ('ad88', 26.8, 2.6, '运通卡（1988 年广告）'),
    'ad89_city': ('ad89', 3.0, 14.5, '纽约城市天际线（1989 年广告）'), 'ad89_gold': ('ad89', 25.4, 5.6, '运通金卡（1989 年广告）'),
    'lg_front': ('lounge', 20.8, 9.7, '百夫长贵宾厅（2018）'), 'lg_bar': ('lounge', 30.9, 9.0, '百夫长贵宾厅酒吧（2018）'),
    'lg_logo': ('lounge', 83.7, 2.7, '贵宾厅里的运通标志（2018）'), 'lg_seats': ('lounge', 143.2, 6.0, '百夫长贵宾厅（2018）'),
    'lg_wall': ('lounge', 170.5, 6.0, '百夫长贵宾厅（2018）'), 'lg_food': ('lounge', 47.1, 2.3, '贵宾厅餐食（2018）'),
    'dl_plane': ('delta', 101.0, 13.0, '达美航空客机（2019）'), 'dl_dusk': ('delta', 136.6, 7.7, '达美航空客机（2019）'),
    'dl_cabin': ('delta', 32.3, 13.0, '达美航空客舱（2019）'),
    # Costco 段落（与第六期同一批片源与时间码）
    'a_floor': ('abc', 150.7, 3.1, '仓库全景'), 'a_aisle': ('abc', 193.8, 3.8, '通道与购物车'), 'a_lot': ('abc', 187.7, 5.8, '停车场推车'),
    'a_sign': ('abc', 179.9, 2.8, 'Costco 招牌'), 'a_crowd': ('abc', 37.0, 8.0, '开业人潮与购物车'), 'a_entrance': ('abc', 142.5, 3.6, '仓库入口'),
    'a_cans': ('abc', 211.4, 6.4, '整托盘罐头'), 'a_walk': ('abc', 183.0, 2.7, '辛内格尔巡店'), 'a_shelf': ('abc', 259.4, 5.3, '辛内格尔检查货架'),
    'w_ext': ('wh91', 124.5, 5.0, 'Costco 仓库外景（1991）'),
    'tc_hand': ('tc60c', 38.0, 7.4, '在旅行支票上签名（1960 年代广告）'), 'tc_bill': ('tc60d', 20.0, 6.6, '用旅行支票付账（1960 年代广告动画）'),
    'tc_car': ('tc60d', 36.6, 5.4, '带着旅行支票出门（1960 年代广告动画）'), 'tc_logo2': ('tc60d', 46.4, 3.6, '运通标志（1960 年代广告）'),
    'lg_conf': ('lounge', 122.5, 12.0, '百夫长贵宾厅会议室（2018）'), 'lg_family': ('lounge', 154.0, 12.8, '百夫长贵宾厅（2018）'),
    'lg_canape': ('lounge', 51.3, 8.2, '贵宾厅餐点（2018）'), 'lg_window': ('lounge', 14.5, 5.9, '机场航站楼与贵宾厅（2018）'),
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
