"""Wikimedia Commons 素材检索与下载（只取允许再使用的授权：公有领域 / CC0 / CC BY / CC BY-SA），记录作者与授权，供片尾与 SOURCES 署名。
python3 src/commons.py search OUT.json "query" [video|bitmap] ...   # 多组查询
python3 src/commons.py get "File:xxx.jpg" DEST [width]
"""
import sys, json, time, urllib.request, urllib.parse, os, re
UA = 'BamangValueDocumentary/1.0 (https://github.com/DanielFu12/claude-code-task; research use)'
API = 'https://commons.wikimedia.org/w/api.php'
OK = re.compile(r'(public domain|^pd|cc0|cc[- ]by(-sa)?[- ]?[0-9.]*$|cc[- ]by(-sa)?[- ][0-9.]+)', re.I)


def call(params, tries=8):
    url = API + '?' + urllib.parse.urlencode({**params, 'format': 'json'})
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60))
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(int(e.headers.get('retry-after') or 30) + 2); continue
            raise
    raise RuntimeError('rate limited')


def info(titles, width=None):
    p = dict(action='query', titles='|'.join(titles), prop='imageinfo', iiprop='url|size|mime|extmetadata|mediatype')
    if width: p['iiurlwidth'] = width
    d = call(p); out = []
    for pg in d['query']['pages'].values():
        if 'imageinfo' not in pg: continue
        ii = pg['imageinfo'][0]; em = ii.get('extmetadata', {})
        g = lambda k: re.sub('<[^>]+>', '', em.get(k, {}).get('value', '')).strip()
        out.append(dict(title=pg['title'], url=ii['url'], thumb=ii.get('thumburl'), w=ii.get('width'), h=ii.get('height'),
                        mime=ii.get('mime'), dur=ii.get('duration'), license=g('LicenseShortName'), artist=g('Artist')[:120],
                        credit=g('Credit')[:120], date=g('DateTimeOriginal')[:40], desc=g('ImageDescription')[:200],
                        ok=bool(OK.search(g('LicenseShortName')))))
    return out


def search(q, kind=None, n=25):
    s = q + (f' filetype:{kind}' if kind else '')
    d = call(dict(action='query', list='search', srsearch=s, srnamespace=6, srlimit=n))
    titles = [x['title'] for x in d['query']['search']]
    res = []
    for i in range(0, len(titles), 20): res += info(titles[i:i + 20]); time.sleep(1)
    return res


def get(title, dest, width=None):
    it = info([title], width)[0]
    url = it['thumb'] if width and it.get('thumb') else it['url']
    for i in range(8):
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=300).read(); break
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(int(e.headers.get('retry-after') or 30) + 2); continue
            raise
    open(dest, 'wb').write(data)
    return it


if __name__ == '__main__':
    if sys.argv[1] == 'search':
        out = sys.argv[2]; res = json.load(open(out)) if os.path.exists(out) else {}
        args = sys.argv[3:]
        for q in args:
            kind = None
            if '|' in q: q, kind = q.split('|')
            if q + str(kind) in res: continue
            try: res[q + str(kind)] = search(q, kind)
            except Exception as e: print('fail', q, e); continue
            json.dump(res, open(out, 'w'), ensure_ascii=False, indent=1)
            print(q, kind, len(res[q + str(kind)]), flush=True); time.sleep(2)
    elif sys.argv[1] == 'get':
        print(json.dumps(get(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else None), ensure_ascii=False))
