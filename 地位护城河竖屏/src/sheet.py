import sys, glob
from PIL import Image
fs = sys.argv[2:]; w = 360; h = 640
im = Image.new('RGB', (w * min(4, len(fs)), h * ((len(fs) + 3) // 4)))
for i, f in enumerate(fs): im.paste(Image.open(f).resize((w, h)), ((i % 4) * w, (i // 4) * h))
im.save(sys.argv[1])
