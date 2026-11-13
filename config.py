import os
from pathlib import Path
from PySide6.QtCore import QSettings, QLocale

class ConfigManager:
    def __init__(self, app_name: str = "AIScreenshoter"):
        base_appdata = Path(os.getenv("APPDATA", Path.home()))
        self.app_dir = base_appdata / app_name
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self.ini_path = self.app_dir / "config.ini"
        self.settings = QSettings(str(self.ini_path), QSettings.Format.IniFormat)

    @property
    def language(self) -> str:
        saved = self.settings.value("General/language", None)
        if saved:
            return str(saved)
        sys_code = QLocale.system().name()[:2].upper()

    @language.setter
    def language(self, value: str):
        self.settings.setValue("General/language", value)
        self.settings.sync()

    @property
    def img_format(self) -> str:
        return str(self.settings.value("General/img_format", "JPG"))

    @img_format.setter
    def img_format(self, value: str):
        self.settings.setValue("General/img_format", value)
        self.settings.sync()

    @property
    def custom_save_dir(self) -> Path | None:
        raw = str(self.settings.value("General/custom_save_dir", "")).strip()
        return Path(raw) if raw else None

    @custom_save_dir.setter
    def custom_save_dir(self, path: Path | None):
        self.settings.setValue("General/custom_save_dir", str(path) if path else "")
        self.settings.sync()
