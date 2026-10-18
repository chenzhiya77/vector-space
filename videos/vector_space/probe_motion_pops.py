"""Probe: depth-threshold crossings during the 15s clip (front/back pops)."""
import numpy as np
import render_vs as R

x, y, z, radius, color, bright, elong, wind, kind = R.build_scene()
mist = kind == 2
big = radius > 5.0  # heroes/supers/leads: visible blur-level change

FPS, N = 24, 360
prev = None
mist_cross = 0
big_cross = 0
cross_frames = []
for k in range(N):
    tt = k / FPS
    sx, sy, depth = R.project(x, y, z, R.spin_angles(x, z, tt))
    t = R.smoothstep((depth / 1.15 + 1.0) * 0.5) ** 0.95
    front = t >= 0.55
    if prev is not None:
        flip = front != prev
        mc = int((flip & mist).sum())
        bc = int((flip & big).sum())
        mist_cross += mc
        big_cross += bc
        if mc or bc:
            cross_frames.append((k, mc, bc))
    prev = front

print(f"clip: {N} frames @ {FPS}fps")
print(f"mist crossings: {mist_cross} total over clip ({len(cross_frames)} frames affected)")
print(f"big-star crossings: {big_cross} total")
print("first 8 crossing events:", cross_frames[:8])
# jump magnitudes at the boundary
print("mist alpha multiplier: back=1.15 front=0.75 -> jump factor %.2f" % (0.75 / 1.15))
print("mist radius multiplier: back=1.10 front=0.92 -> jump factor %.2f" % (0.92 / 1.10))
print("star blur: far=0.85 near=0.35 px")
