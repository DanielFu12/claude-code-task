"""补充素材：按文件页里实际嵌入的图片地址（浏览器打开文件页时加载的那几张）下载，取其中最大的一张；作者 / 许可从同一页面解析。
python3 src/fetch_embedded.py key=文件名 ...   → media/<key>.jpg，登记到 media/credits.json"""
import os, re, sys, json, time, html, urllib.request, urllib.parse
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); OUT = os.path.join(ROOT, 'media')
UA = {'User-Agent': 'BamanValueResearch/1.1 (educational video credits)'}
def get(u):
    try: return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120).read()
    except Exception as e: print('  ', str(e)[:60], u[:110]); return None
def strip(x): return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', x))).strip()
cp = os.path.join(OUT, 'credits.json'); cred = json.load(open(cp))
for arg in sys.argv[1:]:
    key, name = arg.split('=', 1)
    if key in cred and os.path.exists(os.path.join(OUT, key + '.jpg')): continue
    q = urllib.parse.quote(name.replace(' ', '_')); page = get('https://commons.wikimedia.org/wiki/File:' + q)
    if not page: continue
    page = page.decode('utf-8', 'ignore')
    lic = re.search(r'licensetpl(?:_|&#95;)short"[^>]*>(.*?)</span>', page, re.S)
    aut = re.search(r'fileinfotpl(?:_|&#95;)aut"[^>]*>.*?</td>\s*<td[^>]*>(.*?)</td>', page, re.S)
    lic = strip(lic.group(1)) if lic else '?'; aut = strip(aut.group(1))[:80] if aut else '?'
    stem = re.escape(q.split('.')[0][:20])
    urls = set(html.unescape(u) for u in re.findall(r'(//upload\.wikimedia\.org/wikipedia/commons/[^" ,]+)', page) if '/archive/' not in u and 'utm_content=original' not in u)
    def size(u):
        m = re.search(r'/(\d+)px-', u); return int(m.group(1)) if m else (5000 if 'thumbnail_unscaled' in u else 0)
    data = None
    for u in sorted(urls, key=size, reverse=True):
        if urllib.parse.unquote(q)[:12].lower() not in urllib.parse.unquote(u).lower(): continue
        data = get('https:' + u); time.sleep(3)
        if data and len(data) > 20000: print('got', key, size(u), u[-60:]); break
        data = None
    if not data: print('FAIL', key); continue
    tmp = os.path.join(OUT, key + '.tmp'); open(tmp, 'wb').write(data)
    from PIL import Image; im = Image.open(tmp).convert('RGB'); im.save(os.path.join(OUT, key + '.jpg'), quality=94); os.remove(tmp)
    cred[key] = dict(file='File:' + name, page='https://commons.wikimedia.org/wiki/File:' + q, license=lic, artist=aut, date='')
    json.dump(cred, open(cp, 'w'), ensure_ascii=False, indent=1); print('ok', key, im.size, lic, aut[:40], flush=True); time.sleep(5)
