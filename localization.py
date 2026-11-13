import os
import sys
import shutil
from pathlib import Path


def get_bundle_dir() -> Path:
    """Путь к встроенным ресурсам внутри .exe (sys._MEIPASS) или к корню проекта."""
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def get_lang_storage_dir() -> Path:
    """Папка в AppData пользователя, куда автоматически распаковываются .ini файлы."""
    base_appdata = Path(os.getenv("APPDATA", Path.home()))
    lang_dir = base_appdata / "AIScreenshoter" / "lang"
    lang_dir.mkdir(parents=True, exist_ok=True)
    return lang_dir


class LocalizationManager:
    def __init__(self, lang: str = "RU"):
        self.bundle_dir = get_bundle_dir()
        self.lang_dir = get_lang_storage_dir()
        self._unpack_default_locales()

        self.current_lang = lang
        self.strings: dict[str, str] = {}
        self.load(lang)

    def _unpack_default_locales(self):
        """Автораспаковка вшитых .ini файлов в %APPDATA%\\AIScreenshoter\\lang при запуске."""
        for ini_name in ("RU.ini", "EN.ini", "ZH.ini"):
            src = self.bundle_dir / ini_name
            dst = self.lang_dir / ini_name
            if src.exists() and (not dst.exists() or dst.stat().st_size == 0):
                shutil.copy2(src, dst)

    @staticmethod
    def _parse_ini_utf8(path: Path) -> dict[str, str]:
        result: dict[str, str] = {}
        if not path.exists():
            return result
        try:
            text = path.read_text(encoding="utf-8-sig")
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line or line.startswith((";", "#", "[")):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    result[key.strip()] = val.strip()
        except Exception:
            pass
        return result

    def load(self, lang: str):
        self.current_lang = lang
        parsed = self._parse_ini_utf8(self.lang_dir / f"{lang}.ini")
        if not parsed:
            parsed = self._parse_ini_utf8(self.bundle_dir / f"{lang}.ini")
        if not parsed:
            parsed = self._parse_ini_utf8(self.lang_dir / "RU.ini")
        if not parsed:
            parsed = self._parse_ini_utf8(self.bundle_dir / "RU.ini")
        self.strings = parsed

    def tr(self, key: str) -> str:
        return self.strings.get(key, key)

    def get_available_languages(self) -> list[str]:
        """Возвращает отсортированный список всех доступных языков (по именам .ini файлов)."""
        codes: set[str] = set()
        for folder in (self.bundle_dir, self.lang_dir):
            if folder.exists():
                for ini_file in folder.glob("*.ini"):
                    code = ini_file.stem.upper().strip()
                    if code:
                        codes.add(code)
        return sorted(codes) if codes else ["RU", "EN", "ZH"]
