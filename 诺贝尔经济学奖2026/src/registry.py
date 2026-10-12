"""场景注册表：@scene(t0, t1, fade_in, fade_out) 装饰的函数在 [t0-fi, t1+fo] 内被调用，参数 (fr, t, alpha)。"""
SCENES = []


def scene(t0, t1, fi=0.3, fo=0.3):
    def deco(fn):
        SCENES.append((t0, t1, fi, fo, fn))
        return fn
    return deco
