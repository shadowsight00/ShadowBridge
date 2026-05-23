"""Generate NSIS installer bitmap assets for ShadowBridge."""
from PIL import Image, ImageDraw, ImageFont
import os

ASSETS = os.path.dirname(__file__) + "/assets"
os.makedirs(ASSETS, exist_ok=True)

ICON_PATH = os.path.dirname(__file__) + "/../icons/128x128.png"

def make_header():
    """150x57 header banner — dark bg with app name."""
    w, h = 150, 57
    img = Image.new("RGB", (w, h), "#0d1117")
    draw = ImageDraw.Draw(img)

    # Try to paste the app icon (small)
    icon_size = 40
    try:
        icon = Image.open(ICON_PATH).convert("RGBA").resize((icon_size, icon_size), Image.LANCZOS)
        img.paste(icon, (8, (h - icon_size) // 2), icon)
    except Exception:
        pass

    # App name text
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 14)
    except Exception:
        font = ImageFont.load_default()

    text_x = icon_size + 14
    draw.text((text_x, 10), "ShadowBridge", fill="#e6edf3", font=font)
    try:
        small_font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 10)
    except Exception:
        small_font = font
    draw.text((text_x, 30), "Dual-PC Audio Router", fill="#8b949e", font=small_font)

    img.save(os.path.join(ASSETS, "header.bmp"), "BMP")
    print("header.bmp created")

def make_sidebar():
    """164x314 sidebar banner — darker bg with centered logo."""
    w, h = 164, 314
    img = Image.new("RGB", (w, h), "#090d13")
    draw = ImageDraw.Draw(img)

    # Subtle gradient strip on right edge
    for x in range(w - 4, w):
        alpha = (x - (w - 4)) / 4
        col = int(20 + alpha * 10)
        draw.line([(x, 0), (x, h)], fill=(col, col + 5, col + 15))

    # App icon centered in upper 2/3
    icon_size = 80
    icon_x = (w - icon_size) // 2
    icon_y = 60
    try:
        icon = Image.open(ICON_PATH).convert("RGBA").resize((icon_size, icon_size), Image.LANCZOS)
        img.paste(icon, (icon_x, icon_y), icon)
    except Exception:
        # Fallback: colored rectangle
        draw.rectangle([icon_x, icon_y, icon_x + icon_size, icon_y + icon_size], fill="#22c55e")

    # App name below icon
    try:
        font_lg = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 14)
        font_sm = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 10)
    except Exception:
        font_lg = ImageFont.load_default()
        font_sm = font_lg

    name = "ShadowBridge"
    bbox = draw.textbbox((0, 0), name, font=font_lg)
    text_w = bbox[2] - bbox[0]
    draw.text(((w - text_w) // 2, icon_y + icon_size + 14), name, fill="#e6edf3", font=font_lg)

    sub = "Dual-PC Audio Router"
    bbox2 = draw.textbbox((0, 0), sub, font=font_sm)
    sub_w = bbox2[2] - bbox2[0]
    draw.text(((w - sub_w) // 2, icon_y + icon_size + 34), sub, fill="#8b949e", font=font_sm)

    # Version at bottom
    ver = "v0.4.0"
    bbox3 = draw.textbbox((0, 0), ver, font=font_sm)
    ver_w = bbox3[2] - bbox3[0]
    draw.text(((w - ver_w) // 2, h - 30), ver, fill="#484f58", font=font_sm)

    img.save(os.path.join(ASSETS, "sidebar.bmp"), "BMP")
    print("sidebar.bmp created")

make_header()
make_sidebar()
print("Done.")
