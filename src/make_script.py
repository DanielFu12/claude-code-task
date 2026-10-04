# -*- coding: utf-8 -*-
"""根据 content.py 与 build/timeline.json 生成带时间码的完整文案 output/文案.md。"""
import json
import os

from content import SCENES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tl = json.load(open(os.path.join(ROOT, "build/timeline.json")))


def ts(t):
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


out = ["# 进化心理学：你大脑的“出厂设置”", "",
       f"> 科普视频完整文案 · 时长约 {tl['total'] / 60:.0f} 分钟 · 时间码与成片对应", "",
       "## 开场", ""]
for sc, t in zip(SCENES, tl["scenes"]):
    kind = sc.get("kind", "normal")
    if kind == "chapter":
        out += ["", f"## {sc['lines'][0].rstrip('。？')}", ""]
        continue
    if kind == "refs":
        out += ["", "## 参考资料", ""]
        refs = [e for e in sc["els"] if e["t"] == "text"][1]["s"].split("\n")
        out += [f"- {r}" for r in refs]
        continue
    para = "".join(l if isinstance(l, str) else l[0] for l in sc["lines"])
    out.append(f"**[{ts(t['start'])}]** {para}")
    out.append("")
open(os.path.join(ROOT, "output", "文案.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("ok")
