"""Wikimedia Commons 检索（限速、带 UA）。python3 src/commons_search.py "query" [n]"""
import sys, json, time, urllib.request, urllib.parse
UA = {'User-Agent': 'BamanValueShortFilm/1.0 (https://claude.ai/code; educational, low-volume) python-urllib'}
def api(params, tries=6):
    url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)
    for k in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))
        except Exception as e:
            time.sleep(10 + 10 * k)
    raise RuntimeError('api failed')
def search(q, n=12):
    d = api({'action': 'query', 'format': 'json', 'generator': 'search', 'gsrnamespace': 6, 'gsrlimit': n,
             'gsrsearch': q, 'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata|mime',
             'iiextmetadatafilter': 'LicenseShortName|Artist|DateTimeOriginal'})
    out = []
    for p in d.get('query', {}).get('pages', {}).values():
        ii = p['imageinfo'][0]; m = ii.get('extmetadata', {})
        out.append(dict(title=p['title'], w=ii['width'], h=ii['height'], mime=ii.get('mime'), url=ii['url'],
                        page=ii.get('descriptionurl'), lic=m.get('LicenseShortName', {}).get('value'),
                        artist=m.get('Artist', {}).get('value', ''), date=m.get('DateTimeOriginal', {}).get('value', '')))
    return out
if __name__ == '__main__':
    for q in sys.argv[1:]:
        print('==', q)
        for r in search(q):
            print('  %-75s %5dx%-5d %s %s' % (r['title'][:75], r['w'], r['h'], r['lic'], r['mime']))
        time.sleep(9)
