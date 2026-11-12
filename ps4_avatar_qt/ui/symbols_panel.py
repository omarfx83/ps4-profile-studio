"""Symbol picker: PS4 symbol icons and a curated emoji set, grouped by category.

Both kinds of glyph land in the same name field, so the panel exposes a single
``symbol_chosen`` signal regardless of which tab produced the character.
"""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QScrollArea,
                               QToolButton, QVBoxLayout, QWidget)

from .. import emoji as emoji_data
from .. import theme
from .widgets import ComboBox, SegmentedControl, make_faint
from ps4_avatar_qt import symbols as symbol_data

# A flag is a pair of regional indicator symbols (U+1F1E6..U+1F1FF). Windows
# has never shipped flag artwork: its emoji font draws the two letters instead,
# so a tile shows "JP" rather than the flag. The character we insert is still
# the real flag, which the console does have artwork for.
_RI_FIRST = 0x1F1E6


def flag_code(char):
    """Return "JP" for a flag emoji, or None for anything else."""
    cps = [ord(c) for c in char]
    if len(cps) != 2 or any(not 0x1F1E6 <= cp <= 0x1F1FF for cp in cps):
        return None
    return "".join(chr(cp - _RI_FIRST + ord("A")) for cp in cps)


class EmojiButton(QToolButton):
    """Flat tile that draws an emoji as live text, plus its slot count.

    The small number in the corner appears only for emoji built from several
    code points (flags, skin tones, joined families), which use more than one
    of the sixteen name slots. Flags are drawn as a two-letter code because no
    Windows font can draw the flag itself.
    """

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.setObjectName("emojiCell")
        self._slots = int(item.get("slots", 1))
        self._code = flag_code(item["char"])
        self.setText("" if self._code else item["char"])
        self.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.setFixedSize(46, 46)
        self.setCursor(Qt.PointingHandCursor)
        country = item["label"].removeprefix("flag: ")
        if self._code:
            self.setAccessibleName(country)
            self.setToolTip(
                f"{country} — the console shows the national flag "
                f"(uses {self._slots} of 16 name slots)")
        elif self._slots > 1:
            self.setToolTip(
                f"{item['label']} — uses {self._slots} of 16 name slots")
        else:
            self.setToolTip(item["label"])

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        if self._code:
            font = QFont()
            font.setFamilies(theme.FONT_FAMILIES)
            font.setPointSizeF(10.5)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(theme.FG))
            painter.drawText(self.rect(), Qt.AlignCenter, self._code)
        if self._slots <= 1:
            return
        font = QFont()
        font.setFamilies(theme.FONT_FAMILIES)
        font.setPointSizeF(6.5)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(theme.ACCENT))
        painter.drawText(self.rect().adjusted(0, 0, -4, -2),
                         Qt.AlignRight | Qt.AlignBottom, str(self._slots))


class SymbolsPanel(QWidget):
    """A category picker plus a scrollable grid of symbols or emoji."""

    symbol_chosen = Signal(str)

    SYMBOL_COLUMNS = 6
    EMOJI_COLUMNS = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        sections = symbol_data.sections()
        self._symbol_groups = []
        if sections:
            all_items = [item for _s, _l, items in sections for item in items]
            self._symbol_groups.append(("all", "All symbols", all_items))
            self._symbol_groups.extend(sections)
        self._emoji_groups = emoji_data.groups()
        self._groups = self._symbol_groups
        self._mode = "symbols"
        self._build_ui()
        self._refresh_groups()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.switch = SegmentedControl(["PS4 symbols", "Emoji"])
        self.switch.connect_changed(self._set_mode)
        layout.addWidget(self.switch)

        head = QHBoxLayout()
        self.combo = ComboBox()
        self.combo.currentIndexChanged.connect(self._populate)
        head.addWidget(self.combo, 1)
        layout.addLayout(head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.body = QWidget()
        self.body.setObjectName("pickerBody")
        self.grid = QGridLayout(self.body)
        self.grid.setSpacing(4)
        self.grid.setContentsMargins(8, 8, 8, 8)
        self.scroll.setWidget(self.body)
        layout.addWidget(self.scroll, 1)

        self.hint = make_faint(
            "The small number shows how many of the 16 name slots an emoji "
            "uses.", wrap=True)
        self.hint.setVisible(False)
        layout.addWidget(self.hint)

        if not self._symbol_groups and not self._emoji_groups:
            layout.addWidget(make_faint("No symbols found."))

    def _set_mode(self, index):
        if index == 1:
            self._mode = "emoji"
            self._groups = self._emoji_groups
        else:
            self._mode = "symbols"
            self._groups = self._symbol_groups
        self.hint.setVisible(self._mode == "emoji")
        self._refresh_groups()

    def _refresh_groups(self):
        self.combo.blockSignals(True)
        self.combo.clear()
        for _sec, label, items in self._groups:
            self.combo.addItem(f"{label}  ({len(items)})")
        self.combo.setCurrentIndex(0)
        self.combo.blockSignals(False)
        self._populate(0)

    def _clear(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # Hide and detach before deleteLater so the vacated area is
                # repainted at once instead of showing the previous grid.
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def _populate(self, index):
        self._clear()
        if not (0 <= index < len(self._groups)):
            return
        _sec, _label, items = self._groups[index]
        columns = (self.EMOJI_COLUMNS if self._mode == "emoji"
                   else self.SYMBOL_COLUMNS)
        if self._mode == "emoji":
            self._populate_emoji(items)
        else:
            self._populate_symbols(items)
        # Keep the tiles at their natural height and push the spare space to a
        # single trailing row, so a short category does not stretch its tiles.
        for row in range(self.grid.rowCount()):
            self.grid.setRowStretch(row, 0)
        rows = (len(items) + columns - 1) // columns
        self.grid.setRowStretch(rows, 1)

    def _populate_symbols(self, items):
        for i, item in enumerate(items):
            button = QToolButton()
            button.setObjectName("symbolCell")
            button.setIcon(QIcon(str(item["icon_path"])))
            button.setIconSize(QSize(40, 40))
            button.setFixedSize(56, 56)
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(item["label"])
            button.clicked.connect(
                lambda _=False, ch=item["char"]: self.symbol_chosen.emit(ch))
            self.grid.addWidget(button, i // self.SYMBOL_COLUMNS,
                                 i % self.SYMBOL_COLUMNS)

    def _populate_emoji(self, items):
        for i, item in enumerate(items):
            button = EmojiButton(item)
            button.clicked.connect(
                lambda _=False, ch=item["char"]: self.symbol_chosen.emit(ch))
            self.grid.addWidget(button, i // self.EMOJI_COLUMNS,
                                 i % self.EMOJI_COLUMNS)


class SymbolPickerPopup(QWidget):
    """Non-modal symbol picker that behaves like the Windows emoji panel.

    It stays open while you click symbols (each click emits ``symbol_chosen``),
    and closes only when you click outside it (``Qt.Popup``).
    """

    symbol_chosen = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("pickerPopup")
        self.setWindowTitle("PS4 Symbols")
        self.resize(460, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.panel = SymbolsPanel(self)
        self.panel.symbol_chosen.connect(self.symbol_chosen)
        layout.addWidget(self.panel, 1)
