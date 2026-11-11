"""Minimal FTP client for the PS4 GoldHEN FTP server."""

import io
import json
import re

import ftplib

from PIL import Image

from ..dds import SIZES
from ..models import User

PROFILE_ROOT = "/system_data/priv/cache/profile"
AVATAR_FILES = tuple(f"avatar{s}.dds" for s in SIZES) + ("avatar440.png",)


def clean_ps4_text(text):
    """Remove PS4 button glyphs (private-use area) and tidy whitespace."""
    if not text:
        return ""
    kept = "".join(ch for ch in str(text) if not ("\ue000" <= ch <= "\uf8ff"))
    return " ".join(kept.split())


class PS4FTP:
    """Thin wrapper around ftplib with PS4-specific paths and helpers."""

    def __init__(self):
        self.ftp = None
        self.host = ""
        self.port = 2121
        self.user = "root"
        self.password = "root"

    def connect(self, host, port=2121, user="root", password="root", timeout=12):
        self.close()
        ftp = ftplib.FTP(timeout=timeout)
        ftp.connect(host, int(port))
        ftp.login(user or "anonymous", password or "")
        ftp.set_pasv(True)
        ftp.cwd(PROFILE_ROOT)
        self.ftp = ftp
        self.host, self.port = host, int(port)
        self.user, self.password = user, password
        return self

    def close(self):
        if self.ftp is not None:
            try:
                self.ftp.quit()
            except Exception:
                try:
                    self.ftp.close()
                except Exception:
                    pass
            self.ftp = None

    def _mlsd(self, path):
        try:
            return [(name, dict(facts)) for name, facts in self.ftp.mlsd(path)]
        except (ftplib.error_perm, ftplib.error_temp, AttributeError):
            names = self.ftp.nlst(path)
            return [(n.rstrip("/").rsplit("/", 1)[-1], {}) for n in names]

    def list_user_dirs(self):
        users = []
        for name, facts in self._mlsd(PROFILE_ROOT):
            if not re.match(r"^0x[0-9A-Fa-f]{4,16}$", name):
                continue
            if facts.get("type") not in (None, "dir"):
                continue
            users.append((name, facts))
        users.sort(key=lambda item: item[0].upper())
        return users

    def download_bytes(self, remote, limit=None):
        buf = io.BytesIO()

        def sink(chunk):
            if limit is None or buf.tell() < limit:
                buf.write(chunk)

        self.ftp.retrbinary(f"RETR {remote}", sink)
        return buf.getvalue()

    def upload_bytes(self, data, remote):
        self.ftp.storbinary(f"STOR {remote}", io.BytesIO(data))

    def read_user(self, uid):
        user = User(uid=uid)
        try:
            raw = self.download_bytes(f"{PROFILE_ROOT}/{uid}/online.json", limit=64 * 1024)
            data = json.loads(raw.decode("utf-8", "replace"))
            first = clean_ps4_text(data.get("firstName"))
            last = clean_ps4_text(data.get("lastName"))
            user.online_id = clean_ps4_text(data.get("onlineId"))
            name = " ".join(part for part in (first, last) if part)
            if name:
                user.name = name
        except Exception:
            pass

        for fname in ("avatar440.png", "avatar260.dds", "avatar64.dds"):
            try:
                raw = self.download_bytes(f"{PROFILE_ROOT}/{uid}/{fname}")
                with Image.open(io.BytesIO(raw)) as im:
                    im.load()
                    user.thumb = im.convert("RGBA")
                break
            except Exception:
                continue
        return user
