"""Render ShadowBridge Concept C icon at multiple sizes and save as .ico + .png."""
from PIL import Image, ImageDraw

SVG = 48  # SVG viewBox units


def qbez(p0, p1, p2, steps=80):
    """Quadratic bezier points."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = u*u*p0[0] + 2*u*t*p1[0] + t*t*p2[0]
        y = u*u*p0[1] + 2*u*t*p1[1] + t*t*p2[1]
        pts.append((x, y))
    return pts


def sc(pt, s):
    return (pt[0] * s, pt[1] * s)


def scs(pts, s):
    return [sc(p, s) for p in pts]


def poly_lines(draw, pts, color, width):
    """Draw a closed polygon as line segments (handles RGBA draw correctly)."""
    n = len(pts)
    for i in range(n):
        draw.line([pts[i], pts[(i + 1) % n]], fill=color, width=max(1, width))


def alpha_layer(size, draw_fn):
    """Draw onto a fresh RGBA layer, return it."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer), layer)
    return layer


def scale_alpha(img, factor):
    r, g, b, a = img.split()
    a = a.point(lambda v: int(v * factor))
    return Image.merge("RGBA", (r, g, b, a))


def render(size, supersample=4):
    ss = size * supersample
    s = ss / SVG

    CYAN        = (0, 212, 232, 255)
    ORANGE      = (232, 137, 12, 255)
    TEAL        = (0, 127, 140, 255)
    BG          = (0, 20, 30, int(0.95 * 255))

    img = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── Outer octagon fill ───────────────────────────────────────────────────
    outer = [(14,2),(34,2),(46,14),(46,34),(34,46),(14,46),(2,34),(2,14)]
    outer_s = scs(outer, s)
    draw.polygon(outer_s, fill=BG)

    # ── Outer octagon stroke (cyan, width 1.5) ───────────────────────────────
    poly_lines(draw, outer_s, CYAN, round(1.5 * s))

    # ── Inner octagon stroke (cyan 20% alpha) — separate composited layer ────
    inner = [(14,5),(34,5),(43,14),(43,34),(34,43),(14,43),(5,34),(5,14)]
    inner_s = scs(inner, s)
    inner_layer = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    poly_lines(ImageDraw.Draw(inner_layer), inner_s, CYAN, max(1, round(0.5 * s)))
    inner_layer = scale_alpha(inner_layer, 0.2)
    img = Image.alpha_composite(img, inner_layer)
    draw = ImageDraw.Draw(img)  # rebind after composite

    # ── Bridge arch: M10 30 Q10 18 24 18  Q38 18 38 30 ──────────────────────
    arch = (
        qbez((10, 30), (10, 18), (24, 18)) +
        qbez((24, 18), (38, 18), (38, 30))
    )
    arch_s = [sc(p, s) for p in arch]
    draw.line(arch_s, fill=CYAN, width=max(1, round(2 * s)))

    # ── Tower verticals ──────────────────────────────────────────────────────
    draw.line([sc((10,30),s), sc((10,34),s)], fill=CYAN,   width=max(1, round(2 * s)))
    draw.line([sc((38,30),s), sc((38,34),s)], fill=ORANGE, width=max(1, round(2 * s)))

    # ── Dashed baseline (dasharray 3,2) ─────────────────────────────────────
    dash_on  = 3 * s
    dash_gap = 2 * s
    y34 = 34 * s
    x = 10 * s
    x_end = 38 * s
    lw = max(1, round(1.5 * s))
    while x < x_end:
        x2 = min(x + dash_on, x_end)
        draw.line([(x, y34), (x2, y34)], fill=TEAL, width=lw)
        x += dash_on + dash_gap

    # ── Suspension cables ────────────────────────────────────────────────────
    for cx, cy_top in [(18, 28), (24, 26), (30, 28)]:
        draw.line([sc((cx, cy_top), s), sc((cx, 34), s)],
                  fill=CYAN, width=max(1, round(1.5 * s)))

    # ── Anchor dots ──────────────────────────────────────────────────────────
    for (cx, cy, color) in [(10, 30, CYAN), (38, 30, ORANGE)]:
        r = 2 * s
        px, py = cx * s, cy * s
        draw.ellipse([px - r, py - r, px + r, py + r], fill=color)

    # ── Signal mast ──────────────────────────────────────────────────────────
    draw.line([sc((24, 10), s), sc((24, 15), s)],
              fill=ORANGE, width=max(1, round(1 * s)))
    r = 1.5 * s
    px, py = 24 * s, 9 * s
    draw.ellipse([px - r, py - r, px + r, py + r], fill=ORANGE)

    # ── Downsample with LANCZOS ──────────────────────────────────────────────
    return img.resize((size, size), Image.LANCZOS)


SIZES = [16, 32, 48, 64, 128, 256]
OUT_DIR = r"C:\Users\ajsme\OneDrive\Documents\GitHub\ShadowBridge"

images = {sz: render(sz) for sz in SIZES}

png_path = f"{OUT_DIR}\\shadowbridge_icon.png"
images[256].save(png_path)
print(f"PNG saved: {png_path}")

# Pillow's ICO plugin resizes from the primary image; pass the 256px version
# and let it produce all requested sizes (which it downsamples via LANCZOS).
# Our render() already supersamples each size, so write them as raw PNG chunks
# directly into a hand-assembled ICO to preserve our quality.
import struct, io

def make_ico(sized_images):
    """Manually assemble a multi-size ICO from pre-rendered RGBA PIL images."""
    count = len(sized_images)
    # Each directory entry is 16 bytes; header is 6 bytes.
    header_size = 6 + 16 * count
    chunks = []
    entries = []
    offset = header_size
    for img in sized_images:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()
        w, h = img.size
        # ICO dir entry: width(B) height(B) colors(B) reserved(B) planes(H) bpp(H) size(L) offset(L)
        # width/height 0 means 256
        bw = 0 if w == 256 else w
        bh = 0 if h == 256 else h
        entries.append(struct.pack("<BBBBHHLL", bw, bh, 0, 0, 1, 32, len(data), offset))
        chunks.append(data)
        offset += len(data)
    ico = struct.pack("<HHH", 0, 1, count)
    for e in entries:
        ico += e
    for c in chunks:
        ico += c
    return ico

ico_path = f"{OUT_DIR}\\shadowbridge_icon.ico"
ordered = [images[sz] for sz in SIZES]
with open(ico_path, "wb") as f:
    f.write(make_ico(ordered))
print(f"ICO saved: {ico_path}")
