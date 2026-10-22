"""全片时间轴：所有画面与音效事件都对齐到配乐的节拍网格。

配乐（Lyria 生成，见 README）实测 75 BPM：拍长 0.8 s，第 0 拍在 0.12 s，每 4 拍一小节（小节线 k≡0 mod 4），
每 8 拍一个乐句（6.4 s）。关键音乐事件（librosa 起音检测）：
  19.31 s 首个重击  32.1 s 主律动进入  114.8 s 全曲最强冲击  159.3–159.8 s 静默  ~171 s 起渐弱，178.5 s 结束
"""
BEAT0, SPB = 0.12, 0.8


def B(k):
    """第 k 拍的时间（秒）"""
    return BEAT0 + SPB * k


T_TOTAL = 181.0
MUSIC_OFFSET = 0.0

# ---------------------------------------------------------------- 章节
T_TITLE = 19.31          # 标题重击
T_RULES = B(30)          # 规则
RACE_K0 = 40             # 第一年开始于第 40 拍（32.12 s）
YEAR_BEATS = 8           # 每年 8 拍 = 6.4 s
YEARS = list(range(2016, 2026))


def year_t0(i):
    return B(RACE_K0 + YEAR_BEATS * i)


T_RACE_END = year_t0(10)            # 96.12 s
T_FINAL = T_RACE_END                 # 终局：两条资金曲线对撞
T_BREAK = B(137)                     # 109.72 s 音乐收束 → 黑场悬念
T_VERDICT = 114.80                   # 最强冲击：揭晓与热帖的差异
T_WHY = B(166)                       # 132.92 s 原因
T_STATEMENT = 153.9                  # 音乐抽空：核心结论
T_VALUE = 160.0                      # 价值投资原则（音乐重新进入）
T_END = 170.5                        # 片尾品牌动画
T_LOGO = 172.92                      # logo 清晰浮现（配合 boom）
T_GOLD = 174.5                       # 金色「巴芒价值」+ BUFFETT · MUNGER
T_FOLLOW = 176.1                     # 关注语
T_FADE = 178.6                       # 整体淡出至 181 s

# ---------------------------------------------------------------- 音效事件 (time, kind, kwargs)
AUDIO_EVENTS = []


def _ev(t, kind, **kw):
    AUDIO_EVENTS.append((t, kind, kw))


# 开场：心跳 + 两组数字落地
for k in (0, 2, 4, 6):
    _ev(B(k) + 0.02, 'pulse', strength=0.55)
_ev(B(8), 'boom', strength=0.55)            # 美股 +85,470%
_ev(B(12), 'boom', strength=0.6)            # A 股 −96.4%
_ev(B(16), 'subdrop', strength=0.55)
for k in (17, 18, 19, 20, 21, 22, 23):
    _ev(B(k), 'tick', strength=0.18)
_ev(T_TITLE, 'riser', d=3.2, strength=0.45)
_ev(T_TITLE, 'boom', strength=1.0)
_ev(T_TITLE, 'braam', strength=0.55)
_ev(year_t0(0), 'boom', strength=0.7)
for i in range(10):
    t0 = year_t0(i)
    if i:
        _ev(t0, 'boom', strength=0.5)
    _ev(B(RACE_K0 + YEAR_BEATS * i + 4), 'pulse', strength=0.5)   # 年度收益揭晓
_ev(T_FINAL, 'subdrop', strength=0.8)
_ev(T_BREAK + 0.4, 'subdrop', d=2.6, strength=0.7)
_ev(T_VERDICT, 'riser', d=4.0, strength=0.5)
_ev(T_VERDICT, 'boom', strength=1.0)
_ev(T_VERDICT, 'braam', strength=0.6)
_ev(T_WHY, 'boom', strength=0.55)
for k in (174, 180, 185):
    _ev(B(k), 'pulse', strength=0.5)
_ev(B(151), 'pulse', strength=0.5)
_ev(B(159), 'pulse', strength=0.5)
_ev(B(202), 'pulse', strength=0.4)
_ev(B(206), 'pulse', strength=0.4)
_ev(T_STATEMENT, 'subdrop', d=2.4, strength=0.75)
_ev(T_VALUE, 'boom', strength=0.75)
_ev(T_LOGO, 'boom', strength=0.85)
_ev(T_LOGO, 'braam', strength=0.4, d=4.0)
_ev(T_GOLD, 'pulse', strength=0.45)
