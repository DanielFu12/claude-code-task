"""第五期实拍影像：从 Internet Archive 取片源（只取画面，不用原声）→ work_clips/<name>.mp4（30fps，无音轨）。

片源先下到 work/src_dl/（按 archive.org metadata 里的存储服务器直连；会话网络需放行对应的 dn*.us.archive.org 主机），
再按下面的时间段切片：只用干净的时段（制作宪章 二.4），CROP 裁掉台标、水印、字幕条与滚动条。
芒格访谈（HBO / KFF）只取 700–800s 一段（2560×1440，带音轨），供 src/cut_sot.py 切原声。
片源与时间码写进 assets/media/ia_clips.json，供画面署名与 docs/SOURCES.md。
python3 src/fetch_ia.py
"""
import os, json, subprocess, urllib.parse, urllib.request, concurrent.futures as cf
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'work_clips'); os.makedirs(OUT, exist_ok=True)
DL = os.path.join(ROOT, 'work', 'src_dl'); os.makedirs(DL, exist_ok=True)
ENV = dict(os.environ, http_proxy=os.environ.get('HTTPS_PROXY', os.environ.get('https_proxy', '')))   # ffmpeg 直连远程片源时走会话代理

# 片源: (archive.org 标识, 文件名, 本地文件, 署名)
SRC = {
    'factory': ('youtube-P5St03dAHoo', 'P5St03dAHoo.webm', 'factory.webm',
                'Business Insider：See’s Candies Makes 26 Million Pounds of Candy Every Year（2018）'),
    'vegas': ('youtube-KqCYdTtXxrI', 'KqCYdTtXxrI.mkv', 'vegas.mkv', 'KVVU 8 News Now：See’s Candies 拉斯维加斯新店（2021）'),
    'news81': ('youtube-bd0bR2eQypE', 'bd0bR2eQypE.webm', 'news1981.webm', 'KFMB News 8 圣地亚哥：1981 年母亲节送礼新闻'),
    'ad88': ('capture-a-6523', 'CaptureA_6523.mp4', 'kiro1988.mp4', 'See’s Candies 电视广告（KIRO-TV 西雅图 1988-02-07 播出录像）'),
    'moreno': ('comvca-Business_Spotlight_See_s_Candy', 'Business_Spotlight_See_s_Candy.HD.mov', 'moreno.mov',
               'City of Moreno Valley：Business Spotlight – See’s Candy（2016）'),
    'bwb': ('youtube-pKWN0YFf_14', 'pKWN0YFf_14.mkv', 'bwb.mkv', 'Becoming Warren Buffett（HBO, 2017）片段'),
    'kid': ('Brzdac1921', 'Brzdąc (1921).mp4', None, '卓别林《寻子遇仙记》The Kid（1921，美国公有领域）'),
    'munger': ('youtube-F6s2HAzMeL0', 'F6s2HAzMeL0.webm', None, 'Kunhardt Film Foundation：HBO《Becoming Warren Buffett》芒格访谈'),
}
# 裁切（相对比例 x0, y0, x1, y1）：去掉水印 / 台标 / 字幕 / 滚动条
CROP = {'factory': (0.06, 0.13, 0.94, 0.80), 'vegas': (0.0, 0.0, 1.0, 0.77), 'news81': (0.15, 0.17, 0.80, 0.98),
        'ad88': (0.06, 0.06, 0.94, 0.94), 'moreno': (0.0, 0.0, 1.0, 1.0), 'bwb': (0.0, 0.0, 1.0, 1.0), 'kid': (0.04, 0.04, 0.96, 0.96)}
CLIPS = {   # 名称: (片源, 起点秒, 时长, 画面)
    # 喜诗工厂（Insider 2018）：避开片中的标题字与字幕
    'f_kettle': ('factory', 2.2, 5.3, '铜锅熬制'), 'f_fondant': ('factory', 15.0, 8.0, '倒出软糖馅'),
    'f_enrober': ('factory', 27.6, 2.3, '巧克力淋面'), 'f_box': ('factory', 44.3, 1.6, '一盒巧克力'),
    'f_line': ('factory', 50.4, 1.6, '淋面流水线'), 'f_rows': ('factory', 59.0, 2.4, '巧克力淋面'), 'f_rows_b': ('factory', 66.4, 2.2, '一排排裹好的巧克力'),
    'f_hands': ('factory', 68.6, 4.0, '手工整理'), 'f_brittle': ('factory', 72.6, 4.0, '花生脆出锅'),
    'f_brittle2': ('factory', 82.4, 7.6, '花生脆摊开'), 'f_workers': ('factory', 90.0, 10.4, '花生脆分切装盘'),
    'f_pack': ('factory', 100.5, 7.5, '装袋'), 'f_boxes': ('factory', 108.2, 5.8, '成箱的糖'),
    'f_coat': ('factory', 120.6, 6.2, '淋面后的巧克力'), 'f_kettle2': ('factory', 132.6, 2.6, '铜锅'),
    'f_dough': ('factory', 141.0, 8.4, '揉制'), 'f_tray': ('factory', 157.3, 2.6, '从盒里挑巧克力'),
    'f_rows2': ('factory', 179.0, 5.4, '成排的巧克力'), 'f_quality': ('factory', 186.8, 1.8, '“Quality Without Compromise”'),
    # 门店
    'v_ext': ('vegas', 21.2, 4.6, '门店外景'), 'v_street': ('vegas', 37.8, 8.8, '街角的喜诗'),
    'v_case': ('vegas', 18.2, 1.5, '柜台'), 'v_choc': ('vegas', 30.3, 1.2, '糖块特写'),
    'v_shelf': ('vegas', 68.4, 2.6, '店内货架'), 'v_wall': ('vegas', 71.0, 2.8, '老照片墙'),
    'v_vintage': ('vegas', 74.0, 1.6, '老照片：早年的喜诗店员'), 'v_clerk': ('vegas', 80.0, 3.2, '店员'),
    'm_box': ('moreno', 5.0, 3.3, '一盒巧克力'), 'm_store': ('moreno', 9.0, 1.6, '黑白格地砖的店堂'),
    'm_case': ('moreno', 14.0, 3.6, '玻璃柜'), 'm_counter': ('moreno', 18.0, 2.1, '顾客在柜台买糖'),
    # 1981 / 1988 档案
    'n_boxes': ('news81', 13.6, 4.6, '1981 年母亲节礼盒'), 'n_shop': ('news81', 18.5, 2.8, '1981 年的喜诗店里'),
    'a_gift': ('ad88', 686.0, 8.6, '1988 年喜诗广告：送礼'), 'a_box': ('ad88', 703.6, 4.4, '1988 年喜诗广告：糖盒与玛丽·喜'),
    # 卓别林 The Kid（1921）：铁盒里挑烟头
    'k_tin': ('kid', 441.6, 15.4, '铁盒里挑烟头'), 'k_light': ('kid', 457.8, 12.0, '挑中一根'),
    # 巴菲特（HBO 纪录片片段）
    'x_bwb_desk': ('bwb', 262, 4, '办公室'), 'x_bwb_office': ('bwb', 316.5, 5.5, '办公室'),
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
    x0, y0, x1, y1 = CROP[src]
    vf = (f"crop=iw*{x1 - x0:.3f}:ih*{y1 - y0:.3f}:iw*{x0:.3f}:ih*{y0:.3f},"
          "scale='min(1920,iw*2)':-2:flags=lanczos,setsar=1")
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', str(t0), '-i', srcpath, '-t', str(d), '-an', '-r', '30',
                        '-vf', vf, '-c:v', 'libx264', '-preset', 'fast', '-crf', '15', '-pix_fmt', 'yuv420p', out],
                       capture_output=True, text=True, timeout=1800, env=ENV)
    return name, ('ok' if r.returncode == 0 else 'FAIL ' + r.stderr[-300:])


if __name__ == '__main__':
    paths = {s: ensure(s) for s in SRC if s != 'munger'}
    mp = os.path.join(DL, 'munger_hd_700.mp4')          # 芒格访谈 700–800s（含“See’s Candy”一节），供 cut_sot.py
    if not os.path.exists(mp):
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', '700', '-i', url('munger'), '-t', '100', '-vf', 'scale=2560:-2:flags=lanczos',
                        '-c:v', 'libx264', '-crf', '14', '-preset', 'fast', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', mp],
                       check=True, env=ENV)
    with cf.ThreadPoolExecutor(4) as ex:
        for name, st in ex.map(lambda n: grab(n, paths[CLIPS[n][0]]), CLIPS): print(name, st, flush=True)
    p = os.path.join(ROOT, 'assets', 'media', 'ia_clips.json')
    m = json.load(open(p)) if os.path.exists(p) else {}
    for k, (src, t0, d, note) in CLIPS.items():
        m[k] = dict(source=SRC[src][3], ia='https://archive.org/details/' + SRC[src][0], start=t0, dur=d, note=note)
    json.dump(m, open(p, 'w'), ensure_ascii=False, indent=1)
