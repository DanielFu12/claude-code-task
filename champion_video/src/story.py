"""把回测结果（backtest/out_us.json, out_cn.json）整理成画面用的 story.json。"""
import json, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
BT = os.path.join(HERE, '..', 'backtest')

US_CN_NAME = {'NFLX': '奈飞', 'NVDA': '英伟达', 'NRG': 'NRG 能源', 'AMD': '超威半导体', 'TSLA': '特斯拉',
              'DVN': '德文能源', 'OXY': '西方石油', 'PLTR': 'Palantir'}
US_EN_SHORT = {'NFLX': 'Netflix', 'NVDA': 'NVIDIA', 'NRG': 'NRG Energy', 'AMD': 'AMD', 'TSLA': 'Tesla',
               'DVN': 'Devon Energy', 'OXY': 'Occidental', 'PLTR': 'Palantir'}



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
    """原因分析与投资启示的文字和数据（数据来自 backtest/evidence.json，由 evidence.py 生成）"""
    E = json.load(open(os.path.join(BT, 'evidence.json')))
    ut, ct = S['us_total'], S['cn_total']
    S['gap'] = ut / ct
    uy = [y['us']['ret'] for y in S['years']]; ub = [y['us_bench'] for y in S['years']]
    cy = [y['cn']['ret'] for y in S['years']]; cb = [y['cn_bench'] for y in S['years']]
    u_beat = sum(a > b for a, b in zip(uy, ub)); c_beat = sum(a > b for a, b in zip(cy, cb)); c_down = sum(a < 0 for a in cy)
    big = [i for i, y in enumerate(S['years']) if y['us']['code'] in ('NVDA', 'AMD', 'PLTR')]
    share = sum(math.log(1 + uy[i]) for i in big) / math.log(ut)
    S['stats'] = dict(us_beat=u_beat, cn_beat=c_beat, cn_down=c_down, us_big_n=len(big), us_big_share=share)
    # 利润 vs 股价：挑出三类典型（数据均来自东方财富年报）
    P = {x['name']: x for x in E['cn_profit']}
    def mult(n): return P[n]['np_y'] / P[n]['np_prev']
    rows = [
        ('一次性景气：利润是真的，但已到顶', [
            ('英科医疗', P['英科医疗']['year'], P['英科医疗']['price'], f"利润 ×{mult('英科医疗'):.0f}（疫情手套）", P['英科医疗']['next_ret']),
            ('万集科技', P['万集科技']['year'], P['万集科技']['price'], f"利润 ×{mult('万集科技'):.0f}（ETC 政策）", P['万集科技']['next_ret']),
            ('湖北宜化', P['湖北宜化']['year'], P['湖北宜化']['price'], f"利润 ×{mult('湖北宜化'):.1f}（化工周期顶点）", P['湖北宜化']['next_ret'])]),
        ('题材驱动：股价跑在利润前面', [
            ('联特科技', P['联特科技']['year'], P['联特科技']['price'], f"利润 {(mult('联特科技') - 1) * 100:+.0f}%，市盈率约 500 倍", P['联特科技']['next_ret']),
            ('绿康生化', P['绿康生化']['year'], P['绿康生化']['price'], '连续亏损，靠跨界光伏概念', P['绿康生化']['next_ret'])]),
        ('价值兑现：利润追上了股价', [
            ('寒武纪', P['寒武纪']['year'], P['寒武纪']['price'], f"次年扭亏，净利润 {P['寒武纪']['np_next'] / 1e8:.1f} 亿", P['寒武纪']['next_ret'])]),
    ]
    ipo = E['ipo']
    worse = sum(r['top50_next'] < r['market_next'] for r in ipo)
    mo = E['momentum']
    S['why'] = [
        dict(kind='bars', title='差距从哪里来？', sub='冠军的下一年：每根柱子 = 买入当年的实际收益',
             groups=[('美股冠军', (0.31, 0.82, 1.0), uy, ub), ('A股冠军', (1.0, 0.6, 0.24), cy, cb)],
             notes=[f'10 年里 {u_beat} 年跑赢标普500', f'10 年里 {c_down} 年亏损，只有 {c_beat} 年跑赢沪深300']),
        dict(kind='principle', title='回到第一性原理', sub='股价从长期看由什么决定？'),
        dict(kind='profit', title='A股冠军：涨的是利润，还是情绪？', sub='上一年股价涨幅 vs 当年利润变化（年报数据）', rows=rows),
        dict(kind='ipo', title='A股的「炒新」', sub='每年涨幅榜前 50 名里，当年新上市的股票有几只？',
             years=[r['year'] for r in ipo], new=[r['new'] for r in ipo], worse=worse,
             share=E['ipo_summary']['new_share']),
        dict(kind='players', title='谁在交易，决定了价格怎么走', sub='市场的参与者与交易制度',
             us_top10=mo['us']['top10'], cn_top10=mo['cn']['top10']),
        dict(kind='loop', title='FOMO 与反身性', sub='上涨本身，会吸引更多人追涨',
             nodes=['股价大涨', '媒体热议', '新资金涌入', '继续上涨'], center='涨幅冠军',
             **{'break': '直到：预期透支，泡沫破裂'}, foot='价格反过来改变人们的预期——这就是反身性',
             foot2=f'美股这十年也有运气：{len(big)} 笔芯片/AI 交易贡献了约 {share * 100:.0f}% 的复利'),
    ]
    S['value_cmp'] = [('A股', (1.0, 0.6, 0.24), [('追涨冠军', ct, True), ('持有沪深300（含分红）', S['cn_bench_total'], False)]),
                      ('美股', (0.31, 0.82, 1.0), [('追涨冠军', ut, True), ('持有标普500（含分红）', S['us_bench_total'], False)])]
    S['principles'] = [('独立思考', '别人赚钱的消息\n不是买入的理由'), ('护城河', '看企业能否长期\n抵御竞争'),
                       ('内在价值', '估算未来的现金流\n而不是看去年涨幅'), ('安全边际', '价格明显低于价值\n才值得出手')]
    S['final_msg'] = ['投资不是追逐最热门的股票，', '而是判断企业未来能创造多少价值，', '以及今天的价格是否值得支付。']


if __name__ == '__main__':
    build()
