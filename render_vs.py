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


def build_cloud():
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


def build_mist():
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
    for arm in range(n_arm):
        n_rib = int(round(30 * math.hypot(k, ARM_TH_J[arm]) / arc_ref))
        e0, e1 = math.exp(k * a_u0[arm]), math.exp(k * a_u1[arm])
        u_even = np.log(np.linspace(e0, e1, n_rib)) / k
        steps = np.diff(u_even)
        loc = np.concatenate([steps[:1], steps])  # per-point local spacing for the jitter
        rib_u.append(u_even + rng.uniform(-0.30, 0.30, n_rib) * loc)
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
    radius = np.where(is_knot, 6.0 + 22.0 * s ** 2.1, rng.uniform(9.0, 15.0, n))
    # per-arm colour: base hue, transition blend, or enhanced take (ARM_T / ARM_ENH)
    t_col = ARM_T[arm_j][:, None]
    base_col = COL_BLUE[None, :] + (COL_PINK - COL_BLUE)[None, :] * t_col
    chroma = np.where(ARM_ENH[arm_j][:, None], 1.22, 1.0)
    base_col = 128.0 + (base_col - 128.0) * chroma
    color = np.clip(base_col + rng.uniform(-6.0, 6.0, (n, 3)), 0.0, 255.0)
    # size carries the hierarchy: big masses bright, small knots bright too
    size_norm = np.clip((radius - 6.0) / 22.0, 0.0, 1.0)
    bright = np.where(
        is_knot,
        np.clip((0.20 + 0.24 * size_norm ** 1.15) * rng.uniform(0.85, 1.2, n), 0.0, 0.55),
        rng.uniform(0.09, 0.15, n),
    )
    bright = np.clip(bright * a_gain[arm_j], 0.0, 0.60)
    return x, y, z, radius, color, bright, elong, wind


def build_scene():
    c = build_cloud()
    b = build_band()
    m = build_mist()
    l = build_leads()
    x, y, z, radius, color, bright = (
        np.concatenate([c[i], b[i], m[i], l[i]]) for i in range(6)
    )
    n_pre = c[0].size + b[0].size
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

    canvas = BG.copy().convert("RGBA")

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

    far = far.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.85))
    near = near.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.35))
    bloom = ImageChops.lighter(far, near).filter(ImageFilter.GaussianBlur(7.0))
    bloom = bloom.point(lambda v: int(v * 0.20))
    canvas.alpha_composite(bloom)
    canvas.alpha_composite(far)
    canvas.alpha_composite(near)

    out = np.asarray(canvas.convert("RGB")).astype(np.float64)
    out += np.random.default_rng(9000 + int(time_s * 24)).normal(0.0, 2.2, out.shape)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")
