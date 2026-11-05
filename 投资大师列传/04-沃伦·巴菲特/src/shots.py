"""《沃伦·巴菲特：股神的复利人生》分镜数据。

脚本.md 由本文件生成：python3 src/shots.py > 脚本.md
字段：
  year   大字年份（含「同年」），可空
  age    年龄，追加在年份后，如「1965年-35岁」
  lines  白色说明字幕，最多 2 行；【】内的词用红色强调
  kind   画面类型：title / map / photo / film / card / quote / data / end
  visual 画面说明
  dur    时长（秒）
"""

SHOTS = [
    # ── 序章 ──
    dict(kind="title", dur=4, year="", age="", lines=["沃伦·巴菲特", "股神的复利人生"],
         visual="黑底，金色标题从雪粒中聚合；小字「投资大师列传 · 04」"),
    dict(kind="card", dur=4, year="", age="", lines=["祖父在奥马哈开杂货铺", "父亲霍华德是股票经纪人"],
         visual="灰色纸卡 + 右侧「巴菲特父子杂货店」老照片"),
    dict(kind="map", dur=4, year="1930年", age="", lines=["8月30日", "出生于美国内布拉斯加州奥马哈"],
         visual="卫星地图从北美俯冲到奥马哈，红色定位针落下"),
    # ── 少年生意经 ──
    dict(kind="photo", dur=4, year="1936年", age="6岁", lines=["25美分买进6瓶可乐", "5美分一瓶卖出，赚到人生第一笔利润"],
         visual="童年照片 + 6 个可乐瓶依次弹出"),
    dict(kind="data", dur=4, year="1941年", age="11岁", lines=["38美元买入3股城市服务优先股", "跌到27美元，回本后40美元卖出"],
         visual="股价折线：38 → 27 → 40，在 40 处打点「卖出」"),
    dict(kind="data", dur=4, year="", age="", lines=["卖出后它一路涨到200美元", "他学到的第一课：【耐心】"],
         visual="折线继续冲到 200，卖出点变灰"),
    dict(kind="map", dur=3, year="1942年", age="", lines=["父亲当选国会议员", "举家迁往华盛顿"],
         visual="地图定位针从奥马哈跳到华盛顿"),
    dict(kind="photo", dur=4, year="1943年", age="13岁", lines=["每天清晨送约500份《华盛顿邮报》", "第一次报税，自行车抵扣35美元"],
         visual="少年骑车送报的档案照，报纸标头特写"),
    dict(kind="photo", dur=4, year="高中时", age="", lines=["和朋友花25美元买下二手弹子机", "摆进理发店，和店主分成"],
         visual="老式弹子机照片，硬币落入投币口"),
    dict(kind="data", dur=3, year="1947年", age="16岁", lines=["高中毕业", "已攒下约5000美元"],
         visual="数字从 0 滚到 $5,000"),
    # ── 拜师格雷厄姆 ──
    dict(kind="quote", dur=5, year="1949年", age="19岁", lines=["读到格雷厄姆《聪明的投资者》", "「迄今为止最好的投资书」"],
         visual="灰色纸卡：书封 + 引语，黄色描边"),
    dict(kind="map", dur=4, year="1950年", age="", lines=["被哈佛商学院拒绝", "转投哥伦比亚大学，拜师格雷厄姆"],
         visual="地图拉到纽约，红针落在哥伦比亚大学"),
    dict(kind="photo", dur=3, year="1951年", age="", lines=["格雷厄姆课上唯一拿到", "【A+】的学生"],
         visual="格雷厄姆档案照，黄色圆圈圈出"),
    dict(kind="photo", dur=4, year="同年", age="20岁", lines=["周六敲开GEICO大门，长谈4小时", "随后把一大半积蓄买进GEICO"],
         visual="GEICO 老办公楼照片 + 推门动画"),
    dict(kind="photo", dur=4, year="1952年", age="", lines=["与苏珊·汤普森结婚", "报名卡耐基演讲课，克服当众说话的恐惧"],
         visual="婚礼照片；右下角小图为演讲课结业证书"),
    dict(kind="map", dur=4, year="1954年", age="24岁", lines=["加入格雷厄姆-纽曼公司", "年薪1.2万美元"],
         visual="纽约华尔街定位"),
    # ── 合伙基金时代 ──
    dict(kind="photo", dur=5, year="1956年", age="25岁", lines=["回到奥马哈，7位亲友凑出10.5万美元", "成立巴菲特合伙公司，他只出了100美元"],
         visual="地图回到奥马哈 → 合伙协议文件特写"),
    dict(kind="map", dur=4, year="1958年", age="", lines=["3.15万美元买下法纳姆街的房子", "此后一住就是60多年"],
         visual="奥马哈街区卫星图，红针 + 房子实拍小窗"),
    dict(kind="photo", dur=4, year="1959年", age="", lines=["在奥马哈一场晚宴上认识查理·芒格", "此后成为一生的搭档"],
         visual="两人合影，黄色圆圈先圈巴菲特再圈芒格"),
    dict(kind="photo", dur=4, year="1962年", age="", lines=["以每股约7.6美元", "开始买入纺织厂【伯克希尔·哈撒韦】"],
         visual="新贝德福德纺织厂外景"),
    dict(kind="photo", dur=4, year="1964年", age="", lines=["收购要约比口头约定少了1/8美元", "他被激怒，决定买下整家公司"],
         visual="要约文件特写，「11 3/8」被红笔圈出"),
    dict(kind="photo", dur=4, year="同年", age="", lines=["美国运通陷入「色拉油丑闻」", "他把约40%的合伙资金押了上去"],
         visual="美国运通旧标志 + 报纸头条"),
    dict(kind="photo", dur=4, year="1965年", age="34岁", lines=["入主伯克希尔", "后来自嘲这是「最愚蠢的一笔投资」"],
         visual="伯克希尔早期年报封面"),
    dict(kind="photo", dur=4, year="1967年", age="", lines=["860万美元收购国民保险公司", "【浮存金】成为复利的发动机"],
         visual="保险单 → 资金流动画汇入伯克希尔"),
    dict(kind="data", dur=5, year="1969年", age="", lines=["牛市狂热中解散合伙公司", "13年扣费前年化29.5%，同期道指7.4%"],
         visual="两条柱子对比上升，29.5% 金色、7.4% 灰色"),
    # ── 从烟蒂到伟大企业 ──
    dict(kind="photo", dur=4, year="1972年", age="", lines=["2500万美元买下喜诗糖果", "在芒格影响下，从「捡烟蒂」转向「买伟大企业」"],
         visual="喜诗糖果门店老照片"),
    dict(kind="quote", dur=5, year="", age="", lines=["「以合理的价格买入伟大的企业，", "远胜以便宜的价格买入平庸的企业。」"],
         visual="灰色纸卡引语，黄色横线"),
    dict(kind="photo", dur=4, year="1973年", age="", lines=["股灾中买入《华盛顿邮报》", "少年时送的报纸，成了他持股的公司"],
         visual="回放 1943 年送报画面 → 叠化成邮报大楼"),
    dict(kind="quote", dur=4, year="1974年", age="", lines=["美股暴跌近一半，他却说：", "「现在是投资并致富的时候了」"],
         visual="《福布斯》1974 年 11 月访谈页面"),
    dict(kind="photo", dur=4, year="1976年", age="", lines=["GEICO濒临破产", "他逆势出手，再次重仓"],
         visual="GEICO 档案影像，股价跌停数字"),
    dict(kind="photo", dur=3, year="1978年", age="", lines=["芒格出任伯克希尔副董事长", "「巴菲特 + 芒格」正式联手"],
         visual="两人在股东大会台上的合影"),
    dict(kind="photo", dur=4, year="1983年", age="", lines=["握手买下内布拉斯加家具城", "没有审计，只看人品"],
         visual="B 太太与巴菲特合影"),
    dict(kind="photo", dur=3, year="1985年", age="", lines=["关闭最后的纺织工厂", "伯克希尔变身投资控股集团"],
         visual="纺织厂机器停转，灯光熄灭"),
    dict(kind="photo", dur=4, year="1988年", age="", lines=["约10亿美元买入【可口可乐】约7%股权", "一拿就是30多年"],
         visual="巴菲特举可乐的经典镜头"),
    dict(kind="quote", dur=5, year="1991年", age="60岁", lines=["所罗门兄弟丑闻，临危出任董事长", "「让公司亏钱，我能理解；让公司名誉受损，我绝不留情」"],
         visual="国会听证会档案影像"),
    dict(kind="photo", dur=3, year="1993年", age="63岁", lines=["首次登顶《福布斯》", "【美国首富】"],
         visual="《福布斯》富豪榜页面，名字高亮"),
    dict(kind="photo", dur=4, year="1996年", age="", lines=["全资收购GEICO", "20岁时看中的公司，45年后全部归他"],
         visual="1951 年 GEICO 画面与 1996 年新闻并排"),
    # ── 坚守与逆行 ──
    dict(kind="photo", dur=4, year="1999年", age="", lines=["拒绝科技股，被嘲讽「股神过时了」", "《巴伦周刊》：巴菲特怎么了？"],
         visual="杂志封面，纳指曲线飙升"),
    dict(kind="data", dur=4, year="2000年", age="", lines=["互联网泡沫破裂", "伯克希尔股价当年逆势上涨约27%"],
         visual="纳指断崖下跌 vs 伯克希尔上行，两线交叉"),
    dict(kind="photo", dur=4, year="2006年", age="75岁", lines=["宣布将约85%的伯克希尔股票捐给慈善", "大部分交给盖茨基金会"],
         visual="与盖茨夫妇签约照片"),
    dict(kind="photo", dur=4, year="2008年", age="78岁", lines=["金融危机中50亿美元驰援高盛", "《纽约时报》撰文：「买美国，我正在买」"],
         visual="雷曼倒闭新闻 → 纽约时报专栏页面"),
    dict(kind="photo", dur=3, year="同年", age="", lines=["登顶《福布斯》", "【世界首富】"],
         visual="富豪榜封面"),
    dict(kind="quote", dur=5, year="", age="", lines=["「别人贪婪时我恐惧，", "别人恐惧时我贪婪。」"],
         visual="灰色纸卡引语"),
    dict(kind="film", dur=4, year="2009年", age="", lines=["约440亿美元（含债务）收购伯灵顿北方铁路", "他说这是「全押美国经济」"],
         visual="航拍火车穿越平原"),
    dict(kind="photo", dur=3, year="2010年", age="", lines=["与盖茨发起「捐赠誓言」", "号召富豪捐出大部分财富"],
         visual="两人同框发布会"),
    dict(kind="data", dur=4, year="2016年", age="85岁", lines=["开始买入苹果", "后来成为伯克希尔第一大持仓"],
         visual="苹果市值曲线 + 持仓饼图"),
    dict(kind="map", dur=3, year="2020年", age="90岁", lines=["买入日本五大商社", "首次大举押注日本"],
         visual="地图从奥马哈跨越太平洋落到东京"),
    # ── 落幕 ──
    dict(kind="photo", dur=4, year="2023年", age="", lines=["芒格离世，享年99岁", "「没有查理，就没有今天的伯克希尔」"],
         visual="两人最后一次同台，画面渐变黑白"),
    dict(kind="data", dur=4, year="2024年", age="", lines=["大幅减持苹果", "现金储备突破【3000亿美元】"],
         visual="现金柱从地面升起"),
    dict(kind="photo", dur=4, year="2025年", age="94岁", lines=["股东大会宣布年底卸任CEO", "交棒格雷格·阿贝尔"],
         visual="股东大会全场起立鼓掌"),
    dict(kind="photo", dur=4, year="2026年", age="96岁", lines=["仍任伯克希尔董事长", "依旧住在1958年买下的老房子里"],
         visual="法纳姆街老房子外景，黄色圆圈"),
    # ── 尾声 ──
    dict(kind="data", dur=5, year="1965–2024", age="", lines=["伯克希尔每股市值年化19.9%，标普500为10.4%", "累计涨幅：5,502,284% 对 39,054%"],
         visual="两组数字同时滚动，差距拉开"),
    dict(kind="data", dur=4, year="", age="", lines=["他约97%的财富", "是在【65岁之后】获得的"],
         visual="财富曲线：前段贴地，后段垂直上冲"),
    dict(kind="card", dur=5, year="", age="", lines=["11岁买第一只股票，一辈子只做一件事", "60年年化近20%，承诺捐出99%以上财富"],
         visual="灰色纸卡 + 左侧巴菲特招手照片"),
    dict(kind="film", dur=6, year="", age="", lines=["他的一生都在滚一个雪球", "找到很湿的雪、很长的坡，剩下的交给时间"],
         visual="股东大会人群簇拥巴菲特的影像，慢动作"),
    dict(kind="end", dur=5, year="", age="", lines=["巴芒价值", "BUFFETT · MUNGER"],
         visual="片尾：大号 logo + 金色「巴芒价值」+「BUFFETT · MUNGER」"),
]

KIND = dict(title="标题", map="地图", photo="档案照", film="档案影像", card="纸卡", quote="引语卡", data="数据图", end="片尾")


def tc(s):
    return f"{int(s)//60}:{int(s)%60:02d}"


def render():
    out, t = [], 0
    out.append("| # | 时间 | 大字 | 字幕 | 画面类型 | 画面 |")
    out.append("|---|---|---|---|---|---|")
    for i, s in enumerate(SHOTS, 1):
        big = s["year"] + (f"-{s['age']}" if s["age"] else "")
        txt = "<br>".join(l.replace("【", "**").replace("】", "**") for l in s["lines"])
        out.append(f"| {i} | {tc(t)}–{tc(t+s['dur'])} | {big or '—'} | {txt} | {KIND[s['kind']]} | {s['visual']} |")
        t += s["dur"]
    return "\n".join(out), t


if __name__ == "__main__":
    table, total = render()
    print(table)
    print(f"\n共 {len(SHOTS)} 个镜头，总时长 {tc(total)}。")
