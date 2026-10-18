"""Vector-space point cloud: glowing coloured star points."""

import math
import os

import numpy as np
from PIL import Image, ImageChops, ImageFilter

OUT = os.path.dirname(os.path.abspath(__file__))
W, H = 1280, 460
SS = 3
CX, CY = W / 2, H / 2
SCALE = 575.0

PHI = math.radians(13.0)
N_CORE = 3800

# star palette: blue / white / orange / amber
PAL = ((150, 190, 255), (255, 250, 242), (255, 182, 112), (255, 142, 72))

# log-spiral arm: r = 0.22 * (1.02/0.22)**u — starts at 0.22 so the pitch (~29°) bends visibly
ARM_TH = 2.8
ARM_LN = math.log(1.02 / 0.22)

# rotation law: eased start + differential spin — inner rings orbit faster than outer
# ones (real galaxies shear; the old rigid body rotated every point at one rate).
# Anchored on the frozen still: frame at T_REF is exactly angle A_REF for every point.
A_REF = 43.6  # deg, the approved still angle
T_REF = 3.1  # s, the approved still moment
V_MAX = 6.0  # deg/s at the reference ring (one lap per 60 s)
EASE_T = 1.25  # s to ramp from rest to full speed
SHEAR_K = 0.22  # inner/outer speed split, sized to stay subtle over 15 s
R_REF = 0.62

# preview switch: v2 output stays the default; v3 adds the nucleus, a background
# starfield and the mist taper
V3 = False
# v4 = v3 + arm-weighted stars, disk-edge fade, radial colour and dust lanes
V4 = False

def master_angle(time_s):
    t = max(0.0, float(time_s))
    if t <= EASE_T:
        u = t / EASE_T
        return V_MAX * EASE_T * (u ** 3 - 0.5 * u ** 4)
    return V_MAX * (t - 0.5 * EASE_T)


def spin_angles(x, z, time_s):
    r = np.hypot(x, z)
    f = 1.0 + SHEAR_K * (R_REF - r)
    return A_REF + f * (master_angle(time_s) - master_angle(T_REF))

# structural draws on their own stream (build_mist's texture stream stays comparable):
# 1-2 arms coil differently from the rest
_STRUCT_RNG = np.random.default_rng(133)
ARM_TH_J = np.full(8, ARM_TH)
for _a in _STRUCT_RNG.choice(8, int(_STRUCT_RNG.integers(1, 3)), replace=False):
    ARM_TH_J[_a] = ARM_TH + float(_STRUCT_RNG.choice([-1.0, 1.0])) * float(
        _STRUCT_RNG.uniform(0.55, 0.75)
    )
# arm colour system: two base hues dominate (blue-purple reflection / pink-magenta emission);
# every other arm is a transition blend or an enhanced take of those two. Random per arm,
# adjacent arms may match.
COL_BLUE = np.array([95.0, 112.0, 240.0])
COL_PINK = np.array([235.0, 72.0, 158.0])
ARM_T = np.empty(8)
ARM_ENH = np.zeros(8, dtype=bool)
for _a in range(8):
    _r = _STRUCT_RNG.random()
    if _r < 0.35:
        ARM_T[_a] = 0.0
    elif _r < 0.70:
        ARM_T[_a] = 1.0
    elif _r < 0.88:
        ARM_T[_a] = float(_STRUCT_RNG.uniform(0.25, 0.75))  # transition blend
    else:
        ARM_T[_a] = float(_STRUCT_RNG.integers(0, 2))  # enhanced take of one base
        ARM_ENH[_a] = True

# star blob sprites: smooth gaussian core melting into a compact halo (no ring steps)
_SPRITE_CACHE = {}


def _star_sprite(rr, col, peak, spread, elong=1.0, ang_deg=0.0, wf=None):
    key = (
        round(rr * 2.0),
        round(spread * 4.0),
        col,
        round(peak * 256.0),
        round(elong * 4.0),
        round((ang_deg % 180.0) / 2.5),
        None if wf is None else round(wf * 100.0),
    )
    s = _SPRITE_CACHE.get(key)
    if s is not None:
        return s
    half = max(3, int(math.ceil(rr * spread * max(1.0, elong))))
    size = half * 2 + 1
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    dx, dy = xx - half, yy - half
    a = math.radians(ang_deg)
    ca, sa = math.cos(a), math.sin(a)
    xr = dx * ca + dy * sa
    yr = -dx * sa + dy * ca
    d = np.sqrt((xr / max(rr * elong, 0.55)) ** 2 + (yr / max(rr, 0.55)) ** 2)
    prof = 0.72 * np.exp(-4.2 * d * d) + 0.20 * np.exp(-0.95 * d * d) + 0.08 * np.exp(-0.16 * d * d)
    prof = prof * (d <= spread)
    alpha = np.clip(prof * peak, 0.0, 1.0) * 255.0
    # big stars keep their colour into the core; dust stays near-white points
    wfv = min(1.0, max(0.35, 1.0 - 0.055 * rr)) if wf is None else wf
    wgt = np.clip((1.0 - 0.85 * d) * wfv, 0.0, 1.0)[..., None]
    rgb = 255.0 * wgt + np.array(col, dtype=np.float64) * (1.0 - wgt)
    arr = np.concatenate([rgb.astype(np.uint8), alpha.astype(np.uint8)[..., None]], axis=2)
    s = Image.fromarray(arr, "RGBA")
    _SPRITE_CACHE[key] = s
    return s


def build_leads():
    """Focal stars: compositional anchors at the golden-section points of the still angle,
    deliberately a notch above every random star. Live in the disk and rotate with it."""
    ar = math.radians(A_REF)
    ca, sa = math.cos(ar), math.sin(ar)
    sp, cp = math.sin(PHI), math.cos(PHI)
    # (screen px, screen py, radius, bright, colour) at the still angle; depth set to mid
    specs = (
        (791.0, 168.0, 42.0, 4.0, (255.0, 246.0, 228.0)),  # protagonist: upper golden point
        (452.0, 292.0, 28.0, 3.1, (255.0, 232.0, 196.0)),  # companion: lower golden point
    )
    n = len(specs)
    x = np.empty(n)
    y = np.empty(n)
    z = np.empty(n)
    radius = np.empty(n)
    bright = np.empty(n)
    color = np.empty((n, 3))
    for i, (px_, py_, rad, br, col) in enumerate(specs):
        x2 = (px_ - CX) / SCALE
        sy = (py_ - CY) / SCALE
        y[i] = -sy * cp  # depth = 0 (mid) via the tilt term
        z2 = sy * sp
        x[i] = x2 * ca - z2 * sa
        z[i] = x2 * sa + z2 * ca
        radius[i] = rad
        bright[i] = br
        color[i] = col
    return x, y, z, radius, color, bright


def make_bg():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    k = np.clip(0.55 * (xx / W) + 0.45 * (1.0 - yy / H), 0.0, 1.0)
    c0 = np.array([9.0, 22.0, 34.0])
    c1 = np.array([26.0, 56.0, 72.0])
    acc = c0 + (c1 - c0) * k[..., None]
    r2 = ((xx - W * 0.62) / (W * 0.75)) ** 2 + ((yy - H * 0.35) / (H * 1.1)) ** 2
    acc *= (1.0 - 0.18 * np.clip(r2, 0.0, 1.0))[..., None]
    acc += np.random.default_rng(5).normal(0.0, 1.0, (H, W, 1))
    return Image.fromarray(np.clip(acc, 0, 255).astype(np.uint8), "RGB")


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def build_cloud(version=2):
    if version == 4:
        return _build_cloud_v4()
    rng = np.random.default_rng(7)
    u = rng.random(N_CORE)
    r = u ** 0.62
    th = rng.random(N_CORE) * 2.0 * math.pi
    x = r * np.cos(th)
    z = r * np.sin(th)
    y = rng.normal(0.0, 0.045, N_CORE)
    rs = np.random.default_rng(21)
    uu = rs.random(N_CORE)
    radius = 0.9 + 0.8 * uu + 5.0 * uu ** 20
    cu = rs.random(N_CORE)
    pal = PAL
    color = np.empty((N_CORE, 3))
    color[cu < 0.32] = pal[0]
    color[(cu >= 0.32) & (cu < 0.72)] = pal[1]
    color[(cu >= 0.72) & (cu < 0.92)] = pal[2]
    color[cu >= 0.92] = pal[3]
    bright = 0.32 + 1.05 * rs.random(N_CORE) ** 2.2
    # hero tier: 22 stars that punch through — hotter core, wider halo
    hero = np.zeros(N_CORE, dtype=bool)
    hero[rs.choice(N_CORE, 22, replace=False)] = True
    radius[hero] = rs.uniform(10.5, 13.5, int(hero.sum()))
    bright[hero] = rs.uniform(1.9, 2.8, int(hero.sum()))
    # super tier: 6 stars one notch bigger than the heroes
    sup = np.zeros(N_CORE, dtype=bool)
    sup[rs.choice(np.flatnonzero(~hero), 6, replace=False)] = True
    radius[sup] = rs.uniform(16.0, 20.0, int(sup.sum()))
    bright[sup] = rs.uniform(2.0, 3.0, int(sup.sum()))
    return x, y, z, radius, color, bright


def _radial_edge(r):
    return np.exp(-np.clip((r - 0.80) / 0.09, 0.0, None) ** 2)


def _build_cloud_v4():
    """v4 cloud: most stars ride a wide arm haze; the rim thins and the disk cools."""
    rng = np.random.default_rng(107)
    n_arm = int(round(N_CORE * 0.58))
    n_disk = N_CORE - n_arm

    arm = rng.integers(0, 8, n_arm)
    u_a = rng.random(n_arm) ** 0.88
    th_a = (
        arm * (2.0 * math.pi / 8.0)
        + ARM_TH_J[arm] * u_a
        + rng.normal(0.0, 0.13, n_arm)
    )
    r_a = 0.22 * np.exp(ARM_LN * u_a) * (1.0 + rng.normal(0.0, 0.040, n_arm))
    y_a = rng.normal(0.0, 0.036, n_arm)

    u_d = rng.random(n_disk)
    r_d = u_d ** 0.62
    th_d = rng.random(n_disk) * 2.0 * math.pi
    y_d = rng.normal(0.0, 0.045, n_disk)

    # density thinning + dimming at the rim
    edge_a = _radial_edge(r_a)
    keep_a = rng.random(n_arm) < (0.30 + 0.70 * edge_a)
    edge_d = _radial_edge(r_d)
    keep_d = rng.random(n_disk) < (0.30 + 0.70 * edge_d)
    r_a, th_a, y_a, edge_a, arm = (
        r_a[keep_a],
        th_a[keep_a],
        y_a[keep_a],
        edge_a[keep_a],
        arm[keep_a],
    )
    r_d, th_d, y_d, edge_d = r_d[keep_d], th_d[keep_d], y_d[keep_d], edge_d[keep_d]

    n_a = r_a.size
    n_d = r_d.size
    n = n_a + n_d
    x = np.concatenate([r_a * np.cos(th_a), r_d * np.cos(th_d)])
    z = np.concatenate([r_a * np.sin(th_a), r_d * np.sin(th_d)])
    y = np.concatenate([y_a, y_d])
    edge = np.concatenate([edge_a, edge_d])

    cu_a = rng.random(n_a)
    ca = np.empty((n_a, 3))
    ca[cu_a < 0.55] = PAL[0]
    ca[(cu_a >= 0.55) & (cu_a < 0.93)] = PAL[1]
    ca[(cu_a >= 0.93) & (cu_a < 0.985)] = PAL[2]
    ca[cu_a >= 0.985] = PAL[3]

    cu_d = rng.random(n_d)
    blue = 0.22 + 0.38 * smoothstep((r_d - 0.28) / 0.55)
    orange = 0.26 * (1.0 - smoothstep((r_d - 0.20) / 0.45))
    amber = 0.07 * (1.0 - smoothstep((r_d - 0.15) / 0.40))
    cd = np.empty((n_d, 3))
    cd[:] = PAL[1]
    cd[cu_d < blue] = PAL[0]
    cd[(cu_d >= blue) & (cu_d < blue + orange)] = PAL[2]
    cd[(cu_d >= blue + orange) & (cu_d < blue + orange + amber)] = PAL[3]
    color = np.concatenate([ca, cd])

    rs = np.random.default_rng(121)
    uu = rs.random(n)
    radius = 0.9 + 0.8 * uu + 5.0 * uu ** 20
    radius[:n_a] *= 0.90
    bright = 0.32 + 1.05 * rs.random(n) ** 2.2
    bright[:n_a] *= 0.85
    bright *= 0.45 + 0.55 * edge

    hero = np.zeros(n, dtype=bool)
    hero[rs.choice(n, 22, replace=False)] = True
    radius[hero] = rs.uniform(10.5, 13.5, int(hero.sum()))
    bright[hero] = rs.uniform(1.9, 2.8, int(hero.sum()))
    sup = np.zeros(n, dtype=bool)
    sup[rs.choice(np.flatnonzero(~hero), 6, replace=False)] = True
    radius[sup] = rs.uniform(16.0, 20.0, int(sup.sum()))
    bright[sup] = rs.uniform(2.0, 3.0, int(sup.sum()))
    return x, y, z, radius, color, bright


def build_band():
    """Additive dense ring layer: four turbine-blade arcs, not a uniform disc."""
    rng = np.random.default_rng(31)
    n = 2200
    arm = rng.integers(0, 8, n)
    u = rng.random(n) ** 0.85
    th = arm * (2.0 * math.pi / 8.0) + ARM_TH_J[arm] * u + rng.normal(0.0, 0.007, n)
    r = 0.22 * np.exp(ARM_LN * u) * (1.0 + rng.normal(0.0, 0.013, n))
    x = r * np.cos(th)
    z = r * np.sin(th)
    y = rng.normal(0.0, 0.012, n)
    uu = rng.random(n)
    radius = 1.2 + 0.9 * uu + 3.5 * uu ** 12
    # colour-temperature gradient along the arm: blue outer, white mid, orange core
    g = u + rng.normal(0.0, 0.10, n)
    color = np.empty((n, 3))
    color[g < 0.28] = PAL[2]
    color[(g >= 0.28) & (g < 0.62)] = PAL[1]
    color[g >= 0.62] = PAL[0]
    bright = 0.60 + 1.10 * rng.random(n) ** 2.0
    return x, y, z, radius, color, bright


def build_mist(version=2):
    """Nebula: continuous knot chains riding the 8 spiral arms.
    Ribbon tier (overlapping tangent-stretched puffs) keeps each arm one unbroken line;
    knot tier adds random-size bright masses on top. Length along the arm, not width."""
    rng = np.random.default_rng(41)
    n_arm = 8
    # per-arm identity (arm-level only): brightness + extent — line interior untouched
    a_gain = rng.uniform(0.75, 1.30, n_arm)
    a_u0 = 0.08 + rng.uniform(-0.08, 0.08, n_arm)  # inner start: short/long arms interleave
    a_u1 = 0.95 + rng.uniform(-0.08, 0.08, n_arm)  # outer end
    # ribbon tier: even coverage in ARC LENGTH per arm (u-spacing starves the outer arm);
    # count scales with that arm's winding so the odd-curvature arms keep the same density
    k = ARM_LN
    arc_ref = math.hypot(k, ARM_TH)
    rib_u, rib_a = [], []
    # v3 keeps the v2 knot layout: the extra ribbon draws go to their own stream
    rng_rib = rng
    if version >= 3:
        rng_rib = np.random.default_rng(411)
        for arm in range(n_arm):
            n_v2 = int(round(30 * math.hypot(k, ARM_TH_J[arm]) / arc_ref))
            rng.uniform(-0.30, 0.30, n_v2)
    for arm in range(n_arm):
        base_rib = 60 if version >= 3 else 30
        n_rib = int(round(base_rib * math.hypot(k, ARM_TH_J[arm]) / arc_ref))
        e0, e1 = math.exp(k * a_u0[arm]), math.exp(k * a_u1[arm])
        u_even = np.log(np.linspace(e0, e1, n_rib)) / k
        steps = np.diff(u_even)
        loc = np.concatenate([steps[:1], steps])  # per-point local spacing for the jitter
        rib_u.append(u_even + rng_rib.uniform(-0.30, 0.30, n_rib) * loc)
        rib_a.append(np.full(n_rib, arm))
    u_rib = np.concatenate(rib_u)
    rib_arm = np.concatenate(rib_a)
    n_rib_total = u_rib.size
    # knot tier: 2-3-knot clusters (only knots cluster; ribbon stays evenly spread)
    n_kn = 12
    kn_arm = np.repeat(np.arange(n_arm), n_kn)
    u_kn = np.empty(n_arm * n_kn)
    s_kn = np.empty(n_arm * n_kn)
    cluster_sizes = (3, 2, 3, 2, 2)
    for arm in range(n_arm):
        cu = rng.uniform(a_u0[arm], a_u1[arm], len(cluster_sizes))
        i = arm * n_kn
        for c, m in enumerate(cluster_sizes):
            u_kn[i : i + m] = cu[c] + rng.normal(0.0, 0.022, m)
            # one lead mass + smaller companions
            s_kn[i : i + m] = np.concatenate(
                [[rng.uniform(0.55, 1.0)], rng.uniform(0.0, 0.55, m - 1)]
            )
            i += m
    u_kn = np.clip(u_kn, 0.01, 1.03)

    arm_j = np.concatenate([rib_arm, kn_arm])
    u = np.concatenate([u_rib, u_kn])
    n = u.size
    is_knot = np.arange(n) >= n_rib_total
    wind = ARM_TH_J[arm_j]
    th = arm_j * (2.0 * math.pi / 8.0) + wind * u + rng.normal(0.0, 0.010, n)
    r = 0.22 * np.exp(ARM_LN * u) * (1.0 + rng.normal(0.0, 0.012, n))
    x = r * np.cos(th)
    z = r * np.sin(th)
    y = rng.normal(0.0, 0.012, n)
    # tangent stretch: long along the arm, narrow across it
    elong = np.where(is_knot, rng.uniform(1.3, 1.8, n), rng.uniform(1.9, 2.5, n))
    s = rng.random(n)
    s[is_knot] = s_kn
    rib_radius = (
        rng.uniform(8.5, 14.5, n) if version >= 3 else rng.uniform(9.0, 15.0, n)
    )
    radius = np.where(is_knot, 6.0 + 22.0 * s ** 2.1, rib_radius)
    # per-arm colour: base hue, transition blend, or enhanced take (ARM_T / ARM_ENH)
    arm_t = ARM_T
    arm_enh = ARM_ENH
    t_col = arm_t[arm_j][:, None]
    base_col = COL_BLUE[None, :] + (COL_PINK - COL_BLUE)[None, :] * t_col
    chroma = np.where(arm_enh[arm_j][:, None], 1.22, 1.0)
    base_col = 128.0 + (base_col - 128.0) * chroma
    color = np.clip(base_col + rng.uniform(-6.0, 6.0, (n, 3)), 0.0, 255.0)
    # size carries the hierarchy: big masses bright, small knots bright too
    size_norm = np.clip((radius - 6.0) / 22.0, 0.0, 1.0)
    knot_b = np.clip(
        (0.20 + 0.24 * size_norm ** 1.15) * rng.uniform(0.85, 1.2, n), 0.0, 0.55
    )
    rib_b = (
        rng.uniform(0.070, 0.115, n) if version >= 3 else rng.uniform(0.09, 0.15, n)
    )
    bright = np.clip(np.where(is_knot, knot_b, rib_b) * a_gain[arm_j], 0.0, 0.60)
    if version >= 3:
        # broad brightness bands along each arm + a taper at both ends
        phase = arm_j * 1.7
        gain = (
            0.94
            + 0.10 * np.sin(2.0 * math.pi * (1.1 * u + phase))
            + 0.05 * np.sin(2.0 * math.pi * (2.3 * u + 0.5 * phase))
        )
        taper = smoothstep(u / 0.09) * (1.0 - smoothstep((u - 0.86) / 0.15))
        bright = bright * gain * taper
    return x, y, z, radius, color, bright, elong, wind


BG_STAR_PAL = (
    (188, 208, 255),
    (255, 248, 232),
    (148, 180, 255),
    (226, 214, 196),
)


def build_bg_stars(n=240):
    """Faint field stars outside the disk; two drift layers give the still world a parallax."""
    rng = np.random.default_rng(303)
    layer = rng.integers(0, 2, n)
    xs = rng.uniform(-8.0, W + 8.0, n)
    ys = rng.uniform(-8.0, H + 8.0, n)
    r = np.where(layer == 0, rng.uniform(0.45, 0.95, n), rng.uniform(0.70, 1.45, n))
    bright = np.where(
        layer == 0, rng.uniform(0.18, 0.42, n), rng.uniform(0.30, 0.68, n)
    )
    anchor = rng.choice(n, 10, replace=False)
    r[anchor] = rng.uniform(1.6, 2.2, anchor.size)
    bright[anchor] = rng.uniform(0.72, 0.92, anchor.size)
    cu = rng.random(n)
    color = np.empty((n, 3), dtype=np.uint8)
    color[cu < 0.34] = BG_STAR_PAL[0]
    color[(cu >= 0.34) & (cu < 0.66)] = BG_STAR_PAL[1]
    color[(cu >= 0.66) & (cu < 0.86)] = BG_STAR_PAL[2]
    color[cu >= 0.86] = BG_STAR_PAL[3]
    phase = rng.uniform(0.0, 2.0 * math.pi, n)
    freq = rng.uniform(0.06, 0.16, n)
    amp = rng.uniform(0.18, 0.32, n)
    vx = np.where(layer == 0, 0.40, 0.95) + rng.normal(0.0, 0.04, n)
    vy = np.where(layer == 0, 0.12, 0.28) + rng.normal(0.0, 0.03, n)
    return xs, ys, r, bright, color, phase, freq, amp, vx, vy


_BG_STARS = build_bg_stars()


def draw_bg_stars(lay, time_s):
    xs, ys, r, bright, color, phase, freq, amp, vx, vy = _BG_STARS
    for i in range(xs.size):
        p = float(
            bright[i]
            * (1.0 + amp[i] * math.sin(2.0 * math.pi * freq[i] * time_s + phase[i]))
        )
        p = min(0.92, max(0.05, round(p * 20.0) / 20.0))
        spr = _star_sprite(
            float(r[i]) * SS, tuple(int(v) for v in color[i]), p, 1.55
        )
        cx = (xs[i] + vx[i] * time_s) * SS
        cy = (ys[i] + vy[i] * time_s) * SS
        lay.alpha_composite(
            spr, (int(round(cx)) - spr.width // 2, int(round(cy)) - spr.height // 2)
        )


def build_core_stars(n=120):
    rng = np.random.default_rng(77)
    r = 0.115 * rng.random(n) ** 0.55
    th = rng.uniform(0.0, 2.0 * math.pi, n)
    x = r * np.cos(th)
    z = r * np.sin(th)
    y = rng.normal(0.0, 0.014, n)
    radius = 1.0 + 1.8 * rng.random(n) ** 2.2
    color = np.empty((n, 3))
    cu = rng.random(n)
    color[cu < 0.45] = (255, 248, 232)
    color[(cu >= 0.45) & (cu < 0.75)] = (255, 230, 190)
    color[(cu >= 0.75) & (cu < 0.94)] = (255, 210, 160)
    color[cu >= 0.94] = (210, 222, 255)
    bright = 0.55 + 1.15 * rng.random(n) ** 2.0
    idx = rng.choice(n, 8, replace=False)
    radius[idx] = rng.uniform(2.6, 4.6, idx.size)
    bright[idx] = rng.uniform(1.6, 2.5, idx.size)
    x[0] = y[0] = z[0] = 0.0
    radius[0] = 8.5
    bright[0] = 4.0
    color[0] = (255, 246, 226)
    return x, y, z, radius, color, bright


_CORE_GLOW = None


def core_glow():
    global _CORE_GLOW
    if _CORE_GLOW is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
        dx = xx - CX
        dy = yy - CY
        broad = np.exp(-0.5 * ((dx / 74.0) ** 2 + (dy / 52.0) ** 2))
        mid = np.exp(-0.5 * ((dx / 27.0) ** 2 + (dy / 19.0) ** 2))
        core = np.exp(-0.5 * ((dx / 7.0) ** 2 + (dy / 5.5) ** 2))
        amp = 20.0 * broad + 32.0 * mid + 36.0 * core
        _CORE_GLOW = amp[..., None] * np.array([1.0, 0.63, 0.31])
    return _CORE_GLOW


_CORE_HAZE = None


def core_haze():
    global _CORE_HAZE
    if _CORE_HAZE is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
        dx = xx - CX
        dy = yy - CY
        mid = np.exp(-0.5 * ((dx / 27.0) ** 2 + (dy / 19.0) ** 2))
        core = np.exp(-0.5 * ((dx / 7.0) ** 2 + (dy / 5.5) ** 2))
        _CORE_HAZE = (10.0 * mid + 12.0 * core)[..., None] * np.array(
            [1.0, 0.72, 0.45]
        )
    return _CORE_HAZE


DUST_COL = (7, 9, 13)
_DUST = None
_DUST_CACHE = {}


def _dust_sprite(rr, col, peak, spread, elong, ang_deg):
    key = (
        round(rr * 2.0),
        round(spread * 4.0),
        col,
        round(peak * 256.0),
        round(elong * 4.0),
        round((ang_deg % 180.0) / 2.5),
    )
    s = _DUST_CACHE.get(key)
    if s is not None:
        return s
    half = max(3, int(math.ceil(rr * spread * max(1.0, elong))))
    size = half * 2 + 1
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    dx, dy = xx - half, yy - half
    a = math.radians(ang_deg)
    ca, sa = math.cos(a), math.sin(a)
    xr = dx * ca + dy * sa
    yr = -dx * sa + dy * ca
    d = np.sqrt((xr / max(rr * elong, 0.5)) ** 2 + (yr / max(rr, 0.5)) ** 2)
    prof = 0.72 * np.exp(-3.2 * d * d) + 0.28 * np.exp(-0.8 * d * d)
    alpha = np.clip(prof * peak, 0.0, 1.0) * (d <= spread) * 255.0
    rgb = np.empty((size, size, 3), dtype=np.uint8)
    rgb[:] = np.array(col, dtype=np.uint8)
    arr = np.concatenate([rgb, alpha.astype(np.uint8)[..., None]], axis=2)
    s = Image.fromarray(arr, "RGBA")
    _DUST_CACHE[key] = s
    return s


def build_dust(n_per_arm=15, n_mid=8):
    rng = np.random.default_rng(151)
    arm = np.repeat(np.arange(8), n_per_arm)
    n = arm.size
    u = rng.uniform(0.10, 0.98, n)
    th = arm * (2.0 * math.pi / 8.0) + ARM_TH_J[arm] * u + rng.normal(0.0, 0.015, n)
    r = 0.22 * np.exp(ARM_LN * u) - rng.uniform(0.025, 0.045, n)
    x = r * np.cos(th)
    z = r * np.sin(th)
    y = rng.normal(0.0, 0.006, n)
    radius = rng.uniform(7.0, 14.0, n)
    alpha = rng.uniform(0.09, 0.18, n)
    elong = rng.uniform(2.6, 4.2, n)
    wind = ARM_TH_J[arm].astype(np.float64)

    th_m = rng.choice((0.0, math.pi), n_mid) + rng.normal(0.0, 0.10, n_mid)
    r_m = rng.uniform(0.25, 0.90, n_mid)
    x_m = r_m * np.cos(th_m)
    z_m = r_m * np.sin(th_m)
    y_m = np.zeros(n_mid)
    radius_m = rng.uniform(20.0, 36.0, n_mid)
    alpha_m = rng.uniform(0.035, 0.070, n_mid)
    elong_m = rng.uniform(1.2, 2.0, n_mid)
    wind_m = np.full(n_mid, ARM_TH)

    return (
        np.concatenate([x, x_m]),
        np.concatenate([y, y_m]),
        np.concatenate([z, z_m]),
        np.concatenate([radius, radius_m]),
        np.concatenate([alpha, alpha_m]),
        np.concatenate([elong, elong_m]),
        np.concatenate([wind, wind_m]),
    )


def dust_data():
    global _DUST
    if _DUST is None:
        _DUST = build_dust()
    return _DUST


def draw_dust(lay, time_s):
    x, y, z, radius, alpha, elong, wind = dust_data()
    spin = spin_angles(x, z, time_s)
    sx, sy_down, _ = project(x, y, z, spin)
    px = CX + sx * SCALE
    py = CY + sy_down * SCALE
    for i in range(x.size):
        th_i = math.atan2(z[i], x[i])
        w_i = float(wind[i])
        ai = math.radians(float(spin[i]))
        ca_i, sa_i = math.cos(ai), math.sin(ai)
        kx = ARM_LN * math.cos(th_i) - w_i * math.sin(th_i)
        kz = ARM_LN * math.sin(th_i) + w_i * math.cos(th_i)
        tx2 = kx * ca_i + kz * sa_i
        tz2 = -kx * sa_i + kz * ca_i
        ang_scr = math.degrees(math.atan2(tz2 * math.sin(PHI), tx2))
        spr = _dust_sprite(
            radius[i] * SS, DUST_COL, float(alpha[i]), 1.2, float(elong[i]), ang_scr
        )
        lay.alpha_composite(
            spr,
            (
                int(round(px[i] * SS)) - spr.width // 2,
                int(round(py[i] * SS)) - spr.height // 2,
            ),
        )


def build_scene():
    c = build_cloud(4 if V4 else 2)
    b = build_band()
    m = build_mist(3 if V3 else 2)
    g = (
        build_core_stars()
        if V3
        else (
            np.empty(0),
            np.empty(0),
            np.empty(0),
            np.empty(0),
            np.empty((0, 3)),
            np.empty(0),
        )
    )
    l = build_leads()
    x, y, z, radius, color, bright = (
        np.concatenate([c[i], b[i], g[i], m[i], l[i]]) for i in range(6)
    )
    n_pre = c[0].size + b[0].size + g[0].size
    n_m = m[0].size
    elong = np.concatenate([np.ones(n_pre), m[6], np.ones(l[0].size)])
    wind = np.concatenate([np.full(n_pre, ARM_TH), m[7], np.full(l[0].size, ARM_TH)])
    kind = np.concatenate(
        [
            np.zeros(n_pre, dtype=np.int8),
            np.full(n_m, 2, dtype=np.int8),
            np.zeros(l[0].size, dtype=np.int8),
        ]
    )
    return x, y, z, radius, color, bright, elong, wind, kind


def project(x, y, z, angle_deg):
    a = np.radians(angle_deg)
    ca, sa = np.cos(a), np.sin(a)
    x2 = x * ca + z * sa
    z2 = -x * sa + z * ca
    sp, cp = math.sin(PHI), math.cos(PHI)
    return x2, -y * cp + z2 * sp, y * sp + z2 * cp


BG = make_bg()


def frame_image(x, y, z, radius, color, bright, elong, wind, kind, time_s=0.0):
    spin = spin_angles(x, z, time_s)
    sx, sy_down, depth = project(x, y, z, spin)
    t = smoothstep((depth / 1.15 + 1.0) * 0.5) ** 0.95
    px = CX + sx * SCALE
    py = CY + sy_down * SCALE

    if V3:
        canvas = Image.fromarray(
            np.clip(np.asarray(BG).astype(np.float64) + core_glow(), 0.0, 255.0).astype(
                np.uint8
            ),
            "RGB",
        ).convert("RGBA")
    else:
        canvas = BG.copy().convert("RGBA")

    if V3:
        bg_stars = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
        draw_bg_stars(bg_stars, time_s)
        canvas.alpha_composite(bg_stars.resize((W, H), Image.LANCZOS))

    far = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    near = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    for i in np.argsort(depth):
        ti = float(t[i])
        cx, cy = px[i] * SS, py[i] * SS
        lay = far if ti < 0.55 else near
        col = tuple(int(v) for v in color[i])
        b = float(bright[i])
        if kind[i] == 2:
            front = ti >= 0.55
            rr = radius[i] * (0.85 + 0.30 * ti) * (0.92 if front else 1.10) * SS
            # back mist a touch richer than front (front veils stars), but both must read
            a = b * (0.35 + 0.65 * ti) * (0.75 if front else 1.15)
            # stretch along the arm tangent (log-spiral direction at this azimuth), projected
            th_i = math.atan2(z[i], x[i])
            w_i = float(wind[i])
            ai = math.radians(float(spin[i]))
            ca_i, sa_i = math.cos(ai), math.sin(ai)
            kx = ARM_LN * math.cos(th_i) - w_i * math.sin(th_i)
            kz = ARM_LN * math.sin(th_i) + w_i * math.cos(th_i)
            tx2 = kx * ca_i + kz * sa_i
            tz2 = -kx * sa_i + kz * ca_i
            ang_scr = math.degrees(math.atan2(tz2 * math.sin(PHI), tx2))
            spr = _star_sprite(
                rr, col, min(1.0, a), 1.15, elong=float(elong[i]), ang_deg=ang_scr, wf=0.10
            )
            lay.alpha_composite(
                spr, (int(round(cx)) - spr.width // 2, int(round(cy)) - spr.height // 2)
            )
            continue
        else:
            a = (0.42 + 0.55 * ti) * (0.55 + 0.80 * b)
            rr = radius[i] * (0.75 + 0.45 * ti) * 0.45 * SS
            spread = 1.7 + 0.5 * b + 2.6 * max(0.0, b - 1.5)
            # area compensation: a sub-pixel core loses peak alpha when downsampled
            comp = min(2.4, 1.0 + 1.6 / max(rr, 0.8))
        spr = _star_sprite(rr, col, min(1.0, a * comp), spread)
        lay.alpha_composite(
            spr, (int(round(cx)) - spr.width // 2, int(round(cy)) - spr.height // 2)
        )

    dust = None
    if V4:
        dust = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
        draw_dust(dust, time_s)

    far = far.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.85))
    near = near.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.35))
    bloom = ImageChops.lighter(far, near).filter(ImageFilter.GaussianBlur(7.0))
    bloom = bloom.point(lambda v: int(v * 0.20))
    canvas.alpha_composite(bloom)
    canvas.alpha_composite(far)
    if V4:
        dust = dust.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6))
        canvas.alpha_composite(dust)
    canvas.alpha_composite(near)

    out = np.asarray(canvas.convert("RGB")).astype(np.float64)
    if V3:
        out += core_haze()
    out += np.random.default_rng(9000 + int(time_s * 24)).normal(0.0, 2.2, out.shape)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")
