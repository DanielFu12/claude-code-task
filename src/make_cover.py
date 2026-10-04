# -*- coding: utf-8 -*-
"""生成视频封面 output/封面.png。"""
import os

from render import ROOT, emoji, make_background, paste, text_layer, draw_particles

img = make_background()
draw_particles(img, 3.0)
c = img.convert("RGBA")
for ch, x, y, s in [("🐍", 300, 330, 260), ("🧠", 1620, 330, 260), ("🚗", 330, 760, 150), ("🧋", 1590, 760, 150)]:
    e = emoji(ch, s)
    paste(c, e, x - s // 2, y - s // 2)
for s, size, f, col, y in [("为什么你怕蛇，却不怕汽车？", 72, "h", "ink", 260),
                            ("进化心理学", 210, "serif", "amber", 500),
                            ("你大脑的“出厂设置”", 80, "b", "ink", 720),
                            ("12 分钟读懂：我们为什么是现在这个样子", 44, "m", "muted", 850)]:
    t = text_layer(s, size, f, col)
    paste(c, t, (1920 - t.width) // 2, y - t.height // 2)
out = os.path.join(ROOT, "output", "封面.png")
c.convert("RGB").save(out)
print(out)
