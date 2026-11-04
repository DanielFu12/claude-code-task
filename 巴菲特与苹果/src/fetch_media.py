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
    'buffett_2015': ('Warren Buffett at the 2015 SelectUSA Investment Summit.jpg', 'img'),
    'buffett_ku': ('Warren Buffett KU Visit.jpg', 'img'),
    'buffett_osu': ('Warren Buffett with Fisher College of Business Student - 4395164676.jpg', 'img'),
    'buffett_osu2': ('Warren Buffett with Fisher College of Business Student - 4394391213.jpg', 'img'),
    'buffett_2010': ('Warren Buffett Wall Street Money Never Sleeps Premiere', 'img'),
    'buffett_pitch': ('Warren Buffett! He caught a ceremonial first pitch tonight.jpg', 'img'),
    'brk_meeting_2025': ('Berkshire Hathaway Annual Meeting 2025.jpg', 'img'),
    'kiewit': ('File:Kiewit Plaza Omaha.jpg', 'img'),
    'omaha_river': ('Skyline on the Missouri River (30899969517) (cropped).jpg', 'img'),
    'omaha_2026': ("Omaha Skyline viewed from Harrah's, August 2026.jpg", 'img'),
    'apple_park_aerial': ('Apple Park aerial view, June 2024.jpg', 'img'),
    'apple_park_dusk': ('Apple Park dusk aerial.jpg', 'img'),
    'apple_campus2_2016': ('Apple Campus 2 1 2016-09-19.jpg', 'img'),
    'apple_5th_2006': ('Apple Store Fifth Avenue New York NY-2006-05-20.jpg', 'img'),
    'apple_5th': ('Apple Store - Fifth Avenue (7181848534).jpg', 'img'),
    'apple_5th_displays': ('Apple Fifth Avenue store displays.jpg', 'img'),
    'iphone7': ('Apple iPhone 7 in Apple leather case.jpg', 'img'),
    'iphone7_back': ('IPhone 7 - A1778 Rose Gold - Back.jpg', 'img'),
    'iphone11': ('File:IPhone 11.jpeg', 'img'),
    'iphone11_cam': ("Close-Up of the iPhone 11 Pro's cameras.jpg", 'img'),
    'jobs_2010': ('Steve Jobs Headshot 2010-CROP (cropped 2).jpg', 'img'),
    'jobs_wwdc08': ('Steve Jobs at WWDC 2008.jpg', 'img'),
    'cook_2017': ('Tim Cook (2017, cropped).jpg', 'img'),
    'ibm_chq': ('IBM CHQ - Oct 2014.jpg', 'img'),
    'flip_keypad': ('Keypad Samsung flip phone.jpg', 'img'),
    'flip_moto': ('Motorola flip phone, closed.jpg', 'img'),
    'glide': ('File:Glide Memorial.jpg', 'img'),
    'smith_wollensky': ('Smith & Wollensky steakhouse (Manhattan, New York) 001.jpg', 'img'),
    'oppo_vivo': ('Dabri Oppo-Vivo shop.jpg', 'img'),
    'dairy_queen': ('Dairy Queen - October 2023 - Sarah Stierch.jpg', 'img'),
    'nfm_kc': ('Nebraska Furniture Mart (KC).jpg', 'img'),
    'best_buy': ('Best Buy Store (13919887146).jpg', 'img'),
    'nasdaq': ('NASA Mars Perseverance on Nasdaq MarketSite (NHQ202102180118).jpg', 'img'),
    'treasury': ('U.S. Treasury Building and Albert Gallatin Statue.jpg', 'img'),
    'coke_bottles': ('Coca-Cola Bottles Alaska 2010.jpg', 'img'),
    'munger': ('File:Charlie Munger.jpg', 'img'),
    'infinite_loop': ('Apple Campus One Infinite Loop Sign.jpg', 'img'),
    'v_omaha_drone': ('Flying over Omaha, NE, USA - HD Photography Drone.webm', 'vid'),
    'v_dundee_drone': ('Memorial Park, Dundee ~AERIAL DRONE 4K Video.webm', 'vid'),
    'v_dq_sign': ('Rotating Dairy Queen sign.webm', 'vid'),
    'v_apple_park': ('Apple Park 1 2018-12-23.webm', 'vid'),
    'v_cars_night': ('Cars driving at night.webm', 'vid'),
    'v_tokyo': ('Marunouchi,Tokyo shoot by iPhone 5s.webm', 'vid'),
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
            ok = dl(it['thumb'] or it['url'], dest)
        else:
            ok = False
            for q in ('1080p', '720p'):
                if (it['h'] or 0) >= int(q[:-1]) or q == '720p':
                    ok = dl(transcoded(it['url'], q), dest)
                    if ok: break
            if not ok: ok = dl(it['url'], dest)
        if not ok: print('下载失败', k); continue
        credits[k] = dict(title=it['title'], page='https://commons.wikimedia.org/wiki/' + urllib.parse.quote(it['title'].replace(' ', '_')),
                          license=it['license'], artist=it['artist'], date=it['date'], desc=it['desc'])
        json.dump(credits, open(cp, 'w'), ensure_ascii=False, indent=1)
        print('ok', k, it['license'], os.path.getsize(dest) // 1024, 'KB', flush=True)
        time.sleep(1)
