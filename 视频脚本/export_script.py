"""把一期视频的定稿旁白导出成独立的脚本文档（视频脚本/<编号>_<片名>.md）。
用法：python3 视频脚本/export_script.py <工程目录> <编号> "<片名>"
读取 <工程目录>/src/script.py（配音文本 / 字幕文本）和 <工程目录>/work/timeline.json（成片里每句的起始时刻、章节）。
在 build.sh 跑完（时间线定稿）之后执行；脚本改了就重新导出。
"""
import sys, os, json, importlib.util

proj, num, title = sys.argv[1], sys.argv[2], sys.argv[3]
spec = importlib.util.spec_from_file_location('script_mod', os.path.join(proj, 'src', 'script.py'))
sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
tl = json.load(open(os.path.join(proj, 'work', 'timeline.json')))
segs = {s['id']: s for s in tl['segs']}
chapters = tl['chapters']


def mmss(t):
    m, s = divmod(t, 60); return '%d:%04.1f' % (m, s)


total = tl['total']
chap_of = {}
for c in chapters: chap_of[c['id']] = c
nchar = sum(len(x[1]) for x in sm.LINES)
out = ['# %s' % title, '',
       '> 护城河系列第 %s 期 · 定稿视频脚本（由 `视频脚本/export_script.py` 从工程的 `src/script.py` 与成片时间线导出，时间码与竖版、横版成片一致）。' % num,
       '> 工程目录：`%s/`；竖版、横版共用这一条旁白。片长 %s，旁白 %d 字（配音文本）。' % (os.path.basename(os.path.abspath(proj)), mmss(total), nchar),
       '> 数字、引语的来源见该期 `docs/核实笔记.md`。“配音读法”一栏只在配音文本与字幕不同（数字读法等）时列出。', '',
       '## 章节', '', '| 时间 | 章节 |', '|---|---|']
for i, c in enumerate(chapters):
    out.append('| %s | %s |' % (mmss(c['start']), c['name'] or '引子'))
out.append('| %s | 片尾品牌动画 |' % mmss(segs[sm.LINES[-1][0]]['start'] + segs[sm.LINES[-1][0]]['dur']))
out += ['', '## 逐句旁白', '']
for lid, tts, sub in sm.LINES:
    if lid in chap_of:
        c = chap_of[lid]
        out += ['', '### %s%s' % (c['name'] or '引子', ('（%s）' % c['en']) if c['en'] else ''), '',
                '| 时间 | 编号 | 旁白（字幕） | 配音读法 |', '|---|---|---|---|']
    s = segs.get(lid)
    shown = (sub or tts).rstrip('。') + ('' if (sub or tts).endswith(('？', '！', '”', '：')) else '。')
    diff = tts if sub and sub.rstrip('。') != tts.rstrip('。') else ''
    out.append('| %s | %s | %s | %s |' % (mmss(s['start'] + s['speech'][0]) if s else '', lid, shown.replace('|', '｜'), diff.replace('|', '｜')))
out += ['', '## 全文（连读版）', '']
para = []; cur = []
for lid, tts, sub in sm.LINES:
    if lid in chap_of and cur: para.append(''.join(cur)); cur = []
    t_ = (sub or tts)
    cur.append(t_ if t_.endswith(('。', '？', '！', '”', '：')) else t_ + '。')
if cur: para.append(''.join(cur))
out += [p + '\n' for p in para]
name = '%s_%s.md' % (num, title.split('｜')[0].replace('，', '').replace('≠', '不等于').replace(' ', ''))
dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
open(dst, 'w').write('\n'.join(out).rstrip() + '\n')
print(dst)
