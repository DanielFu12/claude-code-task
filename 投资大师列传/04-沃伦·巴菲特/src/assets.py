"""画面素材：用 Gemini 生成复古纪实风格的示意图。

规则：不出现可辨认的真人正脸（人物用背影、远景、虚焦或剪影），
不出现可读的文字和真实商标；成片左下角会标注「画面为 AI 生成示意」。
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
 "grocery":   (OLD, "1930s", "A small family grocery store on a quiet street in Omaha, Nebraska, wooden shelves of canned goods seen through the window, an old delivery truck parked outside."),
 "coke":      (OLD, "1930s", "Close-up of six glass soda bottles in a wooden crate on a porch step, a boy's hands counting nickels beside them, summer light."),
 "paperboy":  (OLD, "1940s", "A teenage paperboy seen from behind riding a bicycle with a canvas bag full of newspapers down a tree-lined Washington D.C. street at dawn."),
 "pinball":   (OLD, "1940s", "A 1940s pinball machine standing in the corner of an old-fashioned barbershop, barber chairs and mirrors, warm light."),
 "book":      (OLD, "1940s", "An old thick hardcover investment book lying open on a wooden desk under a desk lamp at night, a young man's hands and a pencil, stacks of financial newspapers."),
 "classroom": (OLD, "1950s", "A university lecture hall at Columbia in the 1950s, students in suits seen from behind, an older professor at a chalkboard covered in numbers, out of focus."),
 "office_door":(OLD, "1950s", "A young man in a suit and hat seen from behind knocking on the glass door of a closed downtown insurance office building on a quiet Saturday in Washington D.C."),
 "wedding":   (OLD, "1950s", "A small 1950s church wedding seen from the back of the aisle, bride and groom far away at the altar, soft window light."),
 "partners":  (OLD, "1950s", "A modest living room in Omaha, a typed partnership agreement and a fountain pen on a coffee table, a few relatives' hands around it, warm lamp light."),
 "dinner":    (OLD, "1950s", "Two men in suits talking animatedly at a dinner table in a 1950s Omaha restaurant, seen from a distance in soft focus, candles and glasses."),
 "textile":   (OLD, "1960s", "Interior of an old New England textile mill, rows of looms and spools, dusty light beams from tall windows, almost empty."),
 "offer":     (OLD, "1960s", "Close-up of a typed corporate tender offer letter on a desk, numbers blurred, a red pencil circling a figure, a cup of coffee."),
 "salad_oil": (OLD, "1960s", "Huge industrial storage tanks at a New Jersey dock, puddles, overcast sky, newspaper on the ground blown by wind."),
 "annual":    (OLD, "1960s", "A stack of plain old company annual reports and ledgers on a wooden desk, a desk lamp and reading glasses."),
 "insurance": (OLD, "1960s", "An insurance company office in the 1960s with rows of typists and filing cabinets, seen from above at a distance."),
 "candy":     (COLOR, "1970s", "A charming 1970s candy shop interior with black and white checkered floor and glass display cases of boxed chocolates, warm light."),
 "newsroom":  (OLD, "1970s", "A busy 1970s newspaper newsroom with typewriters and printing press rolls, reporters seen from behind, smoke and lamp light."),
 "crash74":   (OLD, "1970s", "A gloomy 1970s stock exchange trading floor almost empty, paper tickets scattered on the floor, tired traders seen from behind."),
 "geico_dark":(COLOR, "1970s", "A 1970s office building at dusk with most windows dark, rain on the street, a single lit window."),
 "meeting":   (COLOR, "1980s", "A shareholders meeting in a small hall in the late 1970s, two men at a long table on stage far away, audience seen from behind."),
 "furniture": (COLOR, "1980s", "A giant furniture warehouse store in Nebraska in the 1980s, rows of sofas and lamps, a handshake between two people in the foreground, faces out of frame."),
 "tv":        (COLOR, "1980s", "A 1980s television broadcast studio with large cameras and studio lights, crew seen from behind."),
 "mill_dark": (OLD, "1980s", "An abandoned textile mill interior with silent looms under dust covers, the last light bulbs switching off."),
 "soda":      (COLOR, "1980s", "Close-up of a hand holding a classic curved glass cola bottle with condensation, red background bokeh, no label text."),
 "razor":     (COLOR, "1980s", "Vintage 1980s still life of a men's safety razor, shaving brush and foam on a bathroom shelf, soft morning light."),
 "bank":      (COLOR, "1990s", "A crowd queueing outside a classic stone bank building with columns in 1990 California, overcast, people seen from behind."),
 "hearing":   (COLOR, "1990s", "A US congressional hearing room in 1991, a witness table with microphones seen from behind the witness, lawmakers out of focus on the dais."),
 "magazine":  (COLOR, "1990s", "A stack of glossy business magazines on a newsstand in 1993, covers blurred and unreadable, city street behind."),
 "geico_new": (COLOR, "1990s", "A modern insurance company headquarters in the 1990s with glass facade under a blue sky, flags."),
 "dotcom":    (COLOR, "1990s", "A late-1990s tech office with glowing CRT monitors showing rising stock charts, young workers celebrating seen from behind, neon light."),
 "charity":   (MODERN, "", "A quiet signing ceremony table with a fountain pen and documents, three people standing around it seen from the shoulders down, library background."),
 "lehman":    (MODERN, "", "Wall Street in September 2008 at dusk, office workers carrying cardboard boxes out of a skyscraper, seen from behind, wet street reflections."),
 "rich":      (MODERN, "", "A dramatic low-angle view of a Manhattan skyscraper at golden hour, gold light reflecting on glass."),
 "byd":       (MODERN, "", "A modern electric vehicle and battery factory in Shenzhen, robotic arms and assembly line, clean bright lighting."),
 "railroad":  (MODERN, "", "Aerial drone shot of a very long freight train crossing endless golden American prairie at sunset."),
 "phone":     (MODERN, "", "A smartphone lying on a wooden table next to a cup of coffee and a printed annual report, soft morning light, screen dark."),
 "tokyo":     (MODERN, "", "Tokyo financial district skyline at night with a port and cargo ships in the foreground."),
 "stamp":     (MODERN, "", "Old paper letters and annual shareholder letters spread on a desk, reading glasses, a red ink stamp pad, moody light."),
 "disney":    (COLOR, "1960s", "A 1960s amusement park with a castle-like silhouette in the distance and families walking, faded colors, no characters."),
 "airplane":  (COLOR, "1980s", "A propeller-era-style commercial airliner parked on a rainy tarmac in the late 1980s, grey sky, puddles."),
 "shoes":     (COLOR, "1990s", "A closed shoe factory in Maine, empty workbenches and leather scraps, dust, gloomy light."),
 "reinsure":  (COLOR, "1990s", "A corporate office tower in Connecticut on a grey winter day, empty plaza."),
 "oil":       (MODERN, "", "Oil pumpjacks silhouetted against a stormy red sunset sky."),
 "mainframe": (COLOR, "1980s", "Rows of large mainframe computer cabinets in a dim data center, blinking lights, cold blue tone."),
 "supermarket":(MODERN, "", "A British supermarket aisle at night with shelves half empty, cold fluorescent light."),
 "ketchup":   (MODERN, "", "Still life of a glass ketchup bottle and processed food packages on a grey table, harsh light, muted colors."),
 "castparts": (MODERN, "", "An aerospace parts foundry with glowing molten metal and turbine blades on racks."),
 "terminal":  (MODERN, "", "An empty airport terminal during the 2020 pandemic, rows of empty seats, planes parked outside the window."),
 "warehouse": (MODERN, "", "A huge modern e-commerce warehouse with conveyor belts and robots, and a glowing data center, split atmosphere."),
 "farewell":  (MODERN, "", "Two elderly men in suits sitting side by side at a long table on a stage, seen from far behind the audience, spotlight, slightly faded."),
 "cash":      (MODERN, "", "Stacks of US dollar bills and gold bars in a vault, dramatic light."),
 "arena":     (MODERN, "", "A huge arena full of thousands of shareholders standing and applauding, seen from the back of the hall, stage lights."),
 "house":     (MODERN, "", "A modest two-story stucco house with a big tree on a quiet Omaha street in autumn, warm late afternoon light."),
 "crowd":     (MODERN, "", "An elderly man in a suit seen from behind walking through a crowd of admirers holding up phones in an exhibition hall, warm bokeh."),
 "podium":    (MODERN, "", "An elderly man seen from behind raising one hand to wave at a large audience from a stage, warm spotlight."),
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
