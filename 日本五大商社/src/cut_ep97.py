"""从用户提供的财讯《投资IN总经》EP97（360p）切出 B-roll → work_clips/e_*.mp4（裁掉顶部标题条与底部字幕，放大到 1280 宽）"""
import os, json, subprocess, glob
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRC = glob.glob(os.path.join(ROOT, '*EP97*.mp4'))[0]
OUT = os.path.join(ROOT, 'work_clips'); os.makedirs(OUT, exist_ok=True)
CLIPS = {   # 名称: (起点秒, 时长)
    'e_logos': (34.5, 3.0), 'e_ticker': (38.5, 5.0), 'e_brk2026': (14.0, 5.5), 'e_abel': (95.0, 9.0),
    'e_meeting': (110.0, 7.0), 'e_lng_port': (152.5, 5.0), 'e_lng_tank': (157.0, 3.5), 'e_yen_hands': (221.0, 4.0),
    'e_yen_count': (225.5, 3.5), 'e_konbini': (244.5, 3.5), 'e_port': (257.0, 4.5), 'e_mine_workers': (261.5, 3.5),
    'e_lng_carrier': (277.0, 4.0), 'e_mitsui_ceo': (332.0, 5.0), 'e_rhodes': (353.0, 8.0), 'e_copper': (391.5, 4.0),
    'e_yen_stack': (472.5, 3.0), 'e_buffett_jp': (465.0, 3.0),
    'e_office_walk': (422.5, 3.5), 'e_office_hall': (429.5, 3.5), 'e_meeting2': (328.5, 4.0), 'e_factory': (305.0, 4.0),
    'e_ana': (316.5, 3.5), 'e_lisbon': (321.0, 4.0), 'e_food': (297.5, 3.5), 'e_cash_man': (214.5, 4.0),
}
SRC_NAME = '财讯《投资IN总经》EP97'
if __name__ == '__main__':
    for k, (t0, d) in CLIPS.items():
        out = os.path.join(OUT, k + '.mp4')
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', str(t0), '-i', SRC, '-t', str(d), '-an', '-r', '30',
                        '-vf', 'crop=640:282:0:27,scale=1280:-2:flags=lanczos,unsharp=5:5:0.6', '-c:v', 'libx264', '-crf', '16',
                        '-preset', 'fast', '-pix_fmt', 'yuv420p', out], check=True)
        print('ok', k)
    p = os.path.join(ROOT, 'assets', 'media', 'ia_clips.json'); m = json.load(open(p))
    for k, (t0, d) in CLIPS.items():
        m[k] = dict(source=SRC_NAME, ia='https://www.youtube.com/watch?v=GIVExayTQwM', start=t0, dur=d)
    json.dump(m, open(p, 'w'), ensure_ascii=False, indent=1)
