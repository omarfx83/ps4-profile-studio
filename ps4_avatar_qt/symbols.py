"""The PS4 symbol set: private-use characters plus their icon tiles.

The data lives in ``assets/symbols/symbols.json`` (a bundled set). Each entry
maps a PUA character to a small icon so the UI can show a picture while
inserting the real character into a name field.

Fields per symbol:
    section        machine name of the category (e.g. "controller")
    section_label  human label for the category (e.g. "Controller")
    label          item label (e.g. "Controller 3")
    char           the actual character to insert (may be >1 code point)
    codepoints     list of "0xNNNN" strings
    icon           path relative to assets/symbols/
    supported      optional; ``false`` hides the symbol (default ``true``)

Only 149 of the 275 characters are actually drawn by the console's system UI.
The rest sit in a private-use range that no console font covers, so a profile
name containing one shows a "?" box on the PS4. Those entries stay in the JSON
with ``"supported": false`` for documentation, but are never offered to users.
"""

import json

from .resources import assets_path

_ASSETS = assets_path("symbols")
_JSON = _ASSETS / "symbols.json"

# Preferred order of categories in the picker.
SECTION_ORDER = [
    "psicon", "controller", "system", "social", "loghi", "keyboard",
    "misc",
]


def load_symbols():
    """Return the supported symbols with an absolute ``icon_path`` added.

    Entries marked ``"supported": false`` are skipped: the PS4 system UI draws
    them as a "?" box, so offering them in the picker would only produce a
    broken name on the console.
    """
    try:
        data = json.loads(_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    symbols = []
    for item in data:
        if not item.get("supported", True):
            continue
        item["icon_path"] = _ASSETS / item["icon"]
        symbols.append(item)
    return symbols


SYMBOLS = load_symbols()


def sections():
    """Return [(section, label, [items...])] in display order."""
    grouped = {}
    for item in SYMBOLS:
        grouped.setdefault(item["section"], []).append(item)
    order = [s for s in SECTION_ORDER if s in grouped]
    order += [s for s in grouped if s not in order]
    result = []
    for sec in order:
        items = grouped[sec]
        result.append((sec, items[0]["section_label"], items))
    return result
