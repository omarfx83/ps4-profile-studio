"""Symbol picker: a grid of PS4 symbol icons, grouped by category."""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QScrollArea,
                               QToolButton, QVBoxLayout, QWidget)

from .. import theme
from .widgets import ComboBox, make_faint
from ps4_avatar_qt import symbols as symbol_data


class SymbolsPanel(QWidget):
    """A category picker plus a scrollable grid of symbol icons."""

    symbol_chosen = Signal(str)

    COLUMNS = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        sections = symbol_data.sections()
        self._groups = []
        if sections:
            all_items = [item for _s, _l, items in sections for item in items]
            self._groups.append(("all", "All", all_items))
            self._groups.extend(sections)
        self._build_ui()
        self._populate(0)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        head = QHBoxLayout()
        self.combo = ComboBox()
        for _sec, label, items in self._groups:
            self.combo.addItem(f"{label}  ({len(items)})")
        self.combo.currentIndexChanged.connect(self._populate)
        head.addWidget(self.combo, 1)
        layout.addLayout(head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.body = QWidget()
        self.body.setStyleSheet(f"background: {theme.PANEL};")
        self.grid = QGridLayout(self.body)
        self.grid.setSpacing(4)
        self.grid.setContentsMargins(8, 8, 8, 8)
        self.scroll.setWidget(self.body)
        layout.addWidget(self.scroll, 1)

        if not self._groups:
            layout.addWidget(make_faint("No symbols found."))

    def _clear(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _populate(self, index):
        self._clear()
        if not (0 <= index < len(self._groups)):
            return
        _sec, _label, items = self._groups[index]
        for i, item in enumerate(items):
            button = QToolButton()
            button.setIcon(QIcon(str(item["icon_path"])))
            button.setIconSize(QSize(40, 40))
            button.setFixedSize(56, 56)
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(item["label"])
            button.clicked.connect(
                lambda _=False, ch=item["char"]: self.symbol_chosen.emit(ch))
            self.grid.addWidget(button, i // self.COLUMNS, i % self.COLUMNS)
        self.grid.setRowStretch(self.grid.rowCount(), 1)


class SymbolPickerPopup(QWidget):
    """Non-modal symbol picker that behaves like the Windows emoji panel.

    It stays open while you click symbols (each click emits ``symbol_chosen``),
    and closes only when you click outside it (``Qt.Popup``).
    """

    symbol_chosen = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setWindowTitle("PS4 Symbols")
        self.setStyleSheet(f"background: {theme.PANEL};")
        self.resize(440, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.panel = SymbolsPanel(self)
        self.panel.symbol_chosen.connect(self.symbol_chosen)
        layout.addWidget(self.panel, 1)
