#!/usr/bin/env python3
"""
make_avatar.py - Build a PS4 profile avatar set from ONE image.

Produces the five files the PS4 profile cache expects:

    avatar64.dds
    avatar128.dds
    avatar260.dds
    avatar440.dds
    avatar440.png

The .dds files are square, DXT5 (BC3) compressed, no mipmaps - the format
used by /system_data/priv/cache/profile/0x<userid>/ on PS4.

online.json and version.json are account/cache metadata, not image data.
Copy them from an existing profile folder (see --copy-json).

Usage:
    python make_avatar.py photo.jpg
    python make_avatar.py photo.jpg --out "D:\\...\\Avatar" --circle
    python make_avatar.py photo.jpg --mode fit --copy-json dumped_profile

Requires: Pillow  (pip install Pillow)
"""

import argparse
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Error: Pillow is required. Install with: pip install Pillow")

from ps4_avatar.dds import SIZES, image_to_dxt5_dds
from ps4_avatar.imaging import MASK_SHAPES, apply_mask


def prepare_square(src, mode):
    """Return an RGBA square image from the source."""
    src = ImageOps.exif_transpose(src)
    if src.mode != "RGBA":
        src = src.convert("RGBA")

    if mode == "stretch":
        return src

    w, h = src.size
    side = min(w, h)

    if mode == "crop":
        left = (w - side) // 2
        top = (h - side) // 2
        return src.crop((left, top, left + side, top + side))

    # mode == "fit": pad to square with transparency
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(src, ((side - w) // 2, (side - h) // 2), src)
    return canvas


def build_set(source, out_dir, mode="crop", mask="Square",
              png_name="avatar440.png", also_avatar_png=False,
              copy_json_from=None):
    src = Image.open(source)
    square = prepare_square(src, mode)

    out_dir.mkdir(parents=True, exist_ok=True)

    for size in SIZES:
        resized = square.resize((size, size), Image.Resampling.LANCZOS)
        resized = apply_mask(resized, mask)

        dds = image_to_dxt5_dds(resized)
        path = out_dir / f"avatar{size}.dds"
        path.write_bytes(dds)
        print(f"  wrote {path.name:16s} {size}x{size}  ({len(dds):,} bytes)")

        if size == 440:
            png_path = out_dir / png_name
            resized.save(png_path, "PNG")
            print(f"  wrote {png_path.name:16s} {size}x{size}")
            if also_avatar_png and png_name != "avatar.png":
                resized.save(out_dir / "avatar.png", "PNG")
                print("  wrote avatar.png       440x440")

    # online.json / version.json are metadata - copy, never invent.
    copied = []
    if copy_json_from:
        src_dir = Path(copy_json_from)
        for name in ("online.json", "version.json"):
            candidate = src_dir / name
            if candidate.is_file():
                shutil.copy2(candidate, out_dir / name)
                copied.append(name)
    for name in ("online.json", "version.json"):
        if (out_dir / name).is_file():
            continue
        print(f"  NOTE: {name} missing - copy it from your PS4 profile dump.")

    return out_dir


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Create PS4 avatar .dds/.png files from one image.")
    p.add_argument("source", help="input image (png/jpg/jpeg/webp/bmp)")
    p.add_argument("--out", default="output",
                   help="output folder (default: output)")
    p.add_argument("--mode", choices=("crop", "fit", "stretch"),
                   default="crop",
                   help="crop = centre square (default), fit = pad, "
                        "stretch = distort")
    p.add_argument("--mask", choices=MASK_SHAPES, default="Square",
                   help="alpha mask shape (default: Square)")
    p.add_argument("--circle", action="store_true",
                   help="shorthand for --mask Circle (PS4-style round avatar)")
    p.add_argument("--png", default="avatar440.png",
                   help="name of the 440px PNG (default: avatar440.png)")
    p.add_argument("--also-avatar-png", action="store_true",
                   help="also write avatar.png (used by some tools)")
    p.add_argument("--copy-json", metavar="DIR",
                   help="copy online.json and version.json from this folder")
    args = p.parse_args(argv)

    source = Path(args.source)
    if not source.is_file():
        sys.exit(f"Error: input image not found: {source}")

    mask = "Circle" if args.circle else args.mask
    print(f"Source: {source}  (mode={args.mode}, mask={mask})")
    out = build_set(source, Path(args.out), mode=args.mode, mask=mask,
                    png_name=args.png, also_avatar_png=args.also_avatar_png,
                    copy_json_from=args.copy_json)
    print(f"\nDone. Avatar set is in: {out.resolve()}")


if __name__ == "__main__":
    main()
