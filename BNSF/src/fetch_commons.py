"""第二季第二期（BNSF）维基共享资源照片（不走 API：API 对本环境限流）→ assets/media/<名称>.jpg，作者与授权写进 credits.json。
  · 文件页 HTML 解析授权简称（licensetpl_short）与作者（fileinfotpl_aut 一行）；只收 CC0 / 公有领域 / CC BY / CC BY-SA；
  · 图片先取 upload.wikimedia.org 原图（缩略图对本环境限流更严），本地缩到 ≤2400 像素；逐张间隔 ~50 秒，遇 429 退避。
python3 src/fetch_commons.py            # 已入库的跳过；ONLY=a,b 只补指定几张
"""
import os, re, json, time, html, hashlib, urllib.parse, urllib.request
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MDIR = os.path.join(ROOT, 'assets', 'media')
UA = {'User-Agent': 'ClaudeCode-video-research/1.0 (https://code.claude.com/docs; documentary image credits)'}
OK = ('cc0', 'public domain', 'pd', 'cc by', 'cc-by', 'no restrictions')
PHOTOS = {   # 名称: (Commons 文件名, 用途)
    'c_obama_buffett': ('President Barack Obama and Warren Buffett in the Oval Office, July 14, 2010.jpg', '巴菲特在白宫（2010-07-14，白宫官方照片）'),
    'c_buffett_2010': ('Warren Buffett in 2010.jpg', '巴菲特（2010）'),
    'c_buffett_ku': ('Warren Buffett KU Visit.jpg', '巴菲特（2005）'),
    'c_lehman': ('Lehman Brothers-NYC-20080915.jpg', '雷曼兄弟总部（2008-09-15）'),
    'c_munger': ('Charlie Munger.jpg', '查理·芒格（2010）'),
    'c_bnsf_coal': ('BNSF train at Sheep Mountain - Montana - 2013-07-07.jpg', 'BNSF 列车经过蒙大拿州（2013）'),
    'c_bnsf_grain': ('BNSF 7256 Leads Grain In GainesvilleTX.jpg', 'BNSF 运粮列车（得州盖恩斯维尔）'),
    'c_bnsf_im': ('BNSF intermodal train in Greenland, CO.jpg', 'BNSF 集装箱列车（科罗拉多州）'),
    'c_bnsf_bridge': ('BNSF Railway train passing over the Canyon Diablo Railroad Bridge - August 2016.jpg', 'BNSF 列车通过亚利桑那州暗黑峡谷铁路桥（2016）'),
    'c_fortworth': ('Fort Worth Skyline 2025.jpg', '得州沃斯堡（BNSF 总部所在城市，2025）'),
    'c_up_train': ('Union Pacific freight train in the Feather River Canyon-3872.jpg', '联合太平洋货运列车（加州羽毛河峡谷）'),
    'c_ns_train': ('Norfolk Southern manifest train at Bound Brook July 2026 1.jpg', '诺福克南方货运列车（新泽西州，2026）'),
    'c_trucks': ('Colorful Semi-Trucks.jpg', '公路上的半挂卡车'),
    'c_abel': ('Greg Abel.jpg', '格雷格·阿贝尔'),
    'c_bnsf_1997': ('19970427 05 BNSF Galesburg, Illinois (5800008026).jpg', '合并两年后的 BNSF 列车（伊利诺伊州盖尔斯堡，1997）'),
    'c_bnsf_coal2': ('BNSF Coal at TW55 Fort Worth TX.jpg', 'BNSF 运煤列车（得州沃斯堡）'),
    'c_bnsf_im2': ('BNSF Intermodal Train passing by the Izaak Walton Inn (May 2018).jpg', 'BNSF 集装箱列车（蒙大拿州，2018）'),
    'c_bnsf_bridge2': ('BNSF train crosses bridge west of Luverne, North Dakota.jpg', 'BNSF 列车过桥（北达科他州）'),
    'c_bnsf_locos': ('BNSF Locomotives in Wolf Point MT.jpg', 'BNSF 机车（蒙大拿州沃尔夫波因特）'),
    'c_bnsf_winter': ('Winter train passing through Livingston.jpg', '冬天的列车（蒙大拿州利文斯顿）'),
    'c_up_train2': ('Union Pacific freight train in Elmhurst, Illinois May 2025.jpg', '联合太平洋货运列车（伊利诺伊州，2025）'),
    'c_tankcars': ('Tank cars, New Orleans.jpg', '铁路罐车'),
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
