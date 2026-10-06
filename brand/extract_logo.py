"""把白底 logo 抠成干净的透明 PNG（边缘去白、无白边）。

原理：观察色 = a·真实色 + (1-a)·白。先取 logo 内部纯色像素，
再把每个边缘像素的「真实色」取为最近内部像素的颜色，
用最暗通道反解 alpha，RGB 保存为去预乘后的真实色 —— 在深色背景上不会出现白边。
用法: python3 brand/extract_logo.py brand/logo_source_white.webp brand/logo_baman.png
"""
import sys
import numpy as np, cv2
from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
obs = np.asarray(Image.open(src).convert('RGB')).astype(np.float32)
d = 255 - obs.min(2)                                   # 离白色的距离
inner = (d > 10).astype(np.uint8)
inner = cv2.erode(inner, np.ones((3, 3), np.uint8), iterations=2)    # 只保留无混色的内部像素
# 每个像素最近内部像素的坐标 -> 真实色
_, lab = cv2.distanceTransformWithLabels(1 - inner, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
ys, xs = np.where(inner > 0)
# distanceTransformWithLabels 的 label 按扫描顺序给零像素编号
order = np.zeros(lab.max() + 1, np.int64)
zy, zx = np.where(inner > 0)
order[lab[zy, zx]] = np.arange(len(zy))
idx = order[lab]
true = obs[zy[idx], zx[idx]]
ch = true.argmin(2)                                    # 真实色里最暗的通道对比度最高
t = np.take_along_axis(true, ch[..., None], 2)[..., 0]
o = np.take_along_axis(obs, ch[..., None], 2)[..., 0]
alpha = np.clip((255 - o) / np.maximum(255 - t, 1), 0, 1)
dist = cv2.distanceTransform(1 - inner, cv2.DIST_L2, 5)
alpha[dist > 6] = 0                                    # 远离图形的地方一律透明
alpha[alpha < 0.02] = 0
rgba = np.dstack([true, alpha * 255]).clip(0, 255).astype(np.uint8)
# 裁到图形边界 + 少量留白，输出正方形
yy, xx = np.where(alpha > 0)
cy, cx = (yy.min() + yy.max()) / 2, (xx.min() + xx.max()) / 2
half = max(yy.max() - yy.min(), xx.max() - xx.min()) / 2 + 12
y0, x0 = int(cy - half), int(cx - half)
s = int(2 * half)
out = np.zeros((s, s, 4), np.uint8)
out[..., :3] = rgba[int(cy), int(cx), :3]  # 透明区也填真实色，缩放时不会渗入黑/白
crop = rgba[max(y0, 0):y0 + s, max(x0, 0):x0 + s]
out[:crop.shape[0], :crop.shape[1]] = crop
Image.fromarray(out).resize((1024, 1024), Image.LANCZOS).save(dst)
print('saved', dst, out.shape)
