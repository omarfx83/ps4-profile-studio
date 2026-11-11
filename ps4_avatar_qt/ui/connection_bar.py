"""Header connection bar: remembered consoles + connect/refresh.

Always visible in the top bar, next to the tabs. Consoles are picked from a
list of recently connected devices, each with an optional friendly name. The
GoldHEN FTP server does not authenticate, so no username or password is needed.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QInputDialog, QLineEdit,
                               QMessageBox, QPushButton, QWidget)

from .. import theme
from .widgets import ComboBox, MenuButton, MenuCard, StatusDot, make_muted
from ps4_avatar import settings as store


def _split_address(text):
    """Split ``host`` / ``host:port`` / ``ftp://host/`` into (host, port|None)."""
    text = text.strip()
    if text.lower().startswith(("ftp://", "ftps://")):
        text = text.split("://", 1)[1]
    text = text.rstrip("/")
    host, sep, tail = text.rpartition(":")
    if sep and tail.isdigit() and host and ":" not in host:
        return host, int(tail)
    return text, None


class ConnectionBar(QWidget):
    """FTP connection controls driven by a shared Connection."""

    def __init__(self, connection, parent=None):
        super().__init__(parent)
        self.conn = connection
        self._devices = store.load_devices()
        self._selected = None          # dict of the picked device, or None
        self._user_count = None
        self._build_ui()
        self._wire()
        self._reload_devices()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        layout.addWidget(make_muted("Device"))
        self.device_combo = ComboBox()
        self.device_combo.setEditable(True)
        self.device_combo.setInsertPolicy(ComboBox.NoInsert)
        self.device_combo.setFixedWidth(200)
        self.device_combo.lineEdit().setPlaceholderText("PS4 IP address")
        self.device_combo.setToolTip(
            "Pick a saved console, or type its IP address.")
        self.device_combo.view().setMinimumWidth(320)
        layout.addWidget(self.device_combo)

        self.device_menu = MenuButton()
        self.device_menu.setObjectName("deviceMenu")
        self.device_menu.setToolTip("Rename or forget saved consoles")
        self._build_menu()
        layout.addWidget(self.device_menu)

        layout.addWidget(make_muted("Port"))
        self.port_edit = QLineEdit(str(store.DEFAULT_PORT))
        self.port_edit.setFixedWidth(68)
        layout.addWidget(self.port_edit)

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("accent")
        self.btn_connect.clicked.connect(self._on_connect)
        layout.addWidget(self.btn_connect)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self._on_refresh)
        layout.addWidget(self.btn_refresh)

        layout.addStretch(1)
        self.status = make_muted("Not connected")
        layout.addWidget(self.status)
        self.dot = StatusDot()
        layout.addWidget(self.dot)

        self._update()

    def _build_menu(self):
        self.menu_card = MenuCard(self.window())
        self.act_rename = self.menu_card.add_action(
            "Rename console\u2026", self._on_rename)
        self.act_forget = self.menu_card.add_action(
            "Forget console", self._on_forget)
        self.menu_card.add_separator()
        self.act_forget_all = self.menu_card.add_action(
            "Forget all consoles", self._on_forget_all)
        self.device_menu.clicked.connect(self._on_menu_clicked)

    def _on_menu_clicked(self):
        card = self.menu_card
        if card.window() is not self.window():
            card.setParent(self.window())
        if card.isVisible():
            card.hide_card()
            return
        self._update_menu()
        card.open_for(self.device_menu)

    def _wire(self):
        self.device_combo.activated.connect(self._on_device_activated)
        self.device_combo.lineEdit().textEdited.connect(self._on_typed)
        self.device_combo.lineEdit().returnPressed.connect(self._on_connect)
        self.port_edit.returnPressed.connect(self._on_connect)

        self.conn.connecting.connect(self._on_connecting)
        self.conn.users_ready.connect(self._on_users_ready)
        self.conn.failed.connect(self._on_failed)
        self.conn.disconnected.connect(self._on_disconnected)

    # -- devices -----------------------------------------------------------

    def _reload_devices(self, select=None):
        """Rebuild the combo from the stored list, optionally selecting one."""
        self._devices = store.load_devices()
        combo = self.device_combo
        combo.blockSignals(True)
        combo.clear()
        for device in self._devices:
            label = store.device_label(device)
            if device["name"]:
                text = f"{label}   \u00b7   {store.device_address(device)}"
            else:
                text = label
            combo.addItem(text)
            combo.setItemData(combo.count() - 1, device, Qt.UserRole)
        combo.blockSignals(False)

        target = None
        if select:
            target = next(
                (d for d in self._devices
                 if store.device_key(d["host"], d["port"])
                 == store.device_key(*select)), None)
        if target is None and self._devices:
            target = self._devices[0]
        if target is not None:
            self._select_device(target)
        else:
            self._selected = None
            combo.setEditText("")
            self.port_edit.setText(str(store.DEFAULT_PORT))
        self._update_menu()

    def _select_device(self, device):
        combo = self.device_combo
        self._selected = dict(device)
        combo.blockSignals(True)
        for index in range(combo.count()):
            data = combo.itemData(index, Qt.UserRole)
            if (data and store.device_key(data["host"], data["port"])
                    == store.device_key(device["host"], device["port"])):
                combo.setCurrentIndex(index)
                break
        combo.setEditText(store.device_label(device))
        combo.blockSignals(False)
        self.port_edit.setText(str(device["port"]))
        combo.setToolTip(f"{store.device_address(device)} "
                         f"\u00b7 {store.device_label(device)}")
        self._update_menu()

    def _on_device_activated(self, index):
        device = self.device_combo.itemData(index, Qt.UserRole)
        if isinstance(device, dict):
            self._select_device(device)

    def _on_typed(self, _text):
        # The user is typing an address by hand; ignore the picked device.
        self._selected = None
        self._update_menu()

    def _current_device(self):
        """The saved device matching the current address, if any."""
        if self._selected is not None:
            return self._selected
        host, port = self._target()
        if not host:
            return None
        key = store.device_key(host, port or store.DEFAULT_PORT)
        return next(
            (d for d in self._devices
             if store.device_key(d["host"], d["port"]) == key), None)

    def _target(self):
        """Return (host, port) for the current controls."""
        if self._selected is not None:
            host = self._selected["host"]
        else:
            host, inline_port = _split_address(self.device_combo.currentText())
            if inline_port is not None:
                self.port_edit.setText(str(inline_port))
        try:
            port = int(self.port_edit.text().strip())
        except ValueError:
            port = None
        return host, port

    def _update_menu(self):
        device = self._current_device()
        has_any = bool(self._devices)
        self.act_rename.setEnabled(device is not None)
        self.act_forget.setEnabled(device is not None)
        self.act_forget_all.setEnabled(has_any)

    # -- state -------------------------------------------------------------

    def _update(self):
        busy = self.conn.busy
        connected = self.conn.is_connected
        self.btn_connect.setText("Disconnect" if connected else "Connect")
        self.btn_connect.setEnabled(not busy)
        self.btn_refresh.setEnabled(connected and not busy)
        self.device_combo.setEnabled(not busy and not connected)
        self.device_menu.setEnabled(not busy and not connected)
        self.port_edit.setEnabled(not busy and not connected)

    # -- actions -----------------------------------------------------------

    def _on_connect(self):
        if self.conn.is_connected:
            self.conn.disconnect()
            return
        if self.conn.busy:
            return
        host, port = self._target()
        if not host:
            QMessageBox.warning(self, "Missing address",
                                "Enter the PS4 IP address.")
            return
        if port is None or not (0 < port < 65536):
            QMessageBox.warning(self, "Invalid port",
                                "Port must be a number, e.g. 2121.")
            return
        self.conn.connect_to(host, port)

    def _on_refresh(self):
        self.conn.refresh()

    def _on_rename(self):
        device = self._current_device()
        if device is None:
            return
        address = store.device_address(device)
        name, ok = QInputDialog.getText(
            self, "Rename console",
            f"Name for {address}\nLeave empty to show the address instead:",
            text=device["name"])
        if not ok:
            return
        store.rename_device(device["host"], device["port"], name)
        self._reload_devices(select=(device["host"], device["port"]))
        if self.conn.is_connected:
            self._set_status_connected()

    def _on_forget(self):
        device = self._current_device()
        if device is None:
            return
        self._selected = None
        self._devices = store.forget_device(device["host"], device["port"])
        if self.conn.is_connected:
            # Keep the connected console visible, just no longer saved.
            self.device_combo.setEditText(device["host"])
            self._update_menu()
            self._set_status_connected()
        else:
            self._reload_devices()
            self.status.setText("Not connected")
            self._update()

    def _on_forget_all(self):
        if not self._devices:
            return
        answer = QMessageBox.question(
            self, "Forget all consoles",
            "Remove every saved console from the list?\n"
            "Your consoles are not affected.")
        if answer != QMessageBox.Yes:
            return
        self._selected = None
        store.forget_all_devices()
        if self.conn.is_connected:
            conn = self.conn.conn or {}
            self.device_combo.setEditText(str(conn.get("host", "")))
            self._update_menu()
        else:
            self._reload_devices()
            self.status.setText("Not connected")
            self._update()

    # -- signals -----------------------------------------------------------

    def _on_connecting(self, message):
        self.status.setText(message)
        self.dot.set_color(theme.WARN)
        self._update()

    def _on_users_ready(self, users):
        conn = self.conn.conn or {}
        host, port = conn.get("host"), conn.get("port")
        self._user_count = len(users)
        if host:
            # A working address becomes the most recent device.
            self._devices = store.remember_device(host, port)
            self._reload_devices(select=(host, port))
        self._set_status_connected()
        self.dot.set_color(theme.SUCCESS)
        self._update()

    def _set_status_connected(self, count=None):
        conn = self.conn.conn or {}
        device = self._current_device()
        label = store.device_label(device) if device else conn.get("host", "")
        parts = ["Connected", label]
        count = self._user_count if count is None else count
        if count is not None:
            parts.append(f"{count} user(s)")
        self.status.setText(" \u00b7 ".join(str(p) for p in parts if p))

    def _on_failed(self, error):
        self._user_count = None
        self.status.setText(f"Connection failed: {error}")
        self.dot.set_color(theme.DANGER)
        self._update()
        QMessageBox.critical(
            self, "PS4 connection failed",
            f"Could not connect to the PS4 FTP server.\n\n{error}\n\n"
            "Check that GoldHEN's FTP server is running and the IP/port "
            "are correct.")

    def _on_disconnected(self):
        self._user_count = None
        self.status.setText("Not connected")
        self.dot.set_color(theme.FAINT)
        self._update()
