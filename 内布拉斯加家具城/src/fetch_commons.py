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
    'c_nfm_kc': ('Nebraska Furniture Mart (KC).jpg', 'NFM 堪萨斯城店'),
    'c_brk2015': ('Kathy Ireland, Warren Buffett and Bill Gates at the 2015 Berkshire Hathaway Shareholders Meeting.jpg', '2015 年伯克希尔股东会'),
    'c_buffett_munger': ('Buffett & Munger.jpg', '巴菲特与芒格'),
    'c_munger': ('Charlie Munger.jpg', '查理·芒格（2010）'),
    'c_buffett_ku': ('Warren Buffett KU Visit.jpg', '巴菲特'),
    'c_buffett_2010': ('Warren Buffett in 2010.jpg', '巴菲特（2010）'),
    'c_kiewit': ('Kiewit Plaza Omaha.jpg', '伯克希尔总部所在的基威特广场'),
    'c_grandscape': ('Grandscape - The Colony, Texas.jpg', '得州 The Colony 的 Grandscape 商圈（NFM 得州店所在地）'),
    'c_west_omaha': ('Above West Omaha.jpg', '奥马哈西区航拍'),
    'c_omaha1995': ('1995 Omaha, Nebraska.jpg', '1995 年的奥马哈'),
    'c_omaha_dt': ('Downtown Omaha view.jpg', '奥马哈市中心'),
    'c_omaha1970': ('Interstate 480 - Exit Ramp (Omaha, Nebraska, 1970).jpg', '1970 年的奥马哈'),
    'c_farnam1906': ('14th & Farnam 1906.jpg', '1906 年奥马哈法纳姆街'),
    'c_rose': ('Rose Blumkin Performing Arts Center Omaha, Nebraska.jpg', '罗丝·布鲁姆金表演艺术中心（B 太太出资保下的老剧院）'),
    'c_rose2': ('Rose Blumkin Performing Arts Center 2025.jpg', '罗丝·布鲁姆金表演艺术中心'),
    'c_star1926': ('Star Furinture in 1926.jpg', '1926 年的 Star Furniture'),
    'c_jordans': ('Jordans Furniture, Reading MA.jpg', 'Jordan’s 家具店（马萨诸塞州雷丁）'),
    'c_jordans2': ("Jordan's Maine Mall.jpg", 'Jordan’s 家具店（缅因州）'),
    'c_rcwilley': ('2019 RC Willey Car show.jpg', 'R.C. Willey 门店'),
    'c_ks_speedway': ('Kansas Speedway aerial.jpg', '堪萨斯城西郊航拍'),
    'c_desmoines': ('Skyline downtown Des Moines.jpg', '得梅因'),
    'c_omaha_sky': ('Omaha skyline, Omaha, Nebraska (66660).jpg', '奥马哈天际线'),
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
