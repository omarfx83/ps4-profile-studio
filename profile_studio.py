#!/usr/bin/env python3
"""
PS4 Profile Studio - launcher (Qt edition).

The application lives in the ``ps4_avatar_qt`` package, with the shared
non-UI core in ``ps4_avatar``. This file stays at the project root so the
existing .bat file and shortcuts keep working:

    python profile_studio.py
    python profile_studio.py --open photo.jpg

Requires: Pillow and PySide6-Essentials.
    pip install Pillow PySide6-Essentials
"""

import sys

try:
    from ps4_avatar_qt.app import main
except ImportError as exc:  # pragma: no cover
    sys.exit(
        f"Missing dependency: {exc}\n"
        "Install the requirements with:\n"
        "    pip install Pillow PySide6-Essentials"
    )

if __name__ == "__main__":
    sys.exit(main())
