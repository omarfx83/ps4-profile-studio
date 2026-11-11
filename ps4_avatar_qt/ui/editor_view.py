"""Editor tab: open, crop, preview and export one avatar set (Qt)."""

import io
import threading
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps
from PySide6.QtCore import QPointF, QRectF, Qt, QUrl, Signal
from PySide6.QtGui import (QColor, QDesktopServices, QFont, QKeySequence,
                           QPainter, QPainterPath, QPen, QPolygonF,
                           QShortcut)
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout,
                               QLabel, QMessageBox, QPushButton, QScrollArea,
                               QSizePolicy, QSpinBox, QVBoxLayout, QWidget)

from .. import theme
from ..ui.widgets import (ComboBox, GlyphButton, Separator, Switch, make_faint,
                          make_heading, make_muted, pil_to_pixmap)

from ps4_avatar.dds import SIZES, image_to_dxt5_dds
from ps4_avatar.imaging import (MASK_SHAPES, MAX_WORKING_SIZE,
                                checkerboard, initial_crop, ps4_background,
                                render_avatar, shape_outline)
from ps4_avatar.models import AvatarSet

CANVAS_BG = theme.CANVAS_BG


def _build_avatar_set(src, crop, shape, padding=0.0):
    """Encode previews/DDS for one crop + mask shape + padding (thread-safe)."""
    x, y, s = crop
    box = src.crop((x, y, x + s, y + s))
    images, dds_files, previews = {}, {}, {}
    for size in SIZES:
        img = render_avatar(box, size, shape, padding)
        dds = image_to_dxt5_dds(img)
        with Image.open(io.BytesIO(dds)) as decoded:
            decoded.load()
            preview = decoded.convert("RGBA")
        images[size] = img
        dds_files[size] = dds
        previews[size] = preview
    return AvatarSet(images=images, dds=dds_files, previews=previews)



class _CropCanvas(QWidget):
    """Interactive surface; all state lives on the parent EditorView."""

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(200, 200)

    def paintEvent(self, _event):
        self.view.paint_canvas(self)

    def mousePressEvent(self, event):
        self.view.on_press(event)

    def mouseMoveEvent(self, event):
        self.view.on_motion(event)

    def mouseReleaseEvent(self, event):
        self.view.on_release(event)

    def wheelEvent(self, event):
        self.view.on_wheel(event)


class EditorView(QWidget):
    outputs_changed = Signal()
    _render_ready = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.src = None
        self.crop = None
        self.scale = 1.0
        self.ox = self.oy = 0.0
        self.auto_fit = True
        self.state = "empty"
        self.outputs = None
        self._render_token = 0
        self.preview_zoom = 1.0

        self.drag_mode = None
        self.drag_handle = None
        self.drag_img0 = (0.0, 0.0)
        self.drag_crop0 = None
        self.drag_anchor = (0.0, 0.0)

        self._src_id = 0
        self._disp_key = None
        self._disp_pix = None
        self._dim_pix = None
        self._snapshot = None

        self.last_dir = str(Path.home())
        self.json_dir = None
        self._dropping = False
        self.setAcceptDrops(True)

        self._build_ui()
        self._wire_shortcuts()
        self._render_ready.connect(self._on_render_ready)
        self._update_buttons()

    # -- UI ----------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(theme.PAD, 10, theme.PAD, 12)
        root.setSpacing(10)

        # toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.btn_open = QPushButton("Open Image")
        self.btn_open.clicked.connect(self.open_dialog)
        toolbar.addWidget(self.btn_open)
        toolbar.addWidget(make_muted("JPG / PNG"))

        toolbar.addStretch(1)

        toolbar.addWidget(make_muted("PS4 blue preview"))
        self.ps4_bg = Switch(checked=True)
        self.ps4_bg.toggled.connect(self.on_bg_toggle)
        toolbar.addWidget(self.ps4_bg)

        toolbar.addSpacing(12)
        toolbar.addWidget(make_muted("Mask"))
        self.mask_combo = ComboBox()
        self.mask_combo.addItems(list(MASK_SHAPES))
        self.mask_combo.currentTextChanged.connect(self.on_mask_change)
        toolbar.addWidget(self.mask_combo)

        toolbar.addSpacing(12)
        toolbar.addWidget(make_muted("Padding"))
        self.pad_spin = QSpinBox()
        self.pad_spin.setRange(0, 40)
        self.pad_spin.setSingleStep(2)
        self.pad_spin.setSuffix(" %")
        self.pad_spin.setValue(0)
        self.pad_spin.setAlignment(Qt.AlignCenter)
        self.pad_spin.setFixedWidth(88)
        self.pad_spin.valueChanged.connect(self.on_padding_change)
        toolbar.addWidget(self.pad_spin)

        root.addLayout(toolbar)

        # body
        body = QHBoxLayout()
        body.setSpacing(theme.PAD)

        canvas_col = QVBoxLayout()
        canvas_col.setSpacing(6)

        self.canvas = _CropCanvas(self)
        canvas_col.addWidget(self.canvas, 1)

        # zoom controls, under the canvas
        self.zoom_row = QHBoxLayout()
        self.zoom_row.setSpacing(6)

        self.btn_fit = QPushButton("Fit")
        self.btn_fit.clicked.connect(self.fit_view)
        self.zoom_row.addWidget(self.btn_fit)

        self.btn_zoom_out = GlyphButton("minus")
        self.btn_zoom_out.setFixedWidth(36)
        self.btn_zoom_out.clicked.connect(lambda: self.zoom_by(1 / 1.25))
        self.zoom_row.addWidget(self.btn_zoom_out)

        self.zoom_lbl = make_muted("100%")
        self.zoom_lbl.setFixedWidth(52)
        self.zoom_lbl.setAlignment(Qt.AlignCenter)
        self.zoom_row.addWidget(self.zoom_lbl)

        self.btn_zoom_in = GlyphButton("plus")
        self.btn_zoom_in.setFixedWidth(36)
        self.btn_zoom_in.clicked.connect(lambda: self.zoom_by(1.25))
        self.zoom_row.addWidget(self.btn_zoom_in)

        self.zoom_row.addSpacing(10)
        self.btn_whole = QPushButton("Whole image")
        self.btn_whole.setToolTip(
            "Frame the whole picture; the extra area stays transparent")
        self.btn_whole.clicked.connect(self.fit_image)
        self.zoom_row.addWidget(self.btn_whole)
        self.zoom_row.addStretch(1)

        canvas_col.addLayout(self.zoom_row)

        body.addLayout(canvas_col, 1)

        panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedWidth(340)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        self._build_panel(content)
        scroll.setWidget(content)
        panel_layout.addWidget(scroll)

        body.addWidget(panel, 0)

        root.addLayout(body, 1)

        # bottom bar
        bottom = QHBoxLayout()
        self.status = make_muted("Open a JPG or PNG to begin.")
        bottom.addWidget(self.status, 1)

        self.btn_export = QPushButton("Export…")
        self.btn_export.setObjectName("accent")
        self.btn_export.clicked.connect(self.export)
        bottom.addWidget(self.btn_export)

        self.btn_recrop = QPushButton("Re-crop")
        self.btn_recrop.clicked.connect(self.re_crop)
        bottom.addWidget(self.btn_recrop)

        self.btn_cancel_mask = QPushButton("Cancel")
        self.btn_cancel_mask.clicked.connect(self.cancel_mask)
        bottom.addWidget(self.btn_cancel_mask)

        self.btn_apply = QPushButton("Apply Crop")
        self.btn_apply.setObjectName("accent")
        self.btn_apply.clicked.connect(self.apply_crop)
        bottom.addWidget(self.btn_apply)

        root.addLayout(bottom)

    def _build_panel(self, panel):
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(18, 12, 18, 12)
        outer.setSpacing(5)

        outer.addWidget(make_heading("PREVIEW"))

        self.lbl440 = QLabel()
        self.lbl440.setAlignment(Qt.AlignCenter)
        self.lbl440.setFixedSize(164, 164)
        outer.addWidget(self.lbl440, 0, Qt.AlignHCenter)

        self.cap440 = make_muted("440 × 440 · —")
        self.cap440.setAlignment(Qt.AlignCenter)
        outer.addWidget(self.cap440)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.small = {}
        for size, px in ((260, 92), (128, 64), (64, 48)):
            cell = QVBoxLayout()
            cell.setSpacing(3)
            img_lbl = QLabel()
            img_lbl.setAlignment(Qt.AlignCenter)
            img_lbl.setFixedSize(px, px)
            cap = make_faint(f"{size} · —")
            cap.setAlignment(Qt.AlignCenter)
            cell.addWidget(img_lbl, 0, Qt.AlignHCenter)
            cell.addWidget(cap)
            wrap = QWidget()
            wrap.setLayout(cell)
            row.addWidget(wrap)
            self.small[size] = (img_lbl, cap, px)
        row.addStretch(1)
        outer.addLayout(row)

        outer.addWidget(make_faint(
            "Previews are real DXT5 output — what the PS4 renders.", wrap=True))
        outer.addWidget(Separator())

        outer.addWidget(make_heading("EXPORT OPTIONS"))
        self.opt_avatar_png = self._option_row(
            outer, "Also write avatar.png")
        self.opt_pictures = self._option_row(
            outer, "Also write picture*.dds / picture.png")
        self.opt_json = self._option_row(
            outer, "Copy online.json + version.json", command=self._on_json_toggle)

        json_row = QHBoxLayout()
        self.btn_json = QPushButton("Folder…")
        self.btn_json.clicked.connect(self.choose_json_dir)
        json_row.addWidget(self.btn_json)
        self.json_label = make_faint("not selected")
        json_row.addWidget(self.json_label, 1)
        outer.addLayout(json_row)

        outer.addWidget(make_faint(
            "JSON files are never generated — account metadata.", wrap=True))
        outer.addStretch(1)

    def _option_row(self, parent, text, command=None):
        row = QHBoxLayout()
        row.addWidget(make_muted(text), 1)
        switch = Switch(checked=False)
        if command:
            switch.toggled.connect(lambda _v: command())
        row.addWidget(switch, 0, Qt.AlignRight)
        parent.addLayout(row)
        return switch

    def _wire_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self.open_dialog)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self.export)
        QShortcut(QKeySequence("Return"), self, activated=self._enter)
        QShortcut(QKeySequence("Escape"), self, activated=self.cancel_mask)

    def _enter(self):
        if self.state == "crop":
            self.apply_crop()

    # -- geometry helpers --------------------------------------------------

    def canvas_size(self):
        return max(2, self.canvas.width()), max(2, self.canvas.height())

    def to_canvas(self, ix, iy):
        return self.ox + ix * self.scale, self.oy + iy * self.scale

    def to_image(self, cx, cy):
        return (cx - self.ox) / self.scale, (cy - self.oy) / self.scale

    def _fit_scale(self):
        cw, ch = self.canvas_size()
        iw, ih = self.src.size
        return max(1e-4, min((cw - 56) / iw, (ch - 56) / ih))

    def _clamp_offset(self):
        if self.src is None:
            return
        cw, ch = self.canvas_size()
        iw, ih = self.src.size
        dw, dh = iw * self.scale, ih * self.scale
        self.ox = (cw - dw) / 2 if dw <= cw else min(0.0, max(cw - dw, self.ox))
        self.oy = (ch - dh) / 2 if dh <= ch else min(0.0, max(ch - dh, self.oy))

    def _center(self):
        cw, ch = self.canvas_size()
        iw, ih = self.src.size
        self.ox = (cw - iw * self.scale) / 2
        self.oy = (ch - ih * self.scale) / 2

    def _min_crop(self):
        iw, ih = self.src.size
        return min(48, iw, ih)

    def _max_crop(self):
        """Largest square that can contain the whole image."""
        iw, ih = self.src.size
        return max(iw, ih)

    def _clamp_crop_pos(self, x, y, s):
        """Keep the square overlapping the image, but allow it outside it.

        This lets a large square (up to the image's long edge) frame the whole
        picture; the area outside the image is rendered as transparent.
        """
        iw, ih = self.src.size
        lo_x, hi_x = min(0, iw - s), max(0, iw - s)
        lo_y, hi_y = min(0, ih - s), max(0, ih - s)
        return (int(round(max(lo_x, min(x, hi_x)))),
                int(round(max(lo_y, min(y, hi_y)))))

    def fit_image(self):
        """Set the crop square to the whole picture (outside area transparent)."""
        if self.src is None or self.state != "crop":
            return
        iw, ih = self.src.size
        s = self._max_crop()
        self.crop = ((iw - s) // 2, (ih - s) // 2, s)
        self.canvas.update()

    # -- loading -----------------------------------------------------------

    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open avatar source image", self.last_dir,
            "Images (*.png *.jpg *.jpeg);;PNG (*.png);;JPEG (*.jpg *.jpeg);;"
            "All files (*)")
        if path:
            self.load_image(path)

    # -- drag & drop -------------------------------------------------------

    _IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".jpe", ".bmp", ".webp", ".gif",
                   ".tif", ".tiff"}

    def _dropped_images(self, mime):
        if not mime.hasUrls():
            return []
        found = []
        for url in mime.urls():
            path = url.toLocalFile()
            if path and Path(path).suffix.lower() in self._IMAGE_EXTS:
                found.append(path)
        return found

    def dragEnterEvent(self, event):
        if self._dropped_images(event.mimeData()):
            event.acceptProposedAction()
            self._dropping = True
            self.canvas.setCursor(Qt.DragCopyCursor)
            self.canvas.update()

    def dragMoveEvent(self, event):
        if self._dropped_images(event.mimeData()):
            event.acceptProposedAction()

    def dragLeaveEvent(self, _event):
        self._dropping = False
        self.canvas.setCursor(Qt.ArrowCursor)
        self.canvas.update()

    def dropEvent(self, event):
        paths = self._dropped_images(event.mimeData())
        self._dropping = False
        self.canvas.setCursor(Qt.ArrowCursor)
        if paths:
            event.acceptProposedAction()
            self.load_image(paths[0])
            self.canvas.update()

    def load_image(self, path):
        try:
            img = Image.open(path)
            img.load()
            img = ImageOps.exif_transpose(img).convert("RGBA")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Cannot open image", f"{path}\n\n{exc}")
            return

        if max(img.size) > MAX_WORKING_SIZE:
            img.thumbnail((MAX_WORKING_SIZE, MAX_WORKING_SIZE),
                          Image.Resampling.LANCZOS)

        self.src = img
        self._src_id += 1
        self._render_token += 1
        self._disp_key = None
        self.outputs = None
        self._clear_previews()
        self.outputs_changed.emit()
        self.last_dir = str(Path(path).parent)

        self.crop = initial_crop(*img.size)
        self.state = "crop"
        self.auto_fit = True
        self._snapshot = (self.crop, self.mask_combo.currentText(),
                          self.pad_spin.value(), False)
        self._update_buttons()
        self.fit_view()

    # -- painting ----------------------------------------------------------

    def paint_canvas(self, widget):
        painter = QPainter(widget)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(widget.rect(), QColor(CANVAS_BG))

        if self.src is None:
            self._paint_empty(painter, widget)
        elif self.state == "preview":
            self._paint_preview(painter, widget)
        else:
            self._paint_crop(painter, widget)

        if self._dropping:
            pen = QPen(QColor(theme.ACCENT), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(
                QRectF(widget.rect()).adjusted(3, 3, -3, -3), 8, 8)

    def _paint_empty(self, painter, widget):
        cw, ch = self.canvas_size()
        painter.setPen(QColor(theme.FAINT))
        f = painter.font()
        f.setPointSize(20)
        f.setWeight(QFont.DemiBold)
        painter.setFont(f)
        painter.drawText(QRectF(0, ch / 2 - 40, cw, 40), Qt.AlignCenter,
                         "Open a JPG or PNG")
        painter.setPen(QColor("#42464c"))
        f.setPointSize(10)
        f.setWeight(QFont.Normal)
        painter.setFont(f)
        painter.drawText(QRectF(0, ch / 2 + 2, cw, 30), Qt.AlignCenter,
                         "or drag & drop an image here · drag the square to "
                         "crop · wheel to zoom")

    def _display_pixmaps(self):
        iw, ih = self.src.size
        dw, dh = max(1, int(iw * self.scale)), max(1, int(ih * self.scale))
        key = (self._src_id, dw, dh)
        if key != self._disp_key:
            disp = self.src.resize((dw, dh), Image.Resampling.LANCZOS)
            dim = ImageEnhance.Brightness(disp).enhance(0.32)
            self._disp_pix = pil_to_pixmap(disp)
            self._dim_pix = pil_to_pixmap(dim)
            self._disp_key = key
        return dw, dh

    def _paint_crop(self, painter, widget):
        self._clamp_offset()
        dw, dh = self._display_pixmaps()
        ox, oy = self.ox, self.oy

        painter.drawPixmap(int(round(ox)), int(round(oy)), self._dim_pix)

        x, y, s = self.crop
        cx0, cy0 = self.to_canvas(x, y)
        cx1, cy1 = self.to_canvas(x + s, y + s)

        painter.save()
        painter.setClipRect(QRectF(cx0, cy0, cx1 - cx0, cy1 - cy0))
        painter.drawPixmap(int(round(ox)), int(round(oy)), self._disp_pix)
        painter.restore()

        grid_pen = QPen(QColor(255, 255, 255, 150), 1, Qt.DashLine)
        painter.setPen(grid_pen)
        for f in (1 / 3, 2 / 3):
            gx = cx0 + (cx1 - cx0) * f
            gy = cy0 + (cy1 - cy0) * f
            painter.drawLine(int(gx), int(cy0), int(gx), int(cy1))
            painter.drawLine(int(cx0), int(gy), int(cx1), int(gy))

        self._draw_mask_outline(painter,
                                QRectF(cx0, cy0, cx1 - cx0, cy1 - cy0))

        painter.setPen(QPen(QColor(theme.ACCENT), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(cx0, cy0, cx1 - cx0, cy1 - cy0))

        painter.setPen(QPen(QColor(theme.ACCENT_TEXT), 1))
        painter.setBrush(QColor(theme.ACCENT))
        for hx, hy in self._handle_points(cx0, cy0, cx1, cy1):
            painter.drawRect(QRectF(hx - 5, hy - 5, 10, 10))

        self.zoom_lbl.setText(f"{self.scale * 100:.0f}%")
        self.status.setText(
            f"Source {self.src.width}×{self.src.height}   ·   "
            f"Crop {s}×{s} @ ({x}, {y})   ·   Zoom {self.scale * 100:.0f}%")

    def _preview_tile(self, img, size):
        if self.ps4_bg.isChecked():
            bg = ps4_background(size).copy()
        else:
            bg = checkerboard(size, max(6, size // 20))
        pad = max(2, round(size * 0.10))
        inner = max(8, size - pad * 2)
        disp = img.resize((inner, inner), Image.Resampling.LANCZOS)
        bg.alpha_composite(disp, (pad, pad))
        return bg

    def _shape_polygon(self, shape, rect):
        points = shape_outline(shape)
        return QPolygonF([
            QPointF(rect.x() + x * rect.width(),
                    rect.y() + y * rect.height())
            for x, y in points])

    def _draw_mask_outline(self, painter, rect):
        """Outline the current mask shape over the given rect (no shading)."""
        pad_frac = self.pad_spin.value() / 100.0
        inner = rect.adjusted(rect.width() * pad_frac, rect.height() * pad_frac,
                              -rect.width() * pad_frac, -rect.height() * pad_frac)
        shape = self.mask_combo.currentText()
        is_square = not shape or shape in ("Square", "None")
        if is_square and pad_frac <= 0:
            return
        path = QPainterPath()
        path.addPolygon(self._shape_polygon(shape, inner))
        path.closeSubpath()
        pen = QPen(QColor(theme.ACCENT), 2)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

    def _paint_preview(self, painter, widget):
        if not self.outputs:
            cw, ch = self.canvas_size()
            painter.setPen(QColor(theme.MUTED))
            painter.drawText(QRectF(0, ch / 2 - 12, cw, 24), Qt.AlignCenter,
                             "Rendering preview…")
            return
        cw, ch = self.canvas_size()
        base = min((cw - 90) / 440, (ch - 90) / 440)
        side = max(32, int(440 * base * self.preview_zoom))
        pixmap = pil_to_pixmap(self._preview_tile(self.outputs.images[440],
                                                  side))
        px = int((cw - side) / 2)
        py = int((ch - side) / 2)
        painter.drawPixmap(px, py, pixmap)
        painter.setPen(QColor(theme.BORDER))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(px, py, side, side))

        self.zoom_lbl.setText(f"{self.preview_zoom * 100:.0f}%")
        self.status.setText(
            f"Crop applied — {self.crop[2]}×{self.crop[2]}   ·   "
            "Re-crop to adjust, or Export to write the files.")

    # -- crop interaction --------------------------------------------------

    def _handle_points(self, x0, y0, x1, y1):
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        return [(x0, y0), (mx, y0), (x1, y0), (x1, my),
                (x1, y1), (mx, y1), (x0, y1), (x0, my)]

    def _hit_handle(self, cx, cy):
        x, y, s = self.crop
        x0, y0 = self.to_canvas(x, y)
        x1, y1 = self.to_canvas(x + s, y + s)
        names = ["nw", "n", "ne", "e", "se", "s", "sw", "w"]
        for name, (hx, hy) in zip(names, self._handle_points(x0, y0, x1, y1)):
            if abs(cx - hx) <= 9 and abs(cy - hy) <= 9:
                return name
        return None

    def _inside_crop(self, cx, cy):
        x, y, s = self.crop
        x0, y0 = self.to_canvas(x, y)
        x1, y1 = self.to_canvas(x + s, y + s)
        return x0 <= cx <= x1 and y0 <= cy <= y1

    def on_press(self, event):
        pos = event.position()
        if event.button() == Qt.MiddleButton:
            self._pan_start = (pos.x(), pos.y())
            self.canvas.setCursor(Qt.ClosedHandCursor)
            return
        if event.button() != Qt.LeftButton:
            return
        if self.state != "crop" or self.src is None:
            return

        handle = self._hit_handle(pos.x(), pos.y())
        self.drag_img0 = self.to_image(pos.x(), pos.y())
        self.drag_crop0 = self.crop

        if handle:
            self.drag_mode = "resize"
            self.drag_handle = handle
        elif self._inside_crop(pos.x(), pos.y()):
            self.drag_mode = "move"
        else:
            ix, iy = self.drag_img0
            iw, ih = self.src.size
            if 0 <= ix <= iw and 0 <= iy <= ih:
                self.drag_mode = "new"
                self.drag_anchor = (ix, iy)
                self.crop = (int(ix), int(iy), self._min_crop())
                self.canvas.update()

    def on_motion(self, event):
        pos = event.position()
        if getattr(self, "_pan_start", None) is not None \
                and event.buttons() & Qt.MiddleButton:
            dx = pos.x() - self._pan_start[0]
            dy = pos.y() - self._pan_start[1]
            self._pan_start = (pos.x(), pos.y())
            self.ox += dx
            self.oy += dy
            self.auto_fit = False
            self.canvas.update()
            return

        if self.drag_mode is None or self.src is None:
            if self.state == "crop" and self.src is not None:
                self._update_cursor(pos.x(), pos.y())
            return

        ix, iy = self.to_image(pos.x(), pos.y())

        if self.drag_mode == "move":
            x0, y0, s = self.drag_crop0
            nx = x0 + (ix - self.drag_img0[0])
            ny = y0 + (iy - self.drag_img0[1])
            nx, ny = self._clamp_crop_pos(nx, ny, s)
            self.crop = (nx, ny, s)
        elif self.drag_mode == "resize":
            self._resize_crop(self.drag_handle, ix, iy)
        elif self.drag_mode == "new":
            ax, ay = self.drag_anchor
            s = int(max(abs(ix - ax), abs(iy - ay)))
            s = max(self._min_crop(), min(s, self._max_crop()))
            x = ax if ix >= ax else ax - s
            y = ay if iy >= ay else ay - s
            x, y = self._clamp_crop_pos(x, y, s)
            self.crop = (x, y, s)

        self.canvas.update()

    def on_release(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan_start = None
            self.canvas.setCursor(Qt.ArrowCursor)
        self.drag_mode = None
        self.drag_handle = None

    def _resize_crop(self, handle, ix, iy):
        x, y, s = self.crop
        min_s = self._min_crop()
        max_s = self._max_crop()

        if handle in ("nw", "ne", "sw", "se"):
            ax = x + s if handle in ("nw", "sw") else x
            ay = y + s if handle in ("nw", "ne") else y
            ns = int(max(abs(ix - ax), abs(iy - ay)))
            ns = max(min_s, min(ns, max_s))
            nx = ax - ns if ix < ax else ax
            ny = ay - ns if iy < ay else ay
        elif handle in ("e", "w"):
            ax = x if handle == "e" else x + s
            ns = int(abs(ix - ax))
            ns = max(min_s, min(ns, max_s))
            nx = ax if handle == "e" else ax - ns
            ny = y + s / 2 - ns / 2
        else:  # n / s
            ay = y if handle == "s" else y + s
            ns = int(abs(iy - ay))
            ns = max(min_s, min(ns, max_s))
            ny = ay if handle == "s" else ay - ns
            nx = x + s / 2 - ns / 2

        nx, ny = self._clamp_crop_pos(nx, ny, ns)
        self.crop = (nx, ny, ns)

    def _update_cursor(self, cx, cy):
        handle = self._hit_handle(cx, cy)
        cursors = {"nw": Qt.SizeFDiagCursor, "se": Qt.SizeFDiagCursor,
                   "ne": Qt.SizeBDiagCursor, "sw": Qt.SizeBDiagCursor,
                   "n": Qt.SizeVerCursor, "s": Qt.SizeVerCursor,
                   "e": Qt.SizeHorCursor, "w": Qt.SizeHorCursor}
        if handle:
            self.canvas.setCursor(cursors[handle])
        elif self._inside_crop(cx, cy):
            self.canvas.setCursor(Qt.SizeAllCursor)
        else:
            self.canvas.setCursor(Qt.CrossCursor)

    def on_wheel(self, event):
        if self.src is None:
            return
        factor = 1.15 ** (event.angleDelta().y() / 120.0)
        if self.state == "preview":
            self.preview_zoom = max(0.3, min(8.0, self.preview_zoom * factor))
            self.canvas.update()
            return
        if self.state != "crop":
            return
        pos = event.position()
        self.zoom_at(pos.x(), pos.y(), factor)

    def zoom_by(self, factor):
        if self.src is None:
            return
        if self.state == "preview":
            self.preview_zoom = max(0.3, min(8.0, self.preview_zoom * factor))
            self.canvas.update()
            return
        if self.state != "crop":
            return
        cw, ch = self.canvas_size()
        self.zoom_at(cw / 2, ch / 2, factor)

    def zoom_at(self, cx, cy, factor):
        iw, ih = self.src.size
        fit = self._fit_scale()
        max_scale = max(fit * 6, 3000 / max(iw, ih))
        new_scale = max(fit * 0.3, min(self.scale * factor, max_scale))
        if abs(new_scale - self.scale) < 1e-6:
            return
        ix, iy = self.to_image(cx, cy)
        self.scale = new_scale
        self.ox = cx - ix * new_scale
        self.oy = cy - iy * new_scale
        self.auto_fit = False
        self.canvas.update()

    def fit_view(self):
        if self.src is None:
            return
        if self.state == "preview":
            self.preview_zoom = 1.0
            self.canvas.update()
            return
        self.scale = self._fit_scale()
        self.auto_fit = True
        self._center()
        self.canvas.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.src is not None and self.auto_fit and self.state == "crop":
            self.scale = self._fit_scale()
            self._center()
        self.canvas.update()

    # -- apply / preview ---------------------------------------------------

    def apply_crop(self):
        if self.state != "crop" or self.src is None:
            return
        self.state = "preview"
        self.preview_zoom = 1.0
        self._update_buttons()
        self.canvas.update()
        self._start_render()

    def re_crop(self):
        if self.src is None:
            return
        # Remember the applied state so Cancel can return to it.
        self._snapshot = (self.crop, self.mask_combo.currentText(),
                          self.pad_spin.value(), self.state == "preview")
        self.state = "crop"
        self.outputs = None
        self._render_token += 1
        self._clear_previews()
        self.auto_fit = True
        self._update_buttons()
        self.outputs_changed.emit()
        self.fit_view()

    def on_mask_change(self, _text=None):
        if self.state == "preview" and self.src is not None:
            self._start_render()
        self._update_buttons()
        self.canvas.update()

    def on_padding_change(self, _value=None):
        if self.state == "preview" and self.src is not None:
            self._start_render()
        self.canvas.update()

    def cancel_mask(self):
        """Revert the crop/mask edits back to the previous state."""
        if self._snapshot is None:
            return
        crop, mask, pad, had_preview = self._snapshot
        self.crop = crop
        self.state = "crop"  # avoid a render while resetting the mask
        self.mask_combo.setCurrentText(mask)
        self.pad_spin.setValue(pad)
        if had_preview:
            self.state = "preview"
            self.preview_zoom = 1.0
            self._update_buttons()
            self.canvas.update()
            self._start_render()
        else:
            self.auto_fit = True
            self._update_buttons()
            self.fit_view()
        self.status.setText("Reverted to the previous state.")

    def on_bg_toggle(self):
        if self.outputs:
            self._update_previews()
        if self.state == "preview":
            self.canvas.update()

    def _start_render(self):
        """Encode the avatar set on a worker thread to keep the UI smooth."""
        if self.src is None or self.crop is None:
            return
        self._render_token += 1
        token = self._render_token
        src, crop = self.src, self.crop
        shape = self.mask_combo.currentText()
        padding = self.pad_spin.value() / 100.0
        self.status.setText("Rendering DXT5 previews…")

        def work():
            try:
                outputs = _build_avatar_set(src, crop, shape, padding)
            except Exception:  # noqa: BLE001
                return
            self._render_ready.emit((token, outputs))

        threading.Thread(target=work, daemon=True).start()

    def _on_render_ready(self, payload):
        token, outputs = payload
        if token != self._render_token:
            return  # a newer render superseded this one
        self.outputs = outputs
        self._update_previews()
        self._update_buttons()
        self.outputs_changed.emit()
        self.canvas.update()

    def _update_previews(self):
        if not self.outputs:
            return
        self.lbl440.setPixmap(pil_to_pixmap(
            self._preview_tile(self.outputs.previews[440], 164)))
        self.cap440.setText(
            f"440 × 440 · {len(self.outputs.dds[440]) / 1024:.0f} KB")
        for size, (lbl, cap, px) in self.small.items():
            lbl.setPixmap(pil_to_pixmap(
                self._preview_tile(self.outputs.previews[size], px)))
            cap.setText(f"{size} · {len(self.outputs.dds[size]) / 1024:.0f} KB")

    def _clear_previews(self):
        self.lbl440.clear()
        self.cap440.setText("440 × 440 · —")
        for size, (lbl, cap, _px) in self.small.items():
            lbl.clear()
            cap.setText(f"{size} · —")

    # -- export ------------------------------------------------------------

    def _on_json_toggle(self):
        if self.opt_json.isChecked() and not self.json_dir:
            self.choose_json_dir()

    def choose_json_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, "Folder containing online.json and version.json",
            self.last_dir)
        if path:
            self.json_dir = path
            self.json_label.setText(Path(path).name or path)
        elif not self.json_dir:
            self.opt_json.setChecked(False)

    def export(self):
        if not self.outputs:
            QMessageBox.information(self, "Nothing to export",
                                    "Apply a crop first, then export.")
            return

        folder = QFileDialog.getExistingDirectory(
            self, "Export avatar set to folder", self.last_dir)
        if not folder:
            return
        out = Path(folder)
        self.last_dir = folder

        files = self.outputs.files(self.opt_pictures.isChecked())
        if self.opt_avatar_png.isChecked():
            files["avatar.png"] = self.outputs.png_bytes()

        existing = [n for n in files if (out / n).exists()]
        if existing:
            shown = ", ".join(existing[:6]) + (" …" if len(existing) > 6 else "")
            reply = QMessageBox.question(
                self, "Overwrite files?",
                f"{len(existing)} file(s) already exist in:\n{out}\n\n"
                f"{shown}\n\nOverwrite them?")
            if reply != QMessageBox.Yes:
                return

        try:
            out.mkdir(parents=True, exist_ok=True)
            for name, data in files.items():
                (out / name).write_bytes(data)
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return

        copied = []
        if self.opt_json.isChecked():
            if not self.json_dir:
                QMessageBox.warning(
                    self, "No JSON folder",
                    "Choose the folder that contains online.json and "
                    "version.json.")
            else:
                src = Path(self.json_dir)
                for name in ("online.json", "version.json"):
                    candidate = src / name
                    if candidate.is_file():
                        try:
                            (out / name).write_bytes(candidate.read_bytes())
                            copied.append(name)
                        except OSError:
                            pass
                missing = [n for n in ("online.json", "version.json")
                           if n not in copied]
                if missing:
                    QMessageBox.warning(
                        self, "JSON not copied",
                        "Not found in the selected folder:\n" + ", ".join(missing))

        self.status.setText(f"Exported {len(files)} file(s) to {out}")
        msg = f"Exported {len(files)} files to:\n{out}"
        if copied:
            msg += "\n\nCopied: " + ", ".join(copied)
        reply = QMessageBox.information(self, "Export complete", msg,
                                        QMessageBox.Open | QMessageBox.Ok)
        if reply == QMessageBox.Open:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(out)))

    # -- misc --------------------------------------------------------------

    def _update_buttons(self):
        crop = self.state == "crop"
        preview = self.state == "preview"
        active = crop or preview
        self.btn_apply.setEnabled(crop)
        self.btn_recrop.setEnabled(preview)
        self.btn_export.setEnabled(preview and self.outputs is not None)
        self.btn_cancel_mask.setEnabled(
            self.state == "crop" and self._snapshot is not None)
        self.btn_fit.setEnabled(active)
        self.btn_zoom_out.setEnabled(active)
        self.btn_zoom_in.setEnabled(active)
        self.btn_whole.setEnabled(crop)
        if not active:
            self.zoom_lbl.setText("—")
