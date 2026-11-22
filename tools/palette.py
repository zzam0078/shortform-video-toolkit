"""Suggest caption and motion-graphics colors that match a video.

Samples 8 frames, finds the dominant colors, and proposes an accent color (the most
vivid color in the footage, lifted), a secondary accent, a dark color, and how strong
a background scrim should be for readable text.

Usage:
    python palette.py input.mp4 [--samples 8]

Requires: ffmpeg on PATH, Pillow.
"""
import argparse
import colorsys
import os
import subprocess
import tempfile

from PIL import Image


def to_hex(r, g, b):
    return "#%02X%02X%02X" % (r, g, b)


def lift(c, s=0.75, l=0.62):
    r, g, b = colorsys.hls_to_rgb(c["h"], l, max(c["s"], s))
    return to_hex(int(r * 255), int(g * 255), int(b * 255))


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True).stdout
    return float(out.strip() or 10)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--samples", type=int, default=8)
    a = ap.parse_args()

    tmp = tempfile.mkdtemp()
    rate = a.samples / max(duration(a.video), 1)
    subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-vf", f"fps={rate},scale=160:-1",
                    os.path.join(tmp, "%02d.png")], check=True)
    px = []
    for f in sorted(os.listdir(tmp)):
        px += list(Image.open(os.path.join(tmp, f)).convert("RGB").getdata())
    img = Image.new("RGB", (len(px), 1))
    img.putdata(px)
    q = img.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:24]

    cols = []
    for n, i in sorted(q.getcolors(), reverse=True):
        r, g, b = pal[i * 3:i * 3 + 3]
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        cols.append(dict(hex=to_hex(r, g, b), share=n / len(px), h=h, l=l, s=s))

    vivid = max(cols, key=lambda c: c["s"] * (1 - abs(c["l"] - 0.5)))
    dark = min(cols, key=lambda c: c["l"])
    lightness = sum(c["l"] * c["share"] for c in cols)

    print("dominant:", ", ".join(f"{c['hex']} ({c['share']:.0%})" for c in cols[:5]))
    print("footage is", "bright -> scrim opacity 0.75" if lightness > 0.55 else "dark -> scrim opacity 0.5")
    print(f"accent   {lift(vivid)}")
    print(f"accent2  {lift(vivid, 0.6, 0.75)}")
    print(f"dark     {dark['hex']}")


if __name__ == "__main__":
    main()
