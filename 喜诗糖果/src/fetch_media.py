"""第五期外部照片下载：Wikimedia Commons（需要网络能访问 commons.wikimedia.org、upload.wikimedia.org）。
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
    'sees_hq': ("Sees Candies headquarters.jpg", '旧金山总部外景'),
    'sees_hq_2025a': ("See's Candies headquarters - December 2025 - Sarah Stierch 01.jpg", '旧金山总部（2025）'),
    'sees_hq_2025b': ("See's Candies headquarters - December 2025 - Sarah Stierch 02.jpg", '旧金山总部（2025）'),
    'sees_store_2025a': ("See's Candies - December 2025 - Sarah Stierch 01.jpg", '门店（2025 年 12 月）'),
    'sees_store_2025b': ("See's Candies - December 2025 - Sarah Stierch 02.jpg", '门店（2025 年 12 月）'),
    'sees_store_2025c': ("See's Candies - December 2025 - Sarah Stierch 03.jpg", '门店（2025 年 12 月）'),
    'sees_store_2025d': ("See's Candies - December 2025 - Sarah Stierch 04.jpg", '门店（2025 年 12 月）'),
    'sees_interior1': ("Sees interior 1.jpg", '店内'),
    'sees_interior2': ("Sees interior 2.jpg", '店内'),
    'sees_pasadena': ("See's Candies South Pasadena, California.jpg", '南帕萨迪纳门店'),
    'sees_balboa': ("See's Candies Balboa Mesa.jpg", '圣地亚哥门店'),
    'sees_modesto': ("See's Candies Vintage Faire Mall Modesto, California.jpg", '莫德斯托商场门店'),
    'sees_tanasbourne': ("Sees Candies Tanasbourne - Hillsboro, Oregon.JPG", '俄勒冈门店'),
    'sees_sunnyvale': ("Sunnyvale Sees Candies.jpg", '桑尼维尔门店'),
    'sees_sv68': ("PIC 0068, Sees Candies, Sunnyvale, CA (4491199840).jpg", '桑尼维尔门店'),
    'sees_sv69': ("PIC 0069, Sees Candies, Sunnyvale, CA (4491199020).jpg", '桑尼维尔门店'),
    'sees_sv70': ("PIC 0070, Sees Candies, Sunnyvale, CA (4491198172).jpg", '桑尼维尔门店'),
    'sees_sv71': ("PIC 0071, Sees Candies, Sunnyvale, CA (4490556023).jpg", '桑尼维尔门店'),
    'sees_sv72': ("PIC 0072, Sees Candies, Sunnyvale, CA (4490559793).jpg", '桑尼维尔门店'),
    'sees_assorted': ("See's Candies Assorted Chocolates - November 2025 - Sarah Stierch.jpg", '什锦巧克力礼盒'),
    'sees_truffles': ("See's Candies Egg Nog Truffles (31011558824).jpg", '松露巧克力'),
    'sees_brittle': ("Plenty of See's Candies Peanut Brittle (24006721623).jpg", '花生脆'),
    'sees_mary': ("Mary SEE'S Candies & Chocolates (11231882025).jpg", '喜诗太太头像招牌'),
    'sees_macau': ("See's Candies Macau (7797179698).jpg", '澳门门店'),
    'munger': ("Charlie Munger (cropped).jpg", '芒格'),
    'munger2': ("Charlie Munger 2.jpg", '芒格'),
    'buffett_munger': ("Buffett and Munger.jpg", '巴菲特与芒格'),
    'buffett_munger2': ("Buffett & Munger.jpg", '巴菲特与芒格'),
    'brk_meeting_2015': ("Kathy Ireland, Warren Buffett and Bill Gates at the 2015 Berkshire Hathaway Shareholders Meeting.jpg", '2015 股东大会'),
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
    FIRST = ['sees_store_2025a', 'sees_interior1', 'sees_assorted', 'munger', 'buffett_munger', 'sees_brittle', 'sees_mary',
             'sees_store_2025b', 'sees_pasadena', 'sees_interior2', 'sees_truffles', 'sees_hq_2025a', 'sees_store_2025c',
             'sees_balboa', 'sees_modesto', 'brk_meeting_2015']
    order = FIRST + [n for n in PHOTOS if n not in FIRST]
    todo = {n: PHOTOS[n] for n in order if not (os.path.exists(os.path.join(MDIR, n + '.jpg')) and n in credits)}
    # 一次请求取全部元数据（减少 API 调用，避免 429）
    d = api(dict(action='query', titles='|'.join('File:' + fn for fn, _ in todo.values()), prop='imageinfo', iiprop='url|extmetadata|size'))
    norm = {x['to']: x['from'] for x in d['query'].get('normalized', [])}
    info = {}
    for pg in d['query']['pages'].values():
        info[norm.get(pg['title'], pg['title'])[5:]] = pg
    for name, (fn, use) in todo.items():
        page = info.get(fn) or info.get(fn.replace('_', ' '))
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
        time.sleep(60)
