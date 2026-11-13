import os
import sys
import hashlib
import ctypes
from ctypes import wintypes
from pathlib import Path

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"

import shiboken6
from PySide6.QtCore import QMimeData, QTimer, QBuffer, QIODevice, QObject, Signal, QUrl
from PySide6.QtGui import QGuiApplication, QPixmap, QAction, QActionGroup, QDesktopServices
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QFileDialog
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from assets import create_app_icon
from config import ConfigManager
from localization import LocalizationManager
from storage import StorageManager
from AnnotationOverlay import AnnotationOverlay


# Низкоуровневый перехватчик Win+Shift+S / PrintScreen, чтобы прятать оверлей до заморозки экрана
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
VK_SNAPSHOT = 0x2C
VK_S = 0x53
VK_SHIFT = 0x10
VK_LWIN = 0x5B
VK_RWIN = 0x5C


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, ctypes.POINTER(KBDLLHOOKSTRUCT)
)


class SnipHotkeyWatcher(QObject):
    snip_triggered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hook = None
        self._proc = HOOKPROC(self._callback)
        self._hook = ctypes.windll.user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._proc, None, 0
        )

    def _callback(self, nCode, wParam, lParam):
        if nCode >= 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
            vk = lParam.contents.vkCode
            user32 = ctypes.windll.user32
            if vk == VK_SNAPSHOT:
                self.snip_triggered.emit()
            elif vk == VK_S:
                shift_down = (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0
                win_down = (
                    (user32.GetAsyncKeyState(VK_LWIN) & 0x8000) != 0
                    or (user32.GetAsyncKeyState(VK_RWIN) & 0x8000) != 0
                )
                if shift_down and win_down:
                    self.snip_triggered.emit()
        return ctypes.windll.user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def stop(self):
        if self._hook:
            ctypes.windll.user32.UnhookWindowsHookEx(self._hook)
            self._hook = None


class TrayController:
    def __init__(self, app: QApplication):
        self.app = app
        self.cfg = ConfigManager("AIScreenshoter")
        self.loc = LocalizationManager(self.cfg.language)
        self.storage = StorageManager(self.loc, "AIScreenshoter")
        self.storage.custom_save_dir = self.cfg.custom_save_dir

        self._ignore_clipboard = False
        self._clipboard_pending = False
        self._last_saved_hash: str = ""
        self._hidden_for_snip = False
        self.overlay: AnnotationOverlay | None = None

        self.tray = QSystemTrayIcon(create_app_icon(), self.app)
        self.menu = QMenu()
        self.tray.setContextMenu(self.menu)
        self._rebuild_menu()
        self.tray.show()

        self.clipboard = QGuiApplication.clipboard()
        self.clipboard.dataChanged.connect(self._on_clipboard_changed)

        self.hotkey_watcher = SnipHotkeyWatcher(self.app)
        self.hotkey_watcher.snip_triggered.connect(self._on_snip_hotkey)
        self.app.aboutToQuit.connect(self.hotkey_watcher.stop)

        self._restore_timer = QTimer(self.app)
        self._restore_timer.setInterval(400)
        self._restore_timer.timeout.connect(self._check_restore_after_snip)

    def _on_snip_hotkey(self):
        if self.overlay is not None and shiboken6.isValid(self.overlay) and self.overlay.isVisible():
            self._hidden_for_snip = True
            self.overlay.prepare_for_next_snip()
            QTimer.singleShot(2200, self._restore_timer.start)

    def _check_restore_after_snip(self):
        if not self._hidden_for_snip:
            self._restore_timer.stop()
            return
        # Если системные Ножницы закрылись (нажали ESC), возвращаем скрытый оверлей
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(hwnd, buf, 256)
        cls_name = buf.value
        if "ScreenClipping" not in cls_name and "Snipping" not in cls_name:
            self._hidden_for_snip = False
            self._restore_timer.stop()
            if self.overlay is not None and shiboken6.isValid(self.overlay):
                self.overlay.setWindowOpacity(1.0)
                self.overlay._mask_screen = False
                self.overlay.toolbar.show()
                self.overlay.show()
                self.overlay.raise_()
                self.overlay.activateWindow()

    def _rebuild_menu(self):
        self.menu.clear()
        self.tray.setToolTip(self.loc.tr("ID1"))

        act_open_ai = QAction(self.loc.tr("ID14"), self.menu)
        act_open_ai.triggered.connect(self._open_ai_dialog)
        self.menu.addAction(act_open_ai)

        act_open_dir = QAction(self.loc.tr("ID9"), self.menu)
        act_open_dir.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self.storage.get_save_dir()))
            )
        )
        self.menu.addAction(act_open_dir)

        act_change_dir = QAction(self.loc.tr("ID24"), self.menu)
        act_change_dir.triggered.connect(self._select_save_folder)
        self.menu.addAction(act_change_dir)

        self.menu.addSeparator()

        fmt_menu = self.menu.addMenu(self.loc.tr("ID25"))
        fmt_group = QActionGroup(fmt_menu)
        for fmt in ("JPG", "PNG"):
            act = QAction(fmt, fmt_menu, checkable=True)
            act.setChecked(self.cfg.img_format == fmt)
            act.triggered.connect(lambda checked, f=fmt: self._set_format(f))
            fmt_group.addAction(act)
            fmt_menu.addAction(act)

        lang_menu = self.menu.addMenu(self.loc.tr("ID15"))
        lang_group = QActionGroup(lang_menu)
        for code in self.loc.get_available_languages():
            act = QAction(code, lang_menu, checkable=True)
            act.setChecked(self.cfg.language == code)
            act.triggered.connect(lambda checked, c=code: self._set_language(c))
            lang_group.addAction(act)
            lang_menu.addAction(act)

        lang_menu.addSeparator()
        act_open_lang_dir = QAction(self.loc.tr("ID9"), lang_menu)
        act_open_lang_dir.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self.loc.lang_dir))
            )
        )
        lang_menu.addAction(act_open_lang_dir)


        act_exit = QAction(self.loc.tr("ID13"), self.menu)
        act_exit.triggered.connect(self.app.quit)
        self.menu.addAction(act_exit)

    def _set_language(self, lang_code: str):
        self.cfg.language = lang_code
        self.loc.load(lang_code)
        self._rebuild_menu()

    def _set_format(self, fmt: str):
        self.cfg.img_format = fmt

    def _select_save_folder(self):
        folder = QFileDialog.getExistingDirectory(None, self.loc.tr("ID23"))
        if folder:
            path = Path(folder)
            self.cfg.custom_save_dir = path
            self.storage.custom_save_dir = path

    def _open_ai_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            self.loc.tr("ID14"),
            str(self.storage.get_save_dir()),
            self.loc.tr("ID27"),
        )
        if file_path:
            self.open_ai_file(file_path)

    def open_ai_file(self, file_path: str | Path):
        pixmap, annotations = self.storage.load_ai_file(file_path)
        if not pixmap.isNull():
            self._launch_overlay(pixmap, annotations)

    def _launch_overlay(self, pixmap: QPixmap, annotations: list[dict] | None = None):
        self._hidden_for_snip = False
        self._restore_timer.stop()

        if self.overlay is not None and shiboken6.isValid(self.overlay) and (
            self.overlay.isVisible() or len(self.overlay.layers) > 0
        ):
            self.overlay.add_layer(pixmap, annotations)
            self.overlay.show()
            self.overlay.raise_()
            self.overlay.activateWindow()
            self.overlay.update()
            return

        if self.overlay is not None and shiboken6.isValid(self.overlay):
            self.overlay.close()
        self.overlay = None

        self.overlay = AnnotationOverlay(
            pixmap=pixmap,
            loc=self.loc,
            storage=self.storage,
            on_clipboard_image=self._write_image_to_clipboard,
            on_clipboard_text=self._write_text_to_clipboard,
            img_format=self.cfg.img_format,
            initial_annotations=annotations,
        )
        self.overlay.destroyed.connect(lambda: setattr(self, "overlay", None))
        self.overlay.show()
        self.overlay.activateWindow()

    @staticmethod
    def _image_hash(img) -> str:
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "BMP")
        return hashlib.md5(buf.data().data()).hexdigest()

    def _on_clipboard_changed(self):
        if self._ignore_clipboard or self._clipboard_pending:
            return
        self._clipboard_pending = True
        QTimer.singleShot(180, self._process_clipboard)

    def _process_clipboard(self):
        self._clipboard_pending = False
        if self._ignore_clipboard:
            return
        mime = self.clipboard.mimeData()
        if mime and mime.hasImage():
            img = self.clipboard.image()
            if not img.isNull():
                current_hash = self._image_hash(img)
                if current_hash == self._last_saved_hash:
                    return
                self._launch_overlay(QPixmap.fromImage(img))

    def _reset_clipboard_ignore(self):
        self._ignore_clipboard = False

    def _write_image_to_clipboard(self, pixmap: QPixmap, prompt_text: str):
        self._ignore_clipboard = True
        img = pixmap.toImage()
        self._last_saved_hash = self._image_hash(img)

        mime = QMimeData()
        mime.setImageData(img)
        mime.setText(prompt_text)
        self.clipboard.setMimeData(mime)
        QTimer.singleShot(800, self._reset_clipboard_ignore)

    def _write_text_to_clipboard(self, prompt_text: str):
        self._ignore_clipboard = True
        self.clipboard.setText(prompt_text)
        QTimer.singleShot(800, self._reset_clipboard_ignore)

def send_to_running_instance(server_name: str, payload: str = "PING") -> bool:
    """Проверяет, запущена ли уже копия программы, и передает ей аргумент."""
    socket = QLocalSocket()
    socket.connectToServer(server_name)
    if socket.waitForConnected(250):
        socket.write(payload.encode("utf-8"))
        socket.flush()
        socket.waitForBytesWritten(250)
        socket.disconnectFromServer()
        return True
    return False


if __name__ == "__main__":
    # Системный мьютекс для установщика Inno Setup
    _mutex = ctypes.windll.kernel32.CreateMutexW(
        None, False, "Global\\AIScreenshoter_SingleInstance_Mutex"
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    SERVER_NAME = "AIScreenshoter_SingleInstance_Server"
    arg_file = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".ai") else ""

    # Если копия уже работает в трее — передаем ей файл .ai (если был) и закрываем дубликат
    if send_to_running_instance(SERVER_NAME, arg_file or "WAKE"):
        sys.exit(0)

    QLocalServer.removeServer(SERVER_NAME)
    local_server = QLocalServer(app)
    local_server.listen(SERVER_NAME)

    controller = TrayController(app)

    def _on_new_instance_message():
        conn = local_server.nextPendingConnection()
        if conn and conn.waitForReadyRead(250):
            msg = bytes(conn.readAll()).decode("utf-8", errors="ignore").strip()
            if msg and msg.lower().endswith(".ai"):
                controller.open_ai_file(msg)
            conn.disconnectFromServer()

    local_server.newConnection.connect(_on_new_instance_message)

    if arg_file:
        controller.open_ai_file(arg_file)

    sys.exit(app.exec())
