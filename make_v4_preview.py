import os
import subprocess

import render_vs as R

R.V3 = True
R.V4 = True

FPS = 24
DURATION = 4.0
N_FRAMES = int(round(DURATION * FPS))


def main():
    x, y, z, radius, color, bright, elong, wind, kind = R.build_scene()

    mp4_path = os.path.join(R.COMPARE, "vs_space_v4_preview.mp4")
    ff = subprocess.Popen(
        [
            "ffmpeg", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{R.W}x{R.H}", "-r", str(FPS), "-i", "-",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18", "-movflags", "+faststart", mp4_path,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    checks = {0: "vs_v4chk_first.png", N_FRAMES - 1: "vs_v4chk_last.png"}
    for k in range(N_FRAMES):
        tt = k / FPS
        img = R.frame_image(x, y, z, radius, color, bright, elong, wind, kind, time_s=tt)
        ff.stdin.write(img.tobytes())
        if k in checks:
            img.save(os.path.join(R.COMPARE, checks[k]))
        if k % 24 == 0:
            print("frame", k, flush=True)
    ff.stdin.close()
    ff.wait()
    print("mp4 done rc", ff.returncode, mp4_path, os.path.getsize(mp4_path))


if __name__ == "__main__":
    main()
