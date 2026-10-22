"""下载沪深 A 股（含已退市）月线/日线（腾讯证券行情接口，不复权），缓存为 JSON。

注意：腾讯的「后复权」序列采用加法调整（复权价/原价之比逐日漂移），且把破产重整中的资本公积转增
当作送股处理，会制造虚假的年度涨幅冠军，因此本项目只用不复权价格。

腾讯接口保留了已退市股票的历史行情，因此通过「遍历全部代码段」得到含退市股的完整股票池，
避免只用当前在市股票造成的幸存者偏差。

用法:
  python3 fetch_cn.py month <cache_dir> [skip_dir]  # 遍历代码段，抓 2014-12 ~ 2025-12 不复权月线
  python3 fetch_cn.py day <cache_dir> code1 code2  # 抓指定股票不复权日线
  python3 fetch_cn.py names <cache_dir>            # 抓股票简称
"""
import json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
import requests

BASES = ['https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get',
         'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get']  # 两个等价入口（后者限流较严），失败时轮换
# 沪市 600/601/603/605 主板 + 688/689 科创板；深市 000/001/002/003 主板(含原中小板) + 300/301 创业板
# （602xxx、604xxx 段从未分配 A 股代码）。北交所不在本研究范围内。
RANGES = ([('sh', i) for r in [(600000, 602000), (603000, 604000), (605000, 606000), (688000, 689000), (689009, 689010)]
           for i in range(*r)] +
          [('sz', i) for i in range(1, 4000)] + [('sz', i) for i in range(300000, 302000)])


def get(query, tries=12):
    for k in range(tries):
        try:
            r = requests.get(BASES[k % 2] + '?' + query, timeout=20)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        time.sleep(0.5 * (k + 1))
    raise RuntimeError('failed: ' + query)


SKIP = set()   # 已确认不存在的代码（来自先前遍历），避免重复请求


def month(cache, mk, code):
    """不复权月线（复权由 adjust.py 用交易所分红送转记录自行按比例计算）"""
    sym = f'{mk}{code:06d}'
    out = os.path.join(cache, sym + '.json')
    if os.path.exists(out) or sym in SKIP:
        return
    t = get(f'param={sym},month,2014-12-01,2025-12-31,200,')
    j = json.loads(t)
    d = j.get('data', {})
    d = d.get(sym) if isinstance(d, dict) else None
    rows = (d or {}).get('month') or []
    json.dump(rows, open(out, 'w'))


def day(cache, sym, fq):
    out = os.path.join(cache, f'{sym}_{fq or "raw"}.json')
    if os.path.exists(out):
        return json.load(open(out))
    rows = []
    # 接口返回「截至结束日的最近 640 条」，按约 2.5 年分段覆盖 2013-11 ~ 2025-12
    for end in ['2016-06-30', '2018-12-31', '2021-06-30', '2023-12-31', '2025-12-31']:
        t = get(f'param={sym},day,2013-01-01,{end},640,{fq}')
        d = json.loads(t)['data'][sym]
        rows += d.get(f'{fq}day') or d.get('day') or []
    json.dump(rows, open(out, 'w'))
    return rows


if __name__ == '__main__':
    mode, cache = sys.argv[1], sys.argv[2]
    os.makedirs(cache, exist_ok=True)
    if mode == 'month':
        if len(sys.argv) > 3:   # 可选：传入一个目录，其中 {} 内容的文件代表不存在的代码
            for f in os.listdir(sys.argv[3]):
                if open(os.path.join(sys.argv[3], f)).read(1) == '{':
                    SKIP.add(f[:-5])
        with ThreadPoolExecutor(16) as ex:
            list(ex.map(lambda a: month(cache, *a), RANGES))
        n = sum(1 for f in os.listdir(cache) if os.path.getsize(os.path.join(cache, f)) > 2)
        print('stocks with data:', n)
    elif mode == 'day':
        with ThreadPoolExecutor(12) as ex:
            list(ex.map(lambda s: day(cache, s, ''), sys.argv[3:]))
    elif mode == 'names':
        syms = sorted(f[:-5] for f in os.listdir(os.path.join(cache, 'month'))
                      if os.path.getsize(os.path.join(cache, 'month', f)) > 2)
        names = {}
        for i in range(0, len(syms), 60):
            t = requests.get('https://qt.gtimg.cn/q=' + ','.join(syms[i:i + 60]), timeout=20).content.decode('gbk', 'ignore')
            for line in t.split(';'):
                if '="' in line:
                    k, v = line.strip().split('="', 1)
                    f = v.split('~')
                    if len(f) > 2:
                        names[k[2:]] = f[1]
        json.dump(names, open(os.path.join(cache, 'names.json'), 'w'), ensure_ascii=False, indent=0)
        print(len(names))
