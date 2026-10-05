# 出厂设置：你的大脑，比你想的更古老

一部 7 分钟的中文进化心理学科普短片。**v3（当前版本）** 不用旁白，由屏幕文字讲故事，配乐和画面完全卡点。

- **叙事主线**：开场先抛出几个日常的“不理性”（怕蛇不怕车、忍不住奶茶、已读不回就焦虑），然后逐个“解锁”大脑的 4 项出厂设置。左上角的进度 1/4 → 4/4 贯穿全片，每项设置回答一个开场谜题，并给一条能用上的建议。之后是“三个提醒”，最后回到开场的草丛首尾呼应。
- **画面**：纯黑背景上，几万颗香槟金粒子在草丛、问号、大脑、年份、片名和线稿图标之间连续变形。辉光、冲击光环和光束穿梭转场都跟着鼓点走；还有 3D 网格、发光节点网络和时间轴镜头。
- **文字**：思源宋体卡片，逐字模糊浮现、结束前上浮淡出，重点词用橙色或青色辉光高亮。
- **配乐**：用代码合成的 D 小调氛围电子乐（96 BPM），按段落能量从心跳、轻、中到满逐级推进。转场只用低频：低音下潜冲击、低频气流铺垫，没有高频的“沙沙/刷”声。

## 成片

| 文件 | 说明 |
| --- | --- |
| `output/出厂设置_进化心理学.mp4` | v3 成片（1080p / 30fps，配乐，无旁白） |
| `output/封面.png` | 视频封面 |
| `output/v2_旁白版/` | v2：粒子风格 + 合成旁白（12 分钟） |
| `output/v1_旧版/` | v1：扁平图标风格 |

## 如何重新生成（v3）

```bash
pip install numpy scipy soundfile
bash src/fetch_assets.sh                  # 字体、图标（v3 不需要语音模型）
cd video2 && npm install && cd ..         # three.js / playwright-core（video3 共用）
ln -sfn ../video2/node_modules video3/node_modules
node video3/timeline.mjs                  # 由 story.js 生成节拍时间轴 → build/v3_timeline.json
python3 src/music_v3.py                   # 合成配乐 → build/v3_music.wav，鼓点表 → build/v3_beats.json
cd video3
node render.mjs --preview 12,60,300       # （可选）导出预览帧到 build/v3prev/
node render.mjs --workers 4 --out ../build/v3_master.mp4
```

- 改文字、节奏：编辑 `video3/story.js`。每张卡片的时长以“拍”为单位，段落会自动对齐到小节；改完重新运行 timeline 和 music。
- 改画面：编辑 `video3/visuals.js`，按段落 id 组织，`S.T(i)` 是本段第 i 张卡片开始的时间。
- 改音乐：编辑 `src/music_v3.py`（和弦进行、各段能量、转场音效）。

## 素材与许可

- 图标：[Twemoji](https://github.com/jdecked/twemoji)（CC-BY 4.0）、[Tabler Icons](https://tabler.io/icons)（MIT）
- 字体：思源宋体 / 思源黑体、Inter、JetBrains Mono（均为 SIL OFL）
- 3D 渲染：three.js（MIT）；配乐与音效全部由 `src/music_v3.py` 合成
