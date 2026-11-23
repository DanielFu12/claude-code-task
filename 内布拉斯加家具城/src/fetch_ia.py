"""第八期实拍影像：Internet Archive 片源（只取画面，不用原声）→ work_clips/<name>.mp4（30fps，无音轨）。

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
    'shop': ('tcoltx-The_Colony_Texas_THE_Lake_THE_Golf_THE_Fun_and_THE_Shopping', 'The_Colony_Texas_THE_Lake_THE_Golf_THE_Fun_and_THE_Shopping.HD.mov',
             'colony_shop.mov', '得州 The Colony 市政府旅游宣传片（2015，片中 NFM 得州店段落）'),
    'open': ('tcoltx-NFM_of_Texas_Grand_Opening', 'NFM_of_Texas_Grand_Opening.mp4', 'nfm_tx_open.mp4',
             'The Colony 市政府电视台：NFM 得州店开业典礼（2015-05-07）'),
    'maf': ('tcoltx-The_Colony_-_Moving_America_Forward', 'The_Colony_-_Moving_America_Forward.mp4', 'colony_maf.mp4',
            'The Colony 市政府电视台节目《Moving America Forward》（2014，NFM 得州店效果图）'),
    'carpet': ('carpet_thats_miles_above', 'carpet_thats_miles_above.mp4', 'carpet_thats_miles_above.mp4',
               '地毯宣传片《The Carpet That’s Miles Above》（约 1960，Prelinger Archives，公有领域）'),
    'look': ('6383_American_Look_M04199_01_22_19_00', '6383_American_Look_M04199_01_22_19_00.mp4', '6383_American_Look_M04199_01_22_19_00.mp4',
             '《American Look》（1958，Prelinger Archives）'),
    'europe': ('0963SomewhereInEuropeImmigrationPt1', '0963_Somewhere_In_Europe_Immigration_Pt_1.mp4', '0963SomewhereInEuropeImmigrationPt1.mp4',
               '公民教育片《Somewhere in Europe》（1921，搬演，Prelinger Archives）'),
    'levitz': ('NJY-015_132385-133284', '132385_Clip-Levitz-89th-Anniversary-Columbus-Day-Sale-Ad-FOXKTTV11_1999-10-08.mp4',
               'NJY-015_132385-133284.mp4', 'Levitz 家具电视广告（1999，VHS Vault 录像）'),
}
CROP = {'levitz': (0.04, 0.02, 0.96, 0.70)}          # 名称或片源: (x0, y0, x1, y1)，按 0..1 比例；缺省为整幅（Levitz 广告：裁掉下方促销字幕）
CLIPS = {   # 名称: (片源, 起点秒, 时长, 画面)
    'tx_promo1': ('shop', 274.97, 3.10, 'NFM 得州店外景与卖场（2015）'),
    'tx_promo2': ('shop', 278.82, 3.66, 'NFM 得州店卖场（2015）'),
    'op_crowd': ('open', 42.6, 11.0, 'NFM 得州店开业前的员工（2015-05-07）'),
    'op_flags': ('open', 58.0, 18.0, 'NFM 得州店开业典礼（2015-05-07）'),
    'op_ribbon': ('open', 1262.0, 16.0, 'NFM 得州店开业剪彩（2015-05-07）'),
    'tx_render': ('maf', 396.2, 3.5, 'NFM 得州店效果图（2014）'),
    'cp_room': ('carpet', 127.2, 3.9, '地毯（约 1960 年宣传片）'),
    'cp_sweep': ('carpet', 133.6, 4.2, '地毯（约 1960 年宣传片）'),
    'cp_slipper': ('carpet', 183.4, 4.6, '地毯（约 1960 年宣传片）'),
    'al_living': ('look', 285.5, 10.0, '1950 年代的客厅家具（1958 年影片）'),
    'al_sideboard': ('look', 299.0, 8.5, '1950 年代的家具（1958 年影片）'),
    'al_chair': ('look', 315.0, 4.5, '1950 年代的家具（1958 年影片）'),
    'al_dining': ('look', 328.5, 6.0, '1950 年代的餐桌椅（1958 年影片）'),
    'eu_field': ('europe', 29.9, 14.4, '欧洲乡村（1921 年教育片，搬演）'),
    'eu_ship': ('europe', 247.0, 10.5, '移民船（1921 年教育片，搬演）'),
    'eu_wait': ('europe', 288.0, 16.5, '移民（1921 年教育片，搬演）'),
    'lv_sofa': ('levitz', 13.0, 4.6, 'Levitz 家具广告（1999）'),
    'lv_sofa2': ('levitz', 17.75, 1.7, 'Levitz 家具广告（1999）'),
}


def url(src):
    ident, fn = SRC[src][0], SRC[src][1]
    md = json.load(urllib.request.urlopen(f'https://archive.org/metadata/{ident}', timeout=60))
    return f"https://{md['server']}{md['dir']}/" + urllib.parse.quote(fn)


def ensure(src):
    p = os.path.join(DL, SRC[src][2])
    if not (os.path.exists(p) and os.path.getsize(p) > 100000):
        subprocess.run(['curl', '-sSL', '--retry', '4', '-o', p + '.part', url(src)], check=True); os.replace(p + '.part', p)
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
    m = {}
    for k, (src, t0, d, note) in CLIPS.items():
        m[k] = dict(source=SRC[src][3], ia='https://archive.org/details/' + SRC[src][0], start=t0, dur=d, note=note)
    json.dump(m, open(p, 'w'), ensure_ascii=False, indent=1)
