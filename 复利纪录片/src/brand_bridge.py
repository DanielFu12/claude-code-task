"""品牌资产桥接：所有品牌颜色、字体、logo、角标都从仓库根目录 brand/ 读取，不在本项目里另行定义。"""
import os, sys
import numpy as np
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'brand'))
import brand as _brand                        # noqa: E402
from brand import Hud, load_logo, SPEC, GOLD_STOPS, SUB_GOLD, LOGO_PNG   # noqa: E402,F401

BRAND_FONT_DIR = os.path.join(REPO, 'brand', 'fonts')


def gold_ramp(h):
    """主标题金色竖向渐变（brand.GOLD_STOPS）"""
    return _brand._ramp(int(h), GOLD_STOPS).astype(np.float32)


def sub_gold():
    return np.array(SUB_GOLD, np.float32) / 255


def brand_font(name, size):
    """品牌字体：与 brand.py 的 FONT_URLS 相同（Noto Serif SC 900 / Cormorant Garamond 600），由 brand._font 下载缓存"""
    return _brand._font(name, size)
