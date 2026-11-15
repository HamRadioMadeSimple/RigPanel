"""Draws RigPanel's icon: a light-blue tile with an analog meter (green-gold-red arc, needle).
Writes icon.png (256 px, with the name), icon_512.png and icon.ico (16-256 px;
the name appears from 64 px up). Run: python make_icon.py"""
import math
from PIL import Image, ImageDraw, ImageFont

BOLD_FONTS = ["DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "segoeuib.ttf", "arialbd.ttf", "Arial Bold.ttf"]


def bold_font(size):
    for f in BOLD_FONTS:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()

S = 1024  # draw big, scale down for clean edges


def tile(small=False, label=False):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # light vertical gradient inside a rounded square
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    top, bot = (236, 246, 255), (178, 214, 247)
    for y in range(S):
        t = y / S
        gd.line([(0, y), (S, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bot)) + (255,))
    mask = Image.new("L", (S, S), 0)
    m = 40
    ImageDraw.Draw(mask).rounded_rectangle([m, m, S - m, S - m], radius=200, fill=255)
    im.paste(grad, (0, 0), mask)
    d.rounded_rectangle([m, m, S - m, S - m], radius=200, outline=(46, 110, 190), width=48 if small else 26)

    # meter arc: green -> gold -> red
    cx, cy, r = (S // 2, 610, 380) if label else (S // 2, 760, 450)
    w = 190 if small else (110 if label else 130)
    box = [cx - r, cy - r, cx + r, cy + r]
    for a0, a1, col in ((205, 268, (34, 197, 94)), (268, 300, (234, 179, 8)), (300, 335, (229, 57, 53))):
        d.arc(box, a0, a1, fill=col, width=w)
    if not small:  # scale ticks (dropped at tiny sizes where they'd be mush)
        for a in range(205, 336, 13):
            ra = math.radians(a)
            x0, y0 = cx + (r - w - 10) * math.cos(ra), cy + (r - w - 10) * math.sin(ra)
            x1, y1 = cx + (r - w - 60) * math.cos(ra), cy + (r - w - 60) * math.sin(ra)
            d.line([(x0, y0), (x1, y1)], fill=(60, 90, 130), width=16)

    # needle and hub
    na = math.radians(286)
    nl = r - 20
    d.line([(cx, cy), (cx + nl * math.cos(na), cy + nl * math.sin(na))],
           fill=(30, 50, 90), width=90 if small else 54)
    hr = 120 if small else 85
    d.ellipse([cx - hr, cy - hr, cx + hr, cy + hr], fill=(30, 50, 90))
    if not small:
        d.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=(229, 57, 53))
    if label:  # the name under the meter, sized to fit the tile
        size = 200
        while True:
            f = bold_font(size)
            x0, y0, x1, y1 = d.textbbox((0, 0), "RigPanel", font=f)
            if x1 - x0 <= 800 or size <= 60:
                break
            size -= 4
        d.text((S // 2 - (x0 + x1) // 2, 845 - (y0 + y1) // 2), "RigPanel", font=f, fill=(24, 60, 120))
    return im


big, small, named = tile(False), tile(True), tile(False, label=True)
sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
# words only where they are readable (64 px and up); tiny sizes get the bold plain meter
frames = [(small if s <= 32 else big if s < 64 else named).resize((s, s), Image.LANCZOS) for s in sizes]
frames[-1].save("icon.png")
frames[3].save("icon_small.png")      # 32 px plain meter for small title bars
named.resize((512, 512), Image.LANCZOS).save("icon_512.png")
frames[-1].save("icon.ico", format="ICO", sizes=[(s, s) for s in sizes], append_images=frames[:-1])
# preview sheet
sheet = Image.new("RGBA", (760, 300), (255, 255, 255, 255))
dk = Image.new("RGBA", (760, 300), (40, 40, 40, 255))
x = 10
for f in frames:
    sheet.paste(f, (x, 20), f); dk.paste(f, (x, 20), f); x += f.width + 12
prev = Image.new("RGB", (760, 600)); prev.paste(sheet, (0, 0)); prev.paste(dk, (0, 300))
prev.save("icon_preview.png")
print("icon.png, icon.ico written")
