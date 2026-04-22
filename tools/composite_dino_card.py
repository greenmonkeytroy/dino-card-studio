"""
Composite a dino battle card from artwork + text inputs.
Usage: py tools/composite_dino_card.py --title "T-Rex" --action attack --footer "..." --border volcanic --artwork .tmp/art.png
"""
import argparse
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

# --- Card dimensions ---
W, H = 750, 1050
BORDER = 35
PAD = 12
IX = BORDER + PAD          # inner x start = 47
IW = W - 2 * IX            # inner width  = 656

TITLE_Y1, TITLE_Y2 = 48, 126
IMAGE_Y1, IMAGE_Y2 = 142, 748   # extends behind the action pill
ACTION_W = 310
ACTION_Y1, ACTION_Y2 = 672, 737
ACTION_X1 = (W - ACTION_W) // 2
ACTION_X2 = ACTION_X1 + ACTION_W
FOOTER_Y1, FOOTER_Y2 = 752, 992

PILL_RADIUS = 14

# --- Border style presets ---
STYLES = {
    "bone": {
        "border": (180, 150, 90),
        "border_inner": (220, 185, 120),
        "card_bg": (245, 238, 218),
        "pill_bg": (101, 76, 14),
        "pill_text": (255, 248, 220),
        "accent": (139, 105, 20),
        "corner": "bone",
        "edge_dot": (160, 130, 70),
    },
    "stone": {
        "border": (60, 60, 60),
        "border_inner": (90, 90, 90),
        "card_bg": (38, 38, 38),
        "pill_bg": (25, 25, 25),
        "pill_text": (210, 210, 210),
        "accent": (140, 140, 140),
        "corner": "stone",
        "edge_dot": (100, 100, 100),
    },
    "jungle": {
        "border": (25, 80, 25),
        "border_inner": (45, 110, 45),
        "card_bg": (10, 35, 10),
        "pill_bg": (8, 28, 8),
        "pill_text": (160, 240, 160),
        "accent": (60, 160, 60),
        "corner": "jungle",
        "edge_dot": (40, 120, 40),
    },
    "volcanic": {
        "border": (120, 30, 0),
        "border_inner": (160, 55, 5),
        "card_bg": (22, 5, 0),
        "pill_bg": (70, 12, 0),
        "pill_text": (255, 195, 140),
        "accent": (220, 80, 0),
        "corner": "volcanic",
        "edge_dot": (200, 70, 0),
    },
    "ice": {
        "border": (20, 65, 105),
        "border_inner": (40, 100, 150),
        "card_bg": (5, 18, 35),
        "pill_bg": (5, 18, 35),
        "pill_text": (170, 225, 255),
        "accent": (80, 170, 230),
        "corner": "ice",
        "edge_dot": (60, 140, 200),
    },
}

ACTION_COLORS = {
    "attack":  (160, 25, 25),
    "defend":  (25, 70, 160),
    "flee":    (25, 120, 65),
    "dodge":   (130, 75, 15),
    "roar":    (110, 25, 120),
    "stomp":   (85, 55, 15),
    "charge":  (160, 90, 0),
    "bite":    (130, 0, 50),
    "crush":   (55, 35, 15),
    "ambush":  (15, 55, 20),
}

ACTION_ICONS = {
    "attack": "⚔",  "defend": "🛡",  "flee": "💨",   "dodge": "↩",
    "roar":   "🦷",  "stomp":  "🦶",  "charge": "⚡", "bite":  "🦴",
    "crush":  "✊",   "ambush": "👁",
}


def load_font(candidates: list, size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default(size=size)


def get_fonts():
    bold_candidates = [
        "C:/Windows/Fonts/impact.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    serif_candidates = [
        "C:/Windows/Fonts/georgiab.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
    ]
    return {
        "title":  load_font(bold_candidates, 52),
        "action": load_font(bold_candidates, 30),
        "footer": load_font(serif_candidates, 22),
        "label":  load_font(bold_candidates, 18),
    }


def draw_rounded_rect(draw, xy, radius, fill, outline=None, outline_width=2):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill,
                           outline=outline, width=outline_width)


def draw_border_corners(draw, style, s):
    accent = s["accent"]
    edge = s["edge_dot"]
    corner = s["corner"]
    cs = 28  # corner decoration size
    inset = 6

    positions = [
        (BORDER + inset, BORDER + inset),
        (W - BORDER - inset - cs, BORDER + inset),
        (BORDER + inset, H - BORDER - inset - cs),
        (W - BORDER - inset - cs, H - BORDER - inset - cs),
    ]

    for px, py in positions:
        if corner == "bone":
            # Cross/bone shape
            draw.rectangle([px + cs//3, py, px + 2*cs//3, py + cs], fill=accent)
            draw.rectangle([px, py + cs//3, px + cs, py + 2*cs//3], fill=accent)
            for ox, oy in [(px, py), (px+cs-8, py), (px, py+cs-8), (px+cs-8, py+cs-8)]:
                draw.ellipse([ox, oy, ox+8, oy+8], fill=accent)
        elif corner == "stone":
            # Diamond
            cx, cy = px + cs//2, py + cs//2
            pts = [(cx, py), (px+cs, cy), (cx, py+cs), (px, cy)]
            draw.polygon(pts, fill=accent)
        elif corner == "jungle":
            # Filled spiral approximation — concentric arcs
            for r in range(4, cs//2, 4):
                draw.arc([px+cs//2-r, py+cs//2-r, px+cs//2+r, py+cs//2+r],
                         0, 270, fill=accent, width=2)
        elif corner == "volcanic":
            # Flame triangles pointing inward
            cx = px + cs // 2
            pts = [(cx, py), (px, py+cs), (px+cs, py+cs)]
            draw.polygon(pts, fill=accent)
        elif corner == "ice":
            # Asterisk / star
            cx, cy = px + cs//2, py + cs//2
            for angle_pts in [
                [(cx, py), (cx, py+cs)],
                [(px, cy), (px+cs, cy)],
                [(px, py), (px+cs, py+cs)],
                [(px+cs, py), (px, py+cs)],
            ]:
                draw.line(angle_pts, fill=accent, width=2)

    # Edge dots along border midpoints
    dot_r = 3
    step = 40
    for x in range(BORDER + step, W - BORDER, step):
        for y in [BORDER // 2, H - BORDER // 2]:
            draw.ellipse([x-dot_r, y-dot_r, x+dot_r, y+dot_r], fill=edge)
    for y in range(BORDER + step, H - BORDER, step):
        for x in [BORDER // 2, W - BORDER // 2]:
            draw.ellipse([x-dot_r, y-dot_r, x+dot_r, y+dot_r], fill=edge)


def draw_card_border(img, draw, s):
    # Outer border fill
    draw.rectangle([0, 0, W, H], fill=s["border"])
    # Inner lighter border line
    draw.rectangle([BORDER-4, BORDER-4, W-BORDER+4, H-BORDER+4],
                   outline=s["border_inner"], width=3)
    # Card background
    draw.rounded_rectangle([BORDER, BORDER, W-BORDER, H-BORDER],
                            radius=8, fill=s["card_bg"])
    # Inner accent line just inside border
    draw.rounded_rectangle([BORDER+6, BORDER+6, W-BORDER-6, H-BORDER-6],
                            radius=6, outline=s["accent"], width=1)
    draw_border_corners(draw, s["corner"], s)


def fit_image_to_area(artwork_path, target_w, target_h, scale=1.0, offset_x=0.0, offset_y=0.0):
    """
    scale: multiplier on top of cover-fit. 1.0 fills the area. >1 zooms in. <1 letterboxes.
    offset_x/y: -1.0 to 1.0, pan within available overflow. 0 = center.
    """
    art = Image.open(artwork_path).convert("RGBA")
    art_ratio = art.width / art.height
    target_ratio = target_w / target_h
    if art_ratio > target_ratio:
        base_h = target_h
        base_w = int(art_ratio * base_h)
    else:
        base_w = target_w
        base_h = int(base_w / art_ratio)

    new_w = max(1, int(base_w * scale))
    new_h = max(1, int(base_h * scale))
    art = art.resize((new_w, new_h), Image.LANCZOS)

    # Center crop origin, then shift by offset within the available overflow
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    if new_w > target_w:
        left += int(offset_x * (new_w - target_w) / 2)
    if new_h > target_h:
        top += int(offset_y * (new_h - target_h) / 2)
    left = max(0, min(left, max(0, new_w - target_w)))
    top = max(0, min(top, max(0, new_h - target_h)))

    # When scale < 1 image is smaller than target — paste centred on black canvas
    if new_w < target_w or new_h < target_h:
        canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 255))
        canvas.paste(art, ((target_w - new_w) // 2, (target_h - new_h) // 2))
        return canvas

    return art.crop((left, top, left + target_w, top + target_h))


def draw_title(draw, fonts, title: str, s):
    draw_rounded_rect(draw, [IX, TITLE_Y1, IX+IW, TITLE_Y2],
                      PILL_RADIUS, s["pill_bg"], s["accent"], 2)
    text = title.upper()
    font = fonts["title"]
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (W - tw) // 2
    ty = TITLE_Y1 + (TITLE_Y2 - TITLE_Y1 - th) // 2 - bbox[1]
    # Shadow
    draw.text((tx+2, ty+2), text, font=font, fill=(0, 0, 0, 160))
    draw.text((tx, ty), text, font=font, fill=s["pill_text"])


def draw_action_pill(draw, fonts, action: str, s):
    color = ACTION_COLORS.get(action, (80, 80, 80))
    darker = tuple(max(0, c - 40) for c in color)
    draw_rounded_rect(draw, [ACTION_X1, ACTION_Y1, ACTION_X2, ACTION_Y2],
                      PILL_RADIUS, color, darker, 2)
    text = action.upper()
    font = fonts["action"]
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = ACTION_X1 + (ACTION_W - tw) // 2
    ty = ACTION_Y1 + (ACTION_Y2 - ACTION_Y1 - th) // 2 - bbox[1]
    draw.text((tx+1, ty+1), text, font=font, fill=(0, 0, 0, 140))
    draw.text((tx, ty), text, font=font, fill=(255, 255, 255))


def draw_footer(draw, fonts, footer: str, s):
    draw_rounded_rect(draw, [IX, FOOTER_Y1, IX+IW, FOOTER_Y2],
                      PILL_RADIUS, s["pill_bg"], s["accent"], 2)
    font = fonts["footer"]
    max_chars = 42
    lines = []
    for para in footer.split("\n"):
        lines.extend(textwrap.wrap(para, width=max_chars) or [""])
    line_h = 30
    total_h = len(lines) * line_h
    start_y = FOOTER_Y1 + ((FOOTER_Y2 - FOOTER_Y1) - total_h) // 2
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        tx = IX + (IW - tw) // 2
        ty = start_y + i * line_h
        draw.text((tx+1, ty+1), line, font=font, fill=(0, 0, 0, 120))
        draw.text((tx, ty), line, font=font, fill=s["pill_text"])


def draw_image_frame(draw, s):
    draw.rounded_rectangle([IX-2, IMAGE_Y1-2, IX+IW+2, IMAGE_Y2+2],
                            radius=6, outline=s["accent"], width=2)


def composite_card(title, action, footer, border_style, artwork_path, output_path,
                   art_scale=1.0, art_offset_x=0.0, art_offset_y=0.0):
    s = STYLES.get(border_style)
    if not s:
        raise ValueError(f"Unknown border style '{border_style}'. Choose: {list(STYLES)}")
    if action not in ACTION_COLORS:
        raise ValueError(f"Unknown action '{action}'. Choose: {list(ACTION_COLORS)}")

    img = Image.new("RGB", (W, H), s["border"])
    draw = ImageDraw.Draw(img, "RGBA")
    fonts = get_fonts()

    draw_card_border(img, draw, s)

    # Artwork
    art_w = IW
    art_h = IMAGE_Y2 - IMAGE_Y1
    art = fit_image_to_area(artwork_path, art_w, art_h, art_scale, art_offset_x, art_offset_y)
    art_rgb = art.convert("RGB")
    img.paste(art_rgb, (IX, IMAGE_Y1))

    draw_image_frame(draw, s)
    draw_title(draw, fonts, title, s)
    draw_action_pill(draw, fonts, action, s)
    draw_footer(draw, fonts, footer, s)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, "PNG")
    print(f"Card saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Composite a dino battle card")
    parser.add_argument("--title", required=True)
    parser.add_argument("--action", required=True, choices=list(ACTION_COLORS))
    parser.add_argument("--footer", required=True)
    parser.add_argument("--border", required=True, choices=list(STYLES))
    parser.add_argument("--artwork", required=True, help="Path to artwork PNG")
    parser.add_argument("--output", default=None, help="Output PNG path")
    args = parser.parse_args()

    slug = args.title.lower().replace(" ", "_")
    output = args.output or f"output/{slug}.png"
    composite_card(args.title, args.action, args.footer, args.border, args.artwork, output)


if __name__ == "__main__":
    main()
