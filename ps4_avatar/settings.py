"""Local settings and backup paths (never committed to git).

The app is distributed as a portable folder, so settings and backups live next
to the executable by default. If that folder is not writable (for example the
app was unpacked under ``Program Files``), they fall back to
``%APPDATA%\\PS4ProfileStudio``. When running from source the project folder is
used, exactly as before.

The settings file keeps the list of recently connected consoles, each with an
optional friendly name::

    {
      "devices": [
        {"host": "192.168.1.50", "port": 2121,
         "name": "Living Room", "last_used": 1762790123.0}
      ]
    }

The list is most-recently-used first, capped at :data:`MAX_DEVICES`.
"""

import json
import os
import sys
import time
from pathlib import Path

APP_NAME = "PS4ProfileStudio"

MAX_DEVICES = 10
MAX_NAME_LENGTH = 40
DEFAULT_PORT = 2121


def _is_writable(folder: Path) -> bool:
    """Return True when *folder* exists (or can be created) and is writable."""
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".write-test"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def _data_dir() -> Path:
    if getattr(sys, "frozen", False):
        # Portable build: keep everything next to the executable.
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent
    if _is_writable(base):
        return base

    appdata = os.environ.get("APPDATA")
    fallback = Path(appdata) if appdata else Path.home() / ".local" / "share"
    fallback = fallback / APP_NAME
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


DATA_DIR = _data_dir()
SETTINGS_PATH = DATA_DIR / "profile_studio.local.json"
BACKUP_DIR = DATA_DIR / "backups"


def load_settings():
    """Return the raw settings dict (empty when missing or unreadable)."""
    try:
        data = json.loads(SETTINGS_PATH.read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_settings(data):
    """Write the settings dict. No credentials are ever stored: the PS4's
    GoldHEN FTP server does not authenticate."""
    try:
        SETTINGS_PATH.write_text(json.dumps(data, indent=2), "utf-8")
    except OSError:
        return False
    return True


# --- remembered devices -----------------------------------------------------

def device_key(host, port):
    """Identity of a console: host names are case-insensitive."""
    return f"{str(host).strip().lower()}:{int(port)}"


def device_address(device):
    return f"{device.get('host', '')}:{int(device.get('port') or DEFAULT_PORT)}"


def device_label(device):
    """Friendly label: the custom name, else the host (plus a non-default port)."""
    name = str(device.get("name") or "").strip()
    if name:
        return name
    host = str(device.get("host") or "")
    port = int(device.get("port") or DEFAULT_PORT)
    return host if port == DEFAULT_PORT else f"{host}:{port}"


def _normalise(device):
    """Return a clean device dict, or None when the entry is unusable."""
    if not isinstance(device, dict):
        return None
    try:
        host = str(device.get("host") or "").strip()
        port = int(device.get("port") or DEFAULT_PORT)
    except (TypeError, ValueError):
        return None
    if not host or not (0 < port < 65536):
        return None
    name = str(device.get("name") or "").strip()[:MAX_NAME_LENGTH]
    try:
        last_used = float(device.get("last_used") or 0.0)
    except (TypeError, ValueError):
        last_used = 0.0
    return {"host": host, "port": port, "name": name, "last_used": last_used}


def load_devices():
    """Return remembered consoles, most recently used first."""
    raw = load_settings()
    devices = raw.get("devices")
    if not isinstance(devices, list):
        # Migrate the single host/port pair written by older versions.
        devices = []
        host = str(raw.get("host") or "").strip()
        if host:
            devices = [{"host": host, "port": raw.get("port") or DEFAULT_PORT}]

    cleaned, merged = [], {}
    for item in devices:
        device = _normalise(item)
        if device is None:
            continue
        key = device_key(device["host"], device["port"])
        kept = merged.get(key)
        if kept is None:
            merged[key] = device
            cleaned.append(device)
            continue
        # Collapse duplicates, keeping the newest use and any name.
        kept["last_used"] = max(kept["last_used"], device["last_used"])
        if not kept["name"]:
            kept["name"] = device["name"]
    cleaned.sort(key=lambda d: d["last_used"], reverse=True)
    return cleaned[:MAX_DEVICES]


def save_devices(devices):
    return save_settings({"devices": list(devices)[:MAX_DEVICES]})


def remember_device(host, port, name=None):
    """Move *host*:*port* to the top of the list, keeping its friendly name.

    Called after a successful connection, so the list means "recently
    connected" rather than "recently typed".
    """
    host = str(host or "").strip()
    if not host:
        return load_devices()
    try:
        port = int(port)
    except (TypeError, ValueError):
        port = DEFAULT_PORT

    key = device_key(host, port)
    devices = load_devices()
    existing = next(
        (d for d in devices if device_key(d["host"], d["port"]) == key), {})
    entry = _normalise({
        "host": host,
        "port": port,
        "name": existing.get("name", "") if name is None else name,
        "last_used": time.time(),
    })
    if entry is None:
        return devices

    devices = [d for d in devices if device_key(d["host"], d["port"]) != key]
    devices.insert(0, entry)
    devices = devices[:MAX_DEVICES]
    save_devices(devices)
    return devices


def rename_device(host, port, name):
    """Set (or clear, with an empty name) the friendly name of a console."""
    key = device_key(host, port)
    devices = load_devices()
    for device in devices:
        if device_key(device["host"], device["port"]) == key:
            device["name"] = str(name or "").strip()[:MAX_NAME_LENGTH]
            save_devices(devices)
            break
    return devices


def forget_device(host, port):
    key = device_key(host, port)
    devices = [d for d in load_devices()
               if device_key(d["host"], d["port"]) != key]
    save_devices(devices)
    return devices


def forget_all_devices():
    save_devices([])
    return []
