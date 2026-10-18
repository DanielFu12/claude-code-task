"""第五章 · 真正可以复制的（逆向思考、失败条件、核心结论）"""
from common import *  # noqa


def rot_text(cv, s, x, y, size, fnt, ang, col, a):
    m, base, w, h = text_mask(s, fnt, size)
    M = cv2.getRotationMatrix2D((m.shape[1] / 2, m.shape[0] / 2), ang, 1.0)
    rm = cv2.warpAffine(m, M, (m.shape[1], m.shape[0]))
    cv.over(np.asarray(col, np.float32), rm * a, x - m.shape[1] / 2, y - m.shape[0] / 2)


def shot_ch5(cv, t):
    # ---- s43：反过来想
    t0, t1 = S('s43') - 0.5, S('s44') + 0.1
    a = env(t, t0, t1, 0.4, 0.3)
    if a > 0:
        p = t - t0
        ang = 180 * (1 - eio((p - 0.6) / 1.2))
        rot_text(cv, 'Invert, always invert.', W / 2, 620, 64, 'typewriter', ang, GOLD_L, a)
        cv.text('反过来想，总是反过来想。', W / 2, 760, 56, 'serif_black', col=CREAM, a=a * eo((p - 1.8) / 0.5))
        cv.text('数学家雅可比的名言 · 芒格常引用（1996）', W / 2, 840, 26, 'sans_light', col=GREY, a=a * eo((p - 2.0) / 0.5))
        k = eo((p - 2.8) / 0.5)
        cv.text('什么会让这笔投资失败？', W / 2, 1100, 52, 'sans_bold', col=WHITE, a=a * k)
    # ---- s44：四种失败
    t0, t1 = S('s44') - 0.2, S('s45') + 0.1
    a = env(t, t0, t1, 0.3, 0.3)
    if a > 0:
        p = t - t0
        items = [('买得太贵', '再好的公司，价格也有上限'), ('借钱，被迫卖出', '杠杆让你等不到回报'),
                 ('恐慌中离场', '在最低点交出筹码'), ('护城河被攻破', '基本面真的变了')]
        for i, (h1, h2) in enumerate(items):
            x = 290 + (i % 2) * 500; y = 560 + (i // 2) * 360
            ti = 0.2 + i * 1.25
            k = eo((p - ti) / 0.4)
            cv.text(f'0{i + 1}', x - 200, y - 95, 30, 'oswald', col=RED, a=a * k, anchor='l')
            cv.line((x - 200, y - 70), (x - 200 + 400 * k, y - 70), RED * 0.7, a * k, 2)
            cv.text(h1, x - 200, y - 10, 50, 'serif_black', col=CREAM, a=a * k, anchor='l')
            cv.text(h2, x - 200, y + 60, 26, 'sans_light', col=GREY, a=a * k, anchor='l')
            ks = eio((p - ti - 0.5) / 0.4)
            if ks > 0:
                tw = text_size(h1, 'serif_black', 50)[0]
                cv.line((x - 205, y - 10), (x - 205 + (tw + 10) * ks, y - 10), RED, a, 4)
    # ---- s45 + 停顿：1996 年的提醒
    quote_card(cv, 'q1996', t, S('s45') - 0.3, S('s46') + 0.1, cy=820, en_size=40, cn_size=46)
    # ---- s46：核心结论
    t0, t1 = S('s46') - 0.3, S('s47') + 0.1
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        x0, x1, y0, y1 = 120, 960, 560, 1080
        xs = np.linspace(x0, x1, 400)
        u = (xs - x0) / (x1 - x0)
        val = y1 - (u ** 1.5) * (y1 - y0) * 0.9
        price = val + 70 * np.sin(u * 23) * np.cos(u * 7) + 40 * np.sin(u * 51)
        n = max(2, int(400 * eio((p - 0.2) / 3.0)))
        cv.poly(np.stack([xs[:n], price[:n]], 1), GREY, a * 0.8, 2)
        cv.poly(np.stack([xs[:n], val[:n]], 1), GOLD, a, 5)
        if n > 380:
            cv.text('内在价值', xs[-1], val[-1] - 50, 34, 'sans_bold', col=GOLD, a=a, anchor='r')
            cv.text('股价', xs[-1], price[-1] + 60, 28, 'sans_med', col=GREY, a=a, anchor='r')
        cv.text('长期持有本身并不创造价值', W / 2, 330, 56, 'serif_black', col=CREAM, a=a * eo(p / 0.5))
        cv.text('创造财富的，是企业持续增长的内在价值', W / 2, 1200, 44, 'serif_black', gold=True, a=a * eo((p - 2.6) / 0.6), glow=0.25)
        cv.text('示意图', x0, y1 + 40, 20, 'sans_light', col=DIM, a=a, anchor='l')
    # ---- s47：三个能力
    t0, t1 = S('s47') - 0.3, S('s48') + 0.1
    a = env(t, t0, t1, 0.4, 0.4)
    if a > 0:
        p = t - t0
        g = sh('RAYS')(t=t, c=(0.5, 0.52), col=(1.0, 0.75, 0.38), k=0.16 * a, spin=t * 0.05)
        cv.img += g[..., :3]
        words = [('合理的价格', S('s47') + 0.9), ('伟大的企业', S('s47') + 2.4), ('耐心陪伴', S('s47') + 5.2)]
        for i, (wd, ta) in enumerate(words):
            k = eo((t - ta) / 0.5)
            cv.text(wd, W / 2, 620 + i * 190, 92, 'serif_black', gold=True, a=a * k, glow=0.35, scale=1.08 - 0.08 * k)
        cv.text('识别', W / 2 - 330, 715, 30, 'sans_light', col=CREAM, a=a * eo((t - S('s47') - 2.2) / 0.5))
        cv.text('基本面未变时', W / 2, 1100, 30, 'sans_light', col=CREAM, a=a * eo((t - S('s47') - 5.0) / 0.5))
    # ---- s48：时间是优秀企业的朋友
    t0, t1 = S('s48') - 0.3, CH['end'][0] + 0.8
    a = env(t, t0, t1, 0.4, 1.0)
    if a > 0:
        p = t - t0
        rng = np.random.default_rng(12)
        n = 700; xs = rng.uniform(60, 1020, n); sp = rng.uniform(30, 120, n)
        ys = 1300 - (p * sp + rng.uniform(0, 900, n)) % 1100
        cv.splat(xs, ys, GOLD_L, a * 0.5, glow=1.5)
        cv.text('时间，', W / 2, 700, 120, 'serif_black', gold=True, a=a * eo(p / 0.6), glow=0.3)
        cv.text('是优秀企业的朋友', W / 2, 860, 92, 'serif_black', gold=True, a=a * eo((p - 0.6) / 0.6), glow=0.3)
        cv.text('“Time is the friend of the wonderful business.”', W / 2, 1010, 34, 'typewriter', col=CREAM, a=a * eo((p - 1.2) / 0.6))
        cv.text('Warren Buffett · 2010 Chairman’s Letter', W / 2, 1070, 24, 'corm', col=GOLD, a=a * eo((p - 1.4) / 0.6))
