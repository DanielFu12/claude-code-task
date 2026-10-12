# 2026 诺贝尔经济学奖：为什么你的预期，决定了经济的未来？

约 3 分钟的竖屏科普短片，从中国居民「不敢借、拼命存」的现实出发，讲清 2026 年诺贝尔经济学奖得主 **Robert E. Hall** 与 **Michael Woodford** 的贡献：他们为宏观经济稳定政策打下了微观经济学基础。

- 成片：`2026诺贝尔经济学奖_为什么你的预期决定了经济的未来.mp4`（1080×1920 竖屏 · 30 fps · 3:08 · H.264 + AAC）
- 预览版：`2026诺贝尔经济学奖_预览版.mp4`（720×1280，< 30 MB，方便直接在手机上看）
- 没有配音。叙事靠原创配乐、动态视觉、关键字幕和数据可视化完成，字幕按每秒不超过约 6 个字校验（`python3 src/timeline.py`）。
- 右上角全程是 `brand.Hud(frame_w=1080)` 画的官方角标，片尾大 logo 出现期间也保留，直到整片淡出。片尾 logo 只用 `brand/logo_baman.png` 原图。

## 一句话主线

> 影响经济的，不只是我们今天拥有多少，更是我们相信明天会发生什么。

## 分镜与音乐

配乐和音效都由 `src/music.py` 用 numpy 原创合成，没有外部采样。120 BPM，1 拍 = 0.5 s = 15 帧，所有段落、重拍和转场都落在拍点上。调性从 D 小调开始，在关键句处转到 D 大调。

| 时间 | 段落 | 画面 | 音乐 |
|---|---|---|---|
| 0:00–0:12 | 钩子 | 夜色中千万家庭的光点平面。5 年期 LPR 4.85% → 3.50% 像里程表一样逐级下跳 →「可是，大家借的钱反而越来越少」：居民新增贷款 2021 年 7.92 万亿 → 2025 年 0.44 万亿 →「钱，纷纷存进了银行」：2022 年新增存款 17.84 万亿 →「这到底是为什么？」 | 每次降息一声滴答。「可是」处先留出一拍空白，再接低频重击。riser 推向标题 |
| 0:12–0:20 | 标题 | 闪白、冲击波，光点平面冲向地平线，「明天」的金色光带亮起，标题逐字浮现 | **重拍 1**：boom + 低沉铜管 braam + 铃音 |
| 0:20–0:28 | 01 反常 · 时间之桥 | 3D 光桥从「今天」通向「明天」。借钱 = 金色光粒从明天流回今天；存钱 = 光粒掉头，变成冰蓝色流向明天 | 拨弦琶音律动开始 |
| 0:28–0:44 | 贷款 / 存款 | 3D 玻璃柱：居民新增贷款 2020–2025 逐年回落，2026 上半年转负（还的比借的多）。新增存款柱拔高，2022 年创历史最高。圆环：想「更多储蓄」的城镇储户从 45.7% 升到 61.8% | 贝斯、拍手、踩镲逐层加入 |
| 0:44–0:48 | 悖论 | 利率线与贷款柱一起向下：「钱更便宜了，人却更谨慎了」 | 抽掉鼓，只剩琶音 |
| 0:48–0:56 | 分化 | 四张磨砂玻璃卡：新房销售额 −12.6%、家电零售 +11%、服务零售 +5.5%、农村人均消费 +5.3%（数字滚动计数）→「消费没有消失，而是在分化」 | 半速律动，每张卡一声铃 |
| 0:56–1:00 | 原因 → 预期 | 收入、就业、房价、债务、人口、社保、物价、补贴八个词绕成 3D 星环，光粒汇向中心 → 金色大字「预期」 | 军鼓滚奏渐强 |
| 1:00–1:12 | 02 地基 | 诺奖金环 →「过去的模型，只看数字间的统计规律」：通胀—失业曲线被逐点画出 → 1970 年代滞胀的数据点出现，曲线碎裂 → 碎片重组成「家庭 / 企业」格点，托起「宏观经济」（微观基础） | **重拍 2**。数据点逐个以下行音落下，晶体碎裂声，再用上行琶音重建 |
| 1:12–1:34 | 03 霍尔：家庭的预期 | 官方肖像化作淡金色线稿作为背景 → 一生收入 / 消费曲线（借 · 存 · 花积蓄），预期未来收入一降，「今天」的消费马上跟着降 →「同样月入一万」：一人相信明天更好，一人担心失业，今天的消费完全不同 → 坏消息的冷色波从地平线推来，光点平面由金变蓝 →「消费，是对未来投出的一票」 | 温暖的钢琴主题 + 弦乐 |
| 1:34–1:56 | 04 伍德福德：企业与央行 | 线稿背景 → 一碗面的价签被锁住，月份翻过，未来成本 / 需求呈扇形展开 → 工厂的窗灯逐个熄灭，同时出现「民间投资 −10.1%」→ 一个利率旋钮，上百根丝线牵着千万家庭，旋钮一转，涟漪扩散（货币政策 ≈ 管理预期；前瞻指引）→ 德拉吉「不惜一切代价」 | 钟表式 16 分拨奏和滴答声 |
| 1:56–2:32 | 05 传导 | 五个节点的 3D 预期循环：预期 → 消费·储蓄 → 定价·投资 → 需求·物价 → 央行·政策，底下的光点平面一起荡开 → 向好时金色加速，悲观时冰蓝逆转（「预期，会自我实现」）→「降息，为什么有时不灵？」：真实借贷成本 ≈ 利率 − 预期涨幅 → 推绳子 → 财政直接出手（以旧换新 2500 亿、育儿补贴 3600 元），一次性 vs 长期可预期，时滞以季度计 | **重拍 3**：全编制高潮。转暗时有心跳低频，财政处重建 |
| 2:32–2:44 | 06 真相 | 光点平面上方日出：「宏观经济，不是抽象的数字 / 是亿万家庭和企业，对明天做出的选择 /…… 更是我们相信明天会发生什么」 | 钢琴 + 弦乐，关键句转 D 大调 |
| 2:44–2:58 | 获奖者 | 深酒红舞台，体积光与金色微尘。官方获奖肖像逐一登场（光带扫过），附姓名、单位、出生年和核心贡献 → 两人并列，加上官方获奖理由（英文原文 + 中文） | 庄重的赞美诗和声，每次登场都有定音鼓滚奏 + 重击 |
| 2:58–3:08 | 品牌片尾 | 两张肖像卡化成光粒，旋成漩涡后汇聚成官方 logo 的轮廓 → 清晰的 `logo_baman.png` 居中浮现（带规范里的淡蓝光晕）→ 在音乐重拍上出现金色「巴芒价值」和与之等宽的「BUFFETT · MUNGER」，流光扫过 → 整片淡出。右上角角标一直保留 | 汇聚 riser → logo 重拍 → 品牌字重拍 + 流光铃音 → 淡出 |

## 品牌执行

- 角标：`brand.Hud(frame_w=1080)`，每帧调用 `Hud.draw(frame, t)`。竖屏 1080 宽时 scale = 1，边距按 BRAND.md 取 52 / 30。角标画在最上层，不跟随镜头推拉，开场 0.5 秒内淡入，片尾一直保留到最终淡出。
- 片尾 logo：`brand.load_logo(220)`，即 BRAND.md 推荐的约 220 px。光晕颜色、σ、强度取 `brand.SPEC`，按 220 / 60 的比例放大。
- 片尾大字：完全按 `brand.build()` 的做法渲染。主标题用 `SPEC['title_font']`（Noto Serif SC Black）配 `GOLD_STOPS` 竖向渐变；小字用 `SPEC['sub_font']`（Cormorant Garamond），颜色为 `SUB_GOLD`，两端对齐到与主标题等宽。字号和间距都由 SPEC 按 220 / 60 推出。流光算法与 `Hud.rgb_at` 相同，时长取 `SPEC['shimmer_dur']`（1.4 s）。
- 粒子汇聚只用 logo 的透明通道采样目标点，最终显示的是原始 logo 图。
- 实现参考了 `love_video/render.py`（分支 `claude/youthful-franklin-j206py`，main 分支上没有这个目录）。

## 数据与出处

画面里所有数据都标了来源。标「示意」的画面（一生收入曲线、「同样月入一万」、真实借贷成本算例、西班牙国债收益率走势）只演示机制，不代表实测数据。

**诺贝尔奖资料**

| 内容 | 出处 |
|---|---|
| 2026 年 10 月 12 日公布；Robert E. Hall（斯坦福大学）、Michael Woodford（哥伦比亚大学）；获奖理由 “for microeconomic foundations of macroeconomic stabilisation”；奖金 1200 万瑞典克朗两人平分 | [Nobel Prize 官方新闻稿](https://www.nobelprize.org/prizes/economic-sciences/2026/press-release/)、[科学背景 PDF](https://www.nobelprize.org/uploads/2026/10/advanced-economicsciencesprize2026.pdf)；[新华网](https://www.news.cn/world/20261012/6cad3976454f435ea1770c585a9bea8a/c.html)、[NBER](https://www.nber.org/news/robert-hall-and-michael-woodford-awarded-2026-nobel-prize)、[CNN](https://www.cnn.com/2026/10/12/business/nobel-prize-economics-intl)、[AP / WBUR](https://www.wbur.org/news/2026/10/12/nobel-prize-economics-hall-woodford-mit) |
| 模型建立在家庭与企业的微观决策上，而不是宏观变量之间的统计关系；家庭和企业做储蓄、定价决策时是前瞻的；适时的财政与货币政策可以削峰填谷；委员会主席 Hassler：为各国央行和政府使用的模型提供了稳定的理论基础 | 同上（官方新闻稿，经 CNN、AP、Business Standard 等报道转述核对） |
| Hall：家庭的购买决定不只看当前购买力，也看对未来收入的预期；1978 年论文把永久收入假说与理性预期结合，消费是预期的指示器 | [NPR](https://www.npr.org/2026/10/12/nx-s1-5996634/last-nobel-prize-of-the-year-to-be-announced-for-economics)、[Axios](https://www.axios.com/2026/10/12/nobel-prize-economics-2026-hall-woodford)、[Fortune](https://fortune.com/2026/10/12/nobel-economics-2026-robert-hall-michael-woodford/) |
| Woodford：企业定价中预期的作用；央行通过利率（而不只是货币数量）影响经济；前瞻指引；著作《利息与价格》（2003） | [Fortune](https://fortune.com/2026/10/12/nobel-economics-2026-robert-hall-michael-woodford/)、[Seoul Economic Daily（获奖发布会）](https://en.sedaily.com/international/2026/10/12/nobel-economics-laureate-woodford-urges-central-banks-to)、[BBVA 知识前沿奖评语](https://www.frontiersofknowledgeawards-fbbva.es/galardonados/michael-woodford-2/) |
| 出生年：Hall 1943 年生（新华社），Woodford 1955 年生（CNN） | 同上 |
| 获奖肖像 | 用户提供的诺贝尔奖官方公布图（`assets/nobel2026_official_illustration.webp`），插画：Niklas Elmehed © Nobel Prize Outreach。片中署名 |
| 德拉吉「不惜一切代价」（2012 年 7 月 26 日）；OMT 计划至今从未启用 | [Wikipedia: Outright Monetary Transactions](https://en.wikipedia.org/wiki/Outright_Monetary_Transactions)、[Bloomberg 2012-07-26](https://www.bloomberg.com/news/articles/2012-07-26/spanish-italian-bonds-climb-as-draghi-pledges-to-preserve-euro) |

**中国经济数据**

| 指标 | 数值 | 出处 |
|---|---|---|
| 居民新增贷款（万亿元） | 2020：7.87；2021：7.92；2022：3.83；2023：4.33；2024：2.72；2025：0.44（2006 年以来最低）；2026 上半年：−0.37 | 中国人民银行《金融统计数据报告》，经[凤凰网](https://finance.ifeng.com/c/82ybrXLN01e)、[人民日报](https://paper.people.com.cn/rmrb/html/2023-01/11/nw.D110000renmrb_20230111_2-10.htm)、[中国日报](https://cn.chinadaily.com.cn/a/202401/13/WS65a1dab9a310af3247ffbcf6.html)、[第一财经](https://www.yicai.com/news/102440523.html)、[新浪财经](https://finance.sina.com.cn/roll/2026-01-15/doc-inhhkmpr7633181.shtml)、[新浪历年数据](https://finance.sina.com.cn/roll/2026-01-19/doc-inhhuvac8126827.shtml)、[《财经》](https://www.mycaijing.com/article/detail/573937)转载核对 |
| 居民新增存款（万亿元） | 2020：11.3；2021：9.9；2022：17.84（历史最高）；2023：16.67；2024：14.26；2025：14.64 | 同上，及[第一财经](https://m.yicai.com/news/101650109.html) |
| 城镇储户「倾向更多储蓄」占比 | 2019Q4：45.7% → 2022Q4：61.8% | 中国人民银行城镇储户问卷调查，经[中证网](https://cs.com.cn/yh/04/201912/t20191223_6011108.html)、[人民网](http://finance.people.com.cn/n1/2022/1228/c1004-32595390.html)转载核对 |
| 5 年期以上 LPR | 4.85%（2019.8）→ 3.50%（2025.5 起，至 2026 年 9 月连续 16 个月不变），钩子画面依次显示其中 8 个历史档位 | 全国银行间同业拆借中心公告，经[新浪财经 2026-09-20](https://finance.sina.com.cn/jryx/bank/2026-09-20/doc-inismrff2613099.shtml)、[新浪财经 2025-05-20](https://finance.sina.cn/2025-05-20/detail-inexeiie6972084.d.html)核对 |
| 新建商品房销售额 | 2025 年 8.39 万亿元，同比 −12.6%，不到 2021 年高点的一半 | [国家统计局](https://www.stats.gov.cn/sj/zxfb/202601/t20260119_1962324.html)、[财新](https://m.caixin.com/m/2026-01-20/102406026.html) |
| 家电零售额（限额以上） | 2025 年 +11% | [新华网](https://www.news.cn/tech/20260121/721161efec11467e892403e72e9d0e0d/c.html)（商务部数据） |
| 服务零售额 / 商品零售额 | 2025 年 +5.5% / +3.8% | [国家统计局](https://www.stats.gov.cn/sj/zxfb/202601/t20260119_1962323.html)、[人民论坛](https://www.rmlt.com.cn/2026/0125/746073.shtml) |
| 人均消费支出实际增速 | 2025 年 农村 +5.3%、城镇 +3.7% | [国家统计局](https://www.stats.gov.cn/sj/zxfb/202601/t20260119_1962321.html) |
| 民间固定资产投资 | 2026 年 1—8 月 −10.1% | [国家统计局](https://www.stats.gov.cn/xxgk/sjfb/zxfb2020/202609/t20260915_1965309.html) |
| 消费品以旧换新 | 2026 年安排超长期特别国债 2500 亿元 | 2026 年政府工作报告，经[光明网](https://m.gmw.cn/2026-09/30/content_1304570184.htm)、[同花顺](https://news.10jqka.com.cn/20260626/c677741567.shtml)核对 |
| 育儿补贴 | 每孩每年 3600 元，发放至满 3 周岁 | 《育儿补贴制度实施方案》（2025 年 7 月），经[中国日报](https://cn.chinadaily.com.cn/a/202507/30/WS6889e361a310a07bb590b11a.html)核对 |

> 制作环境的网络策略屏蔽了 nobelprize.org、stats.gov.cn、pbc.gov.cn 等站点，无法直接打开原文页面。上面的数字都通过检索引擎抓到的官方页面摘要核对，并至少用一家主流媒体的转载交叉验证。

## 目录

```
诺贝尔经济学奖2026/
├── build.sh                     一键重建（字体 → 配乐 → 渲染 → 成片 + 预览版）
├── src/
│   ├── timeline.py              节拍网格、段落、重拍、全部字幕（含阅读速度校验）
│   ├── music.py / synth.py      原创配乐与音效（numpy 合成、numba 时变滤波、卷积混响、-14 LUFS 母带）
│   ├── engine.py                竖屏加色光引擎：多级辉光、3D 相机、文字排版、磨砂玻璃卡片
│   ├── common.py                背景星云、景深尘埃、千万家庭光点平面、章节标签、图标
│   ├── scenes_a.py              钩子 → 标题 → 01 反常
│   ├── scenes_b.py              02 地基 → 03 霍尔 → 04 伍德福德
│   ├── scenes_c.py              05 传导 → 06 真相 → 获奖者 → 品牌片尾
│   ├── portraits.py             官方肖像 → 肖像卡 / 发光线稿
│   ├── video.py                 渲染入口（单帧、联系表、分段、并行整片）
│   └── peek.py                  多帧联系表预览
└── assets/nobel2026_official_illustration.webp
```

## 重新生成

```bash
./build.sh    # 需要 ffmpeg、python3：numpy scipy numba opencv-python-headless pillow soundfile pyloudnorm
```

调试单帧：`cd src && python3 video.py still 12.5 61 117`（输出到 `build/stills/`），或 `python3 peek.py ../build/peek/x.png 30 60 90`。
