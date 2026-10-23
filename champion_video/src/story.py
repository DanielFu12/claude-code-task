"""把回测结果整理成画面用的 story.json（原版：标普 500 vs 沪深全 A 剔除次新股）。

美股：backtest/out_us.json（标普 500 成分股池）
A 股：backtest/out_cn.json（沪深全部 A 股，含退市，剔除次新股；cn.py 主口径）
归因证据：backtest/evidence_v6.json（evidence_v6.py）
"""
import json, os, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
BT = os.path.join(HERE, '..', 'backtest')

US_CN_NAME = {'NFLX': '奈飞', 'NVDA': '英伟达', 'NRG': 'NRG 能源', 'AMD': '超威半导体', 'TSLA': '特斯拉',
              'DVN': '德文能源', 'OXY': '西方石油', 'PLTR': 'Palantir'}
US_EN_SHORT = {'NFLX': 'Netflix', 'NVDA': 'NVIDIA', 'NRG': 'NRG Energy', 'AMD': 'AMD', 'TSLA': 'Tesla',
               'DVN': 'Devon Energy', 'OXY': 'Occidental', 'PLTR': 'Palantir'}
CN_NAME_AT = {'300176': '鸿特精密'}            # A 股用「当时的简称」
US_C, CN_C = (0.31, 0.82, 1.0), (1.0, 0.6, 0.24)


def build():
    us = json.load(open(os.path.join(BT, 'out_us.json')))
    cn = json.load(open(os.path.join(BT, 'out_cn.json')))
    years = []
    for i, ru in enumerate(us['main']):
        pu = ru['picks'][0]
        rc = cn['main'][i]; pc = rc['picks'][0]
        years.append(dict(
            year=ru['year'],
            us=dict(code=pu['sym'], name=US_CN_NAME.get(pu['sym'], pu['name']), en=US_EN_SHORT.get(pu['sym'], pu['name']),
                    prev=pu['prev'], ret=ru['net'], cap=ru['capital'], path=pu['path'], buy=pu['buy_price'], sell=pu['sell_price'],
                    buy_date=pu['buy_date'], sell_date=pu['sell_date']),
            us_bench=us['bench'][i]['ret'], us_bench_cap=us['bench'][i]['capital'], us_bench_path=us['bench'][i]['path'],
            cn=dict(code=pc['sym'][2:], name=CN_NAME_AT.get(pc['sym'][2:], pc['name']), prev=pc['prev'], ret=rc['net'], cap=rc['capital'], path=pc['path'],
                    buy=pc['buy_price'], sell=pc['sell_price'], buy_date=pc['buy_date'], sell_date=pc['sell_date'], notes=pc['notes']),
            cn_bench=cn['bench'][i]['ret'], cn_bench_cap=cn['bench'][i]['capital'], cn_bench_path=cn['bench'][i]['path']))
    S = dict(
        rules=[('1', '每年第一个交易日开盘，买入上一年涨幅冠军', '上一年全年总回报第一名（含分红、拆股、送转）'),
               ('2', '持有一整年，最后一个交易日收盘卖出', '一字涨停买不进、一字跌停卖不出就顺延，退市按最后价格清算'),
               ('3', '本金和收益全部滚入下一年的冠军', '连续复利，十年只做十笔交易'),
               ('4', '计入真实交易成本', '佣金、滑点、印花税；只用当时已知的信息')],
        universe=[('美股', '标普 500 成分股', '按当年年末的真实成分；含后来被收购、退市的公司', US_C),
                  ('A股', '沪深全部 A 股', '含已退市股；剔除次新股（上市不满一年）', CN_C)],
        years=years,
        us_total=us['main'][-1]['capital'], us_bench_total=us['bench'][-1]['capital'],
        cn_total=cn['main'][-1]['capital'], cn_bench_total=cn['bench'][-1]['capital'],
        us_variants={k: us[k][-1]['capital'] for k in ('top5', 'top10', 'start_members')},
        cn_variants={k: cn[k][-1]['capital'] for k in ('ideal', 'incl_sub', 'with_ipo', 'top5', 'top10')},
    )
    S['gap'] = S['us_total'] / S['cn_total']
    add_narrative(S)
    json.dump(S, open(os.path.join(HERE, 'story.json'), 'w'), ensure_ascii=False, indent=1, default=float)
    print('story.json written; gap', round(S['gap']), 'cn total', round(S['cn_total'], 4))


def add_narrative(S):
    E = json.load(open(os.path.join(BT, 'evidence_v6.json')))
    ny = E['next_year']
    uy = [y['us']['ret'] for y in S['years']]; ub = [y['us_bench'] for y in S['years']]
    cy = [y['cn']['ret'] for y in S['years']]; cb = [y['cn_bench'] for y in S['years']]
    names = {(mk, y['year']): y[mk]['name'] for y in S['years'] for mk in ('us', 'cn')}
    prof = [dict(p, name=names[(p['mk'], p['year'])]) for p in E['profit']]
    P = {(p['mk'], p['year']): p for p in prof}

    def med(xs):
        return float(np.median([x for x in xs if x is not None]))
    up = lambda mk: sum(1 for p in prof if p['mk'] == mk and (p['turn'] or (p['growth'] or 0) > 0))
    fast = lambda mk: sum(1 for p in prof if p['mk'] == mk and (p['turn'] or (p['growth'] or 0) >= 0.5))
    decomp = {mk: dict(profit=med([p['growth'] for p in prof if p['mk'] == mk]), pe=med([p['pe_change'] for p in prof if p['mk'] == mk]),
                       ret=med([p['ret'] for p in prof if p['mk'] == mk]), up=up(mk), fast=fast(mk)) for mk in ('us', 'cn')}

    def arc(mk, y, note):
        p = P[(mk, y)]
        return dict(name=p['name'], year=p['year'], vals=[p['np_champ'], p['np_hold'], p['np_after']], ret=p['ret'], note=note)
    S['stats'] = dict(us_beat=ny['us_beat'], cn_beat=ny['cn_beat'], us_worst=ny['us_worst'], cn_loss=ny['cn_loss'],
                      cn_big_loss=ny['cn_big_loss'], cn_worst=ny['cn_worst'])
    big = [i for i, y in enumerate(S['years']) if y['us']['code'] in ('NVDA', 'AMD', 'PLTR')]
    share = sum(math.log(1 + uy[i]) for i in big) / math.log(S['us_total'])
    S['why'] = dict(
        groups=[('美股冠军', US_C, uy, ub), ('A股冠军', CN_C, cy, cb)],
        scatter=prof,
        decomp=decomp,
        examples=dict(us=[('超威半导体', P[('us', 2020)]['growth'], P[('us', 2020)]['pe_change'], P[('us', 2020)]['ret']),
                          ('特斯拉', P[('us', 2021)]['growth'], P[('us', 2021)]['pe_change'], P[('us', 2021)]['ret'])],
                      cn=[(P[('cn', 2017)]['name'], P[('cn', 2017)]['growth'], P[('cn', 2017)]['pe_change'], P[('cn', 2017)]['ret']),
                          (P[('cn', 2022)]['name'], P[('cn', 2022)]['growth'], P[('cn', 2022)]['pe_change'], P[('cn', 2022)]['ret'])]),
        arcs=dict(us=[arc('us', 2021, 'EV 渗透率爬坡'), arc('us', 2020, '数据中心芯片换代'), arc('us', 2024, 'AI 算力')],
                  cn=[arc('cn', 2020, 'ETC 强制安装：装完即止'), arc('cn', 2021, '疫情手套：需求脉冲'),
                      arc('cn', 2022, '化工周期顶点'), arc('cn', 2023, '跨界光伏概念')]),
        flows=dict(us_top10=E['momentum']['us_top10'], cn_top10=E['momentum']['cn_top10'],
                   cn_in_csi300=sum(x['member'] for x in E['in_csi300'])),
        us_big_n=len(big), us_big_share=share,
    )
    S['principles'] = [('独立思考', '别人赚钱的消息\n不是买入的理由'), ('护城河', '看企业能否长期\n抵御竞争'),
                       ('内在价值', '估算未来的现金流\n而不是看去年涨幅'), ('安全边际', '价格明显低于价值\n才值得出手')]
    S['final_msg'] = ['投资不是追逐最热门的股票，', '而是判断企业未来能创造多少价值，', '以及今天的价格是否值得支付。']


if __name__ == '__main__':
    build()
