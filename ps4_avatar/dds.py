"""DDS / DXT5 (BC3) encoder for PS4 profile avatars."""

import struct

from PIL import Image

DDS_MAGIC = 0x20534444  # "DDS "
DDSD_CAPS = 0x1
DDSD_HEIGHT = 0x2
DDSD_WIDTH = 0x4
DDSD_PIXELFORMAT = 0x1000
DDSD_LINEARSIZE = 0x80000
DDPF_FOURCC = 0x4
DDSCAPS_TEXTURE = 0x1000
FOURCC_DXT5 = 0x35545844  # "DXT5"

SIZES = (64, 128, 260, 440)


def _rgb_to_565(r, g, b):
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def _rgb565_to_rgb(c):
    return ((c >> 11) & 0x1F) << 3, ((c >> 5) & 0x3F) << 2, (c & 0x1F) << 3


def compress_dxt5_block(pixels):
    """16 RGBA tuples (4x4, row major) -> 16-byte DXT5 block."""
    alphas = [p[3] for p in pixels]
    a0, a1 = max(alphas), min(alphas)

    if a0 > a1:
        ap = [a0, a1] + [((6 - i) * a0 + (1 + i) * a1) // 7 for i in range(6)]
    else:
        ap = [a0, a1] + [((4 - i) * a0 + (1 + i) * a1) // 5 for i in range(4)] + [0, 255]

    ai = 0
    for i, a in enumerate(alphas):
        best, best_d = 0, abs(a - ap[0])
        for j in range(1, 8):
            d = abs(a - ap[j])
            if d < best_d:
                best, best_d = j, d
        ai |= best << (i * 3)

    alpha_block = struct.pack(
        "<BBHHH", a0, a1, ai & 0xFFFF, (ai >> 16) & 0xFFFF, (ai >> 32) & 0xFFFF
    )

    mnr = mng = mnb = 255
    mxr = mxg = mxb = 0
    for p in pixels:
        r, g, b = p[0], p[1], p[2]
        mnr = min(mnr, r); mxr = max(mxr, r)
        mng = min(mng, g); mxg = max(mxg, g)
        mnb = min(mnb, b); mxb = max(mxb, b)

    c0 = _rgb_to_565(mxr, mxg, mxb)
    c1 = _rgb_to_565(mnr, mng, mnb)
    if c0 < c1:
        c0, c1 = c1, c0
    elif c0 == c1:
        c0 = min(c0 + 1, 0xFFFF)

    p0, p1 = _rgb565_to_rgb(c0), _rgb565_to_rgb(c1)
    palette = (
        p0,
        p1,
        ((2 * p0[0] + p1[0]) // 3, (2 * p0[1] + p1[1]) // 3, (2 * p0[2] + p1[2]) // 3),
        ((p0[0] + 2 * p1[0]) // 3, (p0[1] + 2 * p1[1]) // 3, (p0[2] + 2 * p1[2]) // 3),
    )

    ci = 0
    for i, p in enumerate(pixels):
        r, g, b = p[0], p[1], p[2]
        q = palette[0]
        best, best_d = 0, (r - q[0]) ** 2 + (g - q[1]) ** 2 + (b - q[2]) ** 2
        for j in range(1, 4):
            q = palette[j]
            d = (r - q[0]) ** 2 + (g - q[1]) ** 2 + (b - q[2]) ** 2
            if d < best_d:
                best, best_d = j, d
        ci |= best << (i * 2)

    return alpha_block + struct.pack("<HHI", c0, c1, ci)


def image_to_dxt5_dds(img):
    """Complete single-surface DXT5 DDS file as bytes."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    w, h = img.size
    pad_w, pad_h = (-w) % 4, (-h) % 4
    if pad_w or pad_h:
        canvas = Image.new("RGBA", (w + pad_w, h + pad_h), (0, 0, 0, 0))
        canvas.paste(img, (0, 0))
        img = canvas
        w, h = img.size

    data = img.tobytes()
    out = bytearray()
    for by in range(0, h, 4):
        for bx in range(0, w, 4):
            block = []
            for py in range(4):
                row = (by + py) * w * 4
                for px in range(4):
                    o = row + (bx + px) * 4
                    block.append((data[o], data[o + 1], data[o + 2], data[o + 3]))
            out += compress_dxt5_block(block)

    header = struct.pack(
        "<IIIIIII",
        124,
        DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_LINEARSIZE,
        h, w, (w // 4) * (h // 4) * 16, 0, 0,
    )
    header += b"\x00" * 44
    header += struct.pack("<IIIIIIII", 32, DDPF_FOURCC, FOURCC_DXT5, 0, 0, 0, 0, 0)
    header += struct.pack("<IIIII", DDSCAPS_TEXTURE, 0, 0, 0, 0)
    return struct.pack("<I", DDS_MAGIC) + header + bytes(out)
