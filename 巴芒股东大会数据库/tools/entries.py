#!/usr/bin/env python3
"""精华条目的解析与原话校验。

条目文件 entries/*.txt，每条以 “@ 章节ID” 开头，字段一行一个：
  t:   精华标题（中文）
  s:   发言人 B=巴菲特 M=芒格 BM=两人 A=阿贝尔 J=贾因（可组合）
  th:  主题（分号分隔，取自 THEMES）
  k:   概念簇（用于去重归并与思想演变，取自 CLUSTERS）
  c:   核心观点（中文概括）
  q:   原话锚点 “起始短语 ||| 结束短语”，可多行；程序从该章逐字稿中原样截取
  zh:  中文翻译（本库译文）
  l:   投资启示
  r:   评分 思想深度/投资实用性/启发性（各 1–5）
  rel: 相关章节（可选，逗号分隔；无效 ID 会被报告）

原话只做两处处理：去掉“(Laughter)”“(Applause)”等现场标注；跨段落用空格连接，
换发言人时插入“[Munger:]”之类的标记。其余字符与逐字稿完全一致。
"""
import json
import re
from pathlib import Path

THEMES = ['投资理念', '投资方法', '企业估值', '商业模式', '护城河', '风险管理', '市场周期',
          '投资心理', '人生智慧', '管理与治理', '资本配置', '会计与财务', '保险与浮存金', '宏观与社会']

CLUSTERS = {
    'stock_as_business': '股票是企业的一部分',
    'mr_market': '市场先生与波动',
    'no_forecast': '不预测宏观与市场',
    'circle': '能力圈与保持简单',
    'moat': '护城河与竞争优势',
    'iv': '内在价值与估值方法',
    'discount': '折现率、利率与机会成本',
    'mos': '安全边际',
    'quality': '从烟蒂到伟大企业：质量与价格',
    'concentration': '集中投资与分散',
    'holding': '长期持有与何时卖出',
    'leverage': '杠杆与永不出局',
    'derivatives': '衍生品与系统性金融风险',
    'insurance': '保险经营与浮存金',
    'management': '识别管理层与人品',
    'incentives': '激励机制与高管薪酬',
    'accounting': '会计、EBITDA 与财务造假',
    'buyback': '回购、分红与留存收益',
    'tech_change': '科技、变化与颠覆',
    'mistakes': '错误、复盘与逆向思考',
    'learning': '阅读、学习与多元思维模型',
    'life': '人生、职业与幸福',
    'reputation': '声誉、诚信与文化',
    'psychology': '投资心理、独立思考与理性',
    'index': '指数基金与普通投资者',
    'speculation': '投机、泡沫与非生产性资产',
    'crisis': '恐慌与危机中的机会',
    'america': '长期看好美国',
    'culture': '伯克希尔模式、分权与传承',
    'inflation': '通胀与资产选择',
    'capital_alloc': '资本配置与收购',
    'business_model': '商业模式与资本密集度',
    'efficient_market': '有效市场理论与学术界',
    'due_diligence': '收购决策与尽职调查',
    'projections': '预测、增长与盈利预期',
}

STAGE = re.compile(r'\s*\((?:Laughter|Applause|Laughs|laughter|applause|laughs|Laughter and applause)[^)]*\)')
SPK_SHORT = {'WARREN BUFFETT': 'Buffett', 'CHARLIE MUNGER': 'Munger', 'GREG ABEL': 'Abel',
             'AJIT JAIN': 'Jain'}


def norm(s):
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    s = s.replace('—', '-').replace('–', '-').replace('…', '...')
    return re.sub(r'\s+', ' ', s).strip()


def load_chapters(path):
    return {json.loads(l)['id']: json.loads(l) for l in open(path, encoding='utf-8')}


def chapter_stream(ch):
    """把一章拼成一条字符串，并记录每个字符所属的段落序号。"""
    text, owner = '', []
    for i, p in enumerate(ch['paragraphs']):
        seg = p['text'] + ' '
        text += seg
        owner.extend([i] * len(seg))
    return text, owner


def _norm_map(s):
    """规范化字符串，同时返回规范化后每个字符对应原串的下标。"""
    out, idx = [], []
    prev_space = False
    table = {'’': "'", '‘': "'", '“': '"', '”': '"', '—': '-', '–': '-'}
    for i, c in enumerate(s):
        c = table.get(c, c)
        if c.isspace():
            if prev_space:
                continue
            c, prev_space = ' ', True
        else:
            prev_space = False
        out.append(c)
        idx.append(i)
    return ''.join(out), idx


def extract(ch, start, end):
    text, owner = chapter_stream(ch)
    nt, idx = _norm_map(text)
    ns, ne = norm(start), norm(end)
    a = nt.find(ns)
    if a < 0:
        return None, f'起始短语未找到: {start[:60]}'
    if nt.find(ns, a + 1) >= 0 and ns != ne:
        pass  # 允许重复，取第一个
    b = nt.find(ne, a)
    if b < 0:
        return None, f'结束短语未找到（在起始之后）: {end[:60]}'
    oa, ob = idx[a], idx[b + len(ne) - 1] + 1
    # 逐段拼接，换人时加标记
    pieces, last_spk = [], None
    first_spk = ch['paragraphs'][owner[oa]]['speaker']
    for pi in range(owner[oa], owner[ob - 1] + 1):
        p = ch['paragraphs'][pi]
        seg_start = sum(len(q['text']) + 1 for q in ch['paragraphs'][:pi])
        lo = max(oa, seg_start) - seg_start
        hi = min(ob, seg_start + len(p['text'])) - seg_start
        frag = p['text'][lo:hi]
        if last_spk is not None and p['speaker'] != last_spk:
            frag = f"[{SPK_SHORT.get(p['speaker'], p['speaker'])}:] " + frag
        pieces.append(frag)
        last_spk = p['speaker']
    quote = STAGE.sub('', ' '.join(pieces)).strip()
    words_before = len(text[:oa].split())
    return {'text': quote, 'speaker': first_spk, 'word_offset': words_before,
            'words': len(quote.split())}, None


def parse_entries(folder):
    entries = []
    for f in sorted(Path(folder).glob('*.txt')):
        cur = None
        for ln, raw in enumerate(f.read_text(encoding='utf-8').split('\n'), 1):
            line = raw.rstrip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('@ '):
                cur = {'ch': line[2:].strip(), 'q': [], 'file': f.name, 'line': ln}
                entries.append(cur)
                continue
            m = re.match(r'^(t|s|th|k|c|q|zh|l|r|rel|top):\s?(.*)$', line)
            if not m or cur is None:
                raise ValueError(f'{f.name}:{ln}: 无法解析: {line[:80]}')
            key, val = m.group(1), m.group(2).strip()
            if key == 'q':
                cur['q'].append(val)
            else:
                cur[key] = val
    return entries


def validate(entries, chapters):
    errs = []
    for e in entries:
        where = f"{e['file']}:{e['line']} {e['ch']}"
        ch = chapters.get(e['ch'])
        if ch is None:
            errs.append(f'{where}: 章节不存在')
            continue
        for k in ('t', 's', 'th', 'k', 'c', 'zh', 'l', 'r'):
            if not e.get(k):
                errs.append(f'{where}: 缺字段 {k}')
        for th in e.get('th', '').split(';'):
            if th.strip() and th.strip() not in THEMES:
                errs.append(f'{where}: 未知主题 {th}')
        if e.get('k') not in CLUSTERS:
            errs.append(f"{where}: 未知概念簇 {e.get('k')}")
        if not re.match(r'^[1-5]/[1-5]/[1-5]$', e.get('r', '')):
            errs.append(f'{where}: 评分格式错误')
        e['quotes'] = []
        for q in e['q']:
            if '|||' not in q:
                errs.append(f'{where}: 原话锚点缺少 |||')
                continue
            a, b = [x.strip() for x in q.split('|||')]
            res, err = extract(ch, a, b)
            if err:
                errs.append(f'{where}: {err}')
            else:
                e['quotes'].append(res)
        if not e['q']:
            errs.append(f'{where}: 没有原话')
        rels = [x.strip() for x in e.get('rel', '').split(',') if x.strip()]
        e['rel_ids'] = []
        for x in rels:
            if x in chapters:
                e['rel_ids'].append(x)
            else:
                errs.append(f'{where}: 相关章节 ID 无效 {x}')
    return errs


if __name__ == '__main__':
    import sys
    chs = load_chapters(sys.argv[1])
    es = parse_entries(sys.argv[2])
    errs = validate(es, chs)
    for e in errs:
        print(e)
    print(f'{len(es)} entries, {len(errs)} problems')
