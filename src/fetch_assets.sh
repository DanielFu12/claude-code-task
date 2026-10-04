#!/usr/bin/env bash
# 下载生成视频所需的字体与语音模型到 assets/
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p assets/fonts assets/models

for w in Regular Medium Bold Heavy; do
  f="assets/fonts/SourceHanSansSC-$w.otf"
  [ -f "$f" ] || curl -sSLf -o "$f" "https://raw.githubusercontent.com/adobe-fonts/source-han-sans/release/SubsetOTF/CN/SourceHanSansCN-$w.otf"
done
f="assets/fonts/SourceHanSerifCN-Heavy.otf"
[ -f "$f" ] || curl -sSLf -o "$f" "https://raw.githubusercontent.com/adobe-fonts/source-han-serif/release/SubsetOTF/CN/SourceHanSerifCN-Heavy.otf"

if [ ! -d assets/models/kokoro-multi-lang-v1_1 ]; then
  curl -sSLf -o /tmp/kokoro.tar.bz2 "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_1.tar.bz2"
  tar xjf /tmp/kokoro.tar.bz2 -C assets/models && rm /tmp/kokoro.tar.bz2
fi
echo "assets ready"

# v2 额外字体
for w in Light ExtraLight Normal; do
  f="assets/fonts/SourceHanSansSC-$w.otf"
  [ -f "$f" ] || curl -sSLf -o "$f" "https://raw.githubusercontent.com/adobe-fonts/source-han-sans/release/SubsetOTF/CN/SourceHanSansCN-$w.otf"
done
[ -f assets/fonts/Inter.ttf ] || curl -sSLf -o assets/fonts/Inter.ttf "https://raw.githubusercontent.com/rsms/inter/master/docs/font-files/InterVariable.ttf"
[ -f assets/fonts/JetBrainsMono.ttf ] || curl -sSLf -o assets/fonts/JetBrainsMono.ttf "https://raw.githubusercontent.com/JetBrains/JetBrainsMono/master/fonts/variable/JetBrainsMono%5Bwght%5D.ttf"
# v2 用到的 Twemoji 图标（SVG）
python3 - <<'PY'
import os, re, urllib.request
src = open("video2/scenes.js", encoding="utf-8").read()
os.makedirs("assets/emoji", exist_ok=True)
for ch in re.findall(r"em\('([^']+)'\)", src):
    cps = [f"{ord(c):x}" for c in ch]
    name = "-".join(cps) if "200d" in cps else "-".join(c for c in cps if c != "fe0f")
    p = f"assets/emoji/{name}.svg"
    if not os.path.exists(p):
        urllib.request.urlretrieve(f"https://raw.githubusercontent.com/jdecked/twemoji/main/assets/svg/{name}.svg", p)
PY
echo "v2 assets ready"
