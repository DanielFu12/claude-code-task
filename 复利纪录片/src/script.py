"""动画里用到的全部数字（与 SOURCES.md 第三节一致），画面直接引用这些值。"""
import math

YEARS = 30
MATH = dict(
    up=1.1 ** YEARS,                 # 17.449：每年 +10%，30 年
    down=0.9 ** YEARS,               # 0.04239：每年 −10%，30 年
    ratio=(1.1 / 0.9) ** YEARS,      # 411.6：两者相差
    recover_years=math.log(2) / math.log(1.1),   # 7.27 年：腰斩后按每年 +10% 回到原点
)
ASSUMPTIONS = '数学示意：假设固定年化收益率，不计税费与通胀；不代表任何资产的预期收益。'

if __name__ == '__main__':
    for k, v in MATH.items(): print(k, round(v, 4))
