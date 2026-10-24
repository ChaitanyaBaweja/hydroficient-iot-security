"""Slack promo GIF for the AI Swarm Attacks workshop.

Tells a readable story with a changing caption: a normal fleet -> an attacker
turning devices a few at a time -> pressure collapsing while status still reads
NOMINAL -> ALARM. Ops dashboard style (echoes the reference mockup).
"""
import math
import random
from PIL import Image, ImageDraw, ImageFont

W, H = 860, 480
BG = (10, 14, 22)
PANEL = (17, 24, 36)
LINE = (34, 44, 60)
FG = (233, 239, 248)
DIM = (150, 163, 183)
ACCENT = (88, 166, 255)
OK = (54, 179, 94)
CRIT = (231, 92, 74)
CALM = (38, 96, 150)       # a normal regulator tile
CALM_O = (56, 123, 184)
HOT = (120, 40, 36)        # a turned regulator tile
HOT_O = (231, 92, 74)

FD = "C:/Windows/Fonts/"
f_brand = ImageFont.truetype(FD + "arialbd.ttf", 18)
f_meta = ImageFont.truetype(FD + "arial.ttf", 13)
f_cap = ImageFont.truetype(FD + "arialbd.ttf", 26)
f_label = ImageFont.truetype(FD + "arialbd.ttf", 14)
f_small = ImageFont.truetype(FD + "arial.ttf", 13)
f_pill = ImageFont.truetype(FD + "arialbd.ttf", 15)
f_big = ImageFont.truetype(FD + "consolab.ttf", 50)
f_psi = ImageFont.truetype(FD + "consolab.ttf", 34)
f_title = ImageFont.truetype(FD + "arialbd.ttf", 19)

# Fleet grid geometry: 10 x 8 = 80 tiles.
COLS, ROWS = 10, 8
GX, GY, GW, GH = 28, 150, 360, 268
cw, chh = GW / COLS, GH / ROWS
ts = min(cw, chh) - 6
N = COLS * ROWS

# Spread order: grow outward from a seed so the takeover visibly ripples.
seed_c, seed_r = 3, 5
rng = random.Random(7)
order = sorted(range(N), key=lambda i: (
    ((i % COLS) - seed_c) ** 2 + ((i // COLS) - seed_r) ** 2 + rng.uniform(0, 6)))


def ease(x):
    return x * x * (3 - 2 * x)


def pill(d, cx_right, y, text, fg, bg, bo):
    w = d.textlength(text, font=f_pill) + 26
    x = cx_right - w
    d.rounded_rectangle([x, y, x + w, y + 28], 4, fill=bg, outline=bo, width=1)
    d.ellipse([x + 10, y + 11, x + 17, y + 18], fill=fg)
    d.text((x + 23, y + 6), text, font=f_pill, fill=fg)


def gauge(d, cx, cy, R, p, pmax=80):
    # Upper semicircle, west(low)->east(high). Red zone = below 20 psi.
    def ang(v):
        return 180 + (max(0, min(pmax, v)) / pmax) * 180
    box = [cx - R, cy - R, cx + R, cy + R]
    d.arc(box, 180, 360, fill=LINE, width=14)
    d.arc(box, 180, ang(20), fill=CRIT, width=14)            # danger zone
    d.arc(box, ang(20), 360, fill=(46, 92, 140), width=14)   # safe zone
    a = math.radians(ang(p))
    nx, ny = cx + (R - 6) * math.cos(a), cy + (R - 6) * math.sin(a)
    needle = CRIT if p < 25 else FG
    d.line([cx, cy, nx, ny], fill=needle, width=4)
    d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=needle)
    # 20 psi danger label at the red/safe boundary
    am = math.radians(ang(20))
    lx, ly = cx + (R + 14) * math.cos(am), cy + (R + 14) * math.sin(am)
    d.text((lx - 16, ly - 6), "20", font=f_small, fill=CRIT)


def frame(caption, comp, pressure, alarm):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Header
    d.text((28, 22), "HYDROFICIENT", font=f_brand, fill=FG)
    d.text((170, 26), "FLEET OPS \u00b7 80 REGULATORS \u00b7 us-east-2", font=f_meta, fill=DIM)
    if alarm:
        pill(d, W - 28, 20, "ALARM", (255, 255, 255), (74, 22, 20), CRIT)
    else:
        pill(d, W - 28, 20, "SYSTEMS NOMINAL", OK, (16, 38, 25), (31, 90, 55))

    # Caption (the story)
    d.text((28, 62), caption, font=f_cap, fill=FG)
    d.line([28, 108, W - 28, 108], fill=LINE, width=1)

    # Fleet grid
    hot = set(order[:comp])
    for i in range(N):
        r, c = divmod(i, COLS)
        x, y = GX + c * cw, GY + r * chh
        fill, out = (HOT, HOT_O) if i in hot else (CALM, CALM_O)
        d.rounded_rectangle([x, y, x + ts, y + ts], 3, fill=fill, outline=out, width=1)
    d.text((GX, GY - 22), "THE FLEET", font=f_label, fill=DIM)

    # Right column
    rx = 440
    d.text((rx, GY - 22), "COMPROMISED", font=f_label, fill=DIM)
    d.text((rx, GY - 2), f"{comp:02d}", font=f_big, fill=(CRIT if comp else FG))
    d.text((rx + d.textlength(f'{comp:02d}', font=f_big) + 12, GY + 26),
           "/ 80", font=f_psi, fill=DIM)

    d.text((rx, 268), "LINE PRESSURE", font=f_label, fill=DIM)
    gauge(d, rx + 150, 378, 86, pressure)
    col = CRIT if pressure < 25 else FG
    d.text((rx + 110, 392), f"{pressure:>2.0f}", font=f_psi, fill=col)
    d.text((rx + 110 + d.textlength(f'{pressure:>2.0f}', font=f_psi) + 6, 402),
           "psi", font=f_small, fill=DIM)

    # Title / date bar
    d.rectangle([0, H - 44, W, H], fill=PANEL)
    d.text((28, H - 33), "AI SWARM ATTACKS", font=f_title, fill=ACCENT)
    d.text((28 + d.textlength("AI SWARM ATTACKS", font=f_title) + 14, H - 31),
           "Defending an IoT Fleet", font=f_meta, fill=FG)
    date = "Tue Nov 3  \u00b7  Live on Zoom"
    d.text((W - 28 - d.textlength(date, font=f_small), H - 30), date, font=f_small, fill=DIM)
    return img


# Storyboard: (caption, frames, comp_start, comp_end, p_start, p_end, alarm)
PHASES = [
    ("A fleet of 80 water regulators. All normal.", 9, 0, 0, 58, 58, False),
    ("An attacker turns them \u2014 a few at a time.", 16, 0, 22, 58, 49, False),
    ("Every device still checks out. Status: nominal.", 15, 22, 46, 49, 33, False),
    ("Pressure is collapsing \u2014 and nothing alarmed.", 13, 46, 66, 33, 20, False),
    ("ALARM \u2014 if you watch the whole fleet at once.", 14, 66, 70, 20, 17, True),
]

frames = []
for cap, n, c0, c1, p0, p1, alarm in PHASES:
    for k in range(n):
        e = ease(k / max(1, n - 1))
        comp = round(c0 + (c1 - c0) * e)
        pres = p0 + (p1 - p0) * e
        a = alarm and (k % 2 == 0)        # blink during the alarm phase
        frames.append(frame(cap, comp, pres, a))
for _ in range(7):
    frames.append(frame(PHASES[-1][0], 70, 17, True))

out = "C:/Users/chait/Dropbox/Freelance/Upwork Contracts/Extern/Hydroficient/hydroficient-iot-security/demo/swarm/brochure/swarm-promo.gif"
frames[0].save(out, save_all=True, append_images=frames[1:], duration=150, loop=0, optimize=True)
print("wrote", out, "frames", len(frames))
