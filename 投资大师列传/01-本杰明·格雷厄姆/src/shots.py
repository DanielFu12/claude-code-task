"""《本杰明·格雷厄姆：安全边际的守门人》分镜数据（投资大师列传 · 第 01 集）。

脚本.md 由本文件整份生成：python3 src/shots.py > 脚本.md
字段（与第 04 集一致，见 投资大师列传/制作规范.md 3.3 节）：
  ch     章节名（章节首镜才写）
  kind   画面类型：title / map / photo / film / card / quote / data / end
  year   大字年份（含「同年」），可空
  age    年龄，追加在年份后，如「1934年-40岁」（生日 5 月 9 日，已按生日精确计算）
  lines  白色说明字幕，一般 1–2 句（引语可 3 句）；【】内的词用红色强调
  bg     背景素材：assets/<bg>.jpg（map 表示点阵地图）
  fx     特殊动画（需在 src/render_v.py 的 fx_draw / MAPS 里实现）
  tag    错误清单小标（可选）
  visual 画面说明
  dur    时长：按阅读速度自动计算（见 need()），与 src/music_r.py 的公式一致
"""

SHOTS = [
    # ── 序章 ──
    dict(ch="序章", kind="title", fx="title", year="", age="", lines=["本杰明·格雷厄姆", "安全边际的守门人"],
         visual="黑底飘雪，金色粒子旋转汇聚成「本杰明·格雷厄姆」，副标题擦出"),
    dict(kind="card", bg="london", year="", age="", lines=["1894年5月9日，生于伦敦一个犹太家庭", "父亲做瓷器进口生意"],
         visual="灰色纸卡 + 右侧 19 世纪末伦敦街头瓷器店的老照片"),
    dict(kind="map", fx="london_ny", year="1895年", age="1岁", lines=["举家横渡大西洋", "移民美国纽约"],
         visual="点阵地图：红针先落在伦敦，镜头拉远横跨大西洋，落到纽约"),
    # ── 苦难少年 ──
    dict(ch="苦难少年", kind="photo", bg="mourning", year="1903年", age="", lines=["父亲病逝，家道中落", "母亲开起家庭旅馆维持生计"],
         visual="20 世纪初纽约公寓楼里的家庭旅馆，昏暗的走廊"),
    dict(kind="data", bg="panic1907", fx="panic1907", year="1907年", age="13岁", lines=["母亲借钱买股票", "在【1907年大恐慌】中血本无归"],
         visual="1907 年银行挤兑人群；股价折线断崖下跌，红色「爆仓」标记"),
    dict(kind="photo", bg="boy_work", year="少年时", age="", lines=["打零工补贴家用", "靠奖学金考入哥伦比亚大学"],
         visual="少年背影在街头送货，远处是大学建筑"),
    dict(kind="photo", bg="columbia", year="1914年", age="20岁", lines=["以全班第二名从哥伦比亚大学毕业", "英文、数学、哲学三个系都请他留校任教"],
         visual="哥伦比亚大学校园与毕业典礼的远景"),
    # ── 华尔街学徒 ──
    dict(ch="华尔街学徒", kind="photo", bg="wallst1914", year="同年", age="", lines=["他却去了华尔街", "在券商当跑腿，周薪【12美元】"],
         visual="1910 年代华尔街，年轻人背影在交易所黑板前抄写行情"),
    dict(kind="data", bg="mining", fx="guggenheim", year="1915年", age="21岁", lines=["研究古根海姆勘探公司的解散方案", "算出资产价值高于股价，套利大赚"],
         visual="资产拆分柱状图：「持有资产价值」高于「股价」，差额标成金色利润"),
    dict(kind="photo", bg="ww1", year="1917年", age="", lines=["一战期间反德情绪高涨", "全家把姓氏从格罗斯鲍姆改为格雷厄姆"],
         visual="1917 年纽约街头的征兵海报（文字不可读）与人群"),
    dict(kind="photo", bg="office1923", year="1923年", age="29岁", lines=["自立门户", "成立格雷厄姆公司"],
         visual="1920 年代办公室，打字机与账本"),
    dict(kind="photo", bg="partners1926", year="1926年", age="32岁", lines=["与杰罗姆·纽曼合伙", "成立格雷厄姆联合账户"],
         visual="两位西装男士在办公桌前握手，远景虚焦"),
    # ── 价值的发现 ──
    dict(ch="价值的发现", kind="data", bg="archive", fx="pipeline", year="同年", age="", lines=["在州际商务委员会的档案里发现", "北方管道每股握有约95美元的债券和现金"],
         visual="档案室翻阅卷宗；柱状图：每股资产约 95 美元"),
    dict(kind="data", bg="archive", fx="pipeline2", year="", age="", lines=["股价却只有约65美元", "他买入股份，要求公司把多余现金还给股东"],
         visual="柱状图续：股价约 65 美元的柱子远低于资产柱，差额高亮"),
    dict(kind="photo", bg="proxy1928", year="1928年", age="33岁", lines=["历经两年的代理权之争", "公司最终向股东派发大笔现金"],
         visual="1920 年代股东大会会场，人群举手表决"),
    dict(kind="card", bg="proxy1928", year="", age="", lines=["他是华尔街最早的", "「激进投资者」之一"],
         visual="灰色纸卡 + 股东大会照片"),
    dict(kind="data", fx="netnet", year="", age="", lines=["他的独门方法：只买股价低于", "【净流动资产三分之二】的公司"],
         visual="数据图：一家公司的净流动资产柱 vs 股价柱，股价只到 2/3 刻度线"),
    dict(kind="card", bg="cigar", year="", age="", lines=["后来巴菲特把这种方法称为「捡烟蒂」", "便宜到几乎不会亏钱"],
         visual="灰色纸卡 + 人行道上一截烟蒂的特写"),
    dict(kind="photo", bg="classroom1928", year="同年", age="", lines=["开始在哥伦比亚商学院夜校授课", "一教就是28年"],
         visual="夜晚的大学阶梯教室，黑板写满数字，学生背影"),
    # ── 绝境重生 ──
    dict(ch="绝境重生", kind="data", bg="crash1929", fx="crash29", year="1929年", age="35岁", lines=["大崩盘来袭", "他用了杠杆，账户一路下跌"],
         visual="1929 年交易所外人群；联合账户净值折线一路下跌"),
    dict(kind="data", bg="crash1929", fx="crash29b", year="1932年", age="38岁", lines=["联合账户累计亏损约【70%】", "他几乎倾家荡产"],
         visual="折线触底，-70% 红字砸下"),
    dict(kind="quote", bg="forbes1932", year="同年", age="", lines=["他在《福布斯》连发文章发问：", "「美国企业死了比活着更值钱吗？」"],
         visual="灰色纸卡引语 + 1930 年代报刊堆叠的照片（文字不可读）"),
    dict(kind="data", fx="belowcash", year="", age="", lines=["大批公司的股价", "跌破了账上的现金"],
         visual="数据图：一排公司的股价柱都低于各自的「每股现金」虚线"),
    dict(kind="photo", bg="ledger", year="", age="", lines=["他没有抛下合伙人", "不拿报酬，直到把亏损全部赚回来"],
         visual="深夜台灯下的账本和计算尺"),
    dict(kind="photo", bg="book1934", year="1934年", age="40岁", lines=["与学生戴维·多德合著《证券分析》", "价值投资由此奠基"],
         visual="厚重的旧书放在书桌上，台灯照亮（封面无文字）"),
    dict(kind="quote", year="", age="", lines=["「投资是经过深入分析，", "保证本金安全并获得满意回报的操作；", "做不到这些，就是投机。」"],
         visual="灰色纸卡引语，黄色描边"),
    dict(kind="photo", bg="office1936", year="1936年", age="42岁", lines=["成立格雷厄姆-纽曼公司"],
         visual="1930 年代曼哈顿写字楼办公室全景"),
    # ── 思想的巅峰 ──
    dict(ch="思想的巅峰", kind="photo", bg="insurance1948", year="1948年", age="54岁", lines=["约71万美元买下【GEICO】一半股份", "约占基金资产的四分之一"],
         visual="1940 年代保险公司办公楼，打字员一排排工作"),
    dict(kind="data", fx="geico", year="", age="", lines=["GEICO此后一路成长", "这一笔的利润，超过他其余所有投资的总和"],
         visual="数据图：GEICO 一根柱子拔地而起，高过旁边所有小柱子的总和"),
    dict(kind="photo", bg="book1949", year="1949年", age="", lines=["出版《聪明的投资者》", "写给普通投资者的投资圣经"],
         visual="客厅里一本打开的书和老花镜，窗外暖光"),
    dict(kind="card", bg="book1949", year="", age="", lines=["他把投资者分成两种：", "「防御型」求稳，「进取型」肯下功夫"],
         visual="灰色纸卡：左右两栏「防御型 / 进取型」"),
    dict(kind="quote", bg="mrmarket", year="", age="", lines=["「市场先生」每天都来报价", "你可以利用他，但不要被他左右"],
         visual="灰色纸卡引语 + 老式行情报价机的照片"),
    dict(kind="quote", year="", age="", lines=["「短期看，市场是一台投票机；", "长期看，它是一台称重机。」"],
         visual="灰色纸卡引语"),
    dict(kind="quote", year="", age="", lines=["「如果把稳健投资的秘诀浓缩成四个字，", "那就是：【安全边际】。」"],
         visual="灰色纸卡引语，「安全边际」四字红色加粗"),
    dict(kind="photo", bg="classroom1950", year="1950年", age="", lines=["一个20岁的年轻人走进他的课堂", "他叫【沃伦·巴菲特】"],
         visual="1950 年代教室，一个年轻人的背影坐在前排"),
    # ── 格雷厄姆的错误清单 ──
    dict(ch="格雷厄姆的错误清单", kind="card", bg="stamp", fx="stamp", year="", age="", lines=["价值投资之父也会犯错", "而且错得很痛"],
         visual="灰色纸卡，红色印章「错误清单」盖下；之后每个镜头左上角挂红色小标"),
    dict(kind="photo", bg="tire1919", tag="01 · 跟风投机", year="1919年", age="", lines=["听信朋友的内幕消息，跟风买入萨沃德轮胎股", "操纵者卷款而逃，血本无归"],
         visual="1910 年代轮胎厂外景，人去楼空"),
    dict(kind="data", bg="crash1929", fx="leverage", tag="02 · 加杠杆", year="1929年", age="", lines=["大崩盘前借钱放大仓位", "下跌被杠杆成倍放大"],
         visual="数据图：同样的跌幅，带杠杆的账户柱子缩得更多"),
    dict(kind="data", bg="crash1929", fx="early", tag="03 · 抄底太早", year="1930年", age="", lines=["以为最坏的时候已经过去，加仓抄底", "结果越跌越深"],
         visual="折线：1930 年的「抄底」标记之后又跌了一大段"),
    dict(kind="data", fx="diversify", tag="04 · 过度分散", year="", age="", lines=["一辈子买过数百只便宜股", "一只GEICO却胜过其余所有"],
         visual="数据图：上百个小点 vs 一根 GEICO 长柱"),
    dict(kind="quote", fx="unstamp", year="", age="", lines=["从此他不再借钱投资：", "「投资者最大的敌人，很可能就是他自己。」"],
         visual="灰色纸卡引语，红色印章淡出，金色重新亮起"),
    # ── 落幕 ──
    dict(ch="落幕", kind="photo", bg="office1954", year="1954年", age="60岁", lines=["聘请巴菲特加入格雷厄姆-纽曼公司"],
         visual="1950 年代办公室，两人隔着办公桌交谈的远景"),
    dict(kind="photo", bg="analysts", year="", age="", lines=["他倡导的证券分析师资格认证", "后来发展成今天的【CFA】"],
         visual="1950 年代分析师协会会议室，众人背影"),
    dict(kind="map", fx="california", year="1956年", age="62岁", lines=["宣布退休，解散公司", "移居加州，在大学继续讲课"],
         visual="点阵地图：红针从纽约跨越美国落到洛杉矶"),
    dict(kind="photo", bg="provence", fx="mono", year="1976年", age="82岁", lines=["9月21日在法国去世", "享年82岁"],
         visual="普罗旺斯小镇黄昏，画面渐变黑白"),
    dict(kind="photo", bg="speech1984", year="1984年", age="", lines=["巴菲特发表著名演讲", "《格雷厄姆-多德都市的超级投资者们》", "他的追随者们长期跑赢市场"],
         visual="大学礼堂的演讲台远景"),
    dict(kind="photo", bg="campus_now", year="今天", age="", lines=["他的方法仍在课堂上讲授", "价值投资者都是他的学生"],
         visual="现代大学校园，学生背影走向教学楼"),
    # ── 尾声 ──
    dict(ch="尾声", kind="data", fx="gn_return", year="1936–1956", age="", lines=["格雷厄姆-纽曼公司年化回报约20%", "同期股市约12%"],
         visual="两根柱子对比上升：约 20% 金色、约 12% 灰色"),
    dict(kind="card", bg="podium_old", year="", age="", lines=["先想会亏多少，再想能赚多少", "买股票，就是买企业的一部分"],
         visual="灰色纸卡总结 + 老式讲台照片"),
    dict(kind="film", bg="library", year="", age="", lines=["他没有留下最多的财富", "却留下了最多的「学生」"],
         visual="老图书馆书架间的慢推镜头"),
    dict(kind="film", bg="wallst_dusk", year="", age="", lines=["市场每天都在出价", "守住安全边际，剩下的交给时间"],
         visual="华尔街黄昏慢动作，人流背影"),
    dict(kind="end", fx="end", year="", age="", lines=["关注 MastersTao", "传承大师智慧，领悟投资真谛。"],
         visual="MastersTao 品牌片尾：粒子汇聚成官方 logo → 重拍扫光揭示 → 关注 MastersTao → masterstao.com"),
]

READ_RATE, READ_BASE, READ_MIN = 8.0, 1.0, 3.5


def need(s):
    """按字幕字数估算阅读时长（与 src/music_r.py 一致）"""
    if s["kind"] == "title":
        return 5.0
    if s["kind"] == "end":
        return 17.0
    n = sum(len(l.replace("【", "").replace("】", "")) for l in s["lines"])
    d = READ_BASE + n / READ_RATE
    if s["kind"] == "map" or (s["kind"] == "data" and s.get("fx")):
        d += 0.8
    if s["kind"] in ("quote", "card"):
        d += 0.5
    return max(READ_MIN, d)


for _s in SHOTS:
    _s.setdefault("dur", round(need(_s), 1))

KIND = dict(title="标题", map="地图", photo="档案照", film="档案影像", card="纸卡", quote="引语卡", data="数据图", end="片尾")


def tc(s):
    return f"{int(s)//60}:{int(s)%60:02d}"


HEAD = """# 本杰明·格雷厄姆：安全边际的守门人 · 视频脚本

> 投资大师列传 · 第 01 集 ｜ 竖屏 1080×1920 · 约 {total}（按阅读速度估算，最终以配乐卡点为准）｜ {n} 个镜头 ｜ 无旁白，靠音乐和字幕推进
>
> 本文件由 `src/shots.py` 生成，修改请改分镜数据后执行：`python3 src/shots.py > 脚本.md`。制作按 `投资大师列传/制作规范.md` 执行。

一句话主线：**一个在 1907 年看着母亲爆仓、又在 1929 年几乎破产的人，把自己的伤疤写成了一条原则——安全边际。他没有留下最多的财富，却留下了最多的学生。**

## 一、章节结构

| 章节 | 内容 | 情绪 |
|---|---|---|
| 序章 | 片头、家世、从伦敦移民纽约 | 发闷、回忆 |
| 苦难少年 | 父亲早逝、母亲在 1907 年大恐慌中爆仓、三个系争着留他任教 | 偏暖、压抑 |
| 华尔街学徒 | 周薪 12 美元的跑腿、古根海姆套利、改姓、自立门户、与纽曼合伙 | 逐渐打开 |
| 价值的发现 | 北方管道之战（最早的激进投资之一）、净流动资产选股法、开始授课 | 完全打开，第一次大落点 |
| 绝境重生 | 1929–1932 年因杠杆亏损约 70%、《福布斯》文章「死了比活着更值钱」、不拿报酬还清合伙人、《证券分析》 | 先沉后扬 |
| 思想的巅峰 | GEICO、《聪明的投资者》、防御型与进取型、市场先生、投票机与称重机、安全边际、巴菲特入门 | 全开，最高潮 |
| 格雷厄姆的错误清单 | 跟风投机、加杠杆、抄底太早、过度分散；章尾「最大的敌人是自己」 | 压暗收窄 |
| 落幕 | 聘请巴菲特、倡导分析师认证（CFA）、退休西迁、在法国去世、「格雷厄姆-多德都市」 | 慢慢打开 |
| 尾声 | 20 年年化约 20% vs 约 12%、总结卡、一句话总结 | 全开 |
| 片尾 | MastersTao 品牌片尾 | — |

## 二、分镜脚本

"""

TAIL = """
## 三、制作要点

- **配乐与卡点**：沿用第 04 集的参照片配乐（`assets/music/ref_bgm.m4a`）与 `src/music_r.py` 的做法：章节开头落在重拍上，章内切镜吸附重拍，按阅读时长分配；大落点放在「华尔街学徒」「价值的发现」「思想的巅峰」「尾声」。总时长比第 04 集短，需要重新挑选拼接段 `SEGS`。
- **需要新做的动画**（`src/render_v.py`）：
  - 地图：`london_ny`（伦敦 → 横跨大西洋 → 纽约）、`california`（纽约 → 洛杉矶）
  - 数据：`belowcash`（股价柱低于每股现金虚线）、`panic1907`（股价断崖 + 爆仓标记）、`guggenheim`（资产价值 vs 股价）、`pipeline` / `pipeline2`（每股资产约 95 vs 股价约 65）、`netnet`（股价只到净流动资产 2/3 刻度）、`crash29` / `crash29b`（账户净值下跌至约 -70%）、`geico`（一根长柱 vs 其余总和）、`leverage`（有无杠杆的跌幅对比）、`early`（抄底后继续下跌）、`diversify`（上百个小点 vs 一根长柱）、`gn_return`（约 20% vs 约 12%）
- **画面素材**：需要新生成（`src/assets.py`），id 见上表「画面」列对应的 `bg` 字段；年代风格以 1890–1950 年代黑白泛黄胶片为主，结尾转现代。不画真人正脸，不出现可读文字和商标。
- **品牌**：MastersTao 角标、底部关注语胶囊、MastersTao 品牌片尾，片尾不放评论区互动。
- **错误清单**章名为「格雷厄姆的错误清单」，`render_v.py` 的 `ERR`、`trans_type()` 和 `music_r.py` 的章名引用要同步修改。

## 四、待核实事项（制作前必须核对）

以下根据公开资料整理（主要来源：格雷厄姆回忆录《本杰明·格雷厄姆：华尔街教父》、《证券分析》《聪明的投资者》、巴菲特致股东信与 1984 年演讲），数字和年份需要逐条核对：

1. 移民纽约的年份（1895 年）与当时年龄。
2. 父亲去世的年份（1903 年）；母亲开家庭旅馆、在 1907 年借钱买股票爆仓的细节。
3. 1914 年毕业名次（全班第二）以及英文、数学、哲学三个系邀请留校的说法。
4. 入行时的公司（纽伯格-亨德森-勒布）和周薪 12 美元。
5. 古根海姆勘探公司套利的年份（1915 年）与结果。
6. 改姓的年份（1917 年）。
7. 格雷厄姆公司成立年份（1923 年）；与纽曼成立联合账户的年份（1926 年）。
8. 北方管道公司：每股约 95 美元资产、股价约 65 美元、1928 年的派现金额。
9. 净流动资产「三分之二」的选股标准表述。
10. 1929–1932 年联合账户累计亏损约 70%；此后不收报酬直到弥补亏损的说法与时间。
11. 哥伦比亚商学院授课起止（1928–1956 年，「一教就是 28 年」）。
12. 「投资与投机」定义的原文与出处（《证券分析》1934 年版）。
13. GEICO：1948 年约 71.2 万美元、约一半股份、约占基金资产四分之一；「利润超过其余所有投资总和」出自《聪明的投资者》1973 年版后记。
14. 「投票机与称重机」是巴菲特转述格雷厄姆的话；「安全边际」引语出自《聪明的投资者》第 20 章。
15. 1919 年萨沃德轮胎股投机失利的细节（出自回忆录）；1930 年加仓抄底的细节。
16. 巴菲特 1950 年入学、1954 年加入格雷厄姆-纽曼、1956 年公司解散的时间。
17. 去世日期与地点：1976 年 9 月 21 日，法国艾克斯普罗旺斯，享年 82 岁。
18. 格雷厄姆-纽曼公司 1936–1956 年年化约 20%、同期股市约 12% 的数据来源。
19. 1932 年《福布斯》系列文章（「Is American Business Worth More Dead Than Alive?」）的发表时间，以及「大批公司股价跌破账上现金」的表述。
20. 「防御型 / 进取型投资者」的划分（《聪明的投资者》）。
21. 格雷厄姆倡导证券分析师资格认证与 CFA 的关系（CFA 于 1963 年首次颁发）。
22. 档案照片和影像全部用 AI 示意图，不使用真人肖像。
"""


def render():
    rows, t = [], 0
    rows.append("| # | 时间 | 大字 | 字幕 | 画面类型 | 画面 |")
    rows.append("|---|---|---|---|---|---|")
    for i, s in enumerate(SHOTS, 1):
        if s.get("ch"):
            rows.append(f"| | | **【{s['ch']}】** | | | |")
        big = s["year"] + (f"-{s['age']}" if s["age"] else "")
        if s.get("tag"):
            big = f"错误清单 {s['tag']}" + (f"<br>{big}" if big else "")
        txt = "<br>".join(l.replace("【", "**").replace("】", "**") for l in s["lines"])
        rows.append(f"| {i} | {tc(t)}–{tc(t+s['dur'])} | {big or '—'} | {txt} | {KIND[s['kind']]} | {s['visual']} |")
        t += s["dur"]
    total = f"{int(t)//60} 分 {int(t)%60} 秒"
    return HEAD.format(total=total, n=len(SHOTS)) + "\n".join(rows) + "\n" + TAIL


if __name__ == "__main__":
    print(render(), end="")
