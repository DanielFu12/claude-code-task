"""下载素材。

    python3 src/fetch.py subs  [年份...]   # 只下字幕/转写稿（几十 KB），用来定位时间码
    python3 src/fetch.py media            # 按 locate 的结果，只下载用得到的片段（yt-dlp --download-sections）
    python3 src/fetch.py whisper [年份...] # 没有字幕的来源：下载音频并用 faster-whisper 逐词转写（可选）

来源配置见 sources.json；本地文件放进 local 列表即可跳过下载（同名 .en.vtt / .json3 / .words.json 作为转写稿）。
"""
import glob, json, os, sys
from common import ROOT, load_json, wpath, run

YTDLP = ['yt-dlp', '--no-warnings', '--no-playlist']


def resolve(year, spec):
    """返回 parts：[{kind, path|url, title}]，结果缓存在 work/src/<year>/parts.json。"""
    cache = wpath('src', year, 'parts.json')
    if os.path.exists(cache):
        return json.load(open(cache))
    parts = []
    for p in spec.get('local', []):
        p = p if os.path.isabs(p) else os.path.join(ROOT, p)
        parts.append({'kind': 'local', 'path': p, 'title': os.path.basename(p)})
    if not parts:
        for u in spec.get('urls', []):
            parts.append({'kind': 'url', 'url': u, 'title': u})
    if not parts and spec.get('search'):
        out = run(YTDLP + ['--flat-playlist', '-J', f"ytsearch12:{spec['search']}"], capture_output=True, text=True).stdout
        ents = [e for e in json.loads(out).get('entries', []) if year in (e.get('title') or '') and (e.get('duration') or 0) >= 3600]
        if not ents:
            sys.exit(f'[{year}] 搜索不到时长 ≥1 小时、标题含年份的视频，请在 sources.json 里手动填 urls')
        best = max(ents, key=lambda e: e.get('duration') or 0)
        parts.append({'kind': 'url', 'url': best.get('url') or f"https://www.youtube.com/watch?v={best['id']}",
                      'title': best.get('title'), 'duration': best.get('duration')})
        print(f'[{year}] 选用: {best.get("title")}  ({(best.get("duration") or 0) / 3600:.1f}h)')
    json.dump(parts, open(cache, 'w'), ensure_ascii=False, indent=1)
    return parts


def transcript_for(year, k, part):
    """找到某个分段的转写稿文件（没有返回 None）。"""
    if part['kind'] == 'local':
        base = os.path.splitext(part['path'])[0]
        cands = [base + e for e in ('.words.json', '.en.json3', '.json3', '.en.vtt', '.vtt', '.en.srt', '.srt')]
    else:
        cands = []
    cands += sorted(glob.glob(wpath('src', year, f'p{k}.words.json'))) + \
        sorted(glob.glob(wpath('src', year, f'p{k}.*.json3'))) + sorted(glob.glob(wpath('src', year, f'p{k}.*.vtt')))
    return next((c for c in cands if os.path.exists(c)), None)


def cmd_subs(years):
    srcs = load_json('sources.json')
    for y in years or [k for k in srcs if not k.startswith('_')]:
        for k, p in enumerate(resolve(y, srcs[y])):
            if transcript_for(y, k, p):
                continue
            if p['kind'] == 'url':
                run(YTDLP + ['--skip-download', '--write-subs', '--write-auto-subs', '--sub-langs', 'en.*,en',
                             '--sub-format', 'json3/vtt/best', '-o', wpath('src', y, f'p{k}.%(ext)s'), p['url']])
            if not transcript_for(y, k, p):
                print(f'[{y}] 分段 {k} 没有字幕，请运行: python3 src/fetch.py whisper {y}')


def cmd_whisper(years):
    from faster_whisper import WhisperModel             # pip install faster-whisper
    model = WhisperModel(os.environ.get('WHISPER_MODEL', 'small.en'), compute_type='int8')
    srcs = load_json('sources.json')
    for y in years or [k for k in srcs if not k.startswith('_')]:
        for k, p in enumerate(resolve(y, srcs[y])):
            out = wpath('src', y, f'p{k}.words.json')
            if transcript_for(y, k, p):
                continue
            audio = p['path'] if p['kind'] == 'local' else wpath('src', y, f'p{k}.m4a')
            if p['kind'] == 'url' and not os.path.exists(audio):
                run(YTDLP + ['-f', 'ba[ext=m4a]/ba', '-o', audio, p['url']])
            segs, _ = model.transcribe(audio, word_timestamps=True, vad_filter=True)
            words = [[w.word, w.start, w.end] for s in segs for w in s.words]
            json.dump(words, open(out, 'w'))
            print(f'[{y}] 分段 {k}: {len(words)} 词 -> {out}')


def cmd_media():
    loc = json.load(open(wpath('located.json')))
    srcs = load_json('sources.json')
    media = {}
    for cid, seg in loc.items():
        part = resolve(seg['source'], srcs[seg['source']])[seg['part']]
        if part['kind'] == 'local':
            media[cid] = {'path': part['path'], 't0': 0.0}
            continue
        a, b = max(0.0, seg['start'] - 4), seg['end'] + 4
        out = wpath('media', f'{cid}.mp4')
        if not os.path.exists(out):
            run(YTDLP + ['-f', 'bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=1080]+ba/b',
                         '--merge-output-format', 'mp4', '--download-sections', f'*{a:.2f}-{b:.2f}',
                         '--force-keyframes-at-cuts', '-o', out, part['url']])
        media[cid] = {'path': out, 't0': a}
    json.dump(media, open(wpath('media.json'), 'w'), ensure_ascii=False, indent=1)
    print(f'{len(media)} 段素材就绪 -> {wpath("media.json")}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'subs'
    {'subs': lambda: cmd_subs(sys.argv[2:]), 'whisper': lambda: cmd_whisper(sys.argv[2:]),
     'media': cmd_media}[cmd]()
