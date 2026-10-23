"""把回测结果整理成画面用的 story.json（沪深 300 版）。

美股：champion_video/backtest/out_us.json（标普 500 成分股池）
A 股：champion_video/backtest/out_cn300.json（沪深 300 成分股池，由 cn300.py 生成）
归因证据：evidence300.json（evidence300.py）+ cache/profits.json（fetch_profits.py：SEC 10-K / 东方财富年报）
"""
import json, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
BT = os.path.join(HERE, '..', '..', 'champion_video', 'backtest')       # 回测脚本与数据与原版共用

US_CN_NAME = {'NFLX': '奈飞', 'NVDA': '英伟达', 'NRG': 'NRG 能源', 'AMD': '超威半导体', 'TSLA': '特斯拉',
              'DVN': '德文能源', 'OXY': '西方石油', 'PLTR': 'Palantir'}
US_EN_SHORT = {'NFLX': 'Netflix', 'NVDA': 'NVIDIA', 'NRG': 'NRG Energy', 'AMD': 'AMD', 'TSLA': 'Tesla',
               'DVN': 'Devon Energy', 'OXY': 'Occidental', 'PLTR': 'Palantir'}
# A 股用「当时的简称」（行情接口给的是今天的简称）
CN_NAME_AT = {'300072': '三聚环保', '601012': '隆基股份', '601888': '中国国旅', '603501': '韦尔股份'}
US_C, CN_C = (0.31, 0.82, 1.0), (1.0, 0.6, 0.24)


def cagr(m, n=10):
    return m ** (1 / n) - 1


def build():
    us = json.load(open(os.path.join(BT, 'out_us.json')))
    cn = json.load(open(os.path.join(BT, 'out_cn300.json')))
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
            cn=dict(code=pc['sym'][2:], name=CN_NAME_AT.get(pc['sym'][2:], pc['name']), prev=pc['prev'], ret=rc['net'],
                    cap=rc['capital'], path=pc['path'], buy=pc['buy_price'], sell=pc['sell_price'], buy_date=pc['buy_date'],
                    sell_date=pc['sell_date'], notes=pc['notes']),
            cn_bench=cn['bench'][i]['ret'], cn_bench_cap=cn['bench'][i]['capital'], cn_bench_path=cn['bench'][i]['path']))
    S = dict(
        rules=[('1', '每年第一个交易日开盘，买入上一年涨幅冠军', '上一年全年总回报第一名（含分红、拆股、送转）'),
               ('2', '持有一整年，最后一个交易日收盘卖出', '一字涨停买不进、一字跌停卖不出就顺延'),
               ('3', '本金和收益全部滚入下一年的冠军', '连续复利，十年只做十笔交易'),
               ('4', '计入真实交易成本', '佣金、滑点、印花税；只用当时已知的信息')],
        universe=[('美股', '标普 500 成分股', '按当年年末的真实成分；含后来被收购、退市的公司', US_C),
                  ('A股', '沪深 300 成分股', '按当年年末的真实成分；同为大盘龙头，排除次新股', CN_C)],
        years=years,
        us_total=us['main'][-1]['capital'], us_bench_total=us['bench'][-1]['capital'],
        cn_total=cn['main'][-1]['capital'], cn_bench_total=cn['bench'][-1]['capital'],
        us_variants={k: us[k][-1]['capital'] for k in ('top5', 'top10', 'start_members')},
        cn_variants={k: cn[k][-1]['capital'] for k in ('ideal', 'start', 'top5', 'top10')},
    )
    S['gap'] = S['us_total'] / S['cn_total']
    add_narrative(S)
    json.dump(S, open(os.path.join(HERE, 'story.json'), 'w'), ensure_ascii=False, indent=1, default=float)
    print('story.json written; gap', round(S['gap']), 'cn total', round(S['cn_total'], 4))


def add_narrative(S):
    E = json.load(open(os.path.join(BT, 'evidence300.json')))
    ny = E['next_year']
    uy = [y['us']['ret'] for y in S['years']]; ub = [y['us_bench'] for y in S['years']]
    cy = [y['cn']['ret'] for y in S['years']]; cb = [y['cn_bench'] for y in S['years']]
    big = [i for i, y in enumerate(S['years']) if y['us']['code'] in ('NVDA', 'AMD', 'PLTR')]
    share = sum(math.log(1 + uy[i]) for i in big) / math.log(S['us_total'])
    P = {(p['mk'], p['year']): p for p in E['profit']}

    def prof(mk, i):
        p = P[(mk, S['years'][i]['year'])]
        return dict(name=S['years'][i][mk]['name'], year=p['year'], growth=p['growth'], turn=p['turn'], ret=p['ret'],
                    np_prev=p['np_prev'], np_hold=p['np_hold'])

    scatter = [dict(mk=mk, **prof(mk, i)) for mk in ('us', 'cn') for i in range(10)]
    idx = {y['year']: i for i, y in enumerate(S['years'])}
    cyc = [prof('cn', idx[2018]), prof('cn', idx[2022])]          # 周期见顶：隆基、合盛
    val = [prof('cn', idx[2016]), prof('cn', idx[2023])]          # 估值透支：奥飞、德业
    S['stats'] = dict(us_beat=ny['us_beat'], cn_beat=ny['cn_beat'], us_worst=ny['us_worst'], cn_worst=ny['cn_worst'],
                      cn_loss_years=ny['cn_loss_years'], us_big_n=len(big), us_big_share=share)
    S['why'] = [
        dict(ch='冠军的下一年', groups=[('美股冠军', US_C, uy, ub), ('A股冠军', CN_C, cy, cb)]),
        dict(ch='复利的不对称', wins=ny['cn_wins'], losses=ny['cn_losses'], win_mult=ny['cn_win_mult'],
             lose_mult=ny['cn_lose_mult'], total=S['cn_total']),
        dict(ch='第一性原理', scatter=scatter),
        dict(ch='A股冠军为什么会腰斩', cyc=cyc, val=val,
             cyc_note=['光伏：硅片价格见顶', '工业硅：价格从高点回落'], val_note=['IP 故事讲完，估值回归', '逆变器需求放缓，估值杀']),
        dict(ch='差距的真相', us_top10=E['momentum']['us']['top10'], cn_top10=E['momentum']['cn300']['top10'],
             cn_top5=S['cn_variants']['top5'], cn_bench=S['cn_bench_total'], us_big_n=len(big), us_big_share=share,
             us_profit_up=sum(1 for p in scatter if p['mk'] == 'us' and ((p['growth'] or 0) > 0 or p['turn']))),
    ]
    S['principles'] = [('独立思考', '别人赚钱的消息\n不是买入的理由'), ('护城河', '看企业能否长期\n抵御竞争'),
                       ('内在价值', '估算未来的现金流\n而不是看去年涨幅'), ('安全边际', '价格明显低于价值\n才值得出手')]
    S['final_msg'] = ['投资不是追逐最热门的股票，', '而是判断企业未来能创造多少价值，', '以及今天的价格是否值得支付。']


if __name__ == '__main__':
    build()
