"""第八期外部照片下载 → assets/media/<名称>.jpg，作者与授权写进 assets/media/credits.json。
  · Wikimedia Commons：经 API 取作者、授权、原始页面；只收 CC0 / 公有领域 / CC BY / CC BY-SA（逐张请求，限流时退避）。
  · 美国国会图书馆（LOC）：农业安全局（FSA/OWI）1938 年奥马哈等照片，“No known restrictions on publication”。
  · 伯克希尔 2013 年年报第 114–117 页：1983 年收购提议书与 NFM 1946 年报表原件（文件影像，片中注明出处）。
下载后必须抽帧审片，不合格的从 gg.py 的使用清单里排除（制作宪章 二.4）。
python3 src/fetch_media.py            # 已入库的跳过；ONLY=a,b 只补指定几张
"""
import os, sys, json, time, re, urllib.parse, urllib.request
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MDIR = os.path.join(ROOT, 'assets', 'media'); os.makedirs(MDIR, exist_ok=True)
UA = {'User-Agent': 'ClaudeCode-video-research/1.0 (https://code.claude.com/docs; documentary image credits) python-urllib/3'}
OK_LICENSE = ('cc0', 'public domain', 'pd', 'cc by', 'cc-by', 'no restrictions')

# 名称: (Commons 文件名, 用途)
COMMONS = {
    'omaha1970': ('Interstate 480 - Exit Ramp (Omaha, Nebraska, 1970).jpg', '1970 年的奥马哈'),
    'omaha1914': ('Omaha Nebraska c1914 LOC 6a13849u.jpg', '1914 年前后的奥马哈'),
    'omaha_sky': ('Omaha skyline, Omaha, Nebraska (66660).jpg', '奥马哈天际线'),
    'omaha_sky2': ('Skyline of the Downtown Omaha, Nebraska from Heartland of America Park.jpg', '奥马哈天际线'),
    'ru_village': ('Prokudin 20888 Sumskoe 1909.jpg', '俄罗斯帝国乡村（1909，普罗库金-戈尔斯基摄）'),
    'ru_spin': ('Sergei Prokudin-Gorskii, Spinning yarn in the village of Izvedovo, 1910.jpg', '俄罗斯乡村妇女纺线（1910，普罗库金-戈尔斯基摄）'),
    'seattle1910': ('Seattle waterfront from Elliott Bay, ca. 1910 - DPLA - d2efcf59ae1bf3baf00743843ee41976 (page 1).jpg', '1910 年前后的西雅图港'),
    'seattle_pier': ('Seattle waterfront at Pier 4, ca. 1910 - DPLA - 885aa5020b31023925ce94b55e801b8d.jpg', '1910 年前后的西雅图码头'),
    'omaha_beach': ('Into the Jaws of Death 23-0455M edit.jpg', '1944 年 6 月 6 日，诺曼底奥马哈海滩'),
    'purple_heart': ('Purple Heart Medal.png', '紫心勋章'),
    'nfm_kc': ('Nebraska Furniture Mart (KC).jpg', 'NFM 堪萨斯城店'),
    'ks_speedway': ('Kansas Speedway aerial.jpg', '堪萨斯城西郊（堪萨斯赛车场一带）航拍'),
    'desmoines': ('Skyline downtown Des Moines.jpg', '艾奥瓦州得梅因'),
    'rose_pac': ('Rose Blumkin Performing Arts Center Omaha, Nebraska.jpg', '奥马哈的罗丝·布鲁姆金表演艺术中心'),
    'rose_pac2': ('Rose Blumkin Performing Arts Center 2025.jpg', '罗丝·布鲁姆金表演艺术中心'),
    'star1926': ('Star Furinture in 1926.jpg', '1926 年的 Star Furniture'),
    'jordans': ('Jordans Furniture, Reading MA.jpg', 'Jordan’s 家具店（马萨诸塞州雷丁）'),
    'jordans2': ("Jordan's Maine Mall.jpg", 'Jordan’s 家具店（缅因州）'),
    'rcwilley': ('2019 RC Willey Car show.jpg', 'R.C. Willey 门店'),
    'buffett_ku': ('Warren Buffett KU Visit.jpg', '沃伦·巴菲特'),
}
# 名称: (LOC 条目号, 图片地址, 标题, 摄影师, 年份, 用途)
LOC = {
    'loc_boston': ('2017762765', 'https://tile.loc.gov/storage-services/service/pnp/fsa/8b37000/8b37400/8b37421v.jpg',
                   'The "Boston Store," Omaha\'s largest department store. Omaha, Nebraska', 'John Vachon', '1938-11', '1938 年奥马哈的大百货公司'),
    'loc_brandeis': ('2017762783', 'https://tile.loc.gov/storage-services/service/pnp/fsa/8b14000/8b14200/8b14231v.jpg',
                     'J.I. Brandeis Department Store, Omaha\'s largest. Omaha, Nebraska', 'John Vachon', '1938-11', '1938 年奥马哈的布兰代斯百货'),
    'loc_loans': ('2017767975', 'https://tile.loc.gov/storage-services/service/pnp/fsa/8b14000/8b14200/8b14227v.jpg',
                  'Loan companies on lower Douglas Street. Omaha, Nebraska', 'John Vachon', '1938-11', '1938 年奥马哈道格拉斯街的当铺与放贷行'),
    'loc_omaha_a': ('2017762757', 'https://tile.loc.gov/storage-services/service/pnp/fsa/8b14000/8b14200/8b14207v.jpg',
                    'Omaha, Nebraska', 'John Vachon', '1938-11', '1938 年的奥马哈街头'),
    'loc_omaha_b': ('2017762717', 'https://tile.loc.gov/storage-services/service/pnp/fsa/8b14000/8b14100/8b14163v.jpg',
                    'Omaha, Nebraska', 'John Vachon', '1938-11', '1938 年的奥马哈街头'),
    'loc_omaha_c': ('2017762760', 'https://tile.loc.gov/storage-services/service/pnp/fsa/8b14000/8b14200/8b14209v.jpg',
                    'Omaha, Nebraska', 'John Vachon', '1938-11', '1938 年的奥马哈街头'),
    'loc_omaha_d': ('2017762723', 'https://tile.loc.gov/storage-services/service/pnp/fsa/8b14000/8b14100/8b14168v.jpg',
                    'Omaha, Nebraska', 'John Vachon', '1938-11', '1938 年的奥马哈街头'),
    'loc_omaha_e': ('2017717701', 'https://tile.loc.gov/storage-services/service/pnp/fsa/8a03000/8a03800/8a03886v.jpg',
                    'Omaha, Nebraska', 'John Vachon', '1938-11', '1938 年的奥马哈街头'),
    'loc_resid': ('2017717665', 'https://tile.loc.gov/storage-services/service/pnp/fsa/8a03000/8a03800/8a03850v.jpg',
                  'Residential district, Omaha, Nebraska', 'John Vachon', '1938-11', '1938 年奥马哈的住宅区'),
}


def api(params):
    u = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(dict(params, format='json'))
    for k in range(10):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read())
        except Exception as e:
            print("  retry", k, str(e)[:60], flush=True); time.sleep(min(30 * (k + 1), 240))
    raise RuntimeError(u)


def fetch(url, path):
    for k in range(4):
        try:
            data = urllib.request.urlopen(urllib.request.Request(url.split('?')[0], headers=UA), timeout=120).read()
            open(path, 'wb').write(data); return
        except Exception as e:
            print('  retry', k, str(e)[:60], flush=True); time.sleep(min(40 * (k + 1), 240))
    raise RuntimeError(url)


def save_jpg(path):
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(path))
    if im.mode in ('RGBA', 'LA', 'P'):                     # 透明底（勋章 PNG）：铺深色底
        im = im.convert('RGBA'); bg = Image.new('RGBA', im.size, (14, 12, 10, 255)); bg.alpha_composite(im); im = bg
    im = im.convert('RGB')
    if im.width > 2400: im = im.resize((2400, round(im.height * 2400 / im.width)), Image.LANCZOS)
    im.save(path, quality=92)
    return im.size


def doc_pages():
    """伯克希尔 2013 年年报第 114–117 页（PDF 第 116–119 页）→ doc_proposal1/2、doc_bs1946、doc_pl1946"""
    import pypdfium2
    pdf = os.path.join(ROOT, 'research', 'raw', 'ar2013.pdf')
    if not os.path.exists(pdf):
        os.makedirs(os.path.dirname(pdf), exist_ok=True)
        fetch('https://www.berkshirehathaway.com/2013ar/2013ar.pdf', pdf)
    d = pypdfium2.PdfDocument(pdf)
    out = {}
    for name, pg, use in (('doc_proposal1', 116, '1983-08-30 收购提议书第 1 页'), ('doc_proposal2', 117, '1983-08-30 收购提议书第 2 页（签字页）'),
                          ('doc_bs1946', 118, 'NFM 1946 年资产负债表'), ('doc_pl1946', 119, 'NFM 1946 年损益表')):
        p = os.path.join(MDIR, name + '.jpg')
        if not os.path.exists(p):
            d[pg - 1].render(scale=3.0).to_pil().convert('RGB').save(p, quality=92)
        out[name] = dict(file='Berkshire Hathaway 2013 Annual Report, p.%d' % (pg - 2), page='https://www.berkshirehathaway.com/2013ar/2013ar.pdf',
                         artist='Berkshire Hathaway Inc.', license='文件影像（引用）', via='伯克希尔 2013 年年报第 %d 页' % (pg - 2), use=use)
    return out


if __name__ == '__main__':
    cp = os.path.join(MDIR, 'credits.json')
    credits = json.load(open(cp)) if os.path.exists(cp) else {}
    only = set(os.environ['ONLY'].split(',')) if os.environ.get('ONLY') else None
    credits.update(doc_pages()); json.dump(credits, open(cp, 'w'), ensure_ascii=False, indent=1)
    for name, (item, url, title, who, date, use) in LOC.items():
        p = os.path.join(MDIR, name + '.jpg')
        if (os.path.exists(p) and name in credits) or (only and name not in only): continue
        fetch(url, p); sz = save_jpg(p)
        credits[name] = dict(file=title, page='https://www.loc.gov/item/%s/' % item, artist=who + ' (FSA/OWI)', license='Public domain',
                             credit='Library of Congress, FSA/OWI Collection', date=date, use=use)
        print('ok', name, sz, flush=True); json.dump(credits, open(cp, 'w'), ensure_ascii=False, indent=1); time.sleep(3)
    for name, (fn, use) in COMMONS.items():
        p = os.path.join(MDIR, name + '.jpg')
        if (os.path.exists(p) and name in credits) or (only and name not in only): continue
        d = api(dict(action='query', titles='File:' + fn, prop='imageinfo', iiprop='url|extmetadata|size'))
        page = next(iter(d['query']['pages'].values()))
        if 'imageinfo' not in page: print('MISSING', name, fn, flush=True); continue
        ii = page['imageinfo'][0]; md = ii.get('extmetadata', {})
        lic = md.get('LicenseShortName', {}).get('value', '')
        if not any(k in lic.lower() for k in OK_LICENSE): print('SKIP license', name, lic, flush=True); continue
        try:
            fetch(ii['url'], p)
        except RuntimeError:
            print('FAILED (rate limited), next pass:', name, flush=True); time.sleep(120); continue
        sz = save_jpg(p)
        artist = re.sub(r'<[^>]+>', '', md.get('Artist', {}).get('value', '')).strip()
        credits[name] = dict(file=fn, page=ii['descriptionurl'], artist=artist, license=lic,
                             license_url=md.get('LicenseUrl', {}).get('value', ''), use=use,
                             date=re.sub(r'<[^>]+>', '', md.get('DateTimeOriginal', {}).get('value', '')).strip()[:40])
        print('ok', name, sz, lic, '|', artist[:40], flush=True)
        json.dump(credits, open(cp, 'w'), ensure_ascii=False, indent=1)
        time.sleep(25)
