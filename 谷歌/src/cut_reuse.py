"""复用第三期已入库的财讯《投资IN总经》EP97（360p）里与伯克希尔相关的片段 → work_clips/e_*.mp4
裁法与第三期 cut_ep97.py 相同（裁掉顶部标题条与底部字幕，放大到 1280 宽）；使用前仍按 media.py 的 CROP 裁台标。
python3 src/cut_reuse.py
"""
import os, json, glob, subprocess
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRC = glob.glob(os.path.join(ROOT, '..', '日本五大商社', '*EP97*.mp4'))[0]
OUT = os.path.join(ROOT, 'work_clips'); os.makedirs(OUT, exist_ok=True)
SRC_NAME = '财讯《投资IN总经》EP97'
# 抽帧审过：e_meeting（办公室会议）、e_ticker（日本商社股价牌）、e_cash_man（摆拍点钞）与谷歌无关，不用。
# e_abel 底部有 “BERKSHIRE'S NEW CEO GREG ABEL” 字幕条，使用时按 (0.03, 0.05, 0.97, 0.84) 裁掉。
CLIPS = {   # 名称: (起点秒, 时长, 内容) —— 时间段沿用第三期已审过的干净区间
    'e_abel': (95.0, 9.0, '阿贝尔受访画面'),
    'e_brk2026': (14.0, 5.5, '2026 年伯克希尔股东大会'),
}
if __name__ == '__main__':
    for k, (t0, d, _) in CLIPS.items():
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', str(t0), '-i', SRC, '-t', str(d), '-an', '-r', '30',
                        '-vf', 'crop=640:282:0:27,scale=1280:-2:flags=lanczos,unsharp=5:5:0.6', '-c:v', 'libx264', '-crf', '16',
                        '-preset', 'fast', '-pix_fmt', 'yuv420p', os.path.join(OUT, k + '.mp4')], check=True)
        print('ok', k)
    p = os.path.join(ROOT, 'assets', 'media', 'ia_clips.json'); m = json.load(open(p)) if os.path.exists(p) else {}
    for k, (t0, d, note) in CLIPS.items():
        m[k] = dict(source=SRC_NAME, ia='https://www.youtube.com/watch?v=GIVExayTQwM', start=t0, dur=d, note=note)
    json.dump(m, open(p, 'w'), ensure_ascii=False, indent=1)
