# 李录 · 哥大演讲精华（9:16 竖屏）

- **正式成片**：`李录哥大演讲精华_9x16.mp4`，1080×1920 · 30fps · H.264 + AAC 192k，时长 45:32。
- **预览版**：`李录哥大演讲精华_预览版.mp4`，720×1280，两遍编码，体积控制在 30MB 以内，可直接观看。
- **原始素材**：YouTube [36th Annual Graham & Dodd Event with Li Lu '96](https://www.youtube.com/watch?v=YRhnX_JAbC8)（Columbia Business School，2026-10-05，1:28:17）。云端剪辑环境的出口 IP 过不了 YouTube 视频服务器的校验，所以原片由用户本地下载后上传到本仓库 Release `source-YRhnX_JAbC8`。时长和逐帧时间码都与 YouTube 版一致。
- **中文字幕底本**：哥大商学院官方发布的中文实录（`36th Annual Graham & Dodd Luncheon Transcript 20261005 CBS Chinese.pdf`），按字幕节奏做了精简。

## 九个主题与剪辑来源

| 章 | 主题（中文） | 英文标题 | 成片起点 | 原片区间 |
|---|---|---|---|---|
| 01 | 价值投资的六大原则 | Six Timeless Principles of Value Investing | 0:06 | 0:06:03–0:11:11 |
| 02 | AI 的本质、边界与红线 | What AI Is, Where It Stops, and the Red Line | 5:18 | 0:22:53–0:26:10；0:26:22–0:29:55 |
| 03 | AI 狂热下的资本市场 | The Market in an AI Frenzy | 12:10 | 0:31:13–0:38:22 |
| 04 | 投资中国：看清目标与代价 | Investing in China: Objective or Cost | 19:22 | 0:42:10–0:52:05 |
| 05 | 全球共同市场里的投资机会 | Opportunity in One Global Common Market | 29:21 | 1:02:00–1:06:30 |
| 06 | 中国股市：是目标还是代价 | China's Stock Market: Objective or Cost | 33:53 | 1:09:06–1:10:16 |
| 07 | 一切聪明的投资都是价值投资 | All Intelligent Investing Is Value Investing | 35:06 | 1:13:13–1:14:37 |
| 08 | 业绩落后时，如何坚守价值投资 | When Value Investing Lags Behind | 36:33 | 1:16:24–1:18:36 |
| 09 | 下行保护与复利人生 | Downside Protection and a Compounding Life | 38:47 | 1:21:37–1:28:08 |

主题名在需求原稿的基础上做了统一，都改成「主题 + 观点」的短句。第 2 章原稿里有一段「这个话题可能扯得有点远／塔诺：继续说」的插话，已剪掉（0:26:10–0:26:22）。其余章节都是连续原声，没有在句中拼接。

## 成片结构

1. **片头导览（6 秒）**：标题「李录：价值投资、AI 与中国」+ 九章目录，配乐在第二个重拍处起标题。
2. **每章 3 秒章节卡**：画面是模糊暗化的本章首帧，上面叠大号章节号和金色章名。配乐重拍落在 0.24 秒，章名随拍出现；最后 0.5 秒画面变清晰，接入正片。
3. **正片版式**（自上而下）：
   - 右上角官方角标 `brand.Hud`，全程显示，带流光。左上角是系列标签。
   - **顶部分区导航**：九段进度条，当前章高亮，并实时显示本章进度。下方是 `CHAPTER 0x / 09`、金色中文章名和英文章名。
   - 原片画面：从 16:9 画面中裁出 1:1，放大到 1080×1080。裁切位置按人脸检测（OpenCV YuNet）在镜头内平滑跟随，有死区和限速，换镜头时直接切过去。
   - 说话人标签：每段开头和换人时显示 5 秒，分「李录 / 喜马拉雅资本创始人、董事长」和「塔诺 / 哥大商学院教授 · 主持人」两种。
   - 中英双语字幕：共 463 条。中文 50px，英文 29px。英文就是需求原稿里的文字稿；方括号里的编者补注没有说出口，英文字幕不显示，意思放进了中文。
4. **片尾品牌动画（11.5 秒）**：正片最后一帧的像素化作粒子，旋转汇聚成官方 logo 的形状 → 原始 `brand/logo_baman.png` 居中清晰浮现，带品牌淡蓝光晕 → 在音乐重拍处（片尾 4.6 秒），金色「巴芒价值」和与它等宽的「BUFFETT · MUNGER」出现，扫过一次流光 → 下方细金线展开，引出关注语「关注「巴芒价值」，传承大师智慧，领悟投资真谛」→ 整体淡出。右上角 `brand.Hud` 一直保留到最后的淡出。

## 品牌规范落实

- 角标：`from brand import Hud`，用 `Hud(frame_w=1080).draw(frame, t)` 逐帧合成。尺寸、位置（距右 52px、距上 30px）、光晕、阴影和流光节奏（约 7.5 秒一次、每次 1.4 秒）都沿用 `brand.py` 的默认值，没有改动。
- logo：只用 `brand/logo_baman.png`，经 `brand.load_logo` 加载，用预乘 alpha 缩放。粒子的目标点取自 logo 的透明通道，最终画面显示的是原始 logo。
- 金色：`brand.GOLD_STOPS` 竖向渐变用于章名和片尾主标题；`brand.SUB_GOLD` 用于小字和细线。
- 字体：品牌字体「Noto Serif SC Black」「Cormorant Garamond」经 `brand._font` 获取。字幕和正文用 Noto Sans SC / Noto Sans，由 `build.sh` 从 Google Fonts 下载。
- 片尾小字「BUFFETT · MUNGER」两端对齐到与主标题等宽，算法与 `brand.build` 相同。流光公式与 `Hud.rgb_at` 一致。
- 需求里提到可以参考的 `love_video/render.py` 不在仓库中，main 和本分支都没有。片尾按 `brand/BRAND.md` 和 `不开心视频/src/video.py` 中现有的片尾实现来做。

## 音频

- 原声按剪辑表拼接，片段边界加 12–30ms 淡入淡出，避免爆音。
- 配乐取自仓库根目录 `opus5.5涌现.mp4`（约 112 BPM）。用 librosa 检测出两个重拍：17.14s 和 93.65s，分别对齐到章节卡 0.24s、片尾 4.6s 和片头 0.35s。
- 最终混音用 `loudnorm` 归一化到 -16 LUFS，真峰值 -1.5 dBTP。

## 源文件

| 文件 | 作用 |
|---|---|
| `src/script_en.txt` | 九个主题的英文文字稿（需求原稿） |
| `src/cues.txt` | 双语字幕：英文与文字稿逐句对应，中文以哥大官方中文实录为底本 |
| `src/youtube_asr.en.json3` / `src/youtube_subs.en.json3` | YouTube 自动字幕（逐词时间码）和官方英文字幕 |
| `src/align.py` | 文字稿与原片逐词对齐，算出剪辑点（`SEG_FIX` 是人工校正项） |
| `src/build_cues.py` | 字幕条计时：按逐词时间码切分，并保证最短显示时长 |
| `src/edl.py` | 时间线：片头、章节卡、片段、片尾；章节标题 |
| `src/shots.py` | 镜头切换检测 + 人脸轨迹 |
| `src/audio.py` / `src/render_consts.py` | 音轨合成与节拍常量 |
| `src/render.py` | 逐帧渲染（版式、字幕、章节卡、片尾动画、品牌角标） |
| `build.sh` | 一键重建：`./build.sh <原片.mp4>` |

## 重新生成

```bash
./build.sh /path/to/YRhnX_JAbC8.mp4   # 需要 ffmpeg、python3：numpy opencv-python-headless pillow soundfile librosa
```

抽帧检查：`LILU_SRC=原片.mp4 python3 src/render.py stills out/ 120 736 2729`（参数是成片时间，单位秒）。
