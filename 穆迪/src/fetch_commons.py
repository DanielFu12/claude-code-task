"""维基共享资源照片（不走 API：API 对本环境限流）→ assets/media/<名称>.jpg，作者与授权写进 credits.json。
  · 文件页 HTML 解析授权简称（licensetpl_short）与作者（fileinfotpl_aut 一行）；只收 CC0 / 公有领域 / CC BY / CC BY-SA；
  · 图片先取 upload.wikimedia.org 原图（缩略图对本环境限流更严），本地缩到 ≤2400 像素；逐张间隔 ~50 秒，遇 429 退避。
python3 src/fetch_commons.py            # 已入库的跳过；ONLY=a,b 只补指定几张
"""
import os, re, json, time, html, hashlib, urllib.parse, urllib.request
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MDIR = os.path.join(ROOT, 'assets', 'media')
UA = {'User-Agent': 'ClaudeCode-video-research/1.0 (https://code.claude.com/docs; documentary image credits) python-urllib/3'}
OK = ('cc0', 'public domain', 'pd', 'cc by', 'cc-by', 'no restrictions')
PHOTOS = {   # 名称: (Commons 文件名, 用途)
    'c_moody1903': ('John Moody (financial analyst) 1903.jpg', '约翰·穆迪（1903）'),
    'c_rrgroups': ('Greater Steam Railroad Groups, 1904.jpg', '约翰·穆迪《托拉斯真相》里的美国铁路集团图（1904）'),
    'c_obama_buffett': ('President Barack Obama and Warren Buffett in the Oval Office, July 14, 2010.jpg', '巴菲特在白宫（2010-07-14，白宫官方照片）'),
    'c_buffett_2010': ('Warren Buffett in 2010.jpg', '巴菲特（2010）'),
    'c_7wtc': ('7 World Trade Center 2024.jpg', '纽约世贸中心七号楼（穆迪总部所在）'),
    'c_7wtc2': ('A627, One World Trade Center and 7 World Trade Center, Manhattan, July 2019.jpg', '世贸中心一号楼与七号楼（2019）'),
    'c_foreclosure': ('Foreclosure sign.jpeg', '止赎房屋的告示牌'),
    'c_foreclosure2': ('Sign of the Times-Foreclosure.jpg', '止赎房屋'),
    'c_deserted': ('Foreclosure Deserted House.jpeg', '止赎后空置的房子'),
    'c_lehman': ('Lehman Brothers-NYC-20080915.jpg', '雷曼兄弟总部（2008-09-15）'),
    'c_nyse_floor': ('No Known Restrictions Trading Floor, New York Stock Exchange (Highsmith LOC) (6718386525).jpg', '纽约证券交易所交易大厅（Carol M. Highsmith 摄）'),
}


def get(url, tries=6):
    for k in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
        except Exception as e:
            print('  retry', k, str(e)[:70], flush=True); time.sleep(min(45 * (k + 1), 240))
    raise RuntimeError(url)


def meta(fn):
    n = fn.replace(' ', '_')
    page = 'https://commons.wikimedia.org/wiki/File:' + urllib.parse.quote(n)
    s = get(page).decode('utf-8', 'ignore')
    lic = [html.unescape(re.sub(r'<[^>]+>', '', x)).strip() for x in re.findall(r'class="licensetpl(?:_|&#95;)short"[^>]*>(.*?)</span>', s, re.S)]
    au = re.search(r'id="fileinfotpl(?:_|&#95;)aut"[^>]*>.*?</td>\s*<td[^>]*>(.*?)</td>', s, re.S)
    author = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', au.group(1)))).strip() if au else ''
    dt = re.search(r'id="fileinfotpl(?:_|&#95;)date"[^>]*>.*?</td>\s*<td[^>]*>(.*?)</td>', s, re.S)
    date = html.unescape(re.sub(r'<[^>]+>', ' ', dt.group(1))).strip()[:40] if dt else ''
    return page, (lic[0] if lic else ''), author, date


def orig(fn):
    n = fn.replace(' ', '_'); h = hashlib.md5(n.encode()).hexdigest()
    return f'https://upload.wikimedia.org/wikipedia/commons/{h[0]}/{h[:2]}/{urllib.parse.quote(n)}'


def thumb(fn, w):
    n = fn.replace(' ', '_'); h = hashlib.md5(n.encode()).hexdigest(); q = urllib.parse.quote(n)
    return f'https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/{w}px-{q}' + ('.jpg' if n.lower().endswith(('.tif', '.tiff')) else '')


if __name__ == '__main__':
    from PIL import Image, ImageOps
    cp = os.path.join(MDIR, 'credits.json'); credits = json.load(open(cp))
    only = set(os.environ['ONLY'].split(',')) if os.environ.get('ONLY') else None
    for name, (fn, use) in PHOTOS.items():
        p = os.path.join(MDIR, name + '.jpg')
        if (os.path.exists(p) and name in credits) or (only and name not in only): continue
        try:
            page, lic, author, date = meta(fn)
        except RuntimeError:
            print('META FAILED', name, flush=True); continue
        if not any(k in lic.lower() for k in OK): print('SKIP license', name, repr(lic), flush=True); continue
        data = None
        time.sleep(20)
        for u in (orig(fn), thumb(fn, 1920), thumb(fn, 1280)):   # 原图最不容易被限流（本地再缩到 ≤2400 像素）
            try: data = get(u, tries=3); break
            except RuntimeError: continue
        if data is None: print('IMG FAILED', name, flush=True); continue
        open(p, 'wb').write(data)
        im = ImageOps.exif_transpose(Image.open(p)).convert('RGB'); im.thumbnail((2400, 2400), Image.LANCZOS); im.save(p, quality=92)
        credits[name] = dict(file=fn, page=page, artist=author[:120], license=lic, use=use, date=date)
        json.dump(credits, open(cp, 'w'), ensure_ascii=False, indent=1)
        print('ok', name, im.size, lic, '|', author[:50], flush=True)
        time.sleep(30)
