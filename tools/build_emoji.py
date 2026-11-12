"""Regenerate ``ps4_avatar_qt/assets/emoji/emoji.json``.

The picker's data is a curated subset of the official Unicode emoji list:

* one pass over ``emoji-test.txt`` keeps only fully-qualified entries;
* entries newer than :data:`MAX_EMOJI_VERSION` are skipped, so the set stays
  within what older Windows versions and PS4 firmware can draw;
* a round-robin across subgroups gives every category a mix of faces,
  objects and so on instead of a long run from one subgroup;
* hand-picked extras add skin tones, joined families and country flags;
* each character is finally checked against the local emoji font, so the
  picker never shows a tile the current machine cannot draw.

Usage::

    python tools/build_emoji.py                    # write the bundled file
    python tools/build_emoji.py --out build/emoji.json --any-font

``--any-font`` skips the font check, which is useful when regenerating on a
machine without a colour emoji font installed.
"""

import argparse
import json
import re
import sys
import urllib.request
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "ps4_avatar_qt" / "assets" / "emoji" / "emoji.json"
UNICODE_URL = "https://unicode.org/Public/emoji/latest/emoji-test.txt"

# Newest Emoji release we offer. Older releases are drawn by every PS4
# firmware and by Windows 10, so nothing in the picker shows as a box.
MAX_EMOJI_VERSION = 14.0

# Unicode group -> (section, label, quota)
GROUP_MAP = {
    "Smileys & Emotion": ("smileys", "Smileys & people", 58),
    "People & Body": ("smileys", "Smileys & people", 34),
    "Animals & Nature": ("animals", "Animals & nature", 44),
    "Food & Drink": ("food", "Food & drink", 40),
    "Travel & Places": ("travel", "Travel & places", 34),
    "Activities": ("activities", "Activities", 30),
    "Objects": ("objects", "Objects", 40),
    "Symbols": ("symbols", "Symbols", 44),
    "Flags": ("flags", "Flags", 0),  # explicit list below
}

SECTION_ORDER = ["smileys", "animals", "food", "travel", "activities",
                 "objects", "symbols", "flags"]

# Joined sequences this app deliberately leaves out. Windows' emoji font does
# not assemble them, so the tile (and the name field) would show a person
# followed by a detached symbol instead of one picture. The health-worker and
# technologist sequences share the gender-neutral person (U+1F9D1), which the
# Windows font cannot join with a medical symbol or a laptop.
_UNSUPPORTED_JOINS = [
    ("\U0001F9D1", "\u2695"),   # person + medical symbol
    ("\U0001F9D1", "\U0001F4BB"),  # person + laptop
]


def is_blocked(char):
    return any(a in char and b in char for a, b in _UNSUPPORTED_JOINS)

# Hand-picked extras: skin tones, joined sequences and countries.
EXTRA = {
    "smileys": [
        ("\U0001F44D\U0001F3FD", "thumbs up: medium skin tone"),
        ("\U0001F44F\U0001F3FE", "clapping hands: medium-dark skin tone"),
        ("\U0001F64C\U0001F3FB", "raising hands: light skin tone"),
        ("\U0001F64F\U0001F3FC", "folded hands: medium-light skin tone"),
        ("\U0001F4AA\U0001F3FD", "flexed biceps: medium skin tone"),
        ("\U0001F91D\U0001F3FF", "handshake: dark skin tone"),
        ("\U0001F468\u200D\U0001F469\u200D\U0001F467",
         "family: man, woman, girl"),
        ("\U0001F469\u200D\U0001F4BB", "woman technologist"),
        ("\U0001F468\u200D\U0001F373", "man cook"),
        ("\U0001F469\u200D\U0001F3A4", "woman singer"),
        ("\U0001F468\u200D\U0001F467", "family: man, girl"),
    ],
    "flags": [
        ("\U0001F1EF\U0001F1F5", "flag: Japan"),
        ("\U0001F1FA\U0001F1F8", "flag: United States"),
        ("\U0001F1EC\U0001F1E7", "flag: United Kingdom"),
        ("\U0001F1E8\U0001F1E6", "flag: Canada"),
        ("\U0001F1EB\U0001F1F7", "flag: France"),
        ("\U0001F1E9\U0001F1EA", "flag: Germany"),
        ("\U0001F1EE\U0001F1F9", "flag: Italy"),
        ("\U0001F1EA\U0001F1F8", "flag: Spain"),
        ("\U0001F1F5\U0001F1F9", "flag: Portugal"),
        ("\U0001F1F3\U0001F1F1", "flag: Netherlands"),
        ("\U0001F1E7\U0001F1EA", "flag: Belgium"),
        ("\U0001F1E8\U0001F1ED", "flag: Switzerland"),
        ("\U0001F1E6\U0001F1F9", "flag: Austria"),
        ("\U0001F1F8\U0001F1EA", "flag: Sweden"),
        ("\U0001F1F3\U0001F1F4", "flag: Norway"),
        ("\U0001F1EB\U0001F1EE", "flag: Finland"),
        ("\U0001F1E9\U0001F1F0", "flag: Denmark"),
        ("\U0001F1F5\U0001F1F1", "flag: Poland"),
        ("\U0001F1EE\U0001F1EA", "flag: Ireland"),
        ("\U0001F1EC\U0001F1F7", "flag: Greece"),
        ("\U0001F1F7\U0001F1FA", "flag: Russia"),
        ("\U0001F1FA\U0001F1E6", "flag: Ukraine"),
        ("\U0001F1F9\U0001F1F7", "flag: Turkey"),
        ("\U0001F1E7\U0001F1F7", "flag: Brazil"),
        ("\U0001F1F2\U0001F1FD", "flag: Mexico"),
        ("\U0001F1E6\U0001F1F7", "flag: Argentina"),
        ("\U0001F1EE\U0001F1F3", "flag: India"),
        ("\U0001F1E8\U0001F1F3", "flag: China"),
        ("\U0001F1F0\U0001F1F7", "flag: South Korea"),
        ("\U0001F1E6\U0001F1FA", "flag: Australia"),
        ("\U0001F1F8\U0001F1E6", "flag: Saudi Arabia"),
        ("\U0001F1E6\U0001F1EA", "flag: United Arab Emirates"),
        ("\U0001F1EA\U0001F1EC", "flag: Egypt"),
        ("\U0001F1F2\U0001F1E6", "flag: Morocco"),
        ("\U0001F1F3\U0001F1EC", "flag: Nigeria"),
        ("\U0001F1FF\U0001F1E6", "flag: South Africa"),
    ],
}

LINE = re.compile(
    r"^(?P<cps>[0-9A-F ]+)\s*;\s*(?P<status>\w[\w-]*)"
    r"\s*#\s*(?P<char>\S+)\s*E(?P<ver>[0-9.]+)\s*(?P<name>.+)$")

# Skin tone names, in the order the picker shows them.
TONES = ["light", "medium-light", "medium", "medium-dark", "dark"]

TONE_LINE = re.compile(
    r"^(?P<base>.+?): (?P<tone>" + "|".join(TONES) + r") skin tone$")


def read_source(path):
    """Return the text of emoji-test.txt, downloading it when missing."""
    if path and Path(path).exists():
        return Path(path).read_text(encoding="utf-8")
    print(f"downloading {UNICODE_URL} ...")
    with urllib.request.urlopen(UNICODE_URL, timeout=30) as response:
        return response.read().decode("utf-8")


def font_checker():
    """Return a predicate telling whether the local emoji font can draw *text*."""
    try:
        from PySide6.QtGui import QFont, QRawFont
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("PySide6 is not installed; skipping the font check.")
        return lambda text: True

    app = QApplication.instance() or QApplication(sys.argv)
    font = QFont()
    font.setFamilies(["Segoe UI Emoji", "Apple Color Emoji",
                      "Noto Color Emoji"])
    font.setPointSize(16)
    raw = QRawFont.fromFont(font)
    return lambda text: all(raw.supportsCharacter(ord(c)) for c in text)


def parse_entries(text):
    """Yield (group, subgroup, char, name) for fully-qualified entries."""
    group = subgroup = ""
    for raw in text.splitlines():
        if raw.startswith("# group:"):
            group = raw.split(":", 1)[1].strip()
            continue
        if raw.startswith("# subgroup:"):
            subgroup = raw.split(":", 1)[1].strip()
            continue
        match = LINE.match(raw)
        if not match or match.group("status") != "fully-qualified":
            continue
        if float(match.group("ver")) > MAX_EMOJI_VERSION:
            continue
        cps = [int(x, 16) for x in match.group("cps").split()]
        yield (group, subgroup, "".join(map(chr, cps)),
               match.group("name").strip())


def pick(entries, group_name, quota):
    """Round-robin across subgroups so a category gets variety."""
    buckets = OrderedDict()
    for group, subgroup, char, name in entries:
        if group == group_name:
            buckets.setdefault(subgroup, []).append((char, name))
    picked, i = [], 0
    while len(picked) < quota:
        added = False
        for items in buckets.values():
            if i < len(items) and len(picked) < quota:
                picked.append(items[i])
                added = True
        if not added:
            break
        i += 1
    return picked


def tone_variants(entries):
    """Return {base label: {tone: character}} from the Unicode list.

    Only single-tone variants are kept. Entries that need two tones (a
    handshake, two people holding hands) are left out rather than guessed at.
    """
    mapping = {}
    for _group, _subgroup, char, name in entries:
        match = TONE_LINE.match(name)
        if match:
            mapping.setdefault(match.group("base"), {})[match.group("tone")] = char
    return mapping


def build(text, drawable):
    entries = [entry for entry in parse_entries(text)
               if drawable(entry[2]) and not is_blocked(entry[2])]
    tones = tone_variants(entries)

    sections = OrderedDict()
    for group, (section, label, quota) in GROUP_MAP.items():
        if not quota:
            continue
        sections.setdefault(section, {"label": label, "items": []})["items"] \
            .extend(pick(entries, group, quota))

    for section, extra in EXTRA.items():
        sections.setdefault(section, {"label": "", "items": []})
        seen = {char for char, _name in sections[section]["items"]}
        for char, name in extra:
            if (char not in seen and not is_blocked(char) and drawable(char)):
                sections[section]["items"].append((char, name))

    labels = {section: data["label"] or {"flags": "Flags"}[section]
              for section, data in sections.items()}

    result = []
    for section in SECTION_ORDER:
        for char, name in sections[section]["items"]:
            item = {
                "section": section,
                "section_label": labels[section],
                "label": name,
                "char": char,
                "slots": len(char),
            }
            variants = tones.get(name)
            if variants:
                # Only keep tones that are really a different character, and
                # that the local font can draw too.
                usable = {tone: variants[tone] for tone in TONES
                          if tone in variants and variants[tone] != char
                          and drawable(variants[tone])}
                if usable:
                    item["tones"] = usable
            result.append(item)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", help="path to emoji-test.txt")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help="output JSON (default: the bundled asset)")
    parser.add_argument("--any-font", action="store_true",
                        help="do not check characters against the local font")
    args = parser.parse_args(argv)

    drawable = (lambda text: True) if args.any_font else font_checker()
    data = build(read_source(args.source), drawable)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False),
                   encoding="utf-8")

    print(f"{len(data)} emoji -> {out}")
    labels = {item["section"]: item["section_label"] for item in data}
    for section in SECTION_ORDER:
        count = sum(1 for item in data if item["section"] == section)
        print(f"  {labels[section]:22s} {count:3d}")
    print("multi-slot:", sum(1 for item in data if item["slots"] > 1))


if __name__ == "__main__":
    main()