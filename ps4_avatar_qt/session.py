"""Shared PS4 FTP connection: connect, list/read users, disconnect.

One ``Connection`` instance is shared by the header bar and the tabs, so the
whole app has a single link to the console.
"""

import threading

from PySide6.QtCore import QObject, Signal

from ps4_avatar.ps4.ftp import PS4FTP


class Connection(QObject):
    connecting = Signal(str)      # status message
    users_ready = Signal(list)    # list[User]
    failed = Signal(str)
    disconnected = Signal()

    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self.settings = settings or {}
        self.ftp = None
        self.conn = None
        self.users = []
        self._busy = False
        self._cancel = threading.Event()

    @property
    def is_connected(self):
        return self.ftp is not None and self.conn is not None

    @property
    def busy(self):
        return self._busy

    def connect_to(self, host, port):
        if self._busy:
            return
        self._cancel.clear()
        self._busy = True
        self.connecting.emit(f"Connecting to {host}:{port}…")
        threading.Thread(target=self._worker, args=(host, port),
                         daemon=True).start()

    def refresh(self):
        if self._busy or not self.conn:
            return
        conn = dict(self.conn)
        if self.ftp is not None:
            self.ftp.close()
        self.ftp = None
        self._cancel.clear()
        self._busy = True
        self.connecting.emit("Refreshing user list…")
        threading.Thread(target=self._worker,
                         args=(conn["host"], conn["port"]),
                         daemon=True).start()

    def _worker(self, host, port):
        ftp = None
        try:
            ftp = PS4FTP().connect(host, port)
            dirs = ftp.list_user_dirs()
            users = []
            for uid, facts in dirs:
                if self._cancel.is_set():
                    ftp.close()
                    return
                info = ftp.read_user(uid)
                info.facts = facts
                users.append(info)
            self.ftp = ftp
            self.conn = {"host": host, "port": port}
            self.users = users
            self._busy = False
            self.users_ready.emit(users)
        except Exception as exc:  # noqa: BLE001
            if ftp is not None:
                ftp.close()
            self._busy = False
            self.failed.emit(str(exc))

    def disconnect(self):
        if self._busy:
            return
        self._cancel.set()
        if self.ftp is not None:
            self.ftp.close()
        self.ftp = None
        self.conn = None
        self.users = []
        self.disconnected.emit()
