# 巴菲特与芒格股东大会精华数据库

从 1994–2024 年伯克希尔·哈撒韦股东大会的问答中，挑出 626 条有深度的观点。每条都包含英文原话、中文翻译、投资启示、评分、CNBC 章节和视频估算时间点。

在线浏览（带筛选、Top 100、思想演变、视频目录）：https://claude.ai/artifact/8akCXquPMmj4H99iyrS12c

## 交付物（`output/`）

| 文件 | 内容 |
|---|---|
| `巴芒股东大会精华数据库.xlsx` | 6 个工作表：说明、视频目录、精华数据库（626 行，表头可筛选）、Top100、主题索引、思想演变 |
| `视频目录.md` | 1994–2026 年每届会议的 CNBC 会议页、上午场/下午场（或 Part 1/2）、精华剪辑、单段视频、逐字稿覆盖与缺口 |
| `知识库_按主题.md` | 按 14 个主题归类的全部条目，以及 35 个概念簇的思想演变时间线和综述 |
| `Top100.md` | Top 100 精华片段，含原话、翻译、启示、估算时间与跳转链接 |
| `entries.json` | 机器可读的全部数据 |
| `site/index.html` | 单文件网页版（右上角带「巴芒价值」品牌角标） |

每条精华的字段：标题、发言人、主题、概念簇、核心观点、原话（英文）、中文翻译、投资启示、评分（思想深度/投资实用性/启发性，各 1–5）、视频链接、估算起止时间、跳转链接、CNBC 章节编号与标题、相关条目、Top 100 名次。

## 数据来源与方法

- **视频**：CNBC Warren Buffett Archive（buffett.cnbc.com）。URL 记录在 `data/cnbc_urls.tsv`（经网页检索核实），少量带时间参数的深链样例在 `data/cnbc_anchors.tsv`。
- **逐字稿**：CNBC 档案的章节式逐字稿，取自 GitHub 镜像 `pzponge/Yestoday`；`tools/parse_transcripts.py` 把它切成 2140 个章节，章节编号与 CNBC 页面一致（如 `2013-A03` 表示 2013 年下午场第 3 章）。
- **原话核对**：`entries/YYYY.txt` 里每条原话只写“起始短语 ||| 结束短语”。`tools/entries.py` 在对应章节逐字稿中原样截取，只删去“(Laughter)”等现场标注；对不上原文的锚点在构建时直接报错。目前 626 条全部通过。
- **人工编写**：中文翻译、核心观点、投资启示、评分、概念簇归并和思想演变综述（`data/cluster_notes.tsv`）由本库编写，不是官方内容。
- **去重与演变**：同一思想归入同一概念簇（如“市场先生与波动”“回购、分红与留存收益”），按年份排开，并附人工撰写的演变综述。
- **Top 100**：按总分排序，同分时启发性、深度优先；为保证覆盖面，每年最多 4 条、每个概念簇最多 5 条。

## 时间戳的局限

逐字稿没有时间码，所以**所有秒数都是估算值**：按“该句在本场逐字稿中的累计词数 ÷ 语速”计算。默认语速 2.1 词/秒，由 2020、2024 年已知时长的场次反推；已知时长的场次按实际时长折算。误差通常在几分钟以内，越靠场次后段越大。跳转链接在估算区间前后各多留 60 秒。

要得到精确到秒的时间，需要：在环境网络设置中放行 `buffett.cnbc.com`（以及 YouTube 等视频站），获取视频字幕或音频，再与逐字稿做强制对齐，用对齐结果替换 `tools/build.py` 中的估算。本次运行时这些站点被网络策略屏蔽。

## 覆盖缺口

- 2019 年只有上午场逐字稿；2020 年只有 Part 1（演讲与正式会议），缺 Part 2 问答。
- 2025、2026 年没有逐字稿，只在视频目录中列出链接；2025 年下午场和 2026 年场次视频的链接未核实。
- 1994 年下午场在 CNBC 档案中只有音频。

## 重新构建

```bash
# 1. 取逐字稿并切章节（只需一次）
git clone --depth 1 --filter=blob:none --sparse https://github.com/pzponge/Yestoday SRC
(cd SRC && git sparse-checkout set Warren_Buffett/Berkshire_Hathaway_Annual_Meeting)
python3 tools/parse_transcripts.py SRC/Warren_Buffett/Berkshire_Hathaway_Annual_Meeting chapters.jsonl

# 2. 校验条目（应输出 “626 entries, 0 problems”）
python3 tools/entries.py chapters.jsonl entries

# 3. 生成 Excel / Markdown / JSON，再打包网页
python3 tools/build.py chapters.jsonl output
python3 tools/make_site.py output
```

辅助工具：`tools/show.py chapters.jsonl 2013-A03 ...` 按章节打印逐字稿，供阅读和挑选。
