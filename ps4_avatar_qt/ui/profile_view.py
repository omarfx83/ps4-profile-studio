"""Profile tab: pick a user, read/edit their local name, and push it."""

import threading

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QVBoxLayout, QWidget)

from .. import theme
from .symbols_panel import SymbolPickerPopup
from .user_list import UserListPanel
from .widgets import Separator, Switch, make_faint, make_heading, make_muted

from ps4_avatar.ps4.profile import (backup_profile, get_name, read_profile,
                                    write_name)

_ZWJ = 0x200D


def _extends_cluster(cp):
    """True for marks that belong to the preceding character."""
    return (
        cp in (0xFE0F, 0xFE0E, 0x20E3)
        or 0x1F3FB <= cp <= 0x1F3FF        # skin tone modifiers
        or 0x0300 <= cp <= 0x036F          # combining diacritics
        or 0x1AB0 <= cp <= 0x1AFF
        or 0x1DC0 <= cp <= 0x1DFF
        or 0x20D0 <= cp <= 0x20FF
        or 0xFE20 <= cp <= 0xFE2F
    )


def grapheme_clusters(text):
    """Split *text* into (start, end) ranges, one per visible symbol.

    Enough of UAX #29 for names: everything else falls back to one character
    per cluster, which is what a plain text field does anyway.
    """
    clusters = []
    index, length = 0, len(text)
    while index < length:
        start = index
        cp = ord(text[index])
        index += 1
        if (0x1F1E6 <= cp <= 0x1F1FF and index < length
                and 0x1F1E6 <= ord(text[index]) <= 0x1F1FF):
            index += 1  # a flag is a pair of regional indicators
        while index < length:
            nxt = ord(text[index])
            if nxt == _ZWJ:
                index += 1
                if index < length:
                    index += 1  # the symbol joined to the previous one
            elif _extends_cluster(nxt):
                index += 1
            else:
                break
        clusters.append((start, index))
    return clusters


def _utf16_len(char):
    return 2 if ord(char) > 0xFFFF else 1


def _cluster_at(text, pos):
    """Return the UTF-16 (start, end) of the cluster touching *pos*.

    ``QLineEdit`` positions are UTF-16 code units, so the code-point clusters
    are converted before comparing.
    """
    offset = 0
    for start, end in grapheme_clusters(text):
        width = sum(_utf16_len(ch) for ch in text[start:end])
        if offset <= pos < offset + width:
            return offset, offset + width
        offset += width
    return None


class ProfileView(QWidget):
    _loaded = Signal(object)
    _wrote = Signal(object)
    _failed = Signal(str)

    def __init__(self, connection, parent=None):
        super().__init__(parent)
        self.conn = connection
        self._uid = None
        self._original = ""
        self._busy = False
        self._picker = None
        self._has_online = False

        self._loaded.connect(self._on_loaded)
        self._wrote.connect(self._on_wrote)
        self._failed.connect(self._on_failed)

        self._build_ui()
        self._update_actions()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(theme.PAD, 10, theme.PAD, 12)
        root.setSpacing(theme.PAD)

        self.user_list = UserListPanel(self.conn, single=True)
        self.user_list.picked.connect(self._load_user)
        root.addWidget(self.user_list, 1)

        panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedWidth(340)
        self._build_panel(panel)
        root.addWidget(panel, 0)

    def _build_panel(self, panel):
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(10)

        head_row = QHBoxLayout()
        head_row.setContentsMargins(0, 0, 0, 0)
        head_row.addWidget(make_heading("PROFILE NAME"))
        head_row.addStretch(1)
        self.counter = QLabel("0/16")
        self.counter.setObjectName("nameCounter")
        self.counter.setToolTip(
            "Characters used of the 16 the console stores. Emoji count as one.")
        head_row.addWidget(self.counter, 0, Qt.AlignRight)
        outer.addLayout(head_row)

        self.name_edit = QLineEdit()
        # QLineEdit counts UTF-16 code units, while the console counts
        # characters: an emoji such as U+1F600 is one character but two units.
        # Allow the widest a 16-character name can be, then enforce the real
        # limit per character in _on_name_changed().
        self.name_edit.setMaxLength(32)
        self.name_edit.setPlaceholderText("Type a name, or use Symbols\u2026")
        self.name_edit.textChanged.connect(self._on_name_changed)
        self.name_edit.installEventFilter(self)
        outer.addWidget(self.name_edit)

        btn_row = QHBoxLayout()
        self.btn_symbols = QPushButton("Symbols\u2026")
        self.btn_symbols.clicked.connect(self.open_symbols)
        btn_row.addWidget(self.btn_symbols)
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.clicked.connect(self.reset_name)
        btn_row.addWidget(self.btn_reset)
        outer.addLayout(btn_row)

        self.backup_switch = Switch(checked=True)
        row = QHBoxLayout()
        row.addWidget(make_muted("Back up before saving"), 1)
        row.addWidget(self.backup_switch, 0)
        outer.addLayout(row)

        self.version_lbl = make_faint("Cache version: \u2014")
        outer.addWidget(self.version_lbl)

        outer.addWidget(Separator())
        outer.addWidget(make_faint(
            "Writes the profile's display name (online.json). The console shows "
            "it for an activated user (e.g. activated offline with Apollo Save "
            "Tool); the avatar and other profile fields are left untouched.",
            wrap=True))

        outer.addStretch(1)

        self.btn_save = QPushButton("Apply name")
        self.btn_save.setObjectName("accent")
        self.btn_save.clicked.connect(self.save)
        outer.addWidget(self.btn_save)

        self.status = make_faint("Pick a user from the list.", wrap=True)
        outer.addWidget(self.status)
        self._update_counter()

    # -- state -------------------------------------------------------------

    def _update_actions(self):
        connected = self.conn.is_connected
        has_user = connected and self._uid is not None
        idle = not self._busy
        self.name_edit.setEnabled(has_user and idle)
        self.btn_symbols.setEnabled(has_user and idle)
        self.btn_reset.setEnabled(has_user and idle)
        self.btn_save.setEnabled(has_user and idle)
        self.backup_switch.setEnabled(bool(connected) and idle)

    # -- load --------------------------------------------------------------

    def _load_user(self, uid):
        if self._busy or self.conn.ftp is None:
            return
        self._uid = uid
        self._busy = True
        self.status.setText("Reading profile\u2026")
        self._update_actions()
        threading.Thread(target=self._load_worker,
                         args=(self.conn.ftp, uid), daemon=True).start()

    def _load_worker(self, ftp, uid):
        try:
            profile = read_profile(ftp, uid)
            name = get_name(profile)
            version = str((profile.get("version") or {}).get("cacheVersion", ""))
            self._loaded.emit({"uid": uid, "name": name, "version": version,
                               "has_online": profile.get("online") is not None})
        except Exception as exc:  # noqa: BLE001
            self._failed.emit(str(exc))

    def _on_loaded(self, payload):
        self._busy = False
        if payload.get("uid") != self._uid:
            return
        self._original = payload["name"]
        self._has_online = bool(payload.get("has_online"))
        self.name_edit.setText(payload["name"])
        self._update_counter()
        self.version_lbl.setText(
            f"Cache version: {payload.get('version') or '\u2014'}")
        if self._has_online:
            self.status.setText(f"Loaded name: {payload['name'] or '(empty)'}")
        else:
            self.status.setText(
                "This user has no online.json yet \u2014 applying a name will "
                "create one.")
        self._update_actions()

    # -- symbols -----------------------------------------------------------

    def _on_name_changed(self, text):
        """Keep the field at the console's 16-character limit.

        The limit counts characters, not UTF-16 units, so a name of 16 emoji is
        valid even though the widget holds 32 code units.
        """
        if len(text) > 16:
            self.name_edit.blockSignals(True)
            cursor = self.name_edit.cursorPosition()
            self.name_edit.setText(text[:16])
            self.name_edit.setCursorPosition(min(cursor, 16))
            self.name_edit.blockSignals(False)
            self.status.setText("Name limit is 16 characters.")
            text = self.name_edit.text()
        self._update_counter(text)

    def _update_counter(self, text=None):
        if text is None:
            text = self.name_edit.text()
        used = len(text)
        self.counter.setText(f"{used}/16")
        full = used >= 16
        if self.counter.property("full") != full:
            self.counter.setProperty("full", full)
            self.counter.style().unpolish(self.counter)
            self.counter.style().polish(self.counter)

    def eventFilter(self, obj, event):
        """Delete a whole emoji with Backspace/Delete.

        An emoji can be several characters (a skin tone, a joined family, a
        flag), and the console treats it as one symbol. Deleting it character
        by character leaves stray halves behind, so the default handling is
        replaced with grapheme-aware deletion.
        """
        if (obj is self.name_edit and event.type() == QEvent.KeyPress
                and event.key() in (Qt.Key_Backspace, Qt.Key_Delete)):
            if self.name_edit.hasSelectedText():
                return False
            text = self.name_edit.text()
            pos = self.name_edit.cursorPosition()
            if event.key() == Qt.Key_Backspace:
                if pos == 0:
                    return True
                span = _cluster_at(text, pos - 1)
            else:
                if pos >= len(text.encode("utf-16-le")) // 2:
                    return True
                span = _cluster_at(text, pos)
            if span is None:
                return False
            start, end = span
            if end <= start:
                return False
            self.name_edit.setSelection(start, end - start)
            self.name_edit.del_()
            return True
        return super().eventFilter(obj, event)

    def open_symbols(self):
        if self._picker is None:
            self._picker = SymbolPickerPopup(self)
            self._picker.symbol_chosen.connect(self._insert_symbol)
        picker = self._picker
        if picker.isVisible():
            picker.close()
            self.name_edit.setFocus()
            return
        frame = self.window().frameGeometry()

        # keep the popup inside the app window
        width = min(picker.width(), frame.width() - 24)
        height = min(picker.height(), frame.height() - 24)
        picker.resize(max(320, width), max(320, height))

        button = self.btn_symbols
        anchor = button.mapToGlobal(button.rect().bottomLeft())
        x = min(anchor.x(), frame.right() - picker.width() + 1)
        y = min(anchor.y(), frame.bottom() - picker.height() + 1)
        x = max(x, frame.left())
        y = max(y, frame.top())
        picker.move(x, y)
        picker.show()
        picker.raise_()
        # The picker never takes focus, so the caret stays (and typing keeps
        # working) in the name field while it is open.
        self.name_edit.setFocus()

    def hideEvent(self, event):
        if self._picker is not None:
            self._picker.hide()
        super().hideEvent(event)

    def hide_picker(self):
        """Close the picker, e.g. when the app window is deactivated."""
        if self._picker is not None:
            self._picker.hide()

    def _insert_symbol(self, char):
        if len(self.name_edit.text()) + len(char) > 16:
            self.status.setText("Name limit is 16 characters.")
            if self._picker is not None:
                self._picker.panel.notify(
                    "The name is full (16/16). Delete a character to make room.")
            return
        if self._picker is not None:
            self._picker.panel.clear_notice()
        self.name_edit.insert(char)
        self._update_counter()
        # Keep the caret (and the keyboard) in the name field.
        self.name_edit.setFocus()

    def reset_name(self):
        self.name_edit.setText(self._original)
        self._update_counter()
        self.status.setText("Reverted to the last loaded name (not applied yet).")

    # -- save --------------------------------------------------------------

    def save(self):
        if self._busy or self.conn.ftp is None or self._uid is None:
            return
        name = self.name_edit.text()
        if len(name) > 16:
            self.status.setText("Name is longer than 16 characters.")
            return
        if self._has_online:
            body = (f"Change the local name to:\n\n{name}\n\n"
                    "This writes the console's profile name. The avatar is not "
                    "touched.")
        else:
            body = (f"Set the local name to:\n\n{name}\n\n"
                    "This user has no online.json yet, so one will be created "
                    "with this name. The avatar is not touched.")
        if QMessageBox.question(
                self, "Apply name change?", body) != QMessageBox.Yes:
            return
        ftp, uid = self.conn.ftp, self._uid
        backup = self.backup_switch.isChecked()
        self._busy = True
        self.status.setText("Applying\u2026")
        self._update_actions()
        threading.Thread(target=self._save_worker,
                         args=(ftp, uid, name, backup), daemon=True).start()

    def _save_worker(self, ftp, uid, name, backup):
        try:
            if backup:
                backup_profile(ftp, uid)
            result = write_name(ftp, uid, name)
            # read back to confirm the console stored exactly what we wrote
            profile = read_profile(ftp, uid)
            got = ((profile.get("online") or {}).get("firstName")) or ""
            result["verified"] = (got == name)
            self._wrote.emit(result)
        except Exception as exc:  # noqa: BLE001
            self._failed.emit(str(exc))

    def _on_wrote(self, result):
        self._busy = False
        self._original = result.get("name", self._original)
        self._has_online = True
        if result.get("verified"):
            if result.get("created"):
                self.status.setText(
                    "Created online.json and applied the name (verified).")
            else:
                self.status.setText("Applied and verified on the console.")
        else:
            self.status.setText(
                "Applied, but the read-back didn't match. Restart the PS4.")
        self._update_actions()
        self.conn.refresh()  # re-read the console after the write

    def _on_failed(self, message):
        self._busy = False
        self.status.setText(f"Failed: {message}")
        self._update_actions()
