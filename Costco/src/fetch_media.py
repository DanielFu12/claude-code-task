"""第六期外部照片下载：Wikimedia Commons（需要网络能访问 commons.wikimedia.org、upload.wikimedia.org）。
- 经 API 取作者、授权、原始页面，写进 assets/media/credits.json；只收 CC0 / 公有领域 / CC BY / CC BY-SA。
- 下载后必须抽帧审片，不合格的从 gg.py 的使用清单里排除（制作宪章 二.4）。
python3 src/fetch_media.py
"""
import os, sys, json, time, urllib.parse, urllib.request
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MDIR = os.path.join(ROOT, 'assets', 'media'); os.makedirs(MDIR, exist_ok=True)
UA = {'User-Agent': 'baman-value-doc/1.0 (research use)'}
OK_LICENSE = ('cc0', 'public domain', 'pd', 'cc by', 'cc-by')

# 名称: (Commons 文件名, 用途)
PHOTOS = {
    'hotdog1': ("$1.5 hot-dog combo at Costco Wholesale Queens, October 21 2023, New York.jpg", '一块五热狗套餐'),
    'hotdog2': ("$1.5 hot-dog combo at Costco Wholesale Queens, October 21 2023, New York 2.jpg", '一块五热狗套餐'),
    'hotdog3': ("$1.5 hot-dog combo at Costco Wholesale Queens, October 21 2023, New York 3.jpg", '一块五热狗套餐'),
    'foodcourt': ("Food court at Costco Wholesale Queens, October 21 2023, New York.jpg", '美食区'),
    'foodcourt2': ("Food court at Costco Wholesale Queens, October 21 2023, New York 2.jpg", '美食区'),
    'chicken_oven': ("Costco Waterloo rotisserie chicken oven and salads.jpg", '烤鸡炉'),
    'chicken_pack': ("Costco rotisserie chicken packaging.jpg", '烤鸡'),
    'sinegal': ("James Sinegal (cropped).jpg", '吉姆·辛内格尔'),
    'sams_sz1999': ("Sam's club 山姆俱乐部 Shān mǔ jùlèbù Shenzhen China 1999.jpg", '山姆深圳（1999）'),
    'sams_us': ("Sam's Club store.jpg", '美国山姆会员店'),
    'buffett_munger2': ("Buffett & Munger.jpg", '巴菲特与芒格'),
    'munger2': ("Charlie Munger 2.jpg", '芒格'),
    'costco_pallets': ("Boxes of Nissin Cup Noodles on pallets at Costco, SSF ECR.JPG", '整托盘商品'),
    'sams_bj': ("Sam's Club in Beijing, China, 2020.jpg", '山姆北京'),
    'sams_sz': ("SAM'S CLUB SHENZHEN.jpg", '山姆深圳'),
    'checkout': ("Costco checkout.jpg", '收银台'),
    'crowded': ("More Crowded than Costco - Flickr - brewbooks.jpg", '人流'),
    'kirkland': ("Costco Alcohol Vodka Kirkland.jpg", '科克兰'),
    'costco_japan': ("COSTCO Amagasaki.JPG", '日本尼崎'),
    'costco_korea': ("Costco Sangbong branch Seoul Korea 20181122 161832.jpg", '韩国首尔'),
    'costco_taiwan': ("Costco Taiwan North Kaohsiung Store.jpg", '台湾高雄'),
    'costco_uk': ("Costco warehouse Sheffield - geograph.org.uk - 602234.jpg", '英国谢菲尔德'),
    'costco_neworleans': ("New Orleans Costco, August 2025.jpg", '美国新奥尔良'),
    'price_cart': ("Price Club shopping cart.jpg", 'Price Club 购物车'),
    'costco_ext2': ("Costco Exterior.jpg", 'Costco 外景'),
    'costco_int3': ("Costcointerior.jpg", 'Costco 卖场'),
    'costco_books': ("Book stacks - Costco Warehouse store Kauai (2499689386).jpg", '整箱码放的商品'),
    'checkout2': ("Checkouts at 1st Floor, Costco Neihu Warehouse 20161229.jpg", '收银台'),
    'sams_int': ("Sam's Club interior.jpg", '山姆卖场'),
    'sams_suzhou': ("Sam's Club in Suzhou-1.JPG", '山姆苏州'),
    'card': ("Icelandic Costco membership card.jpg", '会员卡'),
}


def api(params):
    u = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(dict(params, format='json'))
    for k in range(10):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read())
        except Exception as e:
            print("  retry", k, str(e)[:60], flush=True); time.sleep(min(30 * (k + 1), 240))
    raise RuntimeError(u)


def thumb(url, w=1920):
    """Wikimedia 推荐的标准尺寸缩略图（upload.wikimedia.org/.../thumb/…/1920px-…），比原图更不容易被限流"""
    u = url.split('?')[0]; a, b = u.split('/wikipedia/commons/')
    return a + '/wikipedia/commons/thumb/' + b + '/%dpx-' % w + b.rsplit('/', 1)[1]


def fetch(url, path, width=0):
    urls = ([thumb(url)] if width > 1920 else []) + [url.split('?')[0]]
    for k in range(3):
        for u in urls:
            try:
                data = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120).read()
                open(path, 'wb').write(data); return
            except Exception as e:
                print('  retry', k, str(e)[:60], flush=True)
        time.sleep(min(30 * (k + 1), 240))
    raise RuntimeError(url)


if __name__ == '__main__':
    import re
    from PIL import Image, ImageOps
    cp = os.path.join(MDIR, 'credits.json')
    credits = json.load(open(cp)) if os.path.exists(cp) else {}
    FIRST = list(PHOTOS)
    order = FIRST + [n for n in PHOTOS if n not in FIRST]
    todo = {n: PHOTOS[n] for n in order if not (os.path.exists(os.path.join(MDIR, n + '.jpg')) and n in credits)}
    if os.environ.get('ONLY'): todo = {n: v for n, v in todo.items() if n in os.environ['ONLY'].split(',')}   # 只补指定的几张
    # 逐张取元数据（批量请求在限流时整批 429；单张请求更稳）
    info = {}
    for name, (fn, use) in todo.items():
        d = api(dict(action='query', titles='File:' + fn, prop='imageinfo', iiprop='url|extmetadata|size'))
        for pg in d['query']['pages'].values(): info[fn] = pg
        time.sleep(12)
    for name, (fn, use) in todo.items():
        page = info.get(fn)
        if not page or 'imageinfo' not in page: print('MISSING', name, fn); continue
        ii = page['imageinfo'][0]; md = ii.get('extmetadata', {})
        lic = md.get('LicenseShortName', {}).get('value', '')
        if not any(k in lic.lower() for k in OK_LICENSE): print('SKIP license', name, lic); continue
        path = os.path.join(MDIR, name + '.jpg')
        try:
            fetch(ii['url'], path, ii.get('width', 0))
        except RuntimeError:
            print('FAILED (rate limited), next pass:', name, flush=True); time.sleep(120); continue          # 原图在 upload.wikimedia.org；缩略图域名不在白名单，本地缩放
        im = ImageOps.exif_transpose(Image.open(path)).convert('RGB')
        if im.width > 2400: im = im.resize((2400, round(im.height * 2400 / im.width)), Image.LANCZOS)
        im.save(path, quality=92)
        artist = re.sub(r'<[^>]+>', '', md.get('Artist', {}).get('value', '')).strip()
        credits[name] = dict(file=fn, page=ii['descriptionurl'], artist=artist, license=lic,
                             license_url=md.get('LicenseUrl', {}).get('value', ''), use=use,
                             date=re.sub(r'<[^>]+>', '', md.get('DateTimeOriginal', {}).get('value', '')).strip()[:40])
        print('ok', name, ii.get('width'), 'x', ii.get('height'), lic, '|', artist[:40], flush=True)
        json.dump(credits, open(cp, 'w'), ensure_ascii=False, indent=1)
        time.sleep(40)
