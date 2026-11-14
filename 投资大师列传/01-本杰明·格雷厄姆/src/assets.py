"""画面素材：用 Gemini 生成复古纪实风格的示意图。

规则：不出现可辨认的真人正脸（人物用背影、远景、虚焦或剪影），
不出现可读的文字和真实商标。第 01 集《本杰明·格雷厄姆》素材。
用法：python3 src/assets.py           # 只生成缺失的图，结果放在 assets/<id>.jpg
"""
import base64, json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets")

OLD = ("Authentic vintage {era} black-and-white documentary photograph, sepia toned, heavy film grain, "
       "soft vignette, slight scratches. ")
COLOR = ("Authentic {era} color documentary photograph, faded film colors, film grain, soft vignette. ")
MODERN = "Cinematic modern documentary photograph, natural light, shallow depth of field. "
RULES = (" Cinematic 16:9 composition with calm empty space in the lower-left third for captions. "
         "No readable text, no letters, no logos, no brand names. Any people are seen from behind, "
         "far away, in silhouette or out of focus; no clear identifiable faces.")

P = {
 "london":       (OLD, "1890s", "A Victorian-era London street with a small porcelain and china import shop, plates and vases in the window, horse carriage passing, gas lamps, fog."),
 "mourning":     (OLD, "1900s", "A dim hallway of a New York brownstone boarding house around 1903, a widow in black seen from behind carrying linens, a single oil lamp."),
 "panic1907":    (OLD, "1900s", "A large anxious crowd queueing outside a stone bank with columns in New York during the Panic of 1907, people in bowler hats seen from behind, policemen."),
 "boy_work":     (OLD, "1900s", "A teenage boy seen from behind carrying parcels along a New York street around 1908, a university building with columns in the distance."),
 "columbia":     (OLD, "1910s", "A university graduation ceremony on a campus with a domed neoclassical library in 1914, graduates in caps and gowns seen from behind, far away."),
 "wallst1914":   (OLD, "1910s", "A 1914 brokerage office near Wall Street, a young clerk seen from behind chalking stock prices on a huge blackboard, men in waistcoats watching."),
 "analyst1914":  (OLD, "1910s", "A 1910s office desk piled with thick company annual reports and ledgers, a young man in shirt sleeves seen from behind reading under a green desk lamp."),
 "mining":       (OLD, "1910s", "A copper mine in the American West around 1915, ore carts on rails, a smelter chimney with smoke, workers far away."),
 "ww1":          (OLD, "1910s", "A New York street crowd in 1917 during World War One, many flags hanging from buildings, soldiers marching far away, people seen from behind."),
 "office1923":   (OLD, "1920s", "A small 1920s Manhattan investment office, a typewriter, ledger books and a candlestick telephone on a wooden desk, window light."),
 "factory1920s": (OLD, "1920s", "A 1920s automobile assembly line with rows of early cars and workers seen from far away, chemical plant chimneys outside the windows."),
 "partners1926": (OLD, "1920s", "Two men in 1920s suits shaking hands across an office desk, seen from the side and out of focus, a window with the city skyline."),
 "archive":      (OLD, "1920s", "A government records archive room in Washington in the 1920s, tall shelves of bound filings, a man in a suit seen from behind leafing through a ledger."),
 "proxy1928":    (OLD, "1920s", "A 1920s company shareholders meeting in a wood-paneled hall, men in suits raising their hands to vote, seen from the back of the room."),
 "cigar":        (OLD, "1930s", "Close-up of a discarded cigar butt with a last wisp of smoke on a wet city sidewalk, shallow depth of field."),
 "classroom1928":(OLD, "1920s", "A university evening lecture hall in 1928, a blackboard covered in numbers, students in suits seen from behind, lamps glowing."),
 "notes1927":    (OLD, "1920s", "A young man seen from behind in the back row of a lecture hall writing notes rapidly with a fountain pen, close-up of a notebook filled with handwriting (not readable)."),
 "crash1929":    (OLD, "1920s", "A huge crowd gathered in the street outside a stock exchange building on a grey day in October 1929, people seen from behind, tense atmosphere."),
 "forbes1932":   (OLD, "1930s", "A stack of 1930s business magazines and newspapers on a newsstand, mastheads blurred and unreadable, a city street in the Great Depression behind."),
 "ledger":       (OLD, "1930s", "A ledger book and a slide rule under a desk lamp late at night in a 1930s office, a cold cup of coffee, deep shadows."),
 "book1934":     (OLD, "1930s", "A thick heavy hardcover book with a plain cloth cover lying on a wooden desk, a desk lamp illuminating it, stacks of papers."),
 "office1936":   (OLD, "1930s", "A 1930s Manhattan office floor with rows of desks, adding machines and filing cabinets, large windows overlooking skyscrapers."),
 "insurance1948":(OLD, "1940s", "A 1940s insurance company office with rows of typists at desks, seen from above at a distance, ceiling fans."),
 "boardroom":    (OLD, "1940s", "An empty 1940s corporate boardroom with a long polished table, leather chairs and water carafes, light from tall windows."),
 "book1949":     (OLD, "1940s", "An open book and a pair of reading glasses on an armchair in a 1940s living room, warm window light."),
 "mrmarket":     (OLD, "1940s", "A vintage stock ticker tape machine under a glass dome spilling paper tape, in a dim brokerage office."),
 "senate1955":   (OLD, "1950s", "A 1955 US Senate committee hearing room, a witness seen from behind at a table with microphones, senators out of focus on the dais."),
 "stamp":        (OLD, "1930s", "Old ledgers, letters and a red ink stamp pad on a desk, reading glasses, moody light."),
 "tire1919":     (OLD, "1910s", "An abandoned tire factory around 1919, empty workbenches, stacks of rubber tires, dusty light from broken windows."),
 "reader1949":   (OLD, "1940s", "A college dormitory room in 1949 at night, a young man seen from behind reading a thick book under a desk lamp."),
 "classroom1950":(OLD, "1950s", "A 1950s university classroom, a professor at the blackboard far away out of focus, a young student in the front row seen from behind."),
 "office_door":  (OLD, "1950s", "A young man in a suit and hat seen from behind knocking on the glass door of a closed downtown insurance office building on a quiet Saturday morning."),
 "office1954":   (OLD, "1950s", "Two men seen from a distance talking across a desk in a small 1950s New York investment office, stacks of stock manuals."),
 "baby1954":     (OLD, "1950s", "A 1950s wooden crib with a baby blanket near a sunlit window, a teddy bear, soft warm light."),
 "cocoa":        (OLD, "1950s", "A 1950s Brooklyn warehouse stacked high with burlap sacks of cocoa beans, a forklift, light beams through dusty air."),
 "analysts":     (OLD, "1950s", "A 1950s professional society meeting room full of men in suits seen from behind listening to a speaker far away."),
 "book_revise":  (COLOR, "1970s", "A desk with manuscript pages, handwritten corrections and two fountain pens, airmail letters, soft 1970s colors."),
 "provence":     (COLOR, "1970s", "A small town in Provence, France at dusk, stone houses and plane trees, a quiet square, warm fading light."),
 "speech1984":   (COLOR, "1980s", "A university auditorium in 1984 with a lectern on stage far away, audience seen from behind, warm stage lights."),
 "campus_now":   (MODERN, "", "A modern university campus with students seen from behind walking toward a classic library building, autumn trees."),
 "podium_old":   (OLD, "1950s", "An empty old wooden lecture podium in a classic university hall, a shaft of light from a tall window."),
 "library":      (MODERN, "", "A grand old library with tall bookshelves and reading lamps, slow dolly shot feeling, warm light."),
 "wallst_dusk":  (MODERN, "", "Wall Street in New York at dusk, office workers walking seen from behind, wet street reflections, golden light between skyscrapers."),
}


def prompt(k):
    style, era, body = P[k]
    return style.format(era=era) + body + RULES


def gen(k, model="gemini-3.1-flash-image"):
    path = os.path.join(OUT, k + ".jpg")
    if os.path.exists(path):
        return k, "skip"
    body = {"contents": [{"parts": [{"text": prompt(k)}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9"}}}
    for attempt in range(6):
        try:
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": "dummy"})
            r = json.load(urllib.request.urlopen(req, timeout=240))
            for p in r["candidates"][0]["content"]["parts"]:
                if "inlineData" in p:
                    open(path, "wb").write(base64.b64decode(p["inlineData"]["data"]))
                    return k, "ok"
        except Exception as e:
            err = e
        time.sleep(5 * (attempt + 1))
    return k, f"fail {err}"


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    keys = sys.argv[1:] or list(P)
    with ThreadPoolExecutor(4) as ex:
        for k, st in ex.map(gen, keys):
            print(k, st, flush=True)
