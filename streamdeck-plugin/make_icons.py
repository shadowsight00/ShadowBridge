from PIL import Image, ImageDraw
import math, os

BG      = (26, 26, 26)
BLUE    = (88, 166, 255)
GREEN   = (63, 185, 80)

PLUGIN_DIR = "com.shadowbridge.app.sdPlugin"

def save(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "PNG")

def make_canvas(size):
    img = Image.new("RGBA", (size, size), BG + (255,))
    return img, ImageDraw.Draw(img)

# ── Toggle Streaming — play triangle in green ─────────────────────────────────
def toggle_streaming(size):
    img, d = make_canvas(size)
    m = size / 72          # scale multiplier
    cx, cy = size // 2, size // 2
    # Equilateral-ish play triangle, centred
    r = int(24 * m)
    # Vertices: left-top, left-bottom, right-middle
    pts = [
        (cx - int(r * 0.6), cy - int(r * 0.85)),
        (cx - int(r * 0.6), cy + int(r * 0.85)),
        (cx + int(r * 1.0), cy),
    ]
    d.polygon(pts, fill=GREEN + (255,))
    return img

# ── Toggle Channel — 5-bar waveform in blue ──────────────────────────────────
def toggle_channel(size):
    img, d = make_canvas(size)
    m = size / 72
    cx, cy = size // 2, size // 2
    n_bars   = 5
    heights  = [0.45, 0.70, 1.00, 0.70, 0.45]  # relative heights
    bar_w    = int(5 * m)
    gap      = int(5 * m)
    max_h    = int(28 * m)
    total_w  = n_bars * bar_w + (n_bars - 1) * gap
    x0       = cx - total_w // 2
    for i, rel_h in enumerate(heights):
        bh = int(max_h * rel_h)
        x  = x0 + i * (bar_w + gap)
        y1 = cy - bh // 2
        y2 = cy + bh // 2
        d.rounded_rectangle([x, y1, x + bar_w, y2], radius=int(2 * m), fill=BLUE + (255,))
    return img

# ── Connection Status — two PC boxes + arc ───────────────────────────────────
def connection_status(size):
    img, d = make_canvas(size)
    m  = size / 72
    cx = size // 2
    cy = size // 2

    bw = int(18 * m)   # box width
    bh = int(14 * m)   # box height
    lw = max(2, int(2.5 * m))
    gap = int(10 * m)  # gap between centres

    # Left PC box
    lx = cx - gap - bw // 2
    ly = cy - bh // 2
    d.rectangle([lx, ly, lx + bw, ly + bh], outline=BLUE + (255,), width=lw)
    # tiny screen detail
    pad = int(3 * m)
    d.rectangle([lx + pad, ly + pad, lx + bw - pad, ly + bh - pad - int(2 * m)],
                fill=BLUE + (80,))

    # Right PC box
    rx = cx + gap - bw // 2
    ry = cy - bh // 2
    d.rectangle([rx, ry, rx + bw, ry + bh], outline=BLUE + (255,), width=lw)
    pad = int(3 * m)
    d.rectangle([rx + pad, ry + pad, rx + bw - pad, ry + bh - pad - int(2 * m)],
                fill=BLUE + (80,))

    # Arc connecting them (above centre)
    arc_top   = int(cy - 18 * m)
    arc_bot   = int(cy + 2 * m)
    arc_left  = int(lx + bw // 2)
    arc_right = int(rx + bw // 2)
    d.arc([arc_left, arc_top, arc_right, arc_bot], start=200, end=340,
          fill=BLUE + (255,), width=lw)

    # Dot endpoints on the arc
    dot_r = max(2, int(2.5 * m))
    d.ellipse([arc_left - dot_r, cy - dot_r, arc_left + dot_r, cy + dot_r],
              fill=BLUE + (255,))
    d.ellipse([arc_right - dot_r, cy - dot_r, arc_right + dot_r, cy + dot_r],
              fill=BLUE + (255,))
    return img

# ── Plugin icon — ShadowBridge logo scaled with padding ──────────────────────
def plugin_icon(size, src_path):
    src = Image.open(src_path).convert("RGBA")
    canvas = Image.new("RGBA", (size, size), BG + (255,))
    pad = int(size * 0.12)
    inner = size - 2 * pad
    logo = src.resize((inner, inner), Image.LANCZOS)
    canvas.paste(logo, (pad, pad), logo)
    return canvas

# ── Generate everything ───────────────────────────────────────────────────────
src_logo = "../shadowbridge/static/assets/shadowbridge_icon_64.png"

specs = [
    # (generator_fn, rel_path, size)
    (toggle_streaming,    f"{PLUGIN_DIR}/imgs/actions/toggle-streaming/key.png",    72),
    (toggle_streaming,    f"{PLUGIN_DIR}/imgs/actions/toggle-streaming/key@2x.png", 144),
    (toggle_channel,      f"{PLUGIN_DIR}/imgs/actions/toggle-channel/key.png",      72),
    (toggle_channel,      f"{PLUGIN_DIR}/imgs/actions/toggle-channel/key@2x.png",   144),
    (connection_status,   f"{PLUGIN_DIR}/imgs/actions/connection-status/key.png",   72),
    (connection_status,   f"{PLUGIN_DIR}/imgs/actions/connection-status/key@2x.png",144),
]

for fn, path, size in specs:
    img = fn(size)
    save(img, path)
    print(f"  {path}  ({size}x{size})")

# Plugin icon at 288 and 576
for size, path in [
    (288, f"{PLUGIN_DIR}/imgs/plugin/icon.png"),
    (576, f"{PLUGIN_DIR}/imgs/plugin/icon@2x.png"),
]:
    img = plugin_icon(size, src_logo)
    save(img, path)
    print(f"  {path}  ({size}x{size})")

print("Done.")
