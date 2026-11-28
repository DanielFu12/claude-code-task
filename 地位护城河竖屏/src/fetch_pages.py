"""Commons 素材（v3 补充）：API 被限流时，改从文件页 HTML 取作者 / 许可，从缩略图 / 转码地址下载。
python3 src/fetch_pages.py   → media/<key>.jpg、media_raw/<key>.webm，登记到 media/credits.json"""
import os, re, json, time, html, hashlib, urllib.request, urllib.parse
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); OUT = os.path.join(ROOT, 'media'); RAW = os.path.join(ROOT, 'media_raw')
UA = {'User-Agent': 'BamanValueResearch/1.1 (https://github.com/danielfu12/claude-code-task; educational video credits)'}
WANT = {
    'moutai_bottle': 'Maotai - Kweichow Moutai Distillery China, Flasche (1).jpg',
    # 'moutai_bottle2': 'Maotai - Kweichow Moutai Distillery China, Flasche (2).jpg',   （未用到）
    # 'maotai_town': 'Chishui River Bank in Maotai(Moutai) Town, Renhuai City, Zunyi, Guizhou.jpg',   （未用到）
    # 'maotai_vendor': '201904 A Maotai vendor in the city of Zunyi 01.jpg',   （未用到）
    # 'moutai_auction': 'HK Wan Chai North 灣仔北 Grand Hyatt Hotel 保利集團 Poly Auction preview exhibits 拍賣 Moutai 貴州茅台酒 Maotai 大麯白酒 Sept 2017 IX1 08 bottles.jpg',   （未用到）
    'banquet': 'Chinese banquet in a banquet hall.JPG',
    'iphone17_launch': 'IPhone 17 launch at Apple TRX Malaysia 08.jpg',
    'iphone17_launch2': 'IPhone 17 launch at Apple TRX Malaysia 55.jpg',
    # 'apple_queue': 'Line at Apple Store in NYC.jpg',   （未用到）
    'veblen': 'Veblen3a.jpg',
    'hermes_scarf': 'Hermès silk scarf in shop window in London.jpg',
    'v_labubu_bj': '实探LABUBU北京快闪店 外国游客：女儿特地让我来买.webm',
    'v_labubu_hk': '香港设计火爆全球 Labubu撬动香港潮玩经济、旅游热.webm',
}


def get(url, tries=8):
    for k in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300).read()
        except Exception as e: print('  retry', k, str(e)[:80], flush=True); time.sleep(30 + 30 * k)
    return None


def strip(x): return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', x))).strip()


cp = os.path.join(OUT, 'credits.json'); cred = json.load(open(cp))
for key, name in WANT.items():
    if key in cred: continue
    fn = name.replace(' ', '_'); h = hashlib.md5(fn.encode()).hexdigest(); q = urllib.parse.quote(fn)
    page = get('https://commons.wikimedia.org/wiki/File:' + q)
    if not page: print('MISS page', key); continue
    page = page.decode('utf-8', 'ignore')
    lic = re.search(r'licensetpl(?:_|&#95;)short"[^>]*>(.*?)</span>', page, re.S)
    aut = re.search(r'fileinfotpl(?:_|&#95;)aut"[^>]*>.*?</td>\s*<td[^>]*>(.*?)</td>', page, re.S)
    dim = re.search(r'([\d,]+) × ([\d,]+) pixels', page)
    lic = strip(lic.group(1)) if lic else '?'; aut = strip(aut.group(1))[:80] if aut else '?'
    w = int(dim.group(1).replace(',', '')) if dim else 0
    base = 'https://upload.wikimedia.org/wikipedia/commons/'
    if key.startswith('v_'):
        dst = os.path.join(RAW, key + '.webm'); data = None
        for r in ('1080p', '720p'):
            data = get(base + 'transcoded/%s/%s/%s/%s.%s.vp9.webm' % (h[0], h[:2], q, q, r), 4)
            if data: break
    else:
        # 原图被限流（429）；缩略图层只稳定提供已缓存的标准尺寸，按从大到小逐个试
        dst = os.path.join(OUT, key + '.jpg'); std = [s for s in (1920, 1280, 1024, 960, 800, 640) if s < w] if w else [1280, 1024, 800]
        data = None
        for sz in std:
            data = get(base + 'thumb/%s/%s/%s/%dpx-%s' % (h[0], h[:2], q, sz, q), 1)
            if data: break
            time.sleep(4)
    if not data: print('FAIL', key); continue
    if key.startswith('v_'): open(dst, 'wb').write(data)
    else:
        tmp = dst + '.tmp'; open(tmp, 'wb').write(data)
        from PIL import Image; Image.open(tmp).convert('RGB').save(dst, quality=94); os.remove(tmp)
    cred[key] = dict(file='File:' + name, page='https://commons.wikimedia.org/wiki/File:' + q, license=lic, artist=aut, date='')
    json.dump(cred, open(cp, 'w'), ensure_ascii=False, indent=1)
    print('ok', key, lic, aut[:40], w, flush=True); time.sleep(12)
