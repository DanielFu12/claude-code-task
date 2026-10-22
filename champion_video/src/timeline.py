"""全片时间轴：所有画面与音效事件都对齐到配乐的节拍网格。

配乐（Lyria 生成，见 README）实测 75 BPM：拍长 0.8 s，每 4 拍一小节，每 8 拍一个乐句（6.4 s）。
对原曲做了按节拍对齐的拼接（见 MUSIC_EDIT），网格相位全程不变：
  1) 去掉开头 8 拍（6.4 s）的慢铺垫 —— 原曲 6.40 s 处成为成片 0 s；
  2) 「为什么」段落的高能乐段（原曲 115.32–153.72 s，48 拍）完整重复一次，
     让 12 个原因镜头各有 8 拍（6.4 s）—— 先动画搭建，再留出 3 秒以上的阅读时间；
  3) 原曲 154–160 s 的静默段作为「投资启示」金色转场（成片 185.9–192.1 s）；
     随后接回原曲 114.52–140.12 s（全曲最强冲击 + 高潮乐段，32 拍），冲击落在成片 192.4 s，
     让巴菲特 / 芒格的价值投资段落站在全片情绪最高点；
  4) 再接原曲 160.12 s 起的尾段（重新进入的重拍 → 收束），成片 217.72 s 起。
成片里第 k 拍的时间仍是 B(k) = 0.12 + 0.8k。
"""
BEAT0, SPB = 0.12, 0.8


def B(k):
    """第 k 拍的时间（秒）"""
    return BEAT0 + SPB * k


T_TOTAL = 238.6
# 原曲剪辑：[(原曲起点, 原曲终点), ...] 依次拼接（交叉淡化 60 ms）
MUSIC_EDIT = [(6.40, 153.72), (115.32, 160.12), (114.52, 140.12), (160.12, 181.06)]

# ---------------------------------------------------------------- 章节
T_TITLE = 12.91          # 标题重击
T_RULES = B(22)          # 17.72 s 规则
RACE_K0 = 32             # 第一年开始于第 32 拍（25.72 s）
YEAR_BEATS = 8           # 每年 8 拍 = 6.4 s
YEARS = list(range(2016, 2026))


def year_t0(i):
    return B(RACE_K0 + YEAR_BEATS * i)


T_RACE_END = year_t0(10)            # 89.72 s
T_FINAL = T_RACE_END                 # 终局：两条资金曲线对撞
T_BREAK = B(129)                     # 103.32 s 音乐收束 →「为什么差距这么大？」
T_WHY = 108.40                       # 全曲最强冲击：原因分析开始
WHY_T = [T_WHY] + [B(152 + 16 * k) for k in range(5)]     # 六个原因，每个两个乐句（两个 8 拍镜头）
T_INSIGHT = 185.9                    # 音乐抽空：金色「投资启示」转场
T_VALUE = 192.40                     # 全曲最强冲击（拼接后）：同一个市场，换一种方法
T_BUFFETT = B(249)                   # 199.32 巴菲特：价格与价值
T_MUNGER = B(257)                    # 205.72 芒格：反过来想
T_PRIN = B(265)                      # 212.12 四个原则
T_TRUTH = B(272)                     # 217.72 尾段重拍：价值投资的真谛（全片高潮）
T_END = 228.1                        # 片尾品牌动画
T_LOGO = B(288)                      # 230.52 logo 清晰浮现（配合 boom）
T_GOLD = B(290)                      # 232.12 金色「巴芒价值」
T_SUB = B(291)                       # 232.92 BUFFETT · MUNGER
T_FOLLOW = B(292)                    # 233.72 关注语
T_FADE = 236.2                       # 整体淡出至 238.6 s

# ---------------------------------------------------------------- 音效事件 (time, kind, kwargs)
AUDIO_EVENTS = []


def _ev(t, kind, **kw):
    AUDIO_EVENTS.append((t, kind, kw))


# 开场：第一帧就是一记低频冲击，随后心跳脉冲推进
_ev(0.0, 'boom', strength=0.9)
_ev(0.0, 'braam', strength=0.35, d=2.5)
_ev(B(2), 'pulse', strength=0.6)              # 连续 10 年
_ev(B(4), 'boom', strength=0.55)              # 两个账户
for k in (5, 6, 7):
    _ev(B(k), 'tick', strength=0.2)
_ev(B(8), 'boom', strength=0.7)               # 差多少？
for k in (9, 10, 11):
    _ev(B(k), 'tick', strength=0.22)
_ev(B(12), 'boom', strength=0.8)              # 相差超过 1000 倍
_ev(B(12), 'subdrop', strength=0.5)
_ev(T_TITLE, 'riser', d=2.6, strength=0.45)
_ev(T_TITLE, 'boom', strength=1.0)
_ev(T_TITLE, 'braam', strength=0.55)
_ev(year_t0(0), 'boom', strength=0.7)
for i in range(10):
    if i:
        _ev(year_t0(i), 'boom', strength=0.5)
    _ev(B(RACE_K0 + YEAR_BEATS * i + 4), 'pulse', strength=0.5)   # 年度收益揭晓
_ev(T_FINAL, 'subdrop', strength=0.8)
_ev(B(121), 'pulse', strength=0.55)           # 终点数字
_ev(B(123), 'boom', strength=0.6)             # 相差 1,333 倍
_ev(T_BREAK + 0.4, 'subdrop', d=2.6, strength=0.7)
_ev(T_WHY, 'riser', d=4.0, strength=0.5)
_ev(T_WHY, 'boom', strength=1.0)
_ev(T_WHY, 'braam', strength=0.6)
for t in WHY_T[1:]:
    _ev(t, 'boom', strength=0.45)
for t in WHY_T:
    _ev(t + 8 * SPB if t > T_WHY else B(144), 'pulse', strength=0.35)     # 每个原因的第二个镜头
_ev(T_INSIGHT, 'subdrop', d=2.4, strength=0.7)
_ev(T_INSIGHT + 0.6, 'braam', strength=0.3, d=3.5)        # 「投资启示」金字成形
_ev(T_VALUE - 4.0, 'riser', d=4.0, strength=0.6)          # 冲向高潮
_ev(T_VALUE, 'boom', strength=1.0)
_ev(T_VALUE, 'braam', strength=0.6)
_ev(T_VALUE, 'subdrop', strength=0.6)
for t in (T_BUFFETT, T_MUNGER, T_PRIN):
    _ev(t, 'boom', strength=0.65)
for k in range(4):
    _ev(T_PRIN + 0.8 * k, 'pulse', strength=0.4)           # 四个原则逐拍点亮
_ev(T_TRUTH, 'boom', strength=0.95)
_ev(T_TRUTH, 'braam', strength=0.55, d=4.0)
_ev(B(277), 'pulse', strength=0.4)
_ev(T_END, 'riser', d=2.4, strength=0.35)
_ev(T_LOGO, 'boom', strength=0.85)
_ev(T_LOGO, 'braam', strength=0.4, d=4.0)
_ev(T_GOLD, 'pulse', strength=0.5)
_ev(T_FOLLOW, 'pulse', strength=0.3)
