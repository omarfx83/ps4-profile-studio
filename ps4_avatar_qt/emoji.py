"""The curated emoji set offered by the picker.

The data lives in ``assets/emoji/emoji.json``. Each entry is one emoji:

    section        machine name of the category (e.g. "smileys")
    section_label  human label for the category (e.g. "Smileys & people")
    label          Unicode name (e.g. "grinning face")
    char           the character(s) to insert
    slots          how many of the 16 name slots it consumes

``slots`` is the number of code points, not the number of visible glyphs: the
console counts characters, so a joined family such as ``👨‍👩‍👧`` takes five of
the sixteen available slots while looking like a single symbol.
"""

import json

from .resources import assets_path

_JSON = assets_path("emoji") / "emoji.json"

# Preferred order of categories in the picker.
SECTION_ORDER = [
    "smileys", "animals", "food", "travel", "activities", "objects",
    "symbols", "flags",
]


def load_emoji():
    """Return the bundled emoji, or an empty list if the file is missing."""
    try:
        data = json.loads(_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [item for item in data if item.get("char")]


EMOJI = load_emoji()


def sections():
    """Return [(section, label, [items...])] in display order."""
    grouped = {}
    for item in EMOJI:
        grouped.setdefault(item["section"], []).append(item)
    order = [s for s in SECTION_ORDER if s in grouped]
    order += [s for s in grouped if s not in order]
    return [(sec, grouped[sec][0]["section_label"], grouped[sec])
            for sec in order]


def groups():
    """Return the picker groups: "All emoji" first, then each category."""
    result = []
    if EMOJI:
        result.append(("all", "All emoji", EMOJI))
    result.extend(sections())
    return result
