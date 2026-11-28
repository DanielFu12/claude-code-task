"""按 Commons 文件名批量下载（图片取 1920px 缩略图，视频取原文件），登记作者与许可 → media/credits.json
python3 src/fetch_titles.py"""
import os, sys, json, time, re, urllib.request, urllib.parse
UA = {'User-Agent': 'BamanValueResearch/1.1 (https://github.com/danielfu12/claude-code-task; educational video credits)'}
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); OUT = os.path.join(ROOT, 'media'); RAW = os.path.join(ROOT, 'media_raw')
os.makedirs(RAW, exist_ok=True)
WANT = {
    'queue1': 'HK SKD TKO Tseung Kwan O PopCorn mall Pop Deli shop Pop Mart Toy Store n visitors queue April 2025 R12S 01.jpg',
    'queue3': 'HK SKD TKO Tseung Kwan O PopCorn mall Pop Deli shop Pop Mart Toy Store n visitors queue April 2025 R12S 03.jpg',
    'nyc_store': 'Labubu Pop Mart store in New York City.jpg',
    'browsing': 'Browsing for Labubu.jpg',
    'no_labubu': 'We do not sell Labubu.jpg',
    'lafufu': 'A Lafufu (Fake Labubu).jpg',
    'iphone_orange': 'Cosmic Orange iPhone 17 Pro Max.jpg',
    'iphone_back': 'IPhone 17 Pro backside (Cosmic Orange) (Oct 1, 2025).jpg',
    'iphone_line': 'IPhone 17, Air, 17 Pro, and Pro max.jpg',
    'birkin': 'Hermes Birkin.JPG',
    'birkin2': 'Hermes Birkin-2.jpg',
    'birkin_croc': 'Croc Birkin bag.jpg',
    'hermes_paris': 'Hermès Store, Avenue George V, Paris 8e 001.JPG',
    'hermes_paris2': 'Hermès, 42 avenue George-V, 75008 Paris, 15 September 2019.jpg',
    'hermes_ginza': 'Exterior view of the illuminated facade of Maison Hermès, Ginza, Tokyo, Japan.jpg',
    'hermes_lutetia': 'Paris - Piscine Lutetia - Boutique Hermès (27936484975).jpg',
    'peacock': 'Majestic Peacock Display at Pench National Park, India.jpg',
    'munger': 'Charlie Munger (cropped).jpg',
    'sams_sz': "SAM'S CLUB SHENZHEN.jpg",
    'sams_bj': 'Sam\'s Club Beijing Houshayu (20240727170026).jpg',
    'himalaya': 'Dhaulagiri, Himalaya, Nepal.jpg',
    'gold_bracelet': 'Gold bracelet MET DT333008edited3.jpg',
    # 视频
    'v_airport': '7米高特别版LABUBU亮相香港国际机场.webm',
    'v_peacock': 'Peacock displaying in Sri Lanka.webm',
}
def api(params):
    url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)
    for k in range(10):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
        except Exception as e: print('wait', e); time.sleep(20 + 15 * k)
def dl(url, p):
    for k in range(8):
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300).read(); open(p, 'wb').write(data); return True
        except Exception as e: print('retry', os.path.basename(p), e, flush=True); time.sleep(120 + 60 * k)
    return False
cp = os.path.join(OUT, 'credits.json'); cred = json.load(open(cp)) if os.path.exists(cp) else {}
todo = {k: v for k, v in WANT.items() if k not in cred or cred[k].get('artist') == 'PLACEHOLDER'}
info = {}
keys = list(todo)
for i in range(0, len(keys), 20):
    titles = '|'.join('File:' + todo[k] for k in keys[i:i + 20])
    d = api({'action': 'query', 'format': 'json', 'titles': titles, 'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata|mime|derivatives',
             'iiextmetadatafilter': 'LicenseShortName|Artist|DateTimeOriginal'})
    norm = {n['to']: n['from'] for n in d['query'].get('normalized', [])}
    for p in d['query']['pages'].values():
        if 'imageinfo' not in p: print('MISSING', p.get('title')); continue
        info[norm.get(p['title'], p['title'])] = (p['title'], p['imageinfo'][0])
    time.sleep(8)
for k in keys:
    hit = info.get('File:' + todo[k])
    if not hit: print('MISS', k); continue
    title, ii = hit; m = ii.get('extmetadata', {})
    if k.startswith('v_'):
        p = os.path.join(RAW, k + '.webm'); url = ii['url'].split('?')[0]
        der = sorted([x for x in ii.get('derivatives', []) if x.get('transcodekey', '').endswith('.webm') and x.get('height', 0) <= 1080],
                     key=lambda x: -x.get('height', 0))
        if der: url = der[0]['src']   # 转码版（≤1080p）比原文件更不容易被限流
        ok = os.path.exists(p) or dl(url, p)
    else:
        url = ii['url'].split('?')[0]
        std = [s for s in (1920, 1280, 960) if s < ii['width']]   # 原图常被限流，只取 Commons 标准缩略图尺寸
        if std:
            a, b = url.split('/wikipedia/commons/'); name = b.split('/')[-1]
            url = a + '/wikipedia/commons/thumb/' + b + '/%dpx-' % std[0] + name + ('.png' if name.lower().endswith(('.png', '.svg')) else '')
        p = os.path.join(OUT, k + '.jpg'); tmp = p + '.tmp'; ok = dl(url, tmp)
        if ok:
            from PIL import Image; Image.open(tmp).convert('RGB').save(p, quality=94); os.remove(tmp)
    if not ok: print('FAIL', k); continue
    cred[k] = dict(file=title, page=ii.get('descriptionurl'), license=m.get('LicenseShortName', {}).get('value'),
                   artist=re.sub(r'\s+', ' ', re.sub('<[^>]+>', '', m.get('Artist', {}).get('value', ''))).strip(), date=m.get('DateTimeOriginal', {}).get('value', ''))
    json.dump(cred, open(cp, 'w'), ensure_ascii=False, indent=1)
    print('ok', k, cred[k]['license'], cred[k]['artist'][:40], flush=True); time.sleep(25)
