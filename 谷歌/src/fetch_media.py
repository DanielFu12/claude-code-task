"""外部素材下载（需要网络能访问 commons.wikimedia.org、upload.wikimedia.org、archive.org）。
- 照片：Wikimedia Commons，经 API 取作者、授权、原始页面，写进 assets/media/credits.json；只收 CC0 / 公有领域 / CC BY / CC BY-SA。
- 影像：Internet Archive，按时间段远程截取（不整片下载），写进 assets/media/ia_clips.json。
- 下载后必须抽帧审片，不合格的从 USABLE 里排除（制作宪章 二.4）。
python3 src/fetch_media.py            # 下载全部
python3 src/fetch_media.py --search   # 只在 Commons / IA 上搜候选，打印出来供人工挑选（不下载）
2026-11-13 本会话网络白名单不含以上站点，脚本未能运行；候选文件名来自检索结果，运行时以 API 返回为准。
"""
import os, sys, json, subprocess, urllib.parse, urllib.request
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MDIR = os.path.join(ROOT, 'assets', 'media'); OUT = os.path.join(ROOT, 'work_clips')
os.makedirs(MDIR, exist_ok=True); os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'baman-value-doc/1.0 (research use)'}
OK_LICENSE = ('cc0', 'public domain', 'pd', 'cc by', 'cc-by')

# 名称: (Commons 文件名, 用在哪里)
PHOTOS = {
    'g_founders_2008': ('Schmidt-Brin-Page-20080520.jpg', 'c1d 施密特、布林、佩奇（2008，CC BY 2.0）'),
    'g_tpu3': ('Tensor_Processing_Unit_3.0.jpg', 'm7 TPU'),
    'g_googleplex': ('Googleplex_HQ_(cropped).jpg', '第一章 / 片尾 谷歌总部'),
    'g_dc_dalles': ('Google_Data_Center,_The_Dalles.jpg', '第六章 数据中心外景'),
}
# Commons 搜索词（--search 用）：挑出 CC 授权的实拍
COMMONS_QUERIES = ['Google data center Council Bluffs', 'Google data center', 'Googleplex', 'Larry Page Sergey Brin 2004',
                   'Charlie Munger', 'Burlington Northern Santa Fe train', 'GEICO gecko', 'Google search on smartphone',
                   'YouTube on smartphone', 'Android phone', 'Mehta courthouse E. Barrett Prettyman', 'Gemini app']
# Internet Archive 片源（前几期已用过、已审过的条目，可直接复用）
IA_SRC = {
    'mung': ('youtube-F6s2HAzMeL0', 'F6s2HAzMeL0.webm', 'Becoming Warren Buffett：Charlie Munger 访谈（HBO, 2017）'),
    'bwb': ('youtube-pKWN0YFf_14', None, 'Becoming Warren Buffett（HBO, 2017）片段'),
}
IA_CLIPS = {   # 名称: (片源, 起点秒, 时长, 用途) —— 时间段沿用第三期已审过的区间
    'x_bwbm_munger': ('mung', 566, 20, 'm4 / c2d 芒格'),
    'x_bwb_meeting': ('bwb', 346, 30, '开场 / 第二章 股东大会'),
    'x_bwb_arena': ('bwb', 424, 6, '开场 股东大会会场'),
    'x_bwb_office': ('bwb', 310, 12, '第五章 巴菲特办公室'),
}
IA_QUERIES = ['Google IPO 2004', 'Google data center tour', 'Berkshire Hathaway annual meeting 2017', 'AltaVista 1999',
              'Google search 2004', 'Eric Schmidt Larry Page Sergey Brin interview 2004', 'TPU Google Cloud']


def api(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))


def photo(name, fn):
    q = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(dict(
        action='query', titles='File:' + fn, prop='imageinfo', iiprop='url|extmetadata', iiurlwidth=2560, format='json'))
    page = next(iter(api(q)['query']['pages'].values()))
    if 'imageinfo' not in page: return 'MISSING'
    ii = page['imageinfo'][0]; md = ii['extmetadata']; lic = md.get('LicenseShortName', {}).get('value', '')
    if not lic.lower().startswith(OK_LICENSE): return 'SKIP license=' + lic
    urllib.request.urlretrieve(ii.get('thumburl') or ii['url'], os.path.join(MDIR, name + '.jpg'))
    cr = json.load(open(os.path.join(MDIR, 'credits.json'))) if os.path.exists(os.path.join(MDIR, 'credits.json')) else {}
    cr[name] = dict(title='File:' + fn, page=ii['descriptionurl'], license=lic,
                    artist=md.get('Artist', {}).get('value', ''), date=md.get('DateTimeOriginal', {}).get('value', ''),
                    desc=md.get('ImageDescription', {}).get('value', '')[:300])
    json.dump(cr, open(os.path.join(MDIR, 'credits.json'), 'w'), ensure_ascii=False, indent=1)
    return 'ok ' + lic


def clip(name):
    src, t0, d, _ = IA_CLIPS[name]; ident, fn, _ = IA_SRC[src]
    if fn is None:
        md = api(f'https://archive.org/metadata/{ident}')
        fn = max((f for f in md['files'] if f['name'].endswith('.mp4')), key=lambda f: int(f.get('height') or 0))['name']
    url = f'https://archive.org/download/{ident}/' + urllib.parse.quote(fn)
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', str(t0), '-i', url, '-t', str(d), '-an', '-r', '30',
                        '-vf', "scale=-2:1080:flags=lanczos", '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p',
                        os.path.join(OUT, name + '.mp4')], capture_output=True, text=True)
    return 'ok' if r.returncode == 0 else 'FAIL ' + r.stderr[-200:]


def search():
    for q in COMMONS_QUERIES:
        r = api('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(dict(
            action='query', list='search', srsearch=q, srnamespace=6, srlimit=15, format='json')))
        print('## Commons:', q); [print('  ', h['title']) for h in r['query']['search']]
    for q in IA_QUERIES:
        r = api('https://archive.org/advancedsearch.php?' + urllib.parse.urlencode(
            {'q': f'({q}) AND mediatype:movies', 'fl[]': ['identifier', 'title', 'licenseurl'], 'rows': 15, 'output': 'json'}, doseq=True))
        print('## IA:', q); [print('  ', d['identifier'], '|', d.get('title'), '|', d.get('licenseurl', '')) for d in r['response']['docs']]


if __name__ == '__main__':
    if '--search' in sys.argv: search(); sys.exit()
    for k, (fn, _) in PHOTOS.items():
        try: print(k, photo(k, fn))
        except Exception as e: print(k, 'FAIL', e)
    meta = json.load(open(os.path.join(MDIR, 'ia_clips.json'))) if os.path.exists(os.path.join(MDIR, 'ia_clips.json')) else {}
    for k, (src, t0, d, use) in IA_CLIPS.items():
        st = clip(k); print(k, st)
        if st == 'ok': meta[k] = dict(source=IA_SRC[src][2], ia='https://archive.org/details/' + IA_SRC[src][0], start=t0, dur=d, note=use)
    json.dump(meta, open(os.path.join(MDIR, 'ia_clips.json'), 'w'), ensure_ascii=False, indent=1)
