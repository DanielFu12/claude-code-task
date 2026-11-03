#!/usr/bin/env bash
# 成片质检：格式、时长、帧数、黑屏、静音、响度、文件大小。用法：scripts/qc_video.sh <mp4>...
for f in "$@"; do
  echo "=== $f"
  ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=codec_name,width,height,r_frame_rate,nb_read_packets,bit_rate -of default=nw=1 "$f"
  ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels,bit_rate -of default=nw=1 "$f"
  ffprobe -v error -show_entries format=duration,size -of default=nw=1 "$f"
  echo "--- 黑屏（≥0.2s，亮度阈值 0.02）"
  ffmpeg -hide_banner -nostats -i "$f" -vf "blackdetect=d=0.2:pic_th=0.98:pix_th=0.02" -an -f null - 2>&1 | grep -o "black_start.*" || echo "无"
  echo "--- 静音（≥0.5s，-50dB）"
  ffmpeg -hide_banner -nostats -i "$f" -af "silencedetect=n=-50dB:d=0.5" -vn -f null - 2>&1 | grep -o "silence_\(start\|end\).*" || echo "无"
  echo "--- 响度"
  ffmpeg -hide_banner -nostats -i "$f" -af ebur128=peak=true -vn -f null - 2>&1 | grep -A12 "Summary" | grep -E "I:|LRA:|Peak:"
done
