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
