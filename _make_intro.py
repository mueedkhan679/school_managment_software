"""Render the cinematic 8-second intro video: assets/videos/intro.mp4.

Scene (all procedural, no external assets beyond the generated logo):
  * Deep-navy vertical gradient backdrop (matches BrandColors.navyGradient)
  * Drifting emerald/azure radial light sweep
  * Parallax light particles rising with subtle depth
  * The 3D logo badge scaling in (easeOutBack) with a gold pulse ring
  * Cinematic vignette + fade to brand navy at the tail

Output: 1280x720, 24 fps, exactly 8.00 s (192 frames), H.264 yuv420p with
faststart so playback can begin instantly (no waiting for the whole file).
"""
import struct
import zlib
from pathlib import Path

import imageio.v2 as imageio
import numpy as np

ROOT = Path(__file__).resolve().parent
LOGO = ROOT / "student_portal_app" / "assets" / "images" / "logo.png"
OUT = ROOT / "student_portal_app" / "assets" / "videos" / "intro.mp4"

W, H = 1280, 720
FPS = 24
DURATION = 8.0
N_FRAMES = int(round(FPS * DURATION))  # 192

NAVY_TOP = np.array([0x1E, 0x3A, 0x6E], np.float32)
NAVY_MID = np.array([0x0F, 0x1E, 0x3D], np.float32)
NAVY_BOT = np.array([0x0A, 0x17, 0x30], np.float32)
EMERALD = np.array([0x10, 0xB9, 0x81], np.float32)
AZURE = np.array([0x3B, 0x82, 0xF6], np.float32)
GOLD = np.array([0xF5, 0xB3, 0x01], np.float32)


def ease_out_back(t: float) -> float:
    c1, c3 = 1.70158, 2.70158
    t = min(max(t, 0.0), 1.0)
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


def ease_in_out(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return 3.0 * t * t - 2.0 * t * t * t


# ---------------------------------------------------------------- logo decode
data = LOGO.read_bytes()
assert data[:8] == b"\x89PNG\r\n\x1a\n"
lw, lh = struct.unpack(">II", data[16:24])
idat = b""
i = 8
while i < len(data):
    length = struct.unpack(">I", data[i:i + 4])[0]
    tag = data[i + 4:i + 8]
    if tag == b"IDAT":
        idat += data[i + 8:i + 8 + length]
    i += 12 + length
raw = zlib.decompress(idat)
stride = lw * 4 + 1
rows = np.frombuffer(raw, np.uint8).reshape(lh, stride)
logo = rows[:, 1:].reshape(lh, lw, 4).astype(np.float32) / 255.0
logo_rgb = logo[..., :3]
logo_a = logo[..., 3]

WORK = 420
yy = (np.arange(WORK) * (lh / WORK)).astype(np.int32)
xx = (np.arange(WORK) * (lw / WORK)).astype(np.int32)
logo_rgb = logo_rgb[np.ix_(yy, xx)]
logo_a = logo_a[np.ix_(yy, xx)]
LH, LW = WORK, WORK


def bilinear(src: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    squeeze = src.ndim == 2
    a3 = src[..., None] if squeeze else src
    sy = np.linspace(0, a3.shape[0] - 1, out_h)
    sx = np.linspace(0, a3.shape[1] - 1, out_w)
    y0 = np.floor(sy).astype(np.int32); y1 = np.minimum(y0 + 1, a3.shape[0] - 1)
    x0 = np.floor(sx).astype(np.int32); x1 = np.minimum(x0 + 1, a3.shape[1] - 1)
    fy = (sy - y0)[:, None, None]
    fx = (sx - x0)[None, :, None]
    a = a3[y0][:, x0]; b = a3[y0][:, x1]
    c = a3[y1][:, x0]; d = a3[y1][:, x1]
    out = (a * (1 - fx) * (1 - fy) + b * fx * (1 - fy)
           + c * (1 - fx) * fy + d * fx * fy)
    return out[..., 0] if squeeze else out


# ------------------------------------------------------------- static layers
ys = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None]
xs = np.linspace(0.0, 1.0, W, dtype=np.float32)[None, :]
gx, gy = np.meshgrid(np.linspace(-1, 1, W, dtype=np.float32),
                     np.linspace(-1, 1, H, dtype=np.float32))
vignette = (1.0 - 0.38 * np.clip((gx ** 2 + gy ** 2) - 0.25, 0.0, 1.2))[..., None]

grad1d = (NAVY_TOP[None, None, :] * (1 - ys)[..., None]
          + NAVY_MID[None, None, :] * ((1 - ys) * ys * 2.0)[..., None]
          + NAVY_BOT[None, None, :] * (ys * ys)[..., None]).astype(np.float32)
grad = np.broadcast_to(grad1d, (H, W, 3))

rng = np.random.default_rng(20260911)
N_PARTICLES = 56
p_x0 = rng.uniform(0.0, 1.0, N_PARTICLES).astype(np.float32)
p_y0 = rng.uniform(1.1, 1.9, N_PARTICLES).astype(np.float32)
p_depth = rng.uniform(0.35, 1.0, N_PARTICLES).astype(np.float32)
p_phase = rng.uniform(0.0, 2 * np.pi, N_PARTICLES).astype(np.float32)
p_speed = rng.uniform(0.045, 0.14, N_PARTICLES).astype(np.float32)
p_drift = rng.uniform(-0.03, 0.03, N_PARTICLES).astype(np.float32)
p_size = (1.4 + 4.2 * p_depth).astype(np.float32)

KERNEL_R = 7
kk = np.arange(-KERNEL_R, KERNEL_R + 1, dtype=np.float32)
gxk, gyk = np.meshgrid(kk, kk)
KERNEL = np.exp(-(gxk ** 2 + gyk ** 2) / (2 * 1.9 ** 2)).astype(np.float32)


def add_particles(frame, t):
    for j in range(N_PARTICLES):
        py = (p_y0[j] - p_speed[j] * (t * 0.9 + 0.2)) % 1.15 - 0.075
        px = p_x0[j] + p_drift[j] * t + 0.012 * np.sin(t * 1.7 + p_phase[j])
        cx = int(px * (W - 1))
        cy = int(py * (H - 1))
        r0, r1 = KERNEL_R, KERNEL_R + 1
        x_lo, x_hi = max(0, cx - r0), min(W, cx + r1)
        y_lo, y_hi = max(0, cy - r0), min(H, cy + r1)
        if x_lo >= x_hi or y_lo >= y_hi:
            continue
        ksub = KERNEL[(y_lo - cy + r0):(y_hi - cy + r0),
                      (x_lo - cx + r0):(x_hi - cx + r0)]
        depth = p_depth[j]
        color = AZURE * (1 - depth) + EMERALD * depth
        frame[y_lo:y_hi, x_lo:x_hi] += ksub[..., None] * color * (0.10 + 0.22 * depth)


def frame_at(t: float) -> np.ndarray:
    frame = grad.copy()

    cx = 0.5 + 0.34 * np.sin(t * 0.6 + 1.0)
    cy = 0.42 + 0.20 * np.cos(t * 0.45)
    d2 = (xs - cx) ** 2 + ((ys - cy) * 0.9) ** 2
    sweep = np.exp(-d2 * 3.2)[..., None]
    mix_w = 0.5 + 0.5 * np.sin(t * 0.5)
    tint = EMERALD * mix_w + AZURE * (1 - mix_w)
    frame += sweep * tint * 0.10

    add_particles(frame, t)

    ent = ease_out_back(np.clip((t - 0.35) / 1.0, 0.0, 1.0))
    scale = 0.52 + 0.48 * ent
    bob = 0.012 * np.sin(t * 1.3 + 0.8)
    logo_h = int(round(H * 0.46 * scale))
    logo_w = int(round(logo_h * LW / LH))
    if logo_h >= 2 and logo_w >= 2:
        lr = bilinear(logo_rgb, logo_h, logo_w)
        la = bilinear(logo_a, logo_h, logo_w)[..., None]
        ly0 = int((H * (0.44 + bob)) - logo_h / 2)
        lx0 = (W - logo_w) // 2
        y_lo, y_hi = max(0, ly0), min(H, ly0 + logo_h)
        x_lo, x_hi = max(0, lx0), min(W, lx0 + logo_w)
        if y_hi > y_lo and x_hi > x_lo:
            sub_r = lr[(y_lo - ly0):(y_hi - ly0), (x_lo - lx0):(x_hi - lx0)]
            sub_a = la[(y_lo - ly0):(y_hi - ly0), (x_lo - lx0):(x_hi - lx0)]
            region = frame[y_lo:y_hi, x_lo:x_hi]
            frame[y_lo:y_hi, x_lo:x_hi] = region * (1 - sub_a) + sub_r * sub_a

        pulse_t = np.clip((t - 0.25) / 1.6, 0.0, 1.0)
        if pulse_t < 1.0:
            r_px = 60 + 300 * pulse_t
            ring = np.exp(-((np.hypot(gx * W / 2, gy * H / 2) - r_px) ** 2) / 900.0)
            fade = (1 - pulse_t) * ease_in_out(pulse_t)
            frame += ring[..., None] * GOLD * (0.35 * fade)

    frame *= vignette
    frame *= min(1.0, t / 0.4)
    tail = np.clip((t - (DURATION - 0.7)) / 0.7, 0.0, 1.0)
    tail_e = ease_in_out(tail)
    frame = frame * (1 - 0.85 * tail_e) + 0.85 * tail_e * NAVY_MID
    return np.clip(frame, 0, 1)


if __name__ == "__main__":
    import sys

    n_frames = N_FRAMES
    out_path = OUT
    if len(sys.argv) > 1 and sys.argv[1] == "--smoke":
        n_frames = 2
        out_path = OUT.parent / "_smoke.mp4"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(
        str(out_path), fps=FPS, codec="libx264", quality=8,
        pixelformat="yuv420p",
        output_params=["-movflags", "+faststart", "-profile:v", "high"],
    )
    for n in range(n_frames):
        writer.append_data((frame_at(n / FPS) * 255.0).astype(np.uint8))
    writer.close()
    print("wrote", out_path, out_path.stat().st_size, "bytes;", n_frames, "frames")
    print("DONE")

