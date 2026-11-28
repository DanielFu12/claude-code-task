# 便宜≠护城河：低成本成为护城河的三个条件 · 竖屏短视频（v3）

> 护城河系列 · 第 02 期。系列规划见 `../经验沉淀/护城河系列规划.md`；第 01 期为《社会地位象征型护城河》（`../地位护城河视频/`）。

- 成片：`便宜不等于护城河.mp4`（1080×1920 · 30fps · 5:58 · H.264 两遍编码 + AAC · 响度 −14 LUFS · 小于 95MB）
- 预览版：`便宜不等于护城河_预览版.mp4`（CRF 27，方便手机转发）
- 右上角全程挂「巴芒价值」角标（`../brand/`，带流光）；片尾品牌动画（约 11 秒）：结尾金句的字形化作约 3200 颗金色粒子，旋转汇聚成官方 logo → logo 清晰落定（淡蓝柔光 + 光环）→ 金色「巴芒价值」随音乐重拍落下并扫过流光，「BUFFETT · MUNGER」紧随 → 细金线向两侧展开，引出「关注「巴芒价值」，传承大师智慧，领悟投资真谛」→ 整体淡出。片中没有评论区互动。
- 旁白：豆包 Seed-TTS 3.0，音色 `multi_male_liufei2_v3_uranus_bigtts`，1896 字**整篇一次合成**；三种基频估计取一致值、PSOLA 拉平长录音的音高漂移（`src/detrend.py`）；按逐字时间戳切句、对字幕、卡画面。
- 配乐：原创程序作曲（MIDI → FluidSynth + FluidR3 GM），80 BPM；23 个重拍全部取自旁白里某个字的发声时刻。无镲片、无高频扫频。
- 事实核查：`docs/核实笔记.md`；发布文案：`发布文案.md`。
- 仓库 LFS 额度已满，本目录用 `.gitattributes` 把 mp4 按普通文件入库（单文件 < 100MB）。

## 标题为什么这样定

**便宜 ≠ 护城河**——“低价格”永远只是一个决定，谁都能做，所以它本身从来不是护城河；
**低成本成为护城河的三个条件**——真正可能成立的是“低成本”，但它要同时满足三个条件。
标题本身就是全片的第一性原理结论：区分“价格（决定）”和“成本（结构）”，再给出成立条件。

## 一句话主线

利润 = 价格 − 成本。价格是决定，成本是结构；内卷是大家一起降价，成本却拉不开差距。
巴菲特说低成本生产者是屏障，段永平说没见过成本优势能成护城河——两人并不矛盾：
**低成本要成为护城河，必须对手买不到（结构性）、差距越拉越大（可持续）、还能换来定价权（可转化）。**
低价是一种选择，低成本是一种能力，把能力变成定价权，才是护城河。

## 结构

| 时间 | 章节 | 叙事 | 画面 |
|---|---|---|---|
| 0:00 | 引子 · 内卷 | 价签一刀刀划掉 → 2024 光伏组件跌到成本线附近、协会提醒低于成本投标涉嫌违法 → 汽车价格战、外卖 0 元购 → 越卖越亏 → 2024.07 政治局会议“防止内卷式恶性竞争”、2025.07 价格法首次修订 → **价格战打到最后，谁建起了护城河？** | 价签动画；NASA 卫星图“光伏长城”+ 价格曲线与成本线；价格战卡片；价格/利润双线；两份红头文件 |
| 0:35 | 反差 | Costco 热狗 1.5 美元卖了 40 年 vs ofo 一千多万人排队退押金：一个成了护城河，一个成了坟墓 | 热狗实拍 + $1.50 与年份滚动；ofo 总部冷调 + 排队计数点阵；上下分屏 |
| 0:53 | 片名 | **便宜 ≠ 护城河｜低成本成为护城河的三个条件** | 冲击波 + 金色护城河光环碎裂 |
| 0:56 | 01 第一性原理 | 利润 = 价格 − 成本；价格是决定，成本是结构；内卷 = 大家一起降价、成本拉不开差距，利润被挤到零；巴菲特 1985 年纺织厂复盘（单独合理、合起来抵消）；芒格：更好的机器把省下的钱送给了买家；你能买到的效率对手也能买到；检验：对手降到同价你还赚钱吗（A/B 两家店） | 公式逐项点亮、价格滑杆瞬间拨动 vs 成本积木逐块搭建；五家公司价格一起下压；1912 年 Fall River 织布车间（Lewis Hine）+ 1985 年信原文打字机；金币从织机流向买家；A/B 柱图 |
| 2:02 | 02 两位大师 | 巴菲特 2007：低成本生产者是屏障 vs 段永平 2010：没见过成本优势成护城河、性价比是低价的借口 → 线索：GEICO、Costco 靠的是商业模式；护城河 ≈ 定价权 → 并不矛盾 → 三个条件 | 左右对峙面板 + 两张引语卡（对撞处震屏重拍）；“商业模式”“护城河≈定价权”大字；和解双卡 |
| 2:52 | 03 三个条件 | ① 结构性：新织布机谁都能买所以不算；GEICO 直销，靠代理人的对手先得拆掉销售体系；规模/流程/资源/网络密度 ② 可持续：Costco 飞轮；巴菲特“油门踩到底”，一停下优势就成行业标配 ③ 可转化：会员锁定/品牌心智/网络效应 → 定价权；低成本是燃料不是城墙。证据：热狗 40 年不涨、加价 ≤14%（据报道），2024.09 会员费 60→65 美元，续费率仍近九成、会员费约占经营利润一半——商品坚持薄利、会员费却能涨价，巴菲特的低成本与段永平的定价权在此会合 | 每个条件一张大标题卡；直销 vs 代理人链路；成本曲线差距拉大；燃料火星托起四块城砖；Costco 双车道图（热狗平线、会员费台阶）；两个环形数据；双圆会合成“护城河” |
| 4:15 | 04 中国考题 | 比亚迪：结构性 ✓，可持续/可转化待验证（10% 年降目标、账期、60 天付款承诺）；拼多多：网络效应 ✓，最难的题是商家能否赚钱、千亿扶持；只会降价的行业三个条件全 ✗ → 这就是内卷 | 海豹棚拍 / 海鸥实拍 + 三条件体检表；拼多多自提柜门店实拍 → 双边平台粒子图；全 × 体检表 |
| 5:09 | 05 底线 | 偷工减料让飞轮倒转；消费者买的不是便宜，是值不值 | 金色飞轮反转变红；值 = 效用 − 价格 − 麻烦 |
| 5:24 | 06 答案 | 便宜 ≠ 护城河；三个条件同时满足；低价是选择、低成本是能力、把能力变成定价权才是护城河；真正的护城河是：哪天它涨价了，你还是愿意留下 | 三条 ✓ 卡片；三级台阶；Costco 卖场金句 |
| 5:46 | 片尾 | 品牌动画 | 金句字形化作粒子汇聚成 logo → 重拍落字 + 流光 → 金线引出关注语 → 淡出 |

## 重新生成

```bash
./build.sh
```

依赖：ffmpeg、fluidsynth（FluidR3_GM 音色库）、python3（numpy、opencv-python-headless、pillow、soundfile、scipy、pretty_midi、pyloudnorm、fonttools）。
旁白请求 `voice.cn-beijing.volces.com`，API Key 由环境网络代理注入；合成结果按文本哈希缓存在 `work/vo/`。

| 文件 | 作用 |
|---|---|
| `src/script.py` | 旁白脚本：配音文本（数字口语化）、字幕文本、句前留白、语速 |
| `src/tts.py` / `src/tts_take.py` / `src/detrend.py` | Seed-TTS 3.0 调用；整篇一次合成 → 拉平音高漂移 → 按逐字时间戳在停顿能量最低点切句 |
| `src/timeline.py` | 句子排布、章节句首对齐 80 BPM 节拍；`WT(句, '词')` 取某个词的发声时刻 |
| `src/music.py` | 程序作曲 + 低频冲击 + 卷积混响 + 电平均衡；输出重拍时刻 `hits.json` |
| `src/mix.py` | 旁白处理、配乐闪避（−11 dB）、−14 LUFS、真峰 −1.2 dBTP |
| `src/engine.py` / `src/video.py` | 竖屏动态图形引擎与全部分镜 |
| `src/commons_search.py` / `src/fetch_media.py` / `src/fetch_clips.sh` | 素材检索与下载（记录作者、许可） |

## 素材与授权

| 素材 | 作者 | 许可 |
|---|---|---|
| “光伏长城”卫星图（库布其沙漠） | NASA Earth Observatory | Public domain |
| Cornell Mill 织布车间（Fall River，1912） | Lewis Hine（美国国会图书馆） | Public domain |
| [Costco 热狗（浜松）](https://commons.wikimedia.org/wiki/File:20251023_171645_Hamamatsu_Costco_Hot_Dog_and_drink.jpg) | Saimmx | CC0 |
| [ofo 单车](https://commons.wikimedia.org/wiki/File:201703_ofo_bicycles_near_the_exit_1_of_Jiangning_Road_Station.jpg) / [ofo 北京总部](https://commons.wikimedia.org/wiki/File:Beijing_Zhongguancun_ofo_HQ_June-2017.jpg) | MNXANL / Stomatapoll | CC BY-SA 4.0 |
| [巴菲特（2015 SelectUSA）](https://commons.wikimedia.org/wiki/File:Warren_Buffett_at_the_2015_SelectUSA_Investment_Summit.jpg) | USA International Trade Administration | Public domain |
| [比亚迪海豹](https://commons.wikimedia.org/wiki/File:BYD_Seal_IAA_2023_1X7A0026.jpg) / [比亚迪海鸥](https://commons.wikimedia.org/wiki/File:BYD_Seagull_009.jpg) | Alexander-93 / Quzhouliulian | CC BY-SA 4.0 / CC0 |
| 拼多多自提柜门店（香港将军澳，2026-03） | Wikimedia Commons | CC0 |
| [Costco 内湖店](https://commons.wikimedia.org/wiki/File:Costco_Neihu_Warehouse_1st_Floor_Food_Area_20160320b.jpg) | 玄史生 | CC0 |
| [ABC News《20/20》Costco 报道（2005）](https://archive.org/details/youtube-f9Iv_vdO7sw) | ABC News | 档案片段，评论性引用，每段不超过 6 秒 |

段永平没有可用的开放授权照片，片中用排印面板呈现。字体：Noto Serif SC / Noto Sans SC / Cormorant Garamond / Oswald / Playfair Display / Special Elite（OFL / Apache）。
