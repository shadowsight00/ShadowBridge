"""Generate ShadowBridge marketplace assets for Stream Deck."""

import math
from PIL import Image, ImageDraw, ImageFont

BG = (15, 15, 15)          # #0f0f0f
GREEN = (74, 222, 128)      # #4ade80
GREEN_DIM = (40, 120, 70)
WHITE = (255, 255, 255)
GRAY = (180, 180, 180)
DARK_PANEL = (24, 24, 24)
PANEL2 = (30, 30, 30)
PANEL3 = (36, 36, 36)
RED_LIVE = (239, 68, 68)


def load_font(size, bold=False):
    """Try system fonts, fall back to default."""
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def draw_waveform(draw, cx, cy, width, height, color, num_bars=18, amplitude_scale=1.0):
    """Draw an audio waveform bar graph centered at (cx, cy)."""
    amplitudes = [
        0.30, 0.50, 0.70, 0.90, 1.00, 0.85, 0.60, 0.40, 0.25,
        0.25, 0.40, 0.60, 0.85, 1.00, 0.90, 0.70, 0.50, 0.30,
    ]
    bar_w = max(2, width // (num_bars * 2))
    spacing = width / num_bars
    for i, amp in enumerate(amplitudes[:num_bars]):
        bx = cx - width / 2 + spacing * i + spacing / 2
        bh = height * amp * amplitude_scale
        r = bar_w // 2
        draw.rounded_rectangle(
            [bx - r, cy - bh / 2, bx + r, cy + bh / 2],
            radius=r, fill=color,
        )


def draw_bridge_arch(draw, cx, cy, span, rise, color, line_width=4):
    """Draw a parabolic arch (bridge) using polyline."""
    steps = 60
    pts = []
    for i in range(steps + 1):
        t = i / steps  # 0..1
        x = cx - span / 2 + span * t
        y = cy + rise * (4 * t * t - 4 * t)  # parabola peaking at t=0.5
        pts.append((x, y))
    draw.line(pts, fill=color, width=line_width, joint="curve")
    # pylons
    pylon_h = rise * 0.55
    for frac in [0.25, 0.75]:
        px = cx - span / 2 + span * frac
        py_top = cy - pylon_h + rise * (4 * frac * frac - 4 * frac)
        draw.line([(px, cy), (px, py_top)], fill=color, width=line_width)
    # deck (road)
    draw.line([(cx - span / 2, cy), (cx + span / 2, cy)], fill=color, width=line_width)


# ──────────────────────────────────────────────────────────────
# 1. ICON  288 × 288
# ──────────────────────────────────────────────────────────────
def make_icon(path):
    W, H = 288, 288
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded background
    draw.rounded_rectangle([0, 0, W - 1, H - 1], radius=40, fill=BG)

    # Subtle green glow circle behind waveform
    glow_r = 100
    cx, cy = W // 2, H // 2
    for i in range(20, 0, -1):
        alpha = int(18 * (i / 20))
        draw.ellipse(
            [cx - glow_r - i * 2, cy - glow_r - i * 2,
             cx + glow_r + i * 2, cy + glow_r + i * 2],
            fill=(*GREEN, alpha),
        )

    # Bridge arch — upper half
    draw_bridge_arch(draw, cx, cy - 14, span=180, rise=52,
                     color=GREEN, line_width=5)

    # Waveform — lower half, inside arch footprint
    draw_waveform(draw, cx, cy + 30, width=160, height=54,
                  color=GREEN, num_bars=14, amplitude_scale=1.0)

    # "SB" monogram subtle text
    font_big = load_font(28, bold=True)
    draw.text((cx, cy - 60), "ShadowBridge", font=font_big,
              fill=(*WHITE, 200), anchor="mm")

    img.save(path, "PNG")
    print(f"Saved icon: {path}")


# ──────────────────────────────────────────────────────────────
# 2. THUMBNAIL  1920 × 960
# ──────────────────────────────────────────────────────────────
def rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def make_thumbnail(path):
    W, H = 1920, 960
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # ── Background gradient bands ──────────────────────────────
    for y in range(H):
        intensity = int(6 * (1 - y / H))
        draw.line([(0, y), (W, y)], fill=(15 + intensity, 15 + intensity, 15 + intensity))

    # Divider glow
    mid = W // 2
    for i in range(30, 0, -1):
        alpha_val = max(0, 80 - i * 3)
        draw.line([(mid, 0), (mid, H)],
                  fill=(74, 222, 128))  # simplified; use alpha below
    # Green divider line
    draw.line([(mid, 60), (mid, H - 60)], fill=GREEN, width=2)

    # ════════════════════════════════════════════════════════════
    # LEFT — App UI mockup
    # ════════════════════════════════════════════════════════════
    margin = 60
    ui_x1, ui_y1 = margin, 120
    ui_x2, ui_y2 = mid - 40, H - 120
    ui_w = ui_x2 - ui_x1
    ui_h = ui_y2 - ui_y1

    # App window frame
    rounded_rect(draw, [ui_x1, ui_y1, ui_x2, ui_y2],
                 radius=14, fill=DARK_PANEL, outline=(50, 50, 50), width=1)

    # Title bar
    tb_h = 36
    rounded_rect(draw, [ui_x1, ui_y1, ui_x2, ui_y1 + tb_h],
                 radius=14, fill=PANEL2)
    draw.rectangle([ui_x1, ui_y1 + tb_h // 2, ui_x2, ui_y1 + tb_h], fill=PANEL2)

    # Traffic lights
    for idx, col in enumerate([(239, 68, 68), (251, 191, 36), (74, 222, 128)]):
        draw.ellipse([ui_x1 + 14 + idx * 20, ui_y1 + 11,
                      ui_x1 + 24 + idx * 20, ui_y1 + 21], fill=col)

    title_font = load_font(14, bold=True)
    draw.text(((ui_x1 + ui_x2) // 2, ui_y1 + 18), "ShadowBridge",
              font=title_font, fill=WHITE, anchor="mm")

    # ── Sidebar ─────────────────────────────────────────────────
    sb_w = 130
    draw.rectangle([ui_x1, ui_y1 + tb_h, ui_x1 + sb_w, ui_y2], fill=PANEL2)

    label_font = load_font(11)
    label_bold = load_font(11, bold=True)
    nav_items = ["Dashboard", "Routing", "Channels", "Stream Deck", "Settings"]
    for i, item in enumerate(nav_items):
        ny = ui_y1 + tb_h + 20 + i * 34
        is_active = i == 1
        if is_active:
            draw.rounded_rectangle([ui_x1 + 6, ny - 6, ui_x1 + sb_w - 6, ny + 20],
                                   radius=6, fill=(74, 222, 128, 40))
            draw.text((ui_x1 + sb_w // 2, ny + 7), item,
                      font=label_bold, fill=GREEN, anchor="mm")
        else:
            draw.text((ui_x1 + sb_w // 2, ny + 7), item,
                      font=label_font, fill=GRAY, anchor="mm")

    # ── Main content area — Routing panel ───────────────────────
    content_x = ui_x1 + sb_w + 10
    content_y = ui_y1 + tb_h + 12
    content_w = ui_x2 - content_x - 10

    section_font = load_font(13, bold=True)
    small_font = load_font(10)

    draw.text((content_x, content_y), "Audio Routing", font=section_font, fill=WHITE)
    content_y += 24

    # Channel rows
    channels = [
        ("Mic",        0.72, True,  GREEN),
        ("Desktop",    0.55, True,  GREEN),
        ("Discord",    0.38, True,  GREEN),
        ("Music",      0.20, False, GRAY),
        ("Game Audio", 0.65, True,  GREEN),
        ("SFX",        0.45, True,  GREEN),
    ]
    row_h = (ui_y2 - content_y - 12) // len(channels)
    for i, (name, level, active, accent) in enumerate(channels):
        ry = content_y + i * row_h
        # Row bg
        row_fill = (28, 28, 28) if i % 2 == 0 else (32, 32, 32)
        draw.rounded_rectangle([content_x, ry + 2, content_x + content_w, ry + row_h - 2],
                                radius=6, fill=row_fill)

        # Active dot
        dot_col = GREEN if active else (80, 80, 80)
        draw.ellipse([content_x + 8, ry + row_h // 2 - 5,
                      content_x + 18, ry + row_h // 2 + 5], fill=dot_col)

        # Name
        draw.text((content_x + 28, ry + row_h // 2), name,
                  font=small_font, fill=WHITE if active else GRAY, anchor="lm")

        # Meter bar
        bar_x1 = content_x + 95
        bar_x2 = content_x + content_w - 60
        bar_y = ry + row_h // 2
        bar_h2 = 5
        draw.rounded_rectangle([bar_x1, bar_y - bar_h2, bar_x2, bar_y + bar_h2],
                                radius=bar_h2, fill=(45, 45, 45))
        fill_w = int((bar_x2 - bar_x1) * level)
        if fill_w > 0 and active:
            draw.rounded_rectangle([bar_x1, bar_y - bar_h2, bar_x1 + fill_w, bar_y + bar_h2],
                                   radius=bar_h2, fill=accent)

        # dB label
        db_val = int(-20 + level * 20)
        db_str = f"{db_val:+d} dB"
        draw.text((content_x + content_w - 10, ry + row_h // 2), db_str,
                  font=small_font, fill=GRAY, anchor="rm")

    # Connection status bar at bottom of app
    status_y = ui_y2 - 28
    draw.rectangle([ui_x1, status_y, ui_x2, ui_y2], fill=(20, 20, 20))
    draw.ellipse([ui_x1 + 10, status_y + 8, ui_x1 + 20, status_y + 20], fill=GREEN)
    draw.text((ui_x1 + 28, status_y + 14), "Connected  •  Stream Deck MK.2  •  48kHz",
              font=small_font, fill=GRAY, anchor="lm")

    # ════════════════════════════════════════════════════════════
    # RIGHT — Stream Deck buttons
    # ════════════════════════════════════════════════════════════
    deck_cx = mid + (W - mid) // 2
    deck_cy = H // 2

    # Stream Deck device frame
    dev_w, dev_h = 500, 360
    dev_x1 = deck_cx - dev_w // 2
    dev_y1 = deck_cy - dev_h // 2
    dev_x2 = dev_x1 + dev_w
    dev_y2 = dev_y1 + dev_h
    draw.rounded_rectangle([dev_x1, dev_y1, dev_x2, dev_y2],
                            radius=22, fill=(22, 22, 22), outline=(55, 55, 55), width=2)

    # Device label
    dev_font = load_font(10)
    draw.text((deck_cx, dev_y1 + 14), "STREAM DECK MK.2",
              font=dev_font, fill=(90, 90, 90), anchor="mm")

    # 3 × 5 button grid
    cols, rows = 5, 3
    btn_size = 72
    gap = 10
    grid_w = cols * btn_size + (cols - 1) * gap
    grid_h = rows * btn_size + (rows - 1) * gap
    gx0 = deck_cx - grid_w // 2
    gy0 = deck_cy - grid_h // 2 + 10

    btn_font_big = load_font(12, bold=True)
    btn_font_sm = load_font(9)

    # Button definitions: (label_top, label_bot, bg, fg)
    LIVE_BG = (60, 20, 20)
    LIVE_ACT = (239, 68, 68)
    GREEN_BG = (20, 45, 30)

    buttons = [
        # Row 0
        ("START/STOP", "● LIVE",    LIVE_BG,       RED_LIVE),
        ("MIC",        "● ON",      GREEN_BG,      GREEN),
        ("DESKTOP",    "● ON",      GREEN_BG,      GREEN),
        ("DISCORD",    "● ON",      GREEN_BG,      GREEN),
        ("SCENE",      "GAME",      PANEL3,        WHITE),
        # Row 1
        ("VOL ▲",      "Master",   PANEL3,        GRAY),
        ("VOL ▼",      "Master",   PANEL3,        GRAY),
        ("MUSIC",      "● OFF",    PANEL3,        (100, 100, 100)),
        ("MUTE ALL",   "⏸",        (40, 20, 20),  (200, 80, 80)),
        ("SCENE",      "JUST CHAT",PANEL3,        WHITE),
        # Row 2
        ("SFX ▲",      "Fader",    PANEL3,        GRAY),
        ("SFX ▼",      "Fader",    PANEL3,        GRAY),
        ("GAME",       "● ON",     GREEN_BG,      GREEN),
        ("ALERTS",     "● ON",     GREEN_BG,      GREEN),
        ("STATUS",     "✓ OK",     (20, 35, 20),  GREEN),
    ]

    for idx, (top, bot, bg, fg) in enumerate(buttons):
        col = idx % cols
        row = idx // cols
        bx1 = gx0 + col * (btn_size + gap)
        by1 = gy0 + row * (btn_size + gap)
        bx2 = bx1 + btn_size
        by2 = by1 + btn_size

        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=8, fill=bg, outline=(55, 55, 55), width=1)

        # Top label
        draw.text(((bx1 + bx2) // 2, by1 + 20), top,
                  font=btn_font_sm, fill=GRAY, anchor="mm")
        # Bottom label (accent)
        draw.text(((bx1 + bx2) // 2, by2 - 18), bot,
                  font=btn_font_big, fill=fg, anchor="mm")

        # Glow on LIVE button
        if idx == 0:
            for gi in range(8, 0, -1):
                draw.rounded_rectangle(
                    [bx1 - gi, by1 - gi, bx2 + gi, by2 + gi],
                    radius=8 + gi, outline=(*RED_LIVE, 15 * gi), width=1,
                )

    # ── Logo + Tagline centered at top ──────────────────────────
    logo_font = load_font(52, bold=True)
    tag_font = load_font(22)
    sub_font = load_font(18)

    title_y = 48
    # Shadow
    draw.text((mid + 3, title_y + 3), "ShadowBridge",
              font=logo_font, fill=(0, 0, 0), anchor="mt")
    draw.text((mid, title_y), "ShadowBridge",
              font=logo_font, fill=WHITE, anchor="mt")

    tagline_y = title_y + 68
    draw.text((mid, tagline_y), "Audio routing built for streamers",
              font=tag_font, fill=GREEN, anchor="mt")

    # Accent underline
    ul_w = 340
    draw.rounded_rectangle(
        [mid - ul_w // 2, tagline_y + 34, mid + ul_w // 2, tagline_y + 37],
        radius=2, fill=GREEN,
    )

    # Version badge
    badge_font = load_font(12, bold=True)
    draw.rounded_rectangle([mid - 48, H - 60, mid + 48, H - 32],
                            radius=10, fill=GREEN_BG, outline=GREEN, width=1)
    draw.text((mid, H - 46), "v1.0  •  Free",
              font=badge_font, fill=GREEN, anchor="mm")

    # Left-side waveform decoration (behind app, subtle)
    for i in range(3, 0, -1):
        draw_waveform(draw, margin + 30, H - 50, width=140, height=28,
                      color=(74, 222, 128, 20 * i), num_bars=12)

    img.save(path, "PNG")
    print(f"Saved thumbnail: {path}")


if __name__ == "__main__":
    base = r"C:\Users\ajsme\OneDrive\Documents\GitHub\ShadowBridge"
    make_icon(f"{base}\\marketplace-icon.png")
    make_thumbnail(f"{base}\\marketplace-thumbnail.png")
    print("Done.")
