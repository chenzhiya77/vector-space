import os

import render_vs as R

x, y, z, radius, color, bright, elong, wind, kind = R.build_scene()

img = R.frame_image(x, y, z, radius, color, bright, elong, wind, kind, time_s=3.1)
out = os.path.join(R.OUT, "vs_space_still_anchor.png")
img.save(out)
print("saved", out)
