"""Resolve bundled resource files in development and in frozen builds.

PyInstaller sets ``sys._MEIPASS`` to the folder that holds bundled data:
``_internal`` for onedir builds and a temporary folder for onefile builds.
The asset tree is added at ``ps4_avatar_qt/assets`` inside that folder, so the
same relative layout works in a checkout, a wheel install and a frozen app.
"""

import sys
from pathlib import Path

_PACKAGE = "ps4_avatar_qt"


def _root() -> Path:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / _PACKAGE
    return Path(__file__).resolve().parent


def resource_path(*parts) -> Path:
    """Absolute path of a file bundled with the application."""
    return _root().joinpath(*parts)


def assets_path(*parts) -> Path:
    """Absolute path of a file under ``ps4_avatar_qt/assets``."""
    return resource_path("assets", *parts)
