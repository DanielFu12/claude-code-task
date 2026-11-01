# 配乐

`score_lyria_A.mp3`：本片原创配乐素材，由 **Google Lyria 3.5**（Gemini API，`models/lyria-3.5`）根据 `lyria_prompt.txt` 生成（2026-11-01），纯器乐、无人声。生成内容带有 Google SynthID 水印。

- 实测：135.99 BPM，首拍 0.074 s，节拍机器级稳定（多数 10 秒窗口内相位偏差 < 1 ms），161.8 s。
- 本片按小节重新剪辑（`src/audio_track.py` 的 `EDIT` 表：画面小节 → 原曲小节），画面时间轴直接采用 136 BPM，所有切换都踩在鼓点上；再叠加由数据驱动的低频冲击。
- 重新生成：`python3 scripts/gen_music.py`（每次结果不同，需要重新测网格并调整 `EDIT`）。
