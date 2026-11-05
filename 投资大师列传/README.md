# 投资大师列传 · 系列视频

本目录是「投资大师列传」系列视频的工作区：30 位投资大师，每人一集。

## 分支约定（重要）

- 本系列只在分支 `claude/beautiful-archimedes-o816wj` 上开发，这条分支长期独立维护。
- **不得合并到 `main`**：不要对 `main` 开 PR，也不要把本分支 merge、rebase 或 cherry-pick 进 `main`。
- 如果要用 `main` 上的新内容（例如 `brand/` 更新），只能从 `main` 合并进本分支，方向是 `main → 本分支`，不能反过来。

## 品牌规范

每集视频右上角都要放「巴芒价值」角标，统一使用仓库根目录的 `brand/`（规范见 `brand/BRAND.md`）：

- Python 逐帧渲染：`from brand import Hud`，每帧调用 `Hud().draw(frame, t)`。
- 不能逐帧合成时：用 `brand/hud_lockup.png` 做静态叠加。
- 片尾：大号 logo + 金色「巴芒价值」+「BUFFETT · MUNGER」。

## 目录规划

```
投资大师列传/
├── README.md          # 本文件：分支约定、目录规划
├── 选题规划.md         # 30 集标题与每集核心看点
└── NN-大师名/          # 每集一个子目录，例如 04-沃伦·巴菲特/
    ├── 脚本.md        # 分镜脚本（由 src/shots.py 生成）
    ├── src/           # 分镜与渲染源码
    ├── build.sh       # 一键生成
    └── 视频号发布文案.md
```

集数编号与 `选题规划.md` 一致（01–30）。
