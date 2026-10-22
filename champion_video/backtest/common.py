"""回测公共函数：读取缓存数据 → 统一成 pandas DataFrame（日期索引）。"""
import json, os
import numpy as np, pandas as pd

CACHE = os.environ.get('CHAMP_CACHE', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache'))


def load_us(sym):
    """Yahoo 日线 → DataFrame[open, high, low, close, adjclose, volume, split_after]
    open/high/low/close 为 Yahoo 拆股调整后价格；adjclose 另含分红再投资；
    split_after = 该日之后发生的拆股累计倍数（用于还原当时真实成交价）。"""
    p = os.path.join(CACHE, 'us_raw', sym + '.json')
    if not os.path.exists(p):
        return None
    j = json.load(open(p))
    res = (j.get('chart') or {}).get('result')
    if not res:
        return None
    r = res[0]
    if 'timestamp' not in r or 'adjclose' not in r['indicators'] or r['meta'].get('dataGranularity') != '1d':
        return None
    tz = r['meta'].get('exchangeTimezoneName', 'America/New_York')
    idx = pd.to_datetime(r['timestamp'], unit='s', utc=True).tz_convert(tz).tz_localize(None).normalize()
    q = r['indicators']['quote'][0]
    df = pd.DataFrame({k: q[k] for k in ['open', 'high', 'low', 'close', 'volume']}, index=idx)
    df['adjclose'] = r['indicators']['adjclose'][0]['adjclose']
    df = df[~df.index.duplicated(keep='last')].dropna(subset=['close'])
    sp = r.get('events', {}).get('splits', {})
    df['split_after'] = 1.0
    for v in sp.values():
        d = pd.Timestamp(v['date'], unit='s', tz='UTC').tz_convert(tz).tz_localize(None).normalize()
        df.loc[df.index < d, 'split_after'] *= v['numerator'] / v['denominator']
    df.attrs['name'] = r['meta'].get('longName') or r['meta'].get('shortName') or sym
    return df


def load_cn_month(sym):
    p = os.path.join(CACHE, 'cn', 'month', sym + '.json')
    rows = json.load(open(p))
    if not isinstance(rows, list) or not rows:   # 不存在的代码接口返回 {'-1': ...}
        return None
    df = pd.DataFrame([r[:6] for r in rows], columns=['date', 'open', 'close', 'high', 'low', 'vol'])
    df['date'] = pd.to_datetime(df.date)
    df = df.set_index('date').astype(float)
    return df[~df.index.duplicated(keep='last')].sort_index()


def load_cn_day(sym, fq='hfq'):
    p = os.path.join(CACHE, 'cn', 'day', f'{sym}_{fq or "raw"}.json')
    rows = json.load(open(p))
    df = pd.DataFrame([r[:6] for r in rows], columns=['date', 'open', 'close', 'high', 'low', 'vol'])
    df['date'] = pd.to_datetime(df.date)
    df = df.set_index('date').astype(float)
    return df[~df.index.duplicated(keep='last')].sort_index()


def cagr(mult, years):
    return mult ** (1 / years) - 1
