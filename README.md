# 进化心理学：你大脑的“出厂设置”

一部约 12 分钟的中文科普视频，用通俗的语言介绍进化心理学。

**v2（当前版本）** 的视觉风格参考了 B 站视频《从现在看过去——AI 简史》：纯黑背景、几万颗香槟金粒子在问号、大脑、文字和图标之间连续变形，配合辉光、光束穿梭转场、发光节点网络、3D 透视网格、细体排版与 HUD 线框。

## 成片

| 文件 | 说明 |
| --- | --- |
| `output/进化心理学_你大脑的出厂设置.mp4` | v2 成片（1080p / 30fps，旁白 + 配乐 + 字幕） |
| `output/进化心理学_你大脑的出厂设置.srt` | 外挂字幕（上传视频平台时可用） |
| `output/文案.md` | 带时间码的完整旁白文案与参考资料 |
| `output/封面.png` | 视频封面 |
| `output/v1_旧版/` | 第一版（扁平图标风格），留作对比 |

## 内容结构

1. **开场钩子**：为什么你怕蛇、怕蜘蛛，却不怕汽车和插座？为什么忍不住奶茶炸鸡、爱听八卦、消息没人回就焦虑？
   答案：你的大脑是一台“石器时代出厂”的机器。
2. **什么是进化心理学**：达尔文的自然选择与他的预言；核心观点——大脑也是被自然选择塑造的器官。
3. **四把钥匙**：时间错配（30 万年压缩成一天）、烟雾报警器原理、近因与终极原因、“如果……那么……”的规则。
4. **生活里的进化痕迹**：儿童找蛇实验与猴子恐惧学习、沃森选择任务互动小测试与“骗子侦测器”、八卦与邓巴数、社交排斥与“心痛”、亲缘选择、互惠利他、择偶研究。
5. **三个误区**：自然主义谬误、基因决定论、“原来如此的故事”与可重复性争议。
6. **四个能用上的建议**，以及总结和参考资料。

## 如何重新生成

视频完全由代码生成。旁白用离线神经网络语音合成（sherpa-onnx + Kokoro 中文模型）。
v2 画面是一个 three.js 网页（`video2/`），由 headless Chromium 按时间逐帧渲染后用 ffmpeg 合成。

```bash
pip install sherpa-onnx soundfile numpy pillow cairosvg
bash src/fetch_assets.sh                 # 下载字体与语音模型到 assets/
(cd src && python3 build_audio.py)       # 合成旁白，生成时间轴 build/timeline.json 与字幕
(cd src && python3 build_audio_v2.py)    # v2 配乐与音效 → build/audio_v2.wav
cd video2 && npm install
node render.mjs --preview 12,60,300      # （可选）导出几帧预览到 build/v2prev/
node render.mjs --workers 4 --out ../build/v2_master.mp4   # 渲染整片
```

- 改旁白：编辑 `src/content.py`（每个场景的旁白），重新运行 `build_audio.py`。
- 改 v2 画面：编辑 `video2/scenes.js`（每个场景的粒子阵型、文字、HUD、镜头）。渲染引擎在 `video2/engine.js`。
- v1 画面的生成脚本仍在 `src/render.py`。

## 素材与许可

- 图标：[Twemoji](https://github.com/jdecked/twemoji)（CC-BY 4.0）、[Tabler Icons](https://tabler.io/icons)（MIT）
- 字体：思源黑体 / 思源宋体（SIL OFL）、Inter（SIL OFL）、JetBrains Mono（SIL OFL）
- 语音模型：Kokoro-82M v1.1-zh（Apache 2.0），经 sherpa-onnx 运行
- 3D 渲染：three.js（MIT）
