"""把回测结果（backtest/out_us.json, out_cn.json）整理成画面用的 story.json。"""
import json, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
BT = os.path.join(HERE, '..', 'backtest')

US_CN_NAME = {'NFLX': '奈飞', 'NVDA': '英伟达', 'NRG': 'NRG 能源', 'AMD': '超威半导体', 'TSLA': '特斯拉',
              'DVN': '德文能源', 'OXY': '西方石油', 'PLTR': 'Palantir'}
US_EN_SHORT = {'NFLX': 'Netflix', 'NVDA': 'NVIDIA', 'NRG': 'NRG Energy', 'AMD': 'AMD', 'TSLA': 'Tesla',
               'DVN': 'Devon Energy', 'OXY': 'Occidental', 'PLTR': 'Palantir'}

POST_US, POST_CN = 854.70, -0.964    # 热帖：+85,470%（= 855.7 倍），−96.4%


def cagr(m, n=10):
    return m ** (1 / n) - 1


def build():
    us = json.load(open(os.path.join(BT, 'out_us.json')))
    cn = json.load(open(os.path.join(BT, 'out_cn.json'))) if os.path.exists(os.path.join(BT, 'out_cn.json')) else None
    years = []
    for i, ru in enumerate(us['main']):
        pu = ru['picks'][0]
        y = dict(year=ru['year'],
                 us=dict(code=pu['sym'], name=US_CN_NAME.get(pu['sym'], pu['name']), en=US_EN_SHORT.get(pu['sym'], pu['name']),
                         prev=pu['prev'], ret=ru['net'], cap=ru['capital'], path=pu['path'], buy=pu['buy_price'], sell=pu['sell_price'],
                         buy_date=pu['buy_date'], sell_date=pu['sell_date']),
                 us_bench=us['bench'][i]['ret'], us_bench_cap=us['bench'][i]['capital'], us_bench_path=us['bench'][i]['path'])
        if cn:
            rc = cn['main'][i]; pc = rc['picks'][0]
            y['cn'] = dict(code=pc['sym'][2:], name=pc['name'], prev=pc['prev'], ret=rc['net'], cap=rc['capital'], path=pc['path'],
                           buy=pc['buy_price'], sell=pc['sell_price'], buy_date=pc['buy_date'], sell_date=pc['sell_date'],
                           notes=pc['notes'])
            y['cn_bench'] = cn['bench'][i]['ret']; y['cn_bench_cap'] = cn['bench'][i]['capital']
            y['cn_bench_path'] = cn['bench'][i]['path']
        years.append(y)
    S = dict(
        post=dict(text_lines=['每年第一个交易日，', '买入上一年的涨幅冠军，', '连续十年 ——'], us_claim=POST_US, cn_claim=POST_CN,
                  us_claim_cagr=cagr(1 + POST_US), cn_claim_cagr=cagr(1 + POST_CN)),
        rules=[('1', '每年第一个交易日开盘，买入上一年涨幅冠军', '上一年全年总回报第一名（含分红、拆股、送转）'),
               ('2', '持有一整年，最后一个交易日收盘卖出', '一字涨停买不进、一字跌停卖不出就顺延，退市按最后价格清算'),
               ('3', '本金和收益全部滚入下一年的冠军', '连续复利，十年只做十笔交易'),
               ('4', '计入真实交易成本', '佣金、滑点、印花税；只用当时已知的信息')],
        universe=[('美股', '标普 500 成分股', '按当年年末的真实成分；含后来被收购、退市的公司', (0.31, 0.82, 1.0)),
                  ('A股', '沪深全部 A 股', '主板、创业板、科创板，含已退市股；剔除当年才上市的新股', (1.0, 0.6, 0.24))],
        years=years,
        us_total=us['main'][-1]['capital'], us_bench_total=us['bench'][-1]['capital'],
        us_variants={k: us[k][-1]['capital'] for k in ('top5', 'top10', 'start_members')},
    )
    if cn:
        S['cn_total'] = cn['main'][-1]['capital']; S['cn_bench_total'] = cn['bench'][-1]['capital']
        S['cn_variants'] = {k: cn[k][-1]['capital'] for k in ('ideal', 'with_ipo', 'top5', 'top10')}
        add_narrative(S, us, cn)
    json.dump(S, open(os.path.join(HERE, 'story.json'), 'w'), ensure_ascii=False, indent=1, default=float)
    print('story.json written; years', len(years), 'cn' if cn else 'no cn yet')


def add_narrative(S, us, cn):
    ut, ct = S['us_total'], S['cn_total']
    S['verdict_msgs'] = [f'方向没错，但热帖把结果夸大了约 {(1 + POST_US) / ut:.1f} 倍',
                         f'确实大亏，但不是 −96.4%，而是 {(ct - 1) * 100:+.1f}%'.replace('+-', '−').replace('-', '−')]
    uv, cv = S['us_variants'], S['cn_variants']
    S['robust'] = [
        ('美股', (0.31, 0.82, 1.0), [('只买冠军（主口径）', ut, True), ('按年初成分股选', uv['start_members'], False),
                                     ('前 5 名等权', uv['top5'], False), ('前 10 名等权', uv['top10'], False),
                                     ('标普500 全收益', S['us_bench_total'], False)]),
        ('A股', (1.0, 0.6, 0.24), [('只买冠军（主口径）', ct, True), ('包含当年新股', cv['with_ipo'], False),
                                   ('假设必能成交·零成本', cv['ideal'], False), ('前 5 名等权', cv['top5'], False),
                                   ('前 10 名等权', cv['top10'], False), ('沪深300 全收益', S['cn_bench_total'], False)])]
    S['robust_msg'] = '美股：持仓越分散，越接近指数；A股：怎么换口径，都跑输指数'
    uy = [y['us']['ret'] for y in S['years']]; ub = [y['us_bench'] for y in S['years']]
    cy = [y['cn']['ret'] for y in S['years']]; cb = [y['cn_bench'] for y in S['years']]
    u_beat = sum(a > b for a, b in zip(uy, ub)); c_beat = sum(a > b for a, b in zip(cy, cb)); c_down = sum(a < 0 for a in cy)
    # 美股复利中，英伟达 / AMD / Palantir 几笔交易的贡献（按对数收益）
    big = [i for i, y in enumerate(S['years']) if y['us']['code'] in ('NVDA', 'AMD', 'PLTR')]
    share = sum(math.log(1 + uy[i]) for i in big) / math.log(ut)
    S['stats'] = dict(us_beat=u_beat, cn_beat=c_beat, cn_down=c_down, us_big_n=len(big), us_big_share=share)
    S['why'] = [
        dict(kind='twocol', title='同样叫「冠军」，燃料不一样', sub='上一年的大涨，到底来自哪里？',
             cols=[('美股冠军', (0.31, 0.82, 1.0), [('英伟达 · AMD', '芯片与 AI 算力，利润真实爆发'),
                                                    ('特斯拉 · Palantir', '高成长，也伴随极高估值'),
                                                    ('德文能源 · 西方石油', '油价周期，现金流暴增'),
                                                    ('全是标普500大公司', '入选指数要求持续盈利')]),
                   ('A股冠军', (1.0, 0.6, 0.24), [('久远银海 · 中石科技', '次新股，上市后连续涨停'),
                                                  ('英科医疗 · 万集科技', '疫情手套、ETC：一次性景气'),
                                                  ('特力A · 绿康生化', '题材与资金推动，业绩难匹配'),
                                                  ('多为小市值公司', '不多的资金就能推出巨大涨幅')])],
             foot='有的上涨来自持续创造的价值，有的只是情绪与资金的顶点'),
        dict(kind='bars', title='冠军的下一年', sub='每根柱子 = 买入当年的实际收益',
             groups=[('美股冠军', (0.31, 0.82, 1.0), uy, ub), ('A股冠军', (1.0, 0.6, 0.24), cy, cb)],
             notes=[f'10 年里有 {u_beat} 年跑赢标普500', f'10 年里 {c_down} 年亏损，只有 {c_beat} 年跑赢沪深300']),
        dict(kind='loop', title='FOMO 与反身性', sub='上涨本身，会吸引更多人追涨',
             nodes=['股价大涨', '媒体热议', '新资金涌入', '继续上涨'], center='涨幅冠军',
             **{'break': '直到：预期透支，估值泡沫破裂'}, foot='价格会反过来改变人们的预期——这就是反身性',
             foot2='等你在榜单上看到它，往往已是最后一棒'),
        dict(kind='twocol', title='为什么两地结果截然不同？', sub='不是市场谁好谁坏，而是股票池、制度与运气',
             cols=[('美股这十年', (0.31, 0.82, 1.0), [('股票池：500 家大公司', '冠军多是行业龙头'),
                                                      ('中期动量效应较强', '学术研究长期观察到'),
                                                      ('赶上 AI 与芯片浪潮', f'{len(big)} 笔芯片/AI 交易贡献约 {share * 100:.0f}% 的复利'),
                                                      ('换个十年未必成立', '一次回测 ≠ 普遍规律')]),
                   ('A股这十年', (1.0, 0.6, 0.24), [('股票池：5000 只全市场', '冠军多是小盘题材股'),
                                                    ('短期反转效应更明显', '暴涨之后容易均值回归'),
                                                    ('涨跌停与散户情绪', '更容易把价格推向极端'),
                                                    ('同样不能外推', '换股票池，结论也会改变')])],
             foot='单次回测只是一个样本，不能直接推出哪个市场更好'),
    ]
    S['principles'] = [('独立思考', '别人赚钱的消息\n不是买入的理由'), ('护城河', '看企业能否长期\n抵御竞争'),
                       ('内在价值', '估算未来的现金流\n而不是看去年涨幅'), ('安全边际', '价格明显低于价值\n才值得出手')]
    S['final_msg'] = ['投资不是寻找最热门的股票，', '而是判断企业未来能创造多少价值，', '以及今天的价格是否值得支付。']


if __name__ == '__main__':
    build()
