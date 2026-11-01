#!/usr/bin/env python3
"""用 Google Lyria 3.5（Gemini API）生成本片原创配乐素材：music/score_lyria_A.mp3。

提示词在 music/lyria_prompt.txt。生成结果每次不同；本片使用的版本已存入仓库，
src/audio_track.py 里的小节网格（SRC_IBI / SRC_T0）与剪辑表（EDIT）都是针对这一版测出来的。
重新生成后需要重新测量网格并调整 EDIT。

用法：GEMINI_API_KEY=... python3 scripts/gen_music.py [输出前缀]
"""
import os, sys, time
from google import genai

HERE = os.path.dirname(os.path.abspath(__file__))
prompt = open(os.path.join(HERE, "..", "music", "lyria_prompt.txt"), encoding="utf-8").read()
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "music", "score_lyria_new")
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", "dummy"))
for attempt in range(5):
    try:
        r = client.models.generate_content(model="models/lyria-3.5", contents=prompt)
    except Exception as e:
        print("retry:", str(e)[:120]); time.sleep(10); continue
    if not r.candidates:
        print("retry: empty response"); time.sleep(5); continue
    for p in r.candidates[0].content.parts:
        if getattr(p, "inline_data", None) and p.inline_data.data:
            fn = out + (".mp3" if "mpeg" in p.inline_data.mime_type else ".wav")
            open(fn, "wb").write(p.inline_data.data)
            print("saved", fn)
            sys.exit(0)
sys.exit("generation failed")
