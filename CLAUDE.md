# 项目约定

## 品牌角标（所有任务必须遵守）

凡是产出视频、图片、海报、幻灯片、网页等视觉内容，**右上角都要放「巴芒价值」品牌角标**，统一使用 `brand/` 目录下的资产，不要自己另画 logo。

- 规范与用法见 `brand/BRAND.md`。
- logo：`brand/logo_baman.png`。蓝色渐变圆环 + 图形，透明底，已去白边，深色背景上不会有白边。显示高度约 60px（1080p），和右侧文字上下居中对齐，后面加一层很淡的蓝色光晕。
- 文字：金色宋体「巴芒价值」，正下方是小字「BUFFETT · MUNGER」（与主标题等宽）。
- 流光：约每 7.5 秒扫过一次，每次约 1.4 秒，平时是静止的金色。
- Python 渲染用 `from brand import Hud`，调用 `Hud().draw(frame, t)`；不能逐帧合成时，用 `brand/hud_lockup.png` 做静态叠加（如 ffmpeg overlay）。
- 片尾推荐用大号 logo + 金色「巴芒价值」+「BUFFETT · MUNGER」。

## 目录

- `brand/`：品牌资产与合成模块。
- `不开心视频/`：《人为什么会感到不开心》3 分钟视频，含源码和 `build.sh`。
- `love_video/` + `爱的本质.mp4`：《爱的本质》3 分钟视频（`make_music.py` 延长配乐，`render.py render` 渲染）。
- 根目录的 `*.mp4`：参考视频和背景音乐来源。
