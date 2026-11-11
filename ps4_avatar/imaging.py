"""Image helpers shared by the GUI and CLI."""

import math

from PIL import Image, ImageDraw

MAX_WORKING_SIZE = 2000


# --- mask shapes -----------------------------------------------------------

MASK_SHAPES = ("Square", "Circle", "Rounded", "Squircle", "Hexagon", "Octagon",
               "Star", "Diamond", "Heart")

_MASK_CACHE = {}


def _star_points(size, points=5, inner=0.42):
    import math
    cx = cy = size / 2
    outer_r = size / 2
    pts = []
    for i in range(points * 2):
        angle = -math.pi / 2 + i * math.pi / points
        r = outer_r if i % 2 == 0 else outer_r * inner
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


def _heart_points(size, samples=200):
    import math
    pts = []
    for i in range(samples):
        t = math.pi * 2 * i / samples
        x = 16 * math.sin(t) ** 3
        y = (13 * math.cos(t) - 5 * math.cos(2 * t)
             - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((x, -y))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    scale = (size * 0.96) / max(w, h)
    ox = (size - w * scale) / 2 - min(xs) * scale
    oy = (size - h * scale) / 2 - min(ys) * scale
    return [(x * scale + ox, y * scale + oy) for x, y in pts]


def _regular_points(size, sides, rotation_deg=0.0, radius=None):
    cx = cy = size / 2
    r = radius if radius is not None else size / 2
    rot = math.radians(rotation_deg)
    step = 2 * math.pi / sides
    return [(cx + r * math.cos(rot + i * step),
             cy + r * math.sin(rot + i * step)) for i in range(sides)]


def shape_mask(shape, size):
    """Antialiased alpha mask (L mode) for a named shape, cached per size."""
    if shape in (None, "", "Square", "None"):
        return None

    key = (shape, size)
    cached = _MASK_CACHE.get(key)
    if cached is not None:
        return cached

    ss = 4
    s = size * ss
    big = Image.new("L", (s, s), 0)
    draw = ImageDraw.Draw(big)

    if shape == "Circle":
        draw.ellipse((0, 0, s - 1, s - 1), fill=255)
    elif shape == "Rounded":
        draw.rounded_rectangle((0, 0, s - 1, s - 1),
                               radius=max(1, int(s * 0.18)), fill=255)
    elif shape == "Squircle":
        draw.rounded_rectangle((0, 0, s - 1, s - 1),
                               radius=max(1, int(s * 0.32)), fill=255)
    elif shape == "Hexagon":
        draw.polygon(_regular_points(s, 6, rotation_deg=0), fill=255)
    elif shape == "Octagon":
        draw.polygon(_regular_points(s, 8, rotation_deg=22.5,
                                     radius=(s / 2) / math.cos(math.pi / 8)),
                     fill=255)
    elif shape == "Diamond":
        draw.polygon([(s / 2, 0), (s, s / 2), (s / 2, s), (0, s / 2)],
                     fill=255)
    elif shape == "Star":
        draw.polygon(_star_points(s), fill=255)
    elif shape == "Heart":
        draw.polygon(_heart_points(s), fill=255)

    mask = big.resize((size, size), Image.Resampling.LANCZOS)
    _MASK_CACHE[key] = mask
    return mask


def apply_mask(img, shape):
    """Apply a named shape mask to an RGBA image (Square = unchanged)."""
    mask = shape_mask(shape, img.size[0])
    if mask is None:
        return img
    out = img.copy()
    alpha = out.getchannel("A")
    out.putalpha(Image.composite(alpha, Image.new("L", img.size, 0), mask))
    return out


def render_avatar(box, size, shape="Square", padding=0.0):
    """Render one output size from a cropped box.

    ``padding`` is a fraction of the output (0..0.45): the masked avatar is
    scaled down and centred, leaving a transparent margin around it.
    """
    pad = max(0.0, min(0.45, float(padding or 0.0)))
    inner = max(1, int(round(size * (1 - 2 * pad))))
    img = box.resize((inner, inner), Image.Resampling.LANCZOS)
    img = apply_mask(img, shape)
    if inner == size:
        return img
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    offset = (size - inner) // 2
    canvas.alpha_composite(img, (offset, offset))
    return canvas


def _arc_points(cx, cy, r, a0_deg, a1_deg, n=18):
    pts = []
    for i in range(n + 1):
        a = math.radians(a0_deg + (a1_deg - a0_deg) * i / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _rounded_rect_outline(radius_frac, n=18):
    r = max(0.0, min(0.5, radius_frac))
    if r <= 0:
        return [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    pts = [(r, 0.0), (1 - r, 0.0)]
    pts += _arc_points(1 - r, r, r, 270, 360, n)
    pts += [(1.0, r), (1.0, 1 - r)]
    pts += _arc_points(1 - r, 1 - r, r, 0, 90, n)
    pts += [(1 - r, 1.0), (r, 1.0)]
    pts += _arc_points(r, 1 - r, r, 90, 180, n)
    pts += [(0.0, 1 - r), (0.0, r)]
    pts += _arc_points(r, r, r, 180, 270, n)
    return pts


def shape_outline(shape):
    """Normalised (0..1) outline polygon for a shape, for UI overlays."""
    if shape in (None, "", "Square", "None"):
        return [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    if shape == "Circle":
        return _rounded_rect_outline(0.5)
    if shape == "Rounded":
        return _rounded_rect_outline(0.18)
    if shape == "Squircle":
        return _rounded_rect_outline(0.32)
    if shape == "Hexagon":
        return _regular_points(1.0, 6, rotation_deg=0)
    if shape == "Octagon":
        return _regular_points(1.0, 8, rotation_deg=22.5,
                               radius=0.5 / math.cos(math.pi / 8))
    if shape == "Diamond":
        return [(0.5, 0.0), (1.0, 0.5), (0.5, 1.0), (0.0, 0.5)]
    if shape == "Star":
        return _star_points(1.0)
    if shape == "Heart":
        return _heart_points(1.0)
    return [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]




def checkerboard(size, cell=12):
    """Dark checkerboard used behind transparent previews."""
    img = Image.new("RGBA", (size, size), (56, 58, 63, 255))
    draw = ImageDraw.Draw(img)
    for y in range(0, size, cell):
        for x in range(0, size, cell):
            if ((x // cell) + (y // cell)) % 2 == 0:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(70, 72, 78, 255))
    return img


_BG_CACHE = {}


def ps4_background(size):
    """PS4 home-screen style blue gradient for transparent previews.

    The console's default theme is a deep navy-to-blue gradient with soft
    light-blue waves. Drawing it behind the avatar shows what the PNG will
    look like on the PS4 dashboard.
    """
    size = max(2, int(size))
    key = ("ps4", size)
    cached = _BG_CACHE.get(key)
    if cached is not None:
        return cached

    top = (9, 28, 64)
    bottom = (34, 110, 186)
    column = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / (size - 1)
        column.putpixel((0, y), tuple(
            round(a + (b - a) * t) for a, b in zip(top, bottom)))
    img = column.resize((size, size), Image.Resampling.NEAREST).convert("RGBA")

    waves = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(waves)
    line_width = max(2, size // 48)
    for index, alpha in enumerate((34, 24, 16)):
        offset = index * 0.17
        cy = size * (1.02 + offset)
        rx = size * 1.35
        ry = size * (0.82 + offset * 0.6)
        draw.arc((size * 0.5 - rx, cy - ry, size * 0.5 + rx, cy + ry),
                 start=198, end=342, fill=(150, 208, 255, alpha),
                 width=line_width)
    img.alpha_composite(waves)

    _BG_CACHE[key] = img
    return img


def initial_crop(width, height):
    """Centre square crop for a freshly loaded image."""
    side = min(width, height)
    return ((width - side) // 2, (height - side) // 2, side)
