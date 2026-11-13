"""从仓库里的 CNBC 专访（Squawk Box，2026-07-15，Becky Quick 专访巴菲特）切出画面素材 → work_clips/c_*.mp4
- 裁掉下方的 CNBC 字幕条（画面 y ≥ 0.70 处起是 “BUFFETT ON GOOGLE INVESTMENT” 横条与台标），只保留上方 1920×752；
- 去掉音轨：片中不播放巴菲特原声，原话一律做成屏幕引语卡（制作宪章 三.1）；
- 每段对应专访里的哪句话见 research/CNBC专访_20260715_转写.md 和下面的注释，供画面与引语卡对位。
python3 src/cut_cnbc.py
"""
import os, json, glob, subprocess
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRC = glob.glob(os.path.join(ROOT, '*CNBC专访*.mp4'))[0]
OUT = os.path.join(ROOT, 'work_clips'); os.makedirs(OUT, exist_ok=True)
SRC_NAME = 'CNBC Squawk Box：Becky Quick 专访巴菲特（2026-07-15）'
# 名称: (起点秒, 时长, 景别, 这一段巴菲特在说什么)
CLIPS = {
    'c_initiated':   (36.4, 5.5,  'close', '“I initiated it… I normally wouldn’t give you an answer”'),
    'c_two_a':       (42.1, 4.5,  'two',   '双人景：谈阿贝尔'),
    'c_approve':     (46.8, 11.5, 'close', '“I am not doing anything that he doesn’t approve of”'),
    'c_rank':        (69.0, 9.0,  'close', '“It’s probably number five or six”'),
    'c_bnsf':        (89.3, 6.8,  'close', '“We’ve got the Burlington Northern Railroad”'),
    'c_rightterms':  (101.2, 22.0, 'close', '全资与股票一视同仁；“buy a good business on the right terms”'),
    'c_two_b':       (137.3, 9.8, 'two',   '双人景：谈可口可乐'),
    'c_goodbiz':     (147.3, 25.5, 'close', '“a very good business… earn high returns on capital over a long period”'),
    'c_bonds':       (182.7, 32.8, 'close', '国债 vs 好生意：“a lot more than the returns on essentially riskless investments”'),
    'c_amex':        (225.3, 16.0, 'close', '美国运通 “30% plus on capital”'),
    'c_munger':      (243.7, 33.8, 'close', '“the trick… high returns on capital for an extended period”；芒格反复强调'),
    'c_two_c':       (277.7, 8.2,  'two',   '双人景：谈芒格'),
    'c_cash':        (286.1, 18.2, 'close', '真金白银的现金，能分配或再投资'),
    'c_two_d':       (329.7, 8.6,  'two',   '双人景：“Google, you just called an AI company”'),
    'c_hundreds':    (338.5, 7.6,  'close', '“they’re all laying out hundreds of billions”'),
    'c_railroad':    (349.3, 19.9, 'close', '铁路投不起这种钱；“They weren’t playing that game with computer software”'),
    'c_winner':      (391.5, 10.5, 'close', '“more likely to be a winner… than 90% or 95%”'),
    'c_quarter':     (411.8, 10.5, 'close', '华尔街只问下个季度'),
    'c_dontlike':    (466.6, 10.1, 'close', '“I don’t like it as well as at least four or five other businesses”'),
    'c_two_e':       (512.9, 5.0,  'two',   '双人景：问为什么是谷歌而不是其他巨头'),
    'c_game':        (523.7, 23.2, 'close', '“playing a game they don’t want to play”；IBM'),
    'c_grocery':     (555.6, 14.4, 'close', '祖父的杂货店：顾客不傻'),
    'c_two_f':       (597.9, 10.2, 'two',   '双人景：A&P 的好牌没了'),
    'c_ibm':         (647.4, 20.8, 'close', 'Data Documents 与 IBM 反垄断'),
    'c_attacks':     (676.9, 10.4, 'close', '“if you have a wonderful business, you are going to be subject to attacks… how long is it going to be wonderful?”'),
}
if __name__ == '__main__':
    for k, (t0, d, _, _) in CLIPS.items():
        out = os.path.join(OUT, k + '.mp4')
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', str(t0), '-i', SRC, '-t', str(d), '-an', '-r', '30',
                        '-vf', 'crop=1920:752:0:0', '-c:v', 'libx264', '-crf', '16', '-preset', 'fast', '-pix_fmt', 'yuv420p', out], check=True)
        print('ok', k)
    p = os.path.join(ROOT, 'assets', 'media', 'ia_clips.json')
    m = json.load(open(p)) if os.path.exists(p) else {}
    for k, (t0, d, shot, note) in CLIPS.items():
        m[k] = dict(source=SRC_NAME, ia='https://www.cnbc.com/2026/07/15/warren-buffett-tells-cnbc-he-initiated-berkshire-hathaways-investment-in-alphabet.html',
                    start=t0, dur=d, shot=shot, note=note)
    json.dump(m, open(p, 'w'), ensure_ascii=False, indent=1)
