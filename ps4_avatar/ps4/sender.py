"""Backup and upload operations for PS4 profile avatars."""

import ftplib

from ..settings import BACKUP_DIR
from .ftp import AVATAR_FILES, PROFILE_ROOT
from .profile import new_online_json, read_local_name

BACKUP_FILES = list(AVATAR_FILES) + [
    "picture64.dds", "picture128.dds", "picture260.dds", "picture440.dds",
    "picture.png", "online.json", "version.json",
]


def backup_user(ftp, uid, stamp, backup_dir=BACKUP_DIR):
    """Copy the existing profile files to backups/<stamp>/<uid>/.

    Missing files (550) are skipped. Any other error propagates so the caller
    can abort before overwriting a profile that was not backed up.
    """
    dest = backup_dir / stamp / uid
    dest.mkdir(parents=True, exist_ok=True)
    saved = 0
    for name in BACKUP_FILES:
        remote = f"{PROFILE_ROOT}/{uid}/{name}"
        try:
            data = ftp.download_bytes(remote)
        except ftplib.error_perm as exc:
            if str(exc).startswith("550"):
                continue
            raise
        (dest / name).write_bytes(data)
        saved += 1
    return saved


def upload_files(ftp, uid, files):
    """Upload a mapping of filename -> bytes to one profile folder."""
    for name, data in files.items():
        ftp.upload_bytes(data, f"{PROFILE_ROOT}/{uid}/{name}")


def nudge_profile(ftp, uid):
    """Make the console re-read the profile after an avatar upload.

    If the user already has ``online.json`` it is re-written unchanged. If they
    have none, a minimal one is created — seeded with the console's own
    ``username.dat`` name when available, so the local name is preserved.
    Returns ``"rewrote"`` or ``"created"``.
    """
    path = f"{PROFILE_ROOT}/{uid}/online.json"
    try:
        raw = ftp.download_bytes(path)
    except ftplib.error_perm as exc:
        if not str(exc).startswith("550"):
            raise
        ftp.upload_bytes(new_online_json(read_local_name(ftp, uid)), path)
        return "created"
    ftp.upload_bytes(raw, path)
    return "rewrote"
