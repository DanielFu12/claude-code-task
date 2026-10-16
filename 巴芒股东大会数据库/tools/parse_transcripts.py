#!/usr/bin/env python3
"""把 CNBC Buffett Archive 逐字稿（GitHub 镜像 pzponge/Yestoday）切成章节级数据。

用法：
    git clone --depth 1 --filter=blob:none --sparse https://github.com/pzponge/Yestoday SRC
    (cd SRC && git sparse-checkout set Warren_Buffett/Berkshire_Hathaway_Annual_Meeting)
    python3 tools/parse_transcripts.py SRC/Warren_Buffett/Berkshire_Hathaway_Annual_Meeting data/chapters.jsonl

每一章输出：year, session(morning/afternoon/full), chapter(CNBC 章节号), title, paragraphs
(英文段落，含说话人)，以及在本场中的累计词数位置，供估算时间与原话校验使用。
双语稿只保留英文行；章节号必须在本场内递增，用来排除讲话中的编号列表。
"""
import json
import re
import sys
from pathlib import Path

CJK = re.compile(r'[一-鿿]')
HEAD = re.compile(r'^(?:#+\s*)?\**\s*(\d{1,3})\\?\.\s+(.*?)\s*\**\s*(?:</br>.*)?$')
SESSION = re.compile(r'^(?:#+\s*)?\**\s*(morning|afternoon)\s+session', re.I)
SPEAKER = re.compile(r"^([A-Z][A-Z .’'\-]{1,40}?):\s*(.*)$")


def clean(s):
    s = s.replace('\\', '').replace('**', '').strip()
    s = re.sub(r'</?br>', '', s)
    return s


def english_only(line):
    # 双语稿：保留不含汉字的行；行内英文后接中文的，截掉中文部分
    if not CJK.search(line):
        return line
    m = CJK.search(line)
    head = line[:m.start()]
    return head if len(head) > 40 and not CJK.search(head) else ''


def parse_file(path, year):
    lines = path.read_text(encoding='utf-8').split('\n')
    session = 'morning'
    seen_session_header = False
    chapters, cur = [], None
    last_no = 0
    for raw in lines:
        line = raw.rstrip()
        sm = SESSION.match(line)
        if sm and len(line) < 80:
            new = sm.group(1).lower()
            if seen_session_header or new == 'afternoon':
                session = new
            seen_session_header = True
            continue
        hm = HEAD.match(line)
        if hm:
            no = int(hm.group(1))
            title = clean(hm.group(2))
            title = re.split(r'\s*</br>', title)[0]
            if CJK.search(title):
                title = english_only(title) or title
            # 章节号回到 1：进入下一场（部分年份没有“Afternoon session”标题）
            if no == 1 and last_no > 1:
                session = 'afternoon' if session == 'morning' else session
            if no == last_no + 1 or (no == 1 and last_no > 1) or (no == 1 and last_no == 0):
                cur = {'year': year, 'session': session, 'chapter': no,
                       'title': title, 'paragraphs': []}
                chapters.append(cur)
                last_no = no
                continue
        if cur is None:
            continue
        text = english_only(line).strip()
        if not text or text.startswith('---'):
            continue
        cur['paragraphs'].append(clean(text))
    return chapters


def parse_2024(path):
    """2024 年镜像是 Kingswell 英文稿 + RanRan 中译，按“问题 N”分节而不是 CNBC 章节。
    这里每个标题算一章（章节号为本库编号），“07. 下午开场”起算下午场。"""
    chapters, cur, session = [], None, 'morning'
    n = 0
    for raw in path.read_text(encoding='utf-8').split('\n'):
        line = raw.rstrip()
        m = re.match(r'^#+\s*(.+)$', line)
        if m:
            title = clean(m.group(1))
            if title.startswith('07'):
                session, n = 'afternoon', 0
            if 'Q&A' in title:
                continue
            n += 1
            title = re.sub(r'^\d+\.\s*', '', title)
            cur = {'year': 2024, 'session': session, 'chapter': n, 'title': title,
                   'title_lang': 'zh', 'paragraphs': []}
            chapters.append(cur)
            continue
        if cur is None:
            continue
        text = english_only(line).strip()
        if text and not text.startswith('---'):
            cur['paragraphs'].append(clean(text))
    return chapters


def attach_speakers(ch):
    speaker = None
    out = []
    for p in ch['paragraphs']:
        m = SPEAKER.match(p)
        if m:
            speaker = m.group(1).strip()
            body = m.group(2).strip()
            if not body:
                continue
            out.append({'speaker': speaker, 'text': body})
        else:
            out.append({'speaker': speaker, 'text': p})
    ch['paragraphs'] = out
    words = {}
    for p in out:
        words[p['speaker'] or '?'] = words.get(p['speaker'] or '?', 0) + len(p['text'].split())
    ch['words_by_speaker'] = words
    ch['words'] = sum(words.values())


def main(src, dst):
    src = Path(src)
    rows = []
    for f in sorted(src.glob('*_Annual_Meeting.md')):
        year = int(f.name[:4])
        chs = parse_2024(f) if year == 2024 else parse_file(f, year)
        if year == 2020:
            for c in chs:
                c['session'] = 'full'
        for c in chs:
            attach_speakers(c)
        # 本场累计词数位置
        pos = {}
        for c in chs:
            c['word_start'] = pos.get(c['session'], 0)
            pos[c['session']] = c['word_start'] + c['words']
        for c in chs:
            c['session_words'] = pos[c['session']]
        rows.extend(chs)
    with open(dst, 'w', encoding='utf-8') as fh:
        for r in rows:
            r['id'] = f"{r['year']}-{r['session'][0].upper()}{r['chapter']:02d}"
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'{len(rows)} chapters -> {dst}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
