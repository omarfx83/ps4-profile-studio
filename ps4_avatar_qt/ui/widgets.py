"""Reusable Qt widgets and PIL <-> Qt image helpers.

Toggle and check controls are painted with QPainter (which anti-aliases and
is HiDPI-aware) instead of the software Canvas trick used in the Tk edition.
"""

from PySide6.QtCore import (Property, QEasingCurve, QEvent, QPoint, QPointF,
                            QPropertyAnimation, QRectF, QSize, Qt, Signal)
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QPainter, QPainterPath,
                           QPen, QPixmap)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QButtonGroup,
                               QComboBox, QFrame, QHBoxLayout, QListView,
                               QPushButton, QStackedWidget, QToolButton,
                               QVBoxLayout, QWidget)

from .. import theme


def pil_to_pixmap(image):
    """PIL.Image (any mode) -> QPixmap, without touching disk."""
    im = image.convert("RGBA")
    data = im.tobytes("raw", "RGBA")
    from PySide6.QtGui import QImage
    qimg = QImage(data, im.width, im.height, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())


class Switch(QAbstractButton):
    """iOS-style toggle with an animated knob, painted with QPainter."""

    def __init__(self, parent=None, width=46, height=26, checked=False):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(width, height)
        self.setCursor(Qt.PointingHandCursor)
        self._w = width
        self._h = height
        self._offset = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def _get_offset(self):
        return self._offset

    def _set_offset(self, value):
        self._offset = float(value)
        self.update()

    offset = Property(float, _get_offset, _set_offset)

    def _animate(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def sizeHint(self):
        return QSize(self._w, self._h)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        track = QColor(theme.ACCENT if self.isChecked() else "#3a3d42")
        if not self.isEnabled():
            track = QColor("#2f3237")
        painter.setPen(Qt.NoPen)
        painter.setBrush(track)
        radius = self._h / 2
        painter.drawRoundedRect(0, 0, self._w, self._h, radius, radius)

        knob = self._h - 8
        x = 4 + self._offset * (self._w - knob - 8)
        painter.setBrush(QColor("#ffffff" if self.isEnabled() else "#8b9097"))
        painter.drawEllipse(x, 4, knob, knob)


class CheckBox(QAbstractButton):
    """Rounded selection checkbox, painted with QPainter."""

    def __init__(self, parent=None, size=22, checked=False):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self._s = size

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        s = self._s
        rect = self.rect().adjusted(0, 0, -1, -1)

        if self.isChecked():
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(theme.ACCENT))
            painter.drawRoundedRect(rect, 6, 6)

            pen = QPen(QColor(theme.ACCENT_TEXT), 2.2)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            path = QPainterPath()
            path.moveTo(s * 0.27, s * 0.52)
            path.lineTo(s * 0.44, s * 0.70)
            path.lineTo(s * 0.75, s * 0.30)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
        else:
            painter.setPen(QPen(QColor(theme.BORDER), 1))
            painter.setBrush(QColor(theme.INPUT_BG))
            painter.drawRoundedRect(rect, 6, 6)


class StatusDot(QWidget):
    """Small colored connection indicator."""

    def __init__(self, parent=None, size=10, color=None):
        super().__init__(parent)
        self._s = size
        self._color = QColor(color or theme.FAINT)
        self.setFixedSize(size, size)

    def set_color(self, color):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._color)
        painter.drawEllipse(0, 0, self._s, self._s)


class Separator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("separator")
        self.setFixedHeight(1)


def make_heading(text):
    from PySide6.QtWidgets import QLabel
    label = QLabel(text)
    label.setProperty("heading", True)
    return label


def make_muted(text, wrap=None):
    from PySide6.QtWidgets import QLabel
    label = QLabel(text)
    label.setProperty("muted", True)
    if wrap:
        label.setWordWrap(True)
    return label


def make_faint(text, wrap=None):
    from PySide6.QtWidgets import QLabel
    label = QLabel(text)
    label.setProperty("faint", True)
    if wrap:
        label.setWordWrap(True)
    return label


class SegmentedControl(QFrame):
    """Pill-shaped Editor / PS4 switch built from checkable buttons."""

    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.setObjectName("segTrack")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self._buttons = []
        for index, option in enumerate(options):
            button = QPushButton(option)
            button.setObjectName("seg")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            if index == 0:
                button.setChecked(True)
            self.group.addButton(button, index)
            layout.addWidget(button)
            self._buttons.append(button)
        self.setFixedHeight(46)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(),
                           self.sizePolicy().verticalPolicy())

    def set_current_index(self, index):
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)

    def connect_changed(self, callback):
        self.group.idClicked.connect(callback)


class GlyphButton(QPushButton):
    """Flat square button that paints a crisp + / - glyph.

    Icon-style instead of a font character, so it stays sharp and uniform at
    any size and follows the enabled/disabled state.
    """

    def __init__(self, glyph, parent=None):
        super().__init__(parent)
        self._glyph = glyph  # "plus" or "minus"
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(theme.FG if self.isEnabled() else "#6b6f76")
        pen = QPen(color)
        pen.setWidthF(2.2)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        cx, cy, r = self.width() / 2, self.height() / 2, 5.0
        painter.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))
        if self._glyph == "plus":
            painter.drawLine(QPointF(cx, cy - r), QPointF(cx, cy + r))


class MenuButton(QToolButton):
    """Flat square button that paints a three-dot "more" glyph.

    Painted instead of a text character so it looks identical in every font
    and follows the hover/disabled state.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(26, 26)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            color = QColor(theme.FAINT)
        elif self.underMouse():
            color = QColor(theme.FG)
        else:
            color = QColor(theme.MUTED)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        cx, cy = self.width() / 2, self.height() / 2
        for offset in (-6.0, 0.0, 6.0):
            painter.drawEllipse(QPointF(cx + offset, cy), 1.8, 1.8)


def _rounded_path(rect, radius):
    path = QPainterPath()
    path.addRoundedRect(QRectF(rect), radius, radius)
    return path


_ACTIVE_CARD = None


class PopupCard(QFrame):
    """Flat rounded panel drawn as a child of the window.

    A native popup window needs per-pixel transparency for rounded corners, and
    on some Windows setups transparent pixels composite as black; a window mask
    avoids that but has hard, aliased edges. Painting the panel inside the main
    window (QWidget::paintEvent with QPainter, antialiasing on) gives the same
    smooth corners as the rest of the app, with no extra window and no shadow.
    """

    RADIUS = 9
    PADDING = 5
    GAP = 2

    def __init__(self, host):
        super().__init__(host)
        self.setObjectName("popupCard")
        self.setVisible(False)
        self._on_dismiss = None

    # -- geometry ----------------------------------------------------------

    def content_layout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(self.PADDING, self.PADDING,
                                  self.PADDING, self.PADDING)
        layout.setSpacing(1)
        return layout

    def card_size(self):
        return self.sizeHint()

    # -- painting ----------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.fillPath(_rounded_path(rect, self.RADIUS), QColor(theme.PANEL))
        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.drawPath(_rounded_path(rect, self.RADIUS))
        painter.end()

    # -- show / hide -------------------------------------------------------

    def open_below(self, anchor, width=None, card_height=None, align="left"):
        """Show the card attached to *anchor*, flipping above when needed."""
        global _ACTIVE_CARD
        host = self.window()
        if self.parentWidget() is not host:
            self.setParent(host)

        w = width or self.card_size().width()
        h = card_height or self.card_size().height()

        anchor_pos = anchor.mapTo(host, QPoint(0, 0))
        if align == "right":
            x = anchor_pos.x() + anchor.width() - w
        else:
            x = anchor_pos.x()
        x = max(2, min(x, host.width() - w - 2))

        y = anchor_pos.y() + anchor.height() + self.GAP
        if y + h > host.height() - 2:
            above = anchor_pos.y() - self.GAP - h
            y = above if above > 2 else max(2, host.height() - h - 2)

        if _ACTIVE_CARD is not None and _ACTIVE_CARD is not self:
            _ACTIVE_CARD.hide_card()
        _ACTIVE_CARD = self

        self.setGeometry(x, y, w, h)
        self.show()
        self.raise_()
        self._install_watchers()

    def hide_card(self):
        global _ACTIVE_CARD
        self._remove_watchers()
        self.hide()
        if _ACTIVE_CARD is self:
            _ACTIVE_CARD = None

    def _install_watchers(self):
        host = self.window()
        host.installEventFilter(self)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def _remove_watchers(self):
        host = self.window()
        host.removeEventFilter(self)
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)

    def dismiss(self):
        on_dismiss = self._on_dismiss
        self.hide_card()
        if on_dismiss is not None:
            on_dismiss()

    def eventFilter(self, obj, event):
        if not self.isVisible():
            return False
        kind = event.type()
        if kind == QEvent.MouseButtonPress:
            if obj is self.window():
                pos = self.window().mapFromGlobal(
                    event.globalPosition().toPoint())
                if not self.geometry().contains(pos):
                    self.dismiss()
            return False
        if kind in (QEvent.KeyPress, QEvent.ShortcutOverride):
            if event.key() == Qt.Key_Escape:
                event.accept()
                self.dismiss()
                return True
            return False
        if kind == QEvent.Resize and obj is self.window():
            self.dismiss()
        return False


class DropdownCard(PopupCard):
    """Popup list used by :class:`ComboBox`."""

    MAX_VISIBLE = 10

    def __init__(self, host):
        super().__init__(host)
        self.view = QListView(self)
        self.view.setObjectName("popupList")
        self.view.setFrameShape(QFrame.NoFrame)
        self.view.setSelectionMode(QListView.NoSelection)
        self.view.setEditTriggers(QListView.NoEditTriggers)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.view.setUniformItemSizes(True)
        self.view.setMouseTracking(True)
        self.view.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.content_layout().addWidget(self.view)

    def row_height(self):
        height = self.view.sizeHintForRow(0)
        return height if height > 0 else 28

    def show_for(self, combo):
        """Open for *combo*, matching its width and items."""
        self.view.setModel(combo.model())
        self.view.setModelColumn(combo.modelColumn())
        rows = min(combo.count(), self.MAX_VISIBLE)
        row_h = self.row_height()
        content = self.view.sizeHintForColumn(0) + 2 * self.PADDING
        # Match the field's width; only grow when the text really needs it.
        width = content if content > combo.width() + 24 else combo.width()
        height = rows * row_h + 2 * self.PADDING
        self.open_below(combo, width=width, card_height=max(height, row_h))
        self.view.scrollToTop()
        index = combo.currentIndex()
        if index >= 0:
            self.view.scrollTo(self.view.model().index(index, 0))


class ComboBox(QComboBox):
    """Combo box with an in-window, rounded dropdown.

    ``QComboBox::showPopup``/``hidePopup`` are the documented hooks for a
    custom popup, so the list is drawn by :class:`DropdownCard` instead of a
    native popup window.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._card = None
        self._closing = False

    def _ensure_card(self):
        if self._card is None:
            self._card = DropdownCard(self.window())
            self._card._on_dismiss = self.hidePopup
            self._card.view.clicked.connect(self._on_picked)
        return self._card

    def _on_picked(self, index):
        self.hidePopup()
        if index.isValid():
            row = index.row()
            self.setCurrentIndex(row)
            self.activated.emit(row)
            self.textActivated.emit(self.itemText(row))

    def showPopup(self):
        if not self.isEnabled():
            return
        if self._card is not None and self._card.isVisible():
            self.hidePopup()
            return
        card = self._ensure_card()
        if card.window() is not self.window():
            card.setParent(self.window())
            card._on_dismiss = self.hidePopup
        card.view.setModel(self.model())
        card.show_for(self)

    def hidePopup(self):
        if self._closing:
            return
        self._closing = True
        try:
            if self._card is not None:
                self._card.hide_card()
        finally:
            self._closing = False
        super().hidePopup()


class MenuCard(PopupCard):
    """Small action card that replaces a native QMenu."""

    def __init__(self, host):
        super().__init__(host)
        self._layout = self.content_layout()
        self.actions = []

    def add_action(self, text, callback=None):
        button = QPushButton(text, self)
        button.setObjectName("menuRow")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(
            lambda _checked=False, cb=callback: (self.hide_card(), cb and cb()))
        self._layout.addWidget(button)
        self.actions.append(button)
        return button

    def add_separator(self):
        line = QFrame(self)
        line.setObjectName("menuSeparator")
        line.setFixedHeight(1)
        self._layout.addWidget(line)

    def open_for(self, anchor):
        self.open_below(anchor, align="right")


class FolderTabs(QWidget):
    """Folder-style tabs.

    The tabs sit on top of a bordered panel: the panel's top edge (the
    baseline) runs the full width, the **active** tab is drawn in front so it
    merges into the panel, and the inactive tabs sit behind that line. Pages
    are shown in an internal stacked widget filling the panel.
    """

    changed = Signal(int)

    TAB_H = 36
    GAP = 6
    PADX = 24
    RADIUS = 9
    LEFT = 8
    BOTTOM = 10

    def __init__(self, labels, parent=None):
        super().__init__(parent)
        self._labels = list(labels)
        self._index = 0
        self._rects = []
        self._font = QFont(self.font())
        self._font.setBold(True)
        self._stack = QStackedWidget(self)
        self._measure()

    def add_page(self, widget):
        self._stack.addWidget(widget)

    def set_current_index(self, index):
        if 0 <= index < len(self._labels) and index != self._index:
            self._index = index
            self._stack.setCurrentIndex(index)
            self.update()

    def connect_changed(self, callback):
        self.changed.connect(callback)

    def _measure(self):
        metrics = QFontMetrics(self._font)
        self._rects = []
        x = float(self.LEFT)
        for label in self._labels:
            width = metrics.horizontalAdvance(label) + self.PADX * 2
            self._rects.append(QRectF(x, 0, width, self.TAB_H))
            x += width + self.GAP

    def _tab_path(self, rect):
        rad = self.RADIUS
        path = QPainterPath()
        path.moveTo(rect.left(), rect.bottom())
        path.lineTo(rect.left(), rect.top() + rad)
        path.quadTo(rect.left(), rect.top(), rect.left() + rad, rect.top())
        path.lineTo(rect.right() - rad, rect.top())
        path.quadTo(rect.right(), rect.top(), rect.right(), rect.top() + rad)
        path.lineTo(rect.right(), rect.bottom())
        return path

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        top = self.TAB_H

        # inactive tabs first: they stay behind the panel's top edge
        for i, rect in enumerate(self._rects):
            if i == self._index:
                continue
            painter.setBrush(QColor(theme.CANVAS_BG))
            painter.setPen(QPen(QColor(theme.BORDER), 1))
            painter.drawPath(self._tab_path(rect))

        # the panel that wraps the content; its top edge is the baseline
        panel = QRectF(0.5, top - 1.0, w - 1.0, h - self.BOTTOM - top + 0.5)
        rad = self.RADIUS
        path = QPainterPath()
        path.moveTo(panel.left(), panel.top())
        path.lineTo(panel.right(), panel.top())
        path.lineTo(panel.right(), panel.bottom() - rad)
        path.quadTo(panel.right(), panel.bottom(), panel.right() - rad,
                    panel.bottom())
        path.lineTo(panel.left() + rad, panel.bottom())
        path.quadTo(panel.left(), panel.bottom(), panel.left(),
                    panel.bottom() - rad)
        path.lineTo(panel.left(), panel.top())
        painter.setBrush(QColor(theme.BG))
        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.drawPath(path)

        # active tab in front, merging with the panel (baseline broken under it)
        rect = self._rects[self._index]
        painter.setBrush(QColor(theme.BG))
        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.drawPath(self._tab_path(rect))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(theme.BG))
        painter.drawRect(QRectF(rect.left() + 1, top - 1.0, rect.width() - 2, 2))

        # labels
        painter.setFont(self._font)
        for i, rect in enumerate(self._rects):
            painter.setPen(QColor(theme.ACCENT if i == self._index
                                  else theme.MUTED))
            painter.drawText(rect, Qt.AlignCenter, self._labels[i])

    def mousePressEvent(self, event):
        for i, rect in enumerate(self._rects):
            if rect.contains(event.position()):
                self.set_current_index(i)
                self.changed.emit(i)
                break

    def resizeEvent(self, _event):
        self._stack.setGeometry(2, self.TAB_H + 1, self.width() - 4,
                                self.height() - self.BOTTOM - self.TAB_H - 3)
