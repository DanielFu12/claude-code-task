# 资料来源、原始影像与授权说明

《AI 越快，越要慢：李录、巴菲特、芒格谈复利》（第二版，原始影像版）。
片中李录、巴菲特、芒格的每一句话都是**原始影像里的原声**，英文字幕是原话转写，中文字幕是本片翻译。
片中**没有任何 AI 配音，也没有 AI 合成或模仿大师的声音**。文字卡（白色宋体）是本片的串联说明，不是任何人的原话。

---

## 一、片中使用的原始影像（共 8 段，约 2 分 04 秒）

| # | 成片时间 | 人物 · 场合 | 原始录像中的位置 | 时长 | 原话（转写） |
|---|---|---|---|---|---|
| LA | 0:01.2–0:08.9 | 李录 · 哥伦比亚商学院第 36 届格雷厄姆与多德年度活动（2026.10） | YouTube 原片 ≈ 0:18:05–0:18:13 | 7.8 s | "Of course, every wave is different, but this wave is unusually different than anything we have experienced so far." |
| LB | 0:09.9–0:25.6 | 同上 | ≈ 1:24:25–1:24:40 | 15.8 s | "Whatever you learn today is useless tomorrow. You don't accumulate. And so you rely more and more into impersonal. You get a bigger computer, now you use AI, and of course, you'll be replaced at some point." |
| LC | 0:43.3–0:52.6 | 同上 | ≈ 1:23:03–1:23:13 | 9.3 s | "And I always say, look, if you can compound your knowledge in a sustainable fashion, eventually you can compound your capital as well." |
| LD | 0:53.9–1:14.6 | 同上 | ≈ 1:26:49–1:27:10 | 20.7 s | "And the basic idea of compounding is you don't lose what you already have. And that's a profound idea. You don't lose what you already have. That's including your knowledge, that's including your trusting relationship, that's including your wisdom and even your health." |
| BA | 1:18.6–1:36.3 | 巴菲特 · 伯克希尔·哈撒韦 1999 年股东大会（奥马哈） | 整场录像 0:24:00–0:24:18 | 17.7 s | "You only have to get rich once. And why do people, very bright people, risk losing something that's very important to them to gain something that's totally unimportant? The added money has no utility whatsoever. And the money that was lost had enormous utility." |
| MB | 1:38.5–1:56.0 | 芒格 · BBC 专访（2009.10） | 访谈约 0:39 起 | 17.6 s | "In fact, you can argue that if you're not willing to react with equanimity to a market price decline of 50% two or three times a century, you're not fit to be a common shareholder, and you deserve the mediocre result you're going to get" |
| BB | 1:58.2–2:09.4 | 巴菲特 · 伯克希尔·哈撒韦 1999 年股东大会 | 整场录像 3:47:20–3:47:31 | 11.1 s | "The nature of compound interest is it behaves like a snowball of sticky snow. The trick is to have a very long hill, which means either starting very young or living to be very old." |
| MU | 2:11.4–2:35.9 | 芒格 · 南加州大学古尔德法学院毕业典礼演讲（2007.05.13） | 演讲录像 6:31–6:55 | 24.5 s | "I constantly see people rise in life who were not the smartest, sometimes not even the most diligent, but they are learning machines. They go to bed every night a little wiser than they were when they got up. And boy, does that habit help, particularly when you have a long run ahead of you." |

**李录片段合计 53.5 秒**，控制在要求的 1 分钟以内。

**出入点与字幕时间**全部来自本地 Whisper（faster-whisper small.en）对原声做的词级时间戳（`src/clips.py` 中的 `cues`），不是估计值。
关键句另用 Gemini 对同一段音频独立转写交叉核对，措辞一致。

### 语境说明（防止断章取义）

- **LB**「今天学到的，明天就没用了」：李录说的是**零和、短期化的人性倾向**会导致什么（前一句是 "The zero-sum game, the trouble is there's a lot of human nature goes to zero-sum, to the short term"），不是说"学习没用"。画面上方标注了「语境：李录在谈『零和、短期』的人性倾向」。
- **BA**：巴菲特在 1999 年股东大会上谈长期资本管理公司（LTCM）1998 年的崩溃——一群极聪明、已经很富有的人，用高杠杆去冒险。
- **MB**：芒格在同一段访谈里先说 "This is the third time that Warren and I have seen our holdings in Berkshire go down top tick to bottom tick by 50%"，片中截取的是紧随其后的结论。
- **BB**：股东提问"如果你今天三十出头重新开始，会怎么做"，巴菲特先答 "Start young"，片中截取的是他对复利的解释。
- **李录 → 芒格**：文字卡「李录的导师芒格」依据李录本人在同场活动中的原话 "my mentor, partner, teacher, Charlie Munger"（录像 ≈ 1:25:00）。

### 李录活动信息

| 项目 | 内容 |
|---|---|
| 活动 | 36th Annual Graham & Dodd Event，哥伦比亚商学院海尔布伦格雷厄姆与多德投资中心主办 |
| 日期 | 2026 年 10 月 5 日（录像片头标题页） |
| 对谈 | 李录（Li Lu '96，喜马拉雅资本创始人、董事长）× Tano Santos 教授 |
| 原始录像 | Columbia Business School 官方 YouTube：https://www.youtube.com/watch?v=YRhnX_JAbC8 |
| 交叉印证 | 虎嗅（2026-10-16）https://www.huxiu.com/article/4898037.html ；ChainCatcher（2026-10-13）https://www.chaincatcher.com/en/article/2295789 ；Seth Pua（2026-10-16）https://sethpua.substack.com/p/before-you-buy-the-future-listen |

---

## 二、影像是从哪里取得的

本环境访问 YouTube 被机器人验证拦截（`Sign in to confirm you're not a bot`，多种客户端均失败），所以改从 B 站的转载版本截取。
下载命令全部写在 `tools/fetch_footage.sh` 里，可以复现。

| 片段 | 实际下载来源 | 原始版权方 | 处理 |
|---|---|---|---|
| 李录 LA–LD | B 站 BV1t6HS6yEbd（P1，720p，转载者「复利的奇迹价值投资」，带中英硬字幕和水印） | Columbia Business School | 按人物位置逐帧追踪裁切（Gemini 标注头部位置，`assets/track/*.json`），用 `src/desub.py` 去除转载者的硬字幕，裁掉水印 |
| 芒格 MB | B 站 BV1bSTg6NEoc（转载者剪辑的竖版短片，内含 BBC 原画面） | BBC | 只截取内嵌的 BBC 画面区域，转载者添加的标题、贴纸、字幕全部裁掉 |
| 芒格 MU | B 站 BV1Mx411h7cg（无字幕版本） | USC Gould School of Law | 裁切 |
| 巴菲特 BA、BB | B 站 BV1M319ByEQF（「DumbMoneyNote」上传的 1999 年股东大会完整录像，带水印和硬字幕） | Berkshire Hathaway | 只截取讲台区域，水印和底部字幕均在裁切范围外 |

片中出现的**所有字幕、人名条、标题都是本片重新制作的**，没有沿用转载者的字幕。

---

## 三、授权与使用依据（请发布前确认）

**这些影像都没有取得版权方的书面授权。** 本片使用它们的依据是评论、介绍性质的合理使用/适当引用：每段都很短（最长 24.5 秒，李录合计 53.5 秒）、标注了人物、场合、日期和出处、配有本片自己的翻译和串联评述，不替代原片。
但合理使用的认定因平台和地区而异，**在公开发布、尤其是商业化之前，建议：**

1. 李录片段：联系哥伦比亚商学院海尔布伦中心（Heilbrunn Center for Graham & Dodd Investing）确认是否允许引用；
2. 伯克希尔股东大会录像：版权属于伯克希尔·哈撒韦（CNBC 是授权播出方）；
3. BBC 访谈、USC 演讲：分别属于 BBC 与南加州大学。

如果任何一方不同意使用，可以把对应片段换成「原话文字卡 + 出处」（第一版就是这样做的），时间轴不需要改动：在 `src/part1.py` 的 `CHAIN` 中去掉该片段即可。

| 其他素材 | 来源 | 授权 |
|---|---|---|
| 背景音乐 | Google Lyria 3 Pro（`lyria-3-pro-preview`）按本片分镜生成的原创配乐，提示词见 `assets/music/prompt_*.txt` | 按 Gemini API 服务条款使用；没有使用仓库根目录参考视频里的音乐 |
| 低频音效 | `src/audio.py` 本地合成 | 原创，全部经 200Hz 低通 |
| 动画（复利的第一性原理、人生的复利、片尾） | `src/scenes.py` 程序生成 | 原创 |
| 字体 | Noto Serif SC、Noto Sans SC、Cormorant Garamond、JetBrains Mono | SIL Open Font License |
| 品牌 | 仓库 `brand/`（logo_baman.png、brand.py） | 自有品牌资产；右上角角标全程使用 `brand.Hud`，片尾使用原始 logo |
| 配音 | **无**。用户要求先不使用 TTS；本版没有任何 AI 配音 | — |

---

## 四、数学计算依据（动画段，约 1 分钟）

全部数字都在 `src/script.py` 的 `MATH` 里统一计算，画面直接引用这些值：

| 画面 | 计算 | 结果 |
|---|---|---|
| 每年 +10%，30 年 | 1.1³⁰ | **17.449** 倍 |
| 每年 −10%，30 年 | 0.9³⁰ | **0.0424** 倍（"只剩 4%"） |
| 两者差距 | (1.1/0.9)³⁰ | **411.6**（"相差约 412 倍"） |
| −50% 后回到原点 | 0.5 × (1+x) = 1 → x = +100% | 需要 **+100%** |
| 按每年 +10% 恢复要多久 | ln 2 / ln 1.1 | **7.27 年** |
| 永久性 −50% 对终值的影响 | 终值 = 本金 × Π(1+rᵢ)；多乘一个 0.5，不论在哪一年，终值都 ×0.5 | 8.72 倍；恢复 7.27 年后，没有中断的路径已是 **34.9** 倍 |

**假设与边界（画面上也有标注）：**
- 这是数学示意：假设固定年化收益率，不计税费、通胀，不代表任何资产的预期收益。
- **暂时回撤 ≠ 永久损失。** 企业价值还在、投资者没有被迫卖出时，价格下跌可以等回来（芒格 MB 片段说的正是这一点）；永久损失是企业价值真的受损，或因杠杆被迫低价卖出（巴菲特 BA 片段谈的 LTCM）。
- 知识、信任、技能、健康部分是类比，不是等式。

---

## 五、核对后没有使用的内容

- "The first rule of compounding is to never interrupt it unnecessarily"：常被说成是芒格的话，没有找到一手出处，未使用。
- 巴菲特 1998 年佛罗里达大学演讲（"You only have to get rich once" 的另一个版本）：已下载，但 B 站各转载版本的硬字幕压在画面中部，且股东大会版本更符合要求，最终改用 1999 年股东大会。
- 芒格 USC 演讲中 "The highest form that civilization can reach is a seamless web of deserved trust."（演讲录像 35:49–35:56）已处理为片段 MT，因时长限制本版未放入，可替换 MU。
