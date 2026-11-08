"""按清单下载 Wikimedia Commons 素材到 assets/media/（图片取 1920 宽的标准缩略图；视频取 1080p/720p 转码），
并把作者、授权、原始页面写入 assets/media/credits.json（片尾与 SOURCES 署名用）。
python3 src/fetch_media.py WORK
"""
import sys, os, json, time, hashlib, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commons import info, UA

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'assets', 'media')

# key: (Commons 标题里的独特片段, 类型)
WANT = {
    'itochu_hq': ('File:Itochu Tokyo.jpg', 'img'),
    'mitsui_hq': ('File:Mitsui & Co. Headquarters Building.jpg', 'img'),
    'marubeni_hq': ('File:Marubeni Head Office Building.jpg', 'img'),
    'marunouchi_station': ('File:Marunouchi & Tokyo Station 1.jpg', 'img'),
    'tse_entrance': ('File:The Entrance of Tokyo Stock Exchange Main Building 20240329.jpg', 'img'),
    'famima_night': ('File:FamilyMart Ikoma Kamimachi store at night.jpg', 'img'),
    'lawson_store': ('File:LAWSON Yurakucho 1-chome store.jpg', 'img'),
    'lng_tanker': ('File:2023-05-20 01 LNG tanker, GULF ENERGY - IMO 7390143.jpg', 'img'),
    'pilbara_mine': ('File:BHP Yandi mine seen from the air, June 2022 01.jpg', 'img'),
    'ore_train': ('File:BHPB Iron Ore 4352.JPG', 'img'),
    'tokyo_night': ('File:Minato City, Tokyo, Japan (Night)-denoised.jpg', 'img'),
    'whaleback_mine': ('File:Mount Whaleback Iron Ore Mine, Australia (ASTER).jpg', 'img'),
    'hedland_bulk': ('File:Bulk Carrier Maria in Port Hedland Harbour, 2023, 01.jpg', 'img'),
    'tokyo_sunset': ('File:Tokyo - Sunset Skyline.jpg', 'img'),
    'marunouchi_plaza': ('File:Marunouchi Central Plaza with blue sky, Tokyo station and Shin-Marunouchi Building, panoramic view from JP Tower, Tokyo, Japan.jpg', 'img'),
    'v_container': ('File:Aerial views of a container terminal at the Port of Cork, Cork, Ireland.webm', 'video'),
}


def find_titles():
    allr = []
    for f in ('search.json',):
        p = os.path.join(sys.argv[1], 'media', f)
        if os.path.exists(p):
            for v in json.load(open(p)).values(): allr += v
    t = {}
    for k, (frag, kind) in WANT.items():
        m = [x for x in allr if frag.replace('File:', '') in x['title'] and (frag.startswith('File:') is False or x['title'] == frag)]
        if m: t[k] = m[0]['title']
        else: print('未找到', k, frag)
    return t


def dl(url, dest):
    for i in range(10):
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=600).read()
            open(dest, 'wb').write(data); return True
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(int(e.headers.get('retry-after') or 30) + 2); continue
            if e.code == 404: return False
            raise
    return False


def transcoded(url, q):
    # https://upload.wikimedia.org/wikipedia/commons/a/ab/Name.webm → .../commons/transcoded/a/ab/Name.webm/Name.webm.1080p.vp9.webm
    url = url.split('?')[0]
    base, rest = url.split('/wikipedia/commons/')
    name = rest.split('/')[-1]
    return f'{base}/wikipedia/commons/transcoded/{rest}/{name}.{q}.vp9.webm'


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    cp = os.path.join(OUT, 'credits.json')
    credits = json.load(open(cp)) if os.path.exists(cp) else {}
    titles = find_titles()
    PRI = ['v_dq_sign', 'v_omaha_drone', 'iphone11', 'flip_moto', 'ibm_chq', 'dairy_queen', 'nfm_kc', 'cook_2017', 'jobs_2010',
           'glide', 'v_dundee_drone', 'smith_wollensky', 'oppo_vivo', 'coke_bottles', 'treasury', 'best_buy', 'v_tokyo', 'v_cars_night',
           'v_apple_park', 'nasdaq', 'munger', 'iphone7_back', 'iphone11_cam', 'jobs_wwdc08', 'flip_keypad', 'infinite_loop']
    titles = dict(sorted(titles.items(), key=lambda kv: PRI.index(kv[0]) if kv[0] in PRI else -1))
    for k, title in titles.items():
        kind = WANT[k][1]
        dest = os.path.join(OUT, k + ('.jpg' if kind == 'img' else '.webm'))
        if os.path.exists(dest) and k in credits: continue
        it = info([title], 1920 if kind == 'img' else None)[0]
        if kind == 'img':
            ok = dl((it['thumb'] or it['url']).split('?')[0], dest)
        else:
            ok = False
            for q in ('1080p', '720p'):
                if (it['h'] or 0) >= int(q[:-1]) or q == '720p':
                    ok = dl(transcoded(it['url'], q), dest)
                    if ok: break
            if not ok: ok = dl(it['url'].split('?')[0], dest)
        if not ok: print('下载失败', k); continue
        credits[k] = dict(title=it['title'], page='https://commons.wikimedia.org/wiki/' + urllib.parse.quote(it['title'].replace(' ', '_')),
                          license=it['license'], artist=it['artist'], date=it['date'], desc=it['desc'])
        json.dump(credits, open(cp, 'w'), ensure_ascii=False, indent=1)
        print('ok', k, it['license'], os.path.getsize(dest) // 1024, 'KB', flush=True)
        time.sleep(1)
