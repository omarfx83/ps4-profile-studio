"""Avatar tab > Send: pick a user (list) and send the current avatar set."""

import threading
from datetime import datetime

from PIL import Image
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMessageBox,
                               QProgressBar, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from .. import theme
from .user_list import UserListPanel
from .widgets import (Separator, Switch, make_faint, make_heading, make_muted,
                      pil_to_pixmap)

from ps4_avatar.imaging import ps4_background
from ps4_avatar.ps4.sender import backup_user, nudge_profile, upload_files


class SendView(QWidget):
    """User list on the left, a single send panel on the right."""

    progress = Signal(int, int)
    finished = Signal(object, int, bool)

    def __init__(self, connection, outputs_provider, parent=None):
        super().__init__(parent)
        self.conn = connection
        self.outputs_provider = outputs_provider or (lambda: None)
        self._sending = False
        self._cancel = threading.Event()

        self.progress.connect(self._on_progress)
        self.finished.connect(self._on_finished)
        self.conn.users_ready.connect(self._on_conn_users)
        self.conn.disconnected.connect(self._on_conn_disconnected)

        self._build_ui()
        self.update_preview()
        self._update_actions()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(theme.PAD, 10, theme.PAD, 12)
        root.setSpacing(theme.PAD)

        self.user_list = UserListPanel(self.conn, single=True)
        self.user_list.picked.connect(lambda _uid: self._update_actions())
        root.addWidget(self.user_list, 1)

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

        root.addWidget(panel, 0)

    def _build_panel(self, panel):
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(10)

        outer.addWidget(make_heading("SEND AVATAR"))
        self.preview_lbl = QLabel()
        self.preview_lbl.setAlignment(Qt.AlignCenter)
        self.preview_lbl.setFixedSize(120, 120)
        outer.addWidget(self.preview_lbl, 0, Qt.AlignHCenter)
        self.preview_text = make_faint("No avatar ready.", wrap=True)
        self.preview_text.setAlignment(Qt.AlignCenter)
        outer.addWidget(self.preview_text)

        outer.addWidget(Separator())
        outer.addWidget(make_heading("OPTIONS"))
        self.backup = Switch(checked=True)
        outer.addLayout(self._option_row("Backup before overwrite", self.backup))
        self.refresh = Switch(checked=True)
        outer.addLayout(self._option_row(
            "Refresh console after send", self.refresh))
        self.pictures = Switch(checked=False)
        self.pictures.toggled.connect(lambda _v: self.update_preview())
        outer.addLayout(self._option_row(
            "Also write picture*.dds / picture.png", self.pictures))

        outer.addWidget(make_faint(
            "version.json is never uploaded or changed. Refreshing re-writes "
            "the user's existing online.json unchanged.", wrap=True))
        outer.addWidget(make_faint(
            "After sending, the login screen and bottom bar update; sign out "
            "and back in to refresh the in-session top-bar avatar.", wrap=True))

        outer.addStretch(1)

        outer.addWidget(Separator())
        self.btn_send = QPushButton("Send avatar")
        self.btn_send.setObjectName("accent")
        self.btn_send.clicked.connect(self.send_selected)
        outer.addWidget(self.btn_send)

        self.btn_send_all = QPushButton("Send to all users")
        self.btn_send_all.clicked.connect(self.send_all)
        outer.addWidget(self.btn_send_all)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        outer.addWidget(self.progress_bar)

        self.status = make_faint("Not connected.", wrap=True)
        outer.addWidget(self.status)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("danger")
        self.btn_cancel.clicked.connect(self.cancel)
        outer.addWidget(self.btn_cancel)

    def _option_row(self, text, switch):
        row = QHBoxLayout()
        row.addWidget(make_muted(text), 1)
        row.addWidget(switch, 0, Qt.AlignRight)
        return row

    # -- connection --------------------------------------------------------

    def _on_conn_users(self, _users):
        if not self._sending:
            self.status.setText("Connected. Pick a user, then Send avatar.")
        self._update_actions()

    def _on_conn_disconnected(self):
        if not self._sending:
            self.status.setText("Not connected.")
        self._update_actions()

    # -- preview -----------------------------------------------------------

    def update_preview(self):
        outputs = self.outputs_provider()
        if outputs:
            img = outputs.images[440]
            bg = ps4_background(120).copy()
            pad = max(3, round(120 * 0.10))
            inner = 120 - pad * 2
            disp = img.convert("RGBA").resize((inner, inner),
                                              Image.Resampling.LANCZOS)
            bg.alpha_composite(disp, (pad, pad))
            self.preview_lbl.setPixmap(pil_to_pixmap(bg))
            extra = " + picture*" if self.pictures.isChecked() else ""
            self.preview_text.setText(
                "Ready: avatar440.png + avatar64/128/260/440.dds" + extra)
        else:
            self.preview_lbl.clear()
            self.preview_text.setText(
                "No avatar ready.\nApply a crop in the editor first.")
        self._update_actions()

    # -- state -------------------------------------------------------------

    def _update_actions(self):
        busy = self._sending
        outputs = self.outputs_provider()
        selected = self.user_list.selected_uids()
        ready = bool(self.conn.is_connected and not busy and outputs)
        self.btn_send.setEnabled(ready and bool(selected))
        self.btn_send_all.setEnabled(ready and bool(self.user_list.users))
        self.btn_cancel.setEnabled(busy)

    # -- sending -----------------------------------------------------------

    def send_selected(self):
        uids = self.user_list.selected_uids()
        if not uids:
            QMessageBox.information(self, "No user selected",
                                    "Pick a user from the list first.")
            return
        if QMessageBox.question(
                self, "Send avatar?",
                f"Send the current avatar set to {uids[0]}?") != QMessageBox.Yes:
            return
        self._start(uids)

    def send_all(self):
        uids = [u.uid for u in self.user_list.users]
        if not uids:
            return
        if QMessageBox.question(
                self, "Send to all users?",
                f"Send the current avatar set to ALL {len(uids)} user(s) "
                "on this PS4?") != QMessageBox.Yes:
            return
        self._start(uids)

    def _start(self, uids):
        outputs = self.outputs_provider()
        if not outputs:
            QMessageBox.information(self, "No avatar ready",
                                    "Apply a crop in the editor first.")
            return
        if self.conn.ftp is None:
            QMessageBox.warning(self, "Not connected",
                                "Connect to the PS4 first.")
            return
        files = outputs.files(self.pictures.isChecked())
        self._cancel.clear()
        self._sending = True
        self.progress_bar.setRange(0, max(1, len(uids)))
        self.progress_bar.setValue(0)
        self.status.setText(f"Sending to {len(uids)} user(s)\u2026")
        self._update_actions()
        threading.Thread(target=self._worker,
                         args=(list(uids), files, self.backup.isChecked(),
                               self.refresh.isChecked()),
                         daemon=True).start()

    def _worker(self, uids, files, backup, refresh):
        ftp = self.conn.ftp
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        results = []
        for index, uid in enumerate(uids):
            if self._cancel.is_set():
                break
            try:
                if backup:
                    backup_user(ftp, uid, stamp)
                upload_files(ftp, uid, files)
                if refresh:
                    nudge_profile(ftp, uid)
                results.append((uid, True, ""))
            except Exception as exc:  # noqa: BLE001
                results.append((uid, False, str(exc)))
            self.progress.emit(index + 1, len(uids))
        self.finished.emit(results, len(uids), self._cancel.is_set())

    def _on_progress(self, done, total):
        self.progress_bar.setRange(0, max(1, total))
        self.progress_bar.setValue(done)
        self.status.setText(f"Sending\u2026 {done}/{total}")

    def _on_finished(self, results, total, cancelled):
        self._sending = False
        ok = sum(1 for _u, success, _e in results if success)
        failed = [(uid, err) for uid, success, err in results if not success]
        self.status.setText(
            (f"Cancelled. {ok} user(s) updated." if cancelled
             else f"Done. {ok}/{total} user(s) updated."))
        self._update_actions()
        if ok:
            self.conn.refresh()  # pull fresh data (names + thumbnails) back
        lines = [f"Updated: {ok} of {total} user(s)"]
        if cancelled:
            lines.append("Cancelled before finishing.")
        if failed:
            lines.append("")
            lines.append("Failed:")
            for uid, err in failed[:8]:
                lines.append(f"  {uid}: {err}")
            if len(failed) > 8:
                lines.append(f"  \u2026 and {len(failed) - 8} more")
        if self.backup.isChecked() and ok:
            lines.append("")
            lines.append("Backups: backups/<timestamp>/<user>")
        QMessageBox.information(
            self, "Send finished" if not cancelled else "Send cancelled",
            "\n".join(lines))

    def cancel(self):
        if self._sending:
            self._cancel.set()
            self.status.setText("Cancelling after the current user\u2026")

    def close(self):
        self._cancel.set()
