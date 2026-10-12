"""官方获奖插画（用户提供的诺贝尔奖官方公布图，插画作者 Niklas Elmehed）→ 两位获奖者的肖像素材。

- card(name)：原图裁切的肖像卡（保留原纸色与金箔），带羽化边缘的 alpha
- lineart(name)：把墨线/金箔提取成「发光线稿」（深色背景上用于淡淡的背景剪影）
"""
import os
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'assets', 'nobel2026_official_illustration.webp')
BOX = {'hall': (40, 318, 900, 1168), 'woodford': (790, 318, 1630, 1168)}   # (x0, y0, x1, y1)


@lru_cache(1)
def _src():
    return np.asarray(Image.open(SRC).convert('RGB')).astype(np.float32) / 255


@lru_cache(8)
def card(name, width=760, feather=0.06):
    x0, y0, x1, y1 = BOX[name]
    im = _src()[y0:y1, x0:x1]
    h, w = im.shape[:2]
    s = width / w
    im = cv2.resize(im, (width, int(h * s)), interpolation=cv2.INTER_AREA)
    h, w = im.shape[:2]
    # 圆角矩形 + 柔边
    a = np.zeros((h, w), np.float32)
    r = int(0.035 * w)
    cv2.rectangle(a, (r, 0), (w - r, h), 1, -1)
    cv2.rectangle(a, (0, r), (w, h - r), 1, -1)
    for cx, cy in ((r, r), (w - r, r), (r, h - r), (w - r, h - r)):
        cv2.circle(a, (cx, cy), r, 1, -1, cv2.LINE_AA)
    a = cv2.GaussianBlur(a, (0, 0), 1.2)
    return im, a


@lru_cache(8)
def lineart(name, width=900):
    x0, y0, x1, y1 = BOX[name]
    im = _src()[y0:y1, x0:x1]
    h, w = im.shape[:2]
    s = width / w
    im = cv2.resize(im, (width, int(h * s)), interpolation=cv2.INTER_AREA)
    paper = np.median(im.reshape(-1, 3), 0)
    lum = im.mean(2)
    d = np.clip(1 - lum / paper.mean(), 0, 1)
    sat = im.max(2) - im.min(2)
    gold = np.clip((sat - 0.12) * 4, 0, 1)
    alpha = np.clip((d - 0.05) * 1.8, 0, 1)
    ink_col = np.array([1.0, 0.95, 0.86], np.float32)
    gold_col = np.array([1.0, 0.80, 0.42], np.float32)
    rgb = ink_col[None, None] * (1 - gold[..., None]) + gold_col[None, None] * gold[..., None]
    # 边缘羽化（避免裁切边出现硬线）
    yy, xx = np.mgrid[0:alpha.shape[0], 0:alpha.shape[1]].astype(np.float32)
    e = np.minimum.reduce([xx, yy, alpha.shape[1] - xx, alpha.shape[0] - yy]) / (0.08 * width)
    alpha *= np.clip(e, 0, 1)
    return rgb.astype(np.float32), alpha.astype(np.float32)
