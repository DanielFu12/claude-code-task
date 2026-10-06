# 巴芒价值 · 品牌角标规范

所有视频、图片、海报、页面类产出，右上角都要放这套角标。

![lockup](hud_lockup.png)

## 资产

| 文件 | 用途 |
|---|---|
| `logo_baman.png` | logo 原图：透明底，1024×1024，已去白边 |
| `hud_lockup.png` | 1x 静态角标（logo + 巴芒价值 + BUFFETT · MUNGER），可直接给 ffmpeg overlay 等工具用 |
| `hud_lockup@4x.png` + `hud_layout.json` | 4 倍分辨率角标和布局，运行时按需缩放 |
| `brand.py` | `Hud` 类：带光晕、阴影、流光的合成（Python / numpy） |
| `logo_source_white.webp` | 用户提供的白底原稿 |
| `extract_logo.py` | 从白底原稿抠出去白边透明 PNG 的脚本 |

## 设计规范（以 1920×1080 为基准）

**Logo**
- 只保留蓝色渐变的圆环和图形，边缘平滑。
- 放在深色背景上不能出现白边：边缘像素已按「观察色 = α·真实色 + (1−α)·白」反解，并统一用预乘 alpha 缩放。
- 显示尺寸约 **60px**，和右侧文字块上下居中对齐。
- logo 后面有一层**很淡的蓝色光晕**（RGB 110,175,255，σ≈11px，强度 0.2），让它在暗色画面里更清楚。

**文字**
- 主标题：金色宋体「巴芒价值」（Noto Serif SC Black，约 38px），金色竖向渐变：#FFF3C8 → #FFD478 → #E2A03C → #FFD682。
- 小字：「BUFFETT · MUNGER」（Cormorant Garamond），颜色 #D6B270，两端对齐到与主标题等宽，放在主标题正下方。
- 流光：约每 **7.5 秒**扫过一次，每次约 **1.4 秒**，只扫文字；其余时间是静止的金色。

**位置**
- 右上角：距右边 52px，距上边 30px。
- 整个角标下面垫一层很淡的暗色阴影，保证在亮画面上也看得清。
- 4K 画面用 `Hud(scale=2)`。

**片尾**（推荐）：logo 约 220px 居中，下方是大号金色「巴芒价值」和「BUFFETT · MUNGER」。

## 用法

```python
import sys; sys.path.insert(0, 'brand')
from brand import Hud, load_logo
hud = Hud()                 # 1080p
hud.draw(frame, t)          # frame: float32 RGB 0..1，t: 秒
rgb, alpha = load_logo(220) # 片尾等处单独使用 logo
```

ffmpeg 直接叠静态角标（无流光）：
```bash
ffmpeg -i in.mp4 -i brand/hud_lockup.png -filter_complex "overlay=W-w-52:30" out.mp4
```

修改设计：编辑 `brand.py` 里的 `SPEC`，然后运行 `python3 brand/brand.py build`（会自动下载字体）。运行 `python3 brand/brand.py preview out.png` 可以生成深色背景下的预览图。
