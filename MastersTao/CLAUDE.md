# MastersTao 系列约定（本目录优先于仓库根目录 CLAUDE.md）

本目录（`masters-tao-holdings` 分支）专门制作 **MastersTao · 大师持仓洞察** 账号的视频，长期独立维护，**不合并到 main**。

- **品牌**：本系列所有视觉产出使用 `brand/` 下的 MastersTao 官方 logo 与 `brand/BRAND.md` 规范，**不使用**根目录 `brand/` 的「巴芒价值」角标；也不要修改根目录的 `brand/`、`不开心视频/` 等主分支项目。
- **角标**：`from mt_brand import Hud`，`Hud(width=1080).draw(frame, t)`，右上角。
- **数据**：每期数据必须可追溯、可复现——原始数据、机构名单映射、统计脚本、独立复核脚本都放在该期目录的 `data/` 与 `scripts/`；画面中的每个数字都要在 `verify.py` 里有断言。区分事实 / 背景 / 相关 / 推测，不用持仓名单推断机构意图。
- **格式**：竖屏 1080×1920、30fps、3 分钟以内；正式版 + ≤30MB 预览版。
- **目录**：`fonts/` 为构建时下载的字体（不入库）；`epNN_<主题>/` 为每一期。

## 目录

- `brand/`：系列视觉体系（logo-kit、mt_brand.py、BRAND.md）。
- `ep01_national_team/`：EP01《国家队去哪了？》汇金与证金 19 个季度持仓足迹。
