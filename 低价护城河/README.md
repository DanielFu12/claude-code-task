# 低价格，不是护城河 · 竖屏短视频

- 成片：`低价格不是护城河.mp4`（1080×1920 · 30fps · 约 3:02 · H.264 + AAC 256k · 响度 −14 LUFS）
- 右上角全程挂「巴芒价值」品牌角标（`../brand/`，带流光）；片尾是大号 logo + 金色「巴芒价值」+「BUFFETT · MUNGER」。
- 旁白：豆包 Seed-TTS 3.0，音色 `multi_male_liufei2_v3_uranus_bigtts`，**整篇一次合成**（没有段落接缝），按接口返回的逐字时间戳切句、对字幕、卡画面。
- 配乐：原创程序作曲（MIDI → FluidSynth + FluidR3 GM），80 BPM，D 小调 → D 大调；每个重拍都取自旁白里某个字的发声时刻。没有镲片和高频扫频，转场只用低频轰鸣、弦乐渐强和低通气声。
- 事实核查与来源：`docs/核实笔记.md`；发布标题与正文：`发布文案.md`。

## 一句话主线

**低价格只是策略，低成本才是护城河的地基。** 让出去的钱只可能来自三处：补贴、转移、效率——只有效率撑得起护城河；质量是底线，上下游能不能活下去是检验。

## 结构

| 时间 | 章节 | 叙事 | 画面 |
|---|---|---|---|
| 0:00–0:17 | 冷开场 | 1.5 美元的热狗卖了 40 年 vs 一千多万人排队退押金：同样是便宜，一个成了护城河，一个成了坟墓。差别在哪？ | 热狗实拍暖调推近 + $1.50 与年份滚动；ofo 实拍冷调 + 排队人数计数与点阵；上下分屏「护城河 / 坟墓」 |
| 0:17 | 片名 | **低价格 · 不是护城河** | 冲击波 + 金色护城河光环碎裂，第一个重拍 |
| 0:20 | 01 直觉 | 价格谁都能降，挡不住任何人 | 多条价格线竞相下探，穿过「低价」这堵墙 |
| 0:30 | 02 试金石 | 当对手也降到同一个价格，谁还活着？A 成本 75 赚 15，B 成本 95 亏 5 | 两家店价格牌降到 ¥90 → 柱图 +15 / −5，B 柱滴血；「武器 / 失血」重拍 |
| 0:48 | 03 用词 | 巴菲特 2007 年信：不是价格最低，而是**成本最低的生产者** | 巴菲特照片 + 信纸打字机原文，高亮 low-cost producer |
| 0:58 | 04 来源 | 让出去的钱来自补贴 / 转移 / 效率 | 价格柱被切下一块 → 三块来源卡片依次点亮：烧钱火星、供应商被挤压、齿轮 + 护城河光环 |
| 1:17 | 05 飞轮 | Costco：加价 ≤14%（据报道）→ 低价 → 会员 → 采购量 → 成本 的飞轮；会员费≈一半经营利润、续费率 89.8%；规模经济分享；先拥有它的规模 | ABC 2005 年档案画面 + 飞轮动画 + 两个环形数据卡 + 大字标题卡 |
| 1:44 | 06 中国考题 | 比亚迪：垂直整合、2025 年约 460 万辆；10% 年降目标、账期、60 天付款承诺。拼多多：低价心智 + 商家竞争，收入来自商家；商家还赚得到钱吗；千亿扶持。低价里多少是效率、多少是让利——护城河在加宽还是透支 | 海豹棚拍 / 海鸥实拍 + 供应链与账期时钟；拼多多自提柜门店实拍 → 双边平台粒子图；天平 + 城堡护城河加宽 / 干涸 |
| 2:27 | 07 底线 | 偷工减料让飞轮倒转：质量下滑 → 信任流失 → 复购减少 → 再降价；消费者买的不是便宜，是值不值 | 金色飞轮反转变红；「值 = 效用 − 价格 − 麻烦」 |
| 2:40 | 08 答案 | 低价吸引、质量留住、效率支撑、规模强化；真正的护城河是“在这里，我总能用更少的钱，买到靠得住的东西”；哪家公司的低价才是真护城河？ | 四句排印逐句点亮；金句大字；评论区提问 |
| 2:57 | 片尾 | 品牌 | 大号 logo + 巴芒价值 + BUFFETT · MUNGER |

## 重新生成

```bash
./build.sh
```

依赖：ffmpeg、fluidsynth（FluidR3_GM 音色库）、python3（numpy、opencv-python-headless、pillow、soundfile、scipy、pretty_midi、pyloudnorm、fonttools）。旁白请求 `voice.cn-beijing.volces.com`，API Key 由环境的网络代理注入；合成结果按文本哈希缓存在 `work/vo/`。

| 文件 | 作用 |
|---|---|
| `src/script.py` | 旁白脚本：配音文本（数字口语化）、字幕文本、句前留白、语速 |
| `src/tts.py` / `src/tts_take.py` | Seed-TTS 3.0 调用；整篇一次合成，按逐字时间戳在停顿能量最低点切句 |
| `src/timeline.py` | 句子排布，章节句首对齐 80 BPM 节拍网格；提供 `WT(句, '词')` 取某个词的发声时刻 |
| `src/music.py` | 程序作曲 + 低频冲击 + 卷积混响 + 电平均衡；输出重拍时刻 `hits.json` 给画面 |
| `src/mix.py` | 旁白处理、配乐闪避（−11 dB）、−14 LUFS、真峰 −1.2 dBTP |
| `src/engine.py` / `src/video.py` | 竖屏动态图形引擎与全部分镜 |
| `src/commons_search.py` / `src/fetch_media.py` | Wikimedia Commons 检索与下载（记录作者、许可） |

## 素材与授权

| 素材 | 作者 | 许可 |
|---|---|---|
| [Costco 热狗（浜松）](https://commons.wikimedia.org/wiki/File:20251023_171645_Hamamatsu_Costco_Hot_Dog_and_drink.jpg) | Saimmx | CC0 |
| [ofo 单车（江宁路站）](https://commons.wikimedia.org/wiki/File:201703_ofo_bicycles_near_the_exit_1_of_Jiangning_Road_Station.jpg) | MNXANL | CC BY-SA 4.0 |
| [ofo 北京总部](https://commons.wikimedia.org/wiki/File:Beijing_Zhongguancun_ofo_HQ_June-2017.jpg) | Stomatapoll | CC BY-SA 4.0 |
| [巴菲特（2015 SelectUSA）](https://commons.wikimedia.org/wiki/File:Warren_Buffett_at_the_2015_SelectUSA_Investment_Summit.jpg) | USA International Trade Administration | Public domain |
| [比亚迪海豹](https://commons.wikimedia.org/wiki/File:BYD_Seal_IAA_2023_1X7A0026.jpg) | Alexander-93 | CC BY-SA 4.0 |
| [比亚迪海鸥](https://commons.wikimedia.org/wiki/File:BYD_Seagull_009.jpg) | Quzhouliulian | CC0 |
| 拼多多自提柜门店（香港将军澳，2026-03） | Wikimedia Commons | CC0 |
| [Costco 内湖店](https://commons.wikimedia.org/wiki/File:Costco_Neihu_Warehouse_1st_Floor_Food_Area_20160320b.jpg) | 玄史生 | CC0 |
| [ABC News《20/20》Costco 报道（2005）](https://archive.org/details/youtube-f9Iv_vdO7sw) | ABC News | 档案片段，评论性引用，每段不超过 6 秒 |

字体：Noto Serif SC / Noto Sans SC / Cormorant Garamond / Oswald / Playfair Display / Special Elite（均为 OFL / Apache）。
