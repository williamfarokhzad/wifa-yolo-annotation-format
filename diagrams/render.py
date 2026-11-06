"""Regenerate the original diagrams with Pillow, optional for lesson readers."""
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit import parse_box

OUT = Path(__file__).resolve().parent
FG, QUIET, BG = "#172e36", "#3e5961", "#f4f8f8"
TEAL, RED = "#0e7476", "#a93035"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def text(draw, xy, value, size=34, color=FG, bold=False):
    font = ImageFont.truetype(str(FONT_DIR / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size)
    draw.text(xy, value, fill=color, font=font, anchor="lt")


def save(im, name):
    im.save(OUT / (name + ".webp"), "WEBP", quality=88, method=6)
    im.resize((600, im.height//2), Image.Resampling.LANCZOS).save(
        OUT / (name + "-600.webp"), "WEBP", quality=87, method=6)


def center():
    im = Image.new("RGB", (1200, 760), BG)
    d = ImageDraw.Draw(im)
    text(d, (55, 49), "Pixels to a YOLO label", 52, bold=True)
    text(d, (55, 126), "640 × 480 image  •  origin at the top left", 34, QUIET)
    ox, oy, s = 100, 220, .9
    d.rectangle((ox, oy, ox+640*s, oy+480*s), fill="#e1ecec", outline=QUIET, width=3)
    _, edges = parse_box("0 .375 .375 .25 .25", 2)
    l,t,r,b = (float(e)*n for e,n in zip(edges, (640,480,640,480)))
    d.rectangle((ox+l*s, oy+t*s, ox+r*s, oy+b*s), fill="#a9dddd", outline=TEAL, width=6)
    cx, cy = (ox+(l+r)*s/2, oy+(t+b)*s/2)
    d.line((cx-13,cy,cx+13,cy), fill=FG, width=4)
    d.line((cx,cy-13,cx,cy+13), fill=FG, width=4)
    text(d,(ox+l*s-45, oy+t*s-44),"(160, 120)",29)
    text(d,(ox+r*s-53, oy+b*s+17),"(320, 240)",29)
    text(d,(720, 228),"Center (240, 180)",35,bold=True)
    text(d,(720, 298),"240 / 640 = 0.375",34)
    text(d,(720, 356),"180 / 480 = 0.375",34)
    text(d,(720, 435),"Size 160 × 120",35,bold=True)
    text(d,(720, 505),"160 / 640 = 0.25",34)
    text(d,(720, 563),"120 / 480 = 0.25",34)
    text(d,(100, 691),"Class 0    →    0  0.375  0.375  0.25  0.25",35,TEAL,bold=True)
    save(im, "label-center")


def clip():
    im = Image.new("RGB", (1200, 640), BG)
    d = ImageDraw.Draw(im)
    text(d,(55,50),"A legal center can hide an illegal edge",48,bold=True)
    text(d,(55,119),"Zoom into the right side of the same 640 px frame.",35,QUIET)
    a, scale = 106, 3.65  # horizontal domain [440, 704]
    xx = lambda x: a+(x-440)*scale
    d.rectangle((a,217,xx(640),472),fill="#e1ecec")
    d.rectangle((xx(640),217,xx(704),472),fill="#f7e5e5")
    d.rectangle((xx(480),290,xx(672),405),outline=RED,width=7)
    d.rectangle((xx(480)+5,296,xx(640)-6,399),outline=TEAL,width=5)
    d.line((xx(640),207,xx(640),477),fill=FG,width=4)
    text(d,(a+12,231),"Inside image",33,TEAL,bold=True)
    text(d,(xx(640)+15,231),"Outside",32,RED,bold=True)
    for x in (480,640,672):
        d.line((xx(x),472,xx(x),493),fill=FG,width=3)
        text(d,(xx(x)-29,505),str(x),31)
    text(d,(a,572),"Original right edge: 672 px    •    Clipped right edge: 640 px",32)
    save(im, "label-edge")


if __name__ == "__main__":
    center()
    clip()
