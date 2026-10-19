"""去除硬字幕（白字黑边）：在指定横带内用顶帽检测细亮笔画 → 膨胀 → inpaint。"""
import cv2, numpy as np

def sub_mask(bgr, bands, thr=60, white=185):
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m = np.zeros(g.shape, np.uint8)
    H = g.shape[0]
    for y0, y1 in bands:
        a, b = int(y0 * H), int(y1 * H)
        gg = g[a:b]
        th = cv2.morphologyEx(gg, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)))
        bh = cv2.morphologyEx(gg, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)))
        wht = (gg > white) & (hsv[a:b, :, 1] < 70)
        strokes = ((th > thr) & wht).astype(np.uint8)
        # 白色笔画附近必须有黑边
        dark = cv2.dilate((bh > 50).astype(np.uint8), np.ones((5, 5), np.uint8))
        strokes &= dark
        # 字幕行：笔画密集的区域 → 闭运算成块，去掉孤立噪点
        blk = cv2.morphologyEx(strokes, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 9)))
        n, lab, st, _ = cv2.connectedComponentsWithStats(blk)
        keep = np.zeros_like(blk)
        for i in range(1, n):
            if st[i, cv2.CC_STAT_WIDTH] > 40 and st[i, cv2.CC_STAT_AREA] > 300:
                keep[lab == i] = 1
        mm = cv2.dilate(strokes & keep, np.ones((7, 7), np.uint8))
        m[a:b] = np.maximum(m[a:b], mm)
    return m

def desub(bgr, bands, **kw):
    m = sub_mask(bgr, bands, **kw)
    out = cv2.inpaint(bgr, m * 255, 5, cv2.INPAINT_TELEA)
    # 修补区域轻微模糊，弱化痕迹
    soft = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 4)[..., None]
    bl = cv2.GaussianBlur(out, (0, 0), 2.2)
    return (out * (1 - soft) + bl * soft).astype(np.uint8), m
