"""Application window and controller (Qt / PySide6)."""

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QEvent
from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QMainWindow,
                               QStackedWidget, QVBoxLayout, QWidget)

from . import __version__, theme
from .resources import assets_path
from .session import Connection
from .ui.connection_bar import ConnectionBar
from .ui.editor_view import EditorView
from .ui.profile_view import ProfileView
from .ui.send_view import SendView
from .ui.widgets import FolderTabs, SegmentedControl, make_faint

from ps4_avatar.settings import load_settings


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PS4 Profile Studio")
        self.resize(1280, 820)
        self.setMinimumSize(1040, 660)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(theme.PAD, 10, theme.PAD, 0)
        layout.setSpacing(8)

        self.settings = load_settings()
        self.connection = Connection(self.settings)

        header = QHBoxLayout()
        header.setSpacing(10)
        self.segmented = SegmentedControl(["Avatar", "Profile"])
        self.segmented.connect_changed(self.show_view)
        header.addWidget(self.segmented)
        self.conn_bar = ConnectionBar(self.connection)
        header.addWidget(self.conn_bar, 1)
        header.addWidget(make_faint(f"v{__version__}"))
        layout.addLayout(header)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        # Avatar tab = sub-tabs: Editor | Send (folder-tab panel)
        avatar_tab = QWidget()
        avatar_layout = QVBoxLayout(avatar_tab)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.setSpacing(0)

        self.editor = EditorView()
        self.send = SendView(self.connection, lambda: self.editor.outputs)
        self.avatar_sub = FolderTabs(["Editor", "Send"])
        self.avatar_sub.add_page(self.editor)
        self.avatar_sub.add_page(self.send)
        self.avatar_sub.connect_changed(self.show_avatar_sub)
        avatar_layout.addWidget(self.avatar_sub, 1)
        self.editor.outputs_changed.connect(self.send.update_preview)

        self.profile = ProfileView(self.connection)

        self.stack.addWidget(avatar_tab)
        self.stack.addWidget(self.profile)
        self.stack.setCurrentIndex(0)
        self.view = "avatar"

        self.setAcceptDrops(True)

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

    def dragMoveEvent(self, event):
        if self._dropped_images(event.mimeData()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = self._dropped_images(event.mimeData())
        if paths:
            event.acceptProposedAction()
            self.show_view(0)
            self.editor.load_image(paths[0])

    def show_view(self, index):
        self.segmented.set_current_index(index)
        self.stack.setCurrentIndex(index)
        self.view = "profile" if index == 1 else "avatar"
        if index == 0:
            self.send.update_preview()

    def show_avatar_sub(self, index):
        self.avatar_sub.set_current_index(index)
        if index == 1:
            self.send.update_preview()

    def changeEvent(self, event):
        """Close the picker when the window stops being the active one, so it
        never floats over another application."""
        if event.type() == QEvent.ActivationChange and not self.isActiveWindow():
            self.profile.hide_picker()
        super().changeEvent(event)

    def closeEvent(self, event):
        self.send.close()
        self.connection.disconnect()
        super().closeEvent(event)


def _load_bundled_fonts():
    fonts_dir = assets_path("fonts")
    for ttf in sorted(fonts_dir.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(ttf))


def _build_app():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(str(assets_path("app.png"))))
    _load_bundled_fonts()
    font = QFont()
    font.setFamilies(theme.FONT_FAMILIES)
    font.setPointSize(10)
    app.setFont(font)
    app.setStyleSheet(theme.build_qss())
    return app


def main(argv=None):
    parser = argparse.ArgumentParser(description="PS4 Profile Studio")
    parser.add_argument("--open", metavar="IMAGE", help="image to open at startup")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    app = _build_app()
    window = MainWindow()
    if args.open:
        window.editor.load_image(args.open)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
