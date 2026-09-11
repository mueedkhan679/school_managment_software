"""Generate the bundled 3D-style logo: assets/images/logo.png.

Pure-Python PNG writer (zlib + struct) - no PIL required. Renders a
1024x1024 "3D-looking" shield badge: navy vertical gradient, soft drop
shadow, bevel edge highlight, gold ring and an emerald graduation cap
built from simple shaded shapes.
"""
import math
import struct
import zlib
from pathlib import Path

SIZE = 1024
CX = CY = SIZE / 2
OUT = Path(__file__).resolve().parent / "student_portal_app" / "assets" / "images" / "logo.png"

# Palette (matches BrandColors in app_theme.dart).
NAVY_TOP = (0x1E, 0x3A, 0x6E)
NAVY_BOT = (0x0F, 0x1E, 0x3D)
NAVY_EDGE = (0x0A, 0x17, 0x30)
GOLD = (0xF5, 0xB3, 0x01)
GOLD_DARK = (0xC8, 0x8D, 0x00)
EMERALD = (0x10, 0xB9, 0x81)
EMERALD_DARK = (0x05, 0x96, 0x69)
WHITE = (255, 255, 255)


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def mix(c1, c2, t):
    return tuple(int(round(a + (b - a) * t)) for a, b in zip(c1, c2))


def shade(c, k):
    return tuple(int(round(clamp(ch * k, 0, 255))) for ch in c)


# Very dark navy used as the soft drop-shadow colour behind the badge.
SHADOW_RGB = (8, 14, 28)


def lerp_channel(ch, t):
    """Blend one channel from the shadow colour toward the body colour."""
    return SHADOW_RGB[0] * (1.0 - t) + ch * t if ch > SHADOW_RGB[0] else ch


def inside_badge(x, y):
    """Rounded-square badge mask (0..1, 1 = fully inside)."""
    r = SIZE * 0.16
    half = SIZE * 0.36  # badge half-size (72% of canvas)
    dx = abs(x - CX) - (half - r)
    dy = abs(y - CY) - (half - r)
    ddx, ddy = max(dx, 0.0), max(dy, 0.0)
    d = math.hypot(ddx, ddy) + min(max(dx, dy), 0.0) - r
    return clamp(0.5 - d / 1.5)


def inside_ring(x, y, radius, thickness):
    d = math.hypot(x - CX, y - CY)
    return clamp(1.0 - (abs(d - radius) - thickness) / 1.5)


def cap_mask(x, y, scale):
    """Graduation-cap glyph mask + shading hint (0..1)."""
    # Local coords centred, slightly above badge centre.
    lx = (x - CX) / scale
    ly = (y - CY * 1.02) / scale
    # Cap board: wide diamond.
    board = clamp(1.0 - (abs(lx * 1.02 + ly * 0.55) + abs(ly * 1.55 - lx * 0.1) - 2.6) / 0.8)
    # Base: rounded trapezoid below.
    base = 0.0
    if -0.35 <= ly and ly <= 0.75:
        w = 1.45 - (ly + 0.35) * 0.75
        base = clamp(1.0 - (abs(lx) - w) / 0.6) * (1.0 if abs(lx) <= w + 0.3 else 0.0)
        if ly < -0.1:
            base *= 0.0 if ly < -0.22 else clamp((ly + 0.22) / 0.12)
    return board, base


def tassel_mask(x, y, scale):
    lx = (x - CX * 1.005) / scale
    ly = (y - CY * 1.02) / scale
    # Cord from board tip to side, then small bob.
    bob = clamp(1.0 - (math.hypot(lx - 1.9, ly - 0.35) - 0.34) / 0.5)
    return bob


rows = bytearray()
px = SIZE
for y in range(px):
    row = bytearray(b"\x00")
    for x in range(px):
        # ---- soft drop shadow under the badge
        shadow = inside_badge(x + SIZE * 0.012, y + SIZE * 0.022) * 0.55
        # ---- badge body: vertical gradient + centre radial lift (fake 3D)
        badge = inside_badge(x, y)
        body = badge
        color = mix(NAVY_TOP, NAVY_BOT, (y - CY + SIZE * 0.36) / (SIZE * 0.72))
        # radial highlight to fake depth
        d = math.hypot(x - CX, y - CY * 0.92) / (SIZE * 0.45)
        lift = clamp(1.0 - d)
        color = mix(color, shade(NAVY_TOP, 1.45), lift * 0.28)

        # bevel: edge darkening at the bottom-right, light at top-left
        nx = (x - CX) / (SIZE * 0.36)
        ny = (y - CY) / (SIZE * 0.36)
        edge_dir = clamp((nx * 0.6 + ny * 0.8), -1, 1)
        edge = inside_badge(x - nx * 6, y - ny * 6) - inside_badge(x + nx * 6, y + ny * 6)
        color = mix(color, NAVY_EDGE, clamp(abs(edge) * 0.9) * max(0.0, edge_dir) * 0.9)
        color = mix(color, shade(NAVY_TOP, 1.7), clamp(abs(edge)) * max(0.0, -edge_dir) * 0.6)

        # ---- gold ring inset
        ring = inside_ring(x, y, SIZE * 0.295, 6.5) * badge
        ring_sh = mix(GOLD, GOLD_DARK, clamp((y - CY) / (SIZE * 0.5) + 0.5))
        color = mix(color, ring_sh, ring * 0.95)

        # ---- graduation cap (emerald, shaded) + gold tassel
        scale = SIZE * 0.135
        board, base = cap_mask(x, y, scale)
        cap_sh = mix(EMERALD_DARK, EMERALD, clamp(0.5 - (ny) * 0.8))
        board_color = mix(shade(cap_sh, 1.12), shade(cap_sh, 0.78), clamp((x - CX) / (SIZE * 0.4) + 0.5))
        base_color = mix(shade(EMERALD_DARK, 0.85), shade(EMERALD, 0.9), clamp(0.45 - ny * 0.5))
        color = mix(color, board_color, clamp(board) * 0.97)
        color = mix(color, base_color, clamp(base) * 0.97)
        tassel = tassel_mask(x, y, scale) * clamp(board + 0.15)
        color = mix(color, mix(GOLD, GOLD_DARK, clamp((y - CY) / (SIZE * 0.4) + 0.5)), clamp(tassel) * 0.98)

        # ---- composite over transparent background:
        # shadow first (soft dark), then opaque body on top.
        alpha = clamp(max(shadow * 0.85, body))
        if alpha <= 0.003:
            row += b"\x00\x00\x00\x00"
            continue
        t = clamp(body / alpha)
        r = int(round(lerp_channel(color[0], t)))
        g = int(round(lerp_channel(color[1], t)))
        b = int(round(lerp_channel(color[2], t)))
        row += bytes((r, g, b, int(round(alpha * 255))))
    rows += row

raw = bytes(rows)


def chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


png = (
    b"\x89PNG\r\n\x1a\n"
    + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
    + chunk(b"IDAT", zlib.compress(raw, 9))
    + chunk(b"IEND", b"")
)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_bytes(png)
print("wrote", OUT, len(png), "bytes")
print("DONE")

