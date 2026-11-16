"""画面素材：从 Wikimedia Commons 下载公有领域 / 自由授权的历史照片（第 02 集不用 AI 生成图）。

来源清单在 assets/credits.json（每张图的文件名、授权、作者、页面链接），README 有汇总。
用法：python3 src/assets.py           # 只下载缺失的图，存为 assets/<id>.jpg（1280 宽，JPEG q88）
注意：Wikimedia 对批量下载限流，请求间隔 2 秒，遇到 429 按 Retry-After 等待后重试。
特殊处理：chemical.jpg 原图带相框，下载后裁掉边框（CROP）。
"""
import io, json, os, sys, time, urllib.parse, urllib.request, urllib.error
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets")
UA = {"User-Agent": "MastersTaoDocResearch/1.0 (https://masterstao.com; documentary image research) python-urllib"}
CROP = {"chemical": (0.16, 0.2, 0.85, 0.82)}


def get(url):
    for k in range(8):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or k == 7:
                raise
            time.sleep(int(e.headers.get("retry-after", "20")) + 3)


def fetch(key, title):
    q = urllib.parse.urlencode(dict(action="query", format="json", titles=title, prop="imageinfo", iiprop="url", iiurlwidth=1280))
    d = json.loads(get("https://commons.wikimedia.org/w/api.php?" + q))
    url = next(iter(d["query"]["pages"].values()))["imageinfo"][0]["thumburl"]
    url = url.replace("//thumb.wikimedia.org/", "//upload.wikimedia.org/").split("?")[0]
    im = Image.open(io.BytesIO(get(url))).convert("RGB")
    if key in CROP:
        w, h = im.size
        a, b, c, d_ = CROP[key]
        im = im.crop((int(w * a), int(h * b), int(w * c), int(h * d_)))
    im.save(os.path.join(OUT, key + ".jpg"), quality=88)


if __name__ == "__main__":
    credits = json.load(open(os.path.join(OUT, "credits.json")))
    for key, c in credits.items():
        if sys.argv[1:] and key not in sys.argv[1:]:
            continue
        if os.path.exists(os.path.join(OUT, key + ".jpg")) and not sys.argv[1:]:
            continue
        fetch(key, c["title"])
        print(key, "ok", flush=True)
        time.sleep(2)
