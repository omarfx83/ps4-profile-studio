"""Read and write the PS4 local user name via the profile cache JSON.

The console stores each user's local name in
``/system_data/priv/cache/profile/<userid>/online.json`` (key ``firstName``).

Writing the name means editing **only** ``online.json`` — the raw text is
changed with a targeted replacement so every other field and the file's
formatting stay byte-for-byte identical. ``version.json`` is deliberately
**never written**: its ``cacheVersion`` is the console's cache schema version,
and changing it makes the console treat the whole profile cache as invalid and
rebuild it (losing the name and avatar).
"""

import ftplib
import json
import re
from datetime import datetime

from ..settings import BACKUP_DIR
from .ftp import PROFILE_ROOT

# Every file a profile folder may contain (avatar + metadata).
PROFILE_FILES = (
    "avatar64.dds", "avatar128.dds", "avatar260.dds", "avatar440.dds",
    "avatar440.png",
    "picture64.dds", "picture128.dds", "picture260.dds", "picture440.dds",
    "picture.png",
    "online.json", "version.json",
)

# Matches a JSON string value after a given key, honouring escapes.
_VALUE_RE = r'("{key}"\s*:\s*)("(?:[^"\\]|\\.)*")'


def _get(ftp, uid, name):
    """Download a profile file, or None when the console says it is absent.

    Only a "file not found" answer means the file is missing. A dropped
    connection is raised instead: returning None there would make write_name()
    mistake a live profile for a brand-new one and overwrite it with an empty
    template.
    """
    try:
        return ftp.download_bytes(f"{PROFILE_ROOT}/{uid}/{name}")
    except ftplib.error_perm:
        return None


def read_profile(ftp, uid):
    """Return {"online": <dict|None>, "version": <dict|None>} for a user."""
    result = {"online": None, "version": None}
    raw = _get(ftp, uid, "online.json")
    if raw is not None:
        try:
            result["online"] = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            result["online"] = None
    raw = _get(ftp, uid, "version.json")
    if raw is not None:
        try:
            result["version"] = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            result["version"] = None
    return result


def get_name(profile):
    """Best-effort current display name from a read_profile() result."""
    online = (profile or {}).get("online") or {}
    first = online.get("firstName") or ""
    last = online.get("lastName") or ""
    name = f"{first} {last}".strip()
    return name


def read_local_name(ftp, uid):
    """Best-effort local name from ``/user/home/<uid>/username.dat``.

    ``username.dat`` is a NUL-padded UTF-8 name the console keeps for the user
    (e.g. b"User1\\x00..."). Returns "" if it can't be read.
    """
    key = uid.lower().removeprefix("0x")
    for candidate in (key, key.zfill(8)):
        try:
            raw = ftp.download_bytes(f"/user/home/{candidate}/username.dat")
        except Exception:  # noqa: BLE001
            continue
        text = raw.split(b"\x00", 1)[0].decode("utf-8", "replace").strip()
        return text
    return ""


def _replace_string(raw_text, key, value):
    """Replace the JSON string value for ``key``, keeping all other bytes."""
    encoded = json.dumps(value, ensure_ascii=False)
    pattern = _VALUE_RE.format(key=re.escape(key))
    new_text, count = re.subn(pattern, lambda m: m.group(1) + encoded,
                              raw_text, count=1)
    if count == 0:
        raise RuntimeError(f'"{key}" not found in the profile JSON')
    return new_text


# A minimal PSN-style profile sidecar, mirroring what the console stores.
# Used only when a user has no online.json yet.
_TROPHY = ('{\\"level\\":1,\\"progress\\":999,\\"earnedTrophies\\":'
           '{\\"platinum\\":999,\\"gold\\":999,\\"silver\\":999,'
           '\\"bronze\\":999}}')


def new_online_json(first_name):
    """Build a fresh ``online.json`` (bytes) for a user that has none."""
    name = json.dumps(first_name, ensure_ascii=False)
    text = (
        '{"onlineId":"",\n'
        '"avatarUrl":"",\n'
        f'"firstName":{name},\n'
        '"lastName":"",\n'
        f'"trophySummary":"{_TROPHY}"}}'
    )
    return text.encode("utf-8", "surrogateescape")


def write_name(ftp, uid, first_name):
    """Write ``firstName`` to ``online.json`` (and nothing else).

    If the user has no ``online.json`` yet (a fresh/offline profile), a minimal
    one is created. Raises on failure. Returns a small dict describing the
    change (``created`` is True when a new file was written).
    """
    online_raw = _get(ftp, uid, "online.json")
    if online_raw is None:
        ftp.upload_bytes(new_online_json(first_name),
                         f"{PROFILE_ROOT}/{uid}/online.json")
        return {"name": first_name, "created": True}

    online_text = online_raw.decode("utf-8", "surrogateescape")
    new_online = _replace_string(online_text, "firstName", first_name)
    ftp.upload_bytes(new_online.encode("utf-8", "surrogateescape"),
                     f"{PROFILE_ROOT}/{uid}/online.json")
    return {"name": first_name, "created": False}


def backup_profile(ftp, uid, stamp=None, backup_dir=BACKUP_DIR):
    """Copy every profile file (avatar + metadata) to backups/<stamp>/<uid>/."""
    stamp = stamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = backup_dir / stamp / uid
    dest.mkdir(parents=True, exist_ok=True)
    saved = 0
    for name in PROFILE_FILES:
        raw = _get(ftp, uid, name)
        if raw is None:
            continue
        (dest / name).write_bytes(raw)
        saved += 1
    return saved

