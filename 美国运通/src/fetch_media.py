"""第七期外部照片下载：Wikimedia Commons（需要网络能访问 commons.wikimedia.org、upload.wikimedia.org）。
- 经 API 取作者、授权、原始页面，写进 assets/media/credits.json；只收 CC0 / 公有领域 / CC BY / CC BY-SA。
- 下载后必须抽帧审片，不合格的从 gg.py 的使用清单里排除（制作宪章 二.4）。
python3 src/fetch_media.py
"""
import os, sys, json, time, urllib.parse, urllib.request
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MDIR = os.path.join(ROOT, 'assets', 'media'); os.makedirs(MDIR, exist_ok=True)
UA = {'User-Agent': 'ClaudeCode-video-research/1.0 (https://code.claude.com/docs; documentary image credits) python-urllib/3'}
OK_LICENSE = ('cc0', 'public domain', 'pd', 'cc by', 'cc-by')

# 名称: (Commons 文件名, 用途)
PHOTOS = {
    'ad1850': ("Advertisement of American Express, 1850.png", '1850 年运通快运广告'),
    'receipt1853': ("American Express Shipping Receipt 1853.jpg", '1853 年运通托运单'),
    'wagon1913': ("American Express Co Wagon, New Orleans 1913.jpg", '1913 年运通快运马车'),
    'bldg65': ("American Express Company Building 65 Broadway entrance.jpg", '百老汇大街 65 号运通大楼'),
    'tc_usd20': ("American Express Traveler Cheque, with denomination 20 US-Dollars.jpg", '20 美元旅行支票'),
    'tc_four': ("Four Travelers Cheques of 50 USD each, issued by American Express, bought ca. 2012, have long been spent.jpg", '旅行支票'),
    'tc_yen1974': ("Travellers cheques from American Express issued as 5000 Japanese Yen, 1974.jpg", '1974 年日元旅行支票'),
    'lounge_jfk': ("Entrance to American Express Centurion Lounge at JFK NYC airport (2022).jpg", '肯尼迪机场百夫长贵宾厅'),
    'lounge_jfk2': ("American Express Centurion Lounge - JFK Terminal 4 (54984753321).jpg", '肯尼迪机场百夫长贵宾厅'),
    'chenault': ("Kenneth Chenault.jpg", '前 CEO 谢诺'),
    'axp_tower': ("3 World Financial Center.jpg", '纽约运通大厦'),
    'bayonne': ("Bayonne tank farm from BB jeh.jpg", '新泽西州贝永的油罐区（今日）'),
    'delta_a350': ("Delta Air Lines - Airbus A350-941 - N502DN.jpg", '达美航空客机'),
    'contactless': ("Contactless-payment.jpg", '刷卡支付'),
    'terminal': ("Toast Tap Payment Perminal.jpg", '刷卡终端'),
    'buffett_munger2': ("Buffett & Munger.jpg", '巴菲特与芒格'),
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
