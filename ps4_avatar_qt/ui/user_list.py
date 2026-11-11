"""Shared user list: user cards rendered from a Connection's user list."""

from PIL import Image
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from .. import theme
from .widgets import CheckBox, make_faint, make_muted, pil_to_pixmap


def fmt_modify(facts):
    raw = str((facts or {}).get("modify") or "")
    if len(raw) >= 14 and raw[:14].isdigit():
        return (f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]} "
                f"{raw[8:10]}:{raw[10:12]}")
    return ""


class UserCard(QFrame):
    """One PS4 user row with thumbnail, details and checkbox."""

    def __init__(self, user, on_toggle, compact=False, single=False,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.user = user
        self._on_toggle = on_toggle
        self._single = single

        size = 40 if compact else 56
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 12, 7)
        layout.setSpacing(10)

        thumb = QLabel()
        thumb.setFixedSize(size, size)
        thumb.setAlignment(Qt.AlignCenter)
        if user.thumb is not None:
            disp = user.thumb.convert("RGBA").resize(
                (size, size), Image.Resampling.LANCZOS)
            thumb.setPixmap(pil_to_pixmap(disp))
        else:
            thumb.setText(user.display_name[:1].upper())
            thumb.setStyleSheet(
                f"background: {theme.BTN}; color: {theme.MUTED};"
                f"border-radius: 8px; font-size: 16pt; font-weight: 600;")
        layout.addWidget(thumb)

        text = QVBoxLayout()
        text.setSpacing(1)
        name = QLabel(user.display_name)
        name.setStyleSheet(f"font-weight: 600; color: {theme.FG};")
        text.addWidget(name)

        if user.online_id and user.online_id != user.display_name:
            sub_text = f"{user.online_id}  \u00b7  {user.uid}"
        else:
            sub_text = user.uid
        text.addWidget(make_faint(sub_text))
        modified = fmt_modify(user.facts)
        if modified:
            text.addWidget(make_faint(modified))
        layout.addLayout(text, 1)

        self.check = CheckBox(checked=bool(user.selected))
        self.check.clicked.connect(self._apply)
        layout.addWidget(self.check, 0, Qt.AlignRight)

        for widget in (self, thumb, name):
            widget.setCursor(Qt.PointingHandCursor)
            widget.mousePressEvent = self._click  # type: ignore[assignment]

        self.set_selected(bool(user.selected))

    def _click(self, _event):
        if self._single:
            self.check.setChecked(True)
        else:
            self.check.setChecked(not self.check.isChecked())
        self._apply()

    def _apply(self):
        selected = self.check.isChecked()
        self.user.selected = selected
        self.set_selected(selected)
        self._on_toggle(self.user, selected)

    def set_selected(self, value):
        self.check.setChecked(bool(value))
        self.setProperty("selected", bool(value))
        self.style().unpolish(self)
        self.style().polish(self)


class UserListPanel(QWidget):
    """Scrollable list of user cards with an All / None header."""

    changed = Signal()
    picked = Signal(str)      # uid, in single-select mode

    def __init__(self, connection, compact=False, single=False, parent=None):
        super().__init__(parent)
        self.conn = connection
        self.compact = compact
        self.single = single
        self.cards = []
        self.users = []
        self._build_ui()
        connection.users_ready.connect(self.set_users)
        connection.disconnected.connect(lambda: self.set_users([]))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        head = QHBoxLayout()
        self.count_lbl = make_muted("Not connected")
        head.addWidget(self.count_lbl, 1)
        self.btn_all = QPushButton("All")
        self.btn_all.clicked.connect(self.select_all)
        head.addWidget(self.btn_all)
        self.btn_none = QPushButton("None")
        self.btn_none.clicked.connect(self.select_none)
        head.addWidget(self.btn_none)
        if self.single:
            self.btn_all.hide()
            self.btn_none.hide()
        layout.addLayout(head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("listBg")
        self.body = QWidget()
        self.body.setObjectName("listBg")
        self.list_layout = QVBoxLayout(self.body)
        self.list_layout.setContentsMargins(6, 6, 6, 6)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.body)
        layout.addWidget(self.scroll, 1)

    # -- data --------------------------------------------------------------

    def set_users(self, users):
        prev = {u.uid for u in self.users if u.selected}
        self.users = list(users)
        if prev:
            for user in self.users:
                user.selected = user.uid in prev
        self._render()
        self._update()

    def _render(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.cards = []
        if not self.users:
            text = ("Connect to your PS4 to list its users."
                    if not self.conn.is_connected else
                    "No 0x\u2026 profile folders found on the console.")
            empty = QLabel(text)
            empty.setProperty("faint", True)
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("font-size: 13pt;")
            self.list_layout.insertWidget(0, empty)
            return
        for user in self.users:
            card = UserCard(user, self._on_toggle, compact=self.compact,
                            single=self.single)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)
            self.cards.append(card)

    def selected_uids(self):
        return [u.uid for u in self.users if u.selected]

    def _on_toggle(self, user, _selected):
        if self.single:
            for other in self.users:
                other.selected = other is user
            for card in self.cards:
                if card.user is not user:
                    card.set_selected(False)
            self._update()
            self.changed.emit()
            self.picked.emit(user.uid)
        else:
            self._update()
            self.changed.emit()

    def select_all(self):
        for card in self.cards:
            card.set_selected(True)
            card.user.selected = True
        self._update()
        self.changed.emit()

    def select_none(self):
        for card in self.cards:
            card.set_selected(False)
            card.user.selected = False
        self._update()
        self.changed.emit()

    def _update(self):
        selected = len(self.selected_uids())
        if self.users:
            self.count_lbl.setText(
                f"{len(self.users)} user(s) \u00b7 {selected} selected")
        elif self.conn.is_connected:
            self.count_lbl.setText("No 0x\u2026 profile folders found")
        else:
            self.count_lbl.setText("Not connected")
        busy = self.conn.busy
        self.btn_all.setEnabled(bool(self.users) and not busy)
        self.btn_none.setEnabled(bool(self.users) and not busy)
