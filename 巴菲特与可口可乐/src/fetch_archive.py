"""下载片中使用的历史图片（Wikimedia 对代理出口限流较严，必要时多次重试或改用 1280px 缩略图）（Wikimedia Commons，公有领域或 CC 授权），并记录作者/授权/来源。
python3 src/fetch_archive.py → assets/archive/*.jpg + assets/archive/credits.json
"""
import json, os, time, urllib.request, urllib.parse, re
FILES = {
    'evans_coke_shack_1935': 'File:Coca-Cola shack in Alabama by Walker Evans.jpg',
    'evans_sandwich_shop_1936': 'File:Roadside sandwich shop. Ponchatoula, Louisiana, 1936-02.jpg',
    'coke_ad_1890s': 'File:Cocacola-5cents-1900 edit1.jpg',
    'bottle_patent_1915': 'File:Coke bottle patent.png',
    'buffett_2015': 'File:Warren Buffett at the 2015 SelectUSA Investment Summit.jpg',
    'munger_2010': 'File:Charlie Munger.jpg',
}
UA = {'User-Agent': 'doc-research/1.0 (contact@example.org)'}
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'assets', 'archive')


def api(params):
    params.update(format='json')
    u = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)
    for k in range(8):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
        except Exception as e: print('retry', e); time.sleep(10 * (k + 1))


def clean(h): return re.sub(r'<[^>]+>', '', h or '').strip()


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    cp = os.path.join(OUT, 'credits.json')
    credits = json.load(open(cp)) if os.path.exists(cp) else {}
    for key, title in FILES.items():
        if key in credits and os.path.exists(os.path.join(OUT, key + '.jpg')): continue
        r = api(dict(action='query', titles=title, prop='imageinfo', iiprop='url|extmetadata|size', iiurlwidth=2200))
        p = list(r['query']['pages'].values())[0]; ii = p['imageinfo'][0]; m = ii['extmetadata']
        url = ii.get('thumburl') or ii['url']
        dst = os.path.join(OUT, key + '.jpg')
        if not os.path.exists(dst):
            data = None
            for k in range(10):
                try:
                    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120)
                    if not r.headers.get('Content-Type', '').startswith('image/'): raise IOError('not an image')
                    data = r.read(); break
                except Exception as e: print('retry dl', e); time.sleep(15 * (k + 1))
            if data is None: print('FAILED', key); continue
            open(dst + '.src', 'wb').write(data)
            os.system(f'ffmpeg -loglevel error -y -i "{dst}.src" -q:v 3 "{dst}" && rm "{dst}.src"')
        credits[key] = dict(title=title, page='https://commons.wikimedia.org/wiki/' + urllib.parse.quote(title.replace(' ', '_')),
                            author=clean(m.get('Artist', {}).get('value')), date=clean(m.get('DateTimeOriginal', {}).get('value')),
                            license=clean(m.get('LicenseShortName', {}).get('value')),
                            license_url=clean(m.get('LicenseUrl', {}).get('value')),
                            credit=clean(m.get('Credit', {}).get('value'))[:300])
        print(key, credits[key]['license'], '|', credits[key]['author'][:60], flush=True)
        json.dump(credits, open(cp, 'w'), ensure_ascii=False, indent=1)
        time.sleep(8)
    json.dump(credits, open(os.path.join(OUT, 'credits.json'), 'w'), ensure_ascii=False, indent=1)
