"""下载 Wikimedia Commons 图片（缩略到长边 2400），记录作者与许可 → media/credits.json
python3 src/fetch_media.py"""
import os, sys, json, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commons_search import api, UA, search
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); OUT = os.path.join(ROOT, 'media')
# key: (检索词, 文件名须包含的片段)
WANT = {
    'hotdog_v': ('Costco hot dog Taichung', 'Taichung Taiwan (vertical)'),
    'hotdog_drink': ('Hamamatsu Costco Hot Dog', 'Hot Dog and drink'),
    'ofo_station': ('ofo bicycles', 'Jiangning Road Station'),
    'ofo_hangzhou': ('ofo bicycles', 'Ofo in Hangzhou'),
    'ofo_hq': ('ofo bicycles', 'ofo HQ'),
    'byd_seagull': ('BYD Seagull', 'Seagull 009'),
    'byd_seagull2': ('BYD Seagull', 'Seagull 010'),
    'byd_seal': ('BYD Seal', '1X7A0026'),
    'byd_hq': ('BYD headquarters Shenzhen', 'headquarters 01'),
    'byd_show': ('BYD headquarters Shenzhen', 'showcased at BYD HQ, Shenzhen, China 01'),
    'pdd_poster': ('Pinduoduo', 'red poster July 2025'),
    'pdd_pickup': ('Pinduoduo', 'logistics'),
    'pdd_goods': ('Pinduoduo', 'HuDieSu'),
    'pdd_logo': ('Pinduoduo', 'Pinduoduologo'),
    'costco_tc': ('Costco warehouse', 'Taichung Warehouse'),
    'costco_checkout': ('Costco shopping carts', 'Checkouts at 1st Floor'),
    'costco_guests': ('Costco shopping carts', 'Guests Walking'),
}
cred = json.load(open(os.path.join(OUT, 'credits.json'))) if os.path.exists(os.path.join(OUT, 'credits.json')) else {}
cache = {}
for key, (q, sub) in WANT.items():
    if key in cred and os.path.exists(os.path.join(OUT, key + '.jpg')): continue
    if q not in cache: cache[q] = search(q, 20); time.sleep(6)
    hit = [r for r in cache[q] if sub.lower() in r['title'].lower()]
    if not hit: print('MISS', key); continue
    r = hit[0]
    url = r['url'].split('?')[0]
    if r['w'] > 1920:
        a, b = url.split('/wikipedia/commons/'); name = b.split('/')[-1]
        url = a + '/wikipedia/commons/thumb/' + b + '/1920px-' + name + ('.png' if name.lower().endswith(('.png', '.svg')) else '')
    for k in range(5):
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read(); break
        except Exception as e: print('retry', key, e); time.sleep(30 * (k + 1))
    ext = '.png' if url.lower().endswith('.png') else '.jpg'
    p = os.path.join(OUT, key + ext); open(p, 'wb').write(data)
    if ext == '.png':
        from PIL import Image; im = Image.open(p)
        if key != 'pdd_logo': im.convert('RGB').resize((min(im.width,2600), round(im.height*min(im.width,2600)/im.width))).save(os.path.join(OUT, key + '.jpg'), quality=94); os.remove(p)
    import re
    cred[key] = dict(file=r['title'], page=r['page'], license=r['lic'], artist=re.sub('<[^>]+>', '', r['artist']).strip(), date=r['date'])
    json.dump(cred, open(os.path.join(OUT, 'credits.json'), 'w'), ensure_ascii=False, indent=1)
    print('ok', key, r['title'][:70], r['lic']); time.sleep(5)
