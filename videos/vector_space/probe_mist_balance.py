"""Probe: mist mass balance top/bottom half + per-arm continuity + size/bright stats."""
import numpy as np
import render_vs as R

x, y, z, radius, color, bright, elong, wind, kind = R.build_scene()
mist = kind == 2
xm, ym, zm, rm, bm, em = x[mist], y[mist], z[mist], radius[mist], bright[mist], elong[mist]

angle = 25.0 + 6.0 * 3.1  # same as the still
sx, sy_down, depth = R.project(xm, ym, zm, angle)
t = R.smoothstep((depth / 1.15 + 1.0) * 0.5) ** 0.95
py = R.CY + sy_down * R.SCALE
px = R.CX + sx * R.SCALE
front = t >= 0.55

# multipliers mirror frame_image's mist branch
rr = rm * (0.85 + 0.30 * t) * np.where(front, 0.92, 1.10)
a = bm * (0.35 + 0.65 * t) * np.where(front, 0.75, 1.15)
mass = a * rr ** 2
top = py < R.CY

print(f"puffs n={len(py)}  top={int(top.sum())}  bottom={int((~top).sum())}")
print(f"RENDERED  mass top/bottom = {mass[top].sum() / mass[~top].sum():.2f}")
print(f"RENDERED  mean alpha top={a[top].mean():.3f} bottom={a[~top].mean():.3f}")
print(f"RENDERED  mean rr    top={rr[top].mean():.1f} bottom={rr[~top].mean():.1f}")

a0 = bm * (0.35 + 0.65 * t)
rr0 = rm * (0.85 + 0.30 * t)
m0 = a0 * rr0 ** 2
print(f"GEOMETRY-ONLY mass top/bottom = {m0[top].sum() / m0[~top].sum():.2f}")

n_arm, n_kn = 8, 12
# ribbon counts scale with each arm's winding (mirrors build_mist)
import math
arc_ref = math.hypot(R.ARM_LN, R.ARM_TH)
counts = [int(round(30 * math.hypot(R.ARM_LN, R.ARM_TH_J[a]) / arc_ref)) for a in range(n_arm)]
n_rib_total = sum(counts)
print(f"tiers: ribbon={n_rib_total} knot={n_arm * n_kn} total={len(py)}")
print("ARM_TH_J:", " ".join("%.2f" % v for v in R.ARM_TH_J))

# continuity: consecutive ribbon centres along each arm vs long-axis length
gaps = []
off = 0
for arm in range(n_arm):
    idx = slice(off, off + counts[arm])
    cx, cy = px[idx], py[idx]
    d = np.sqrt(np.diff(cx) ** 2 + np.diff(cy) ** 2)
    gaps.append(d)
    off += counts[arm]
gaps = np.concatenate(gaps)
long_axis = 2.0 * rr[:n_rib_total] * em[:n_rib_total]
print(
    "ribbon gap px: p50=%.1f p90=%.1f max=%.1f | long-axis p50=%.1f | covered(p90<axis)=%s"
    % (
        np.percentile(gaps, 50),
        np.percentile(gaps, 90),
        gaps.max(),
        np.percentile(long_axis, 50),
        bool(np.percentile(gaps, 90) < np.percentile(long_axis, 50)),
    )
)

print(f"radius: p10={np.percentile(rm,10):.1f} p50={np.percentile(rm,50):.1f} p90={np.percentile(rm,90):.1f} max={rm.max():.1f}")
print(f"elong : p10={np.percentile(em,10):.2f} p50={np.percentile(em,50):.2f} p90={np.percentile(em,90):.2f}")
print(f"bright: p10={np.percentile(bm,10):.3f} p50={np.percentile(bm,50):.3f} p90={np.percentile(bm,90):.3f}")

# hue spread of the mist palette actually used
cols = color[mist] if False else None
q = (px >= R.CX).astype(int) + 2 * (py >= R.CY).astype(int)
print("quadrant puff counts (TL,TR,BL,BR) =",
      int((q == 2).sum()), int((q == 3).sum()), int((q == 0).sum()), int((q == 1).sum()))
