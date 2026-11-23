"""字体：从 GitHub 上的 google/fonts 仓库取可变字体，用 fontTools 切出各字重的静态字体 → fonts/<name>.ttf
（前几期 fonts/ 未入库；fonts.googleapis.com 在部分环境不可达，故改走 raw.githubusercontent.com）
python3 src/get_fonts.py
"""
import os, urllib.request
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRC = os.path.join(ROOT, 'fonts_src'); OUT = os.path.join(ROOT, 'fonts')
os.makedirs(SRC, exist_ok=True); os.makedirs(OUT, exist_ok=True)
BASE = 'https://raw.githubusercontent.com/google/fonts/main/'
VF = {'serif': 'ofl/notoserifsc/NotoSerifSC%5Bwght%5D.ttf', 'sans': 'ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf',
      'corm': 'ofl/cormorantgaramond/CormorantGaramond%5Bwght%5D.ttf', 'oswald': 'ofl/oswald/Oswald%5Bwght%5D.ttf',
      'playfair': 'ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf', 'mono': 'ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf'}
STATIC = {'typewriter': 'apache/specialelite/SpecialElite-Regular.ttf'}
NAMES = {'serif_reg': ('serif', 400), 'serif_semi': ('serif', 600), 'serif_black': ('serif', 900),
         'sans_light': ('sans', 300), 'sans_med': ('sans', 500), 'sans_bold': ('sans', 700), 'sans_black': ('sans', 900),
         'corm': ('corm', 500), 'corm_med': ('corm', 600), 'oswald': ('oswald', 500), 'playfair': ('playfair', 700),
         'mono': ('mono', 400)}


def fetch(rel):
    p = os.path.join(SRC, os.path.basename(rel))
    if not os.path.exists(p): urllib.request.urlretrieve(BASE + rel, p)
    return p


if __name__ == '__main__':
    for name, (vf, w) in NAMES.items():
        out = os.path.join(OUT, name + '.ttf')
        if os.path.exists(out): continue
        f = TTFont(fetch(VF[vf])); instancer.instantiateVariableFont(f, {'wght': w}, inplace=True); f.save(out); print('ok', name)
    for name, rel in STATIC.items():
        out = os.path.join(OUT, name + '.ttf')
        if not os.path.exists(out): os.replace(fetch(rel), out) if False else open(out, 'wb').write(open(fetch(rel), 'rb').read())
