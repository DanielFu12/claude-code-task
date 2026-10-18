"""配乐剪辑方案 + 卡点（写 work/music_plan.json，供 timeline.py 和 audio_mix.py 使用）。

三段 Lyria 原创配乐（同一调性/配器，提示词见 music_gen.py）：
  A = A_2：开场悬念 → 标题重拍 → 怀旧钢琴（第一章）→ 推进的弦乐固定音型（第二章）
  C = A_1 的后段：第三章「复利账本」从安静处起步，层层叠加到高潮
  B = B_0：第四章泡沫的阴影 → 坚定 → 第五章反思钢琴 → 史诗升腾 → 片尾大和弦
每段配乐的关键重拍（用 librosa onset 检测并人工核对包络图）在下面列出，
卡点 = 音乐时间 + 该段在成片中的偏移。
"""
import json, os, sys

# (名称, 文件, 音乐内起点, 成片起点, 成片终点, 淡入, 淡出)
def plan():
    A_OFF = 27.67 - 26.11          # A_2 的标题重拍在 26.11s → 成片 27.67s
    C_IN = 126.6                   # A_1 第三段（安静的起步）
    C_AT = 130.5
    C_OFF = C_AT - C_IN
    B_AT = 186.4                   # 第四章：先留出“并不平坦”的低频空拍，再进入 B
    pieces = [
        dict(name='A', file='A_2.mp3', src_in=0.0, at=A_OFF, until=C_AT + 1.2, fade_in=0.0, fade_out=2.6),
        dict(name='C', file='A_1.mp3', src_in=C_IN - 1.2, at=C_AT - 1.2, until=B_AT + 1.5, fade_in=1.6, fade_out=3.0),
        dict(name='B', file='B_0.mp3', src_in=0.0, at=B_AT, until=None, fade_in=0.8, fade_out=4.0),
    ]
    anchors = {
        'title': 27.67,                       # A 26.11 重拍
        'ch2': A_OFF + 71.70,                 # A 推进段落起点
        'ch3': C_AT,                          # 切到 C（安静起步）
        's27': C_OFF + 142.91,                # C 开始叠加 → 拆股动画
        's28': C_OFF + 154.2,                 # C 大段落 → 市值揭晓
        's39': B_AT + 27.23,                  # B 转为坚定 → “那他为什么还不卖？”
        'ch5': B_AT + 51.3,                   # B 回落到钢琴 → 第五章
        's46': B_AT + 74.37 - 2.0,            # B 升腾 → 核心观点
        'end': B_AT + 91.9,                   # B 峰值 → 片尾
    }
    # 原曲里的上扬/镲片过渡（Gemini 听审 + 频谱核对），这些窗口内配乐低通到 2.5kHz
    lp_windows = [
        (A_OFF + 24.6, A_OFF + 26.4),         # A 标题重拍前的反向上扬
        (A_OFF + 69.8, A_OFF + 71.6),         # A 进入第二章前的过渡
        (A_OFF + 126.5, C_AT + 0.6),          # A 末尾的上扬（与切换点重合）
        (C_OFF + 128.0, C_OFF + 129.2),       # C 起点附近的镲片
        (B_AT + 84.5, B_AT + 93.0),           # B 高潮前后的镲片卷与镲片余音
    ]
    # 声音设计重拍（低频冲击 / sub drop），成片秒
    hits = {
        'title': 27.67, 'ch1': None, 'ch2': anchors['ch2'], 'ch3': C_AT, 'ch4': None,
        'logo': B_AT + 95.79,                 # B 最后一个重拍 → logo 浮现
    }
    return dict(pieces=pieces, anchors=anchors, hits=hits, lp_windows=lp_windows, A_OFF=A_OFF, C_OFF=C_OFF, B_AT=B_AT)


if __name__ == '__main__':
    work = sys.argv[1]
    p = plan()
    json.dump(p, open(os.path.join(work, 'music_plan.json'), 'w'), indent=1)
    for k, v in p['anchors'].items(): print(k, round(v, 2))
