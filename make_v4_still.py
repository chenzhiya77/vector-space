import os

from PIL import Image, ImageDraw

import render_vs as R

R.V3 = True
R.V4 = True


def main():
    x, y, z, radius, color, bright, elong, wind, kind = R.build_scene()
    img = R.frame_image(x, y, z, radius, color, bright, elong, wind, kind, time_s=3.1)
    out = os.path.join(R.OUT, "vs_space_still_v4.png")
    img.save(out)

    old = Image.open(os.path.join(R.OUT, "vs_space_still_v3.png")).convert("RGB")
    sheet = Image.new("RGB", (R.W, R.H * 2 + 6), (0, 0, 0))
    sheet.paste(old, (0, 0))
    sheet.paste(img, (0, R.H + 6))
    draw = ImageDraw.Draw(sheet)
    draw.text((8, 5), "v3 - nucleus + bg starfield + mist taper", fill=(235, 235, 235))
    draw.text(
        (8, R.H + 11),
        "v4 - arm-weighted stars + rim fade + radial colour + dust lanes",
        fill=(235, 235, 235),
    )
    sheet.save(os.path.join(R.OUT, "vs_v4_ab.png"))
    print("saved", out)


if __name__ == "__main__":
    main()
