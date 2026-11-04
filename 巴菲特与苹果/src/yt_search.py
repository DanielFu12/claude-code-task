"""YouTube 知识共享（CC BY）视频检索：只保留 license 字段为 Creative Commons 的视频（允许再使用，需署名）。
python3 src/yt_search.py OUT.json "query" ...
"""
import sys, json, subprocess, os
out = sys.argv[1]; res = json.load(open(out)) if os.path.exists(out) else {}
for q in sys.argv[2:]:
    if q in res: continue
    url = 'https://www.youtube.com/results?search_query=' + q.replace(' ', '+') + '&sp=EgIwAQ%253D%253D'
    ids = subprocess.run(['yt-dlp', '--flat-playlist', '--playlist-end', '12', '--print', '%(id)s', url],
                         capture_output=True, text=True, timeout=300).stdout.split()
    items = []
    for vid in ids:
        r = subprocess.run(['yt-dlp', '-J', '--skip-download', f'https://www.youtube.com/watch?v={vid}'], capture_output=True, text=True, timeout=300)
        try: j = json.loads(r.stdout)
        except Exception: continue
        items.append(dict(id=vid, title=j.get('title'), channel=j.get('channel'), uploader_url=j.get('uploader_url') or j.get('channel_url'),
                          license=j.get('license'), duration=j.get('duration'), height=j.get('height'), date=j.get('upload_date'),
                          desc=(j.get('description') or '')[:300]))
    res[q] = items; json.dump(res, open(out, 'w'), ensure_ascii=False, indent=1)
    print(q, len(items), sum(1 for i in items if i['license'] and 'Creative' in i['license']), flush=True)
