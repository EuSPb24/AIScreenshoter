import ctypes
from ctypes import wintypes
from PySide6.QtCore import Qt
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

# COM-интерфейсы Windows Spell Checking API (работает на всех языках системы)
class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_str(cls, s: str) -> "GUID":
        import uuid
        u = uuid.UUID(s)
        data4 = (ctypes.c_ubyte * 8)(*u.bytes[8:])
        return cls(u.time_low, u.time_mid, u.time_hi_version, data4)


CLSID_SpellCheckerFactory = GUID.from_str("7AB36653-1796-484B-BDFA-E74F1DB7C1DC")
IID_ISpellCheckerFactory = GUID.from_str("8E018A9D-2415-4677-BF08-794EA61F94BB")


class WindowsSpellChecker:
    """Обертка над нативным системным проверщиком орфографии Windows."""

    def __init__(self):
        self._factory = None
        self._checkers: dict[str, ctypes.c_void_p] = {}
        try:
            ole32 = ctypes.windll.ole32
            ole32.CoInitialize(None)
            factory_ptr = ctypes.c_void_p()
            hr = ole32.CoCreateInstance(
                ctypes.byref(CLSID_SpellCheckerFactory),
                None,
                1,  # CLSCTX_INPROC_SERVER
                ctypes.byref(IID_ISpellCheckerFactory),
                ctypes.byref(factory_ptr),
            )
            if hr == 0 and factory_ptr.value:
                self._factory = factory_ptr
        except Exception:
            self._factory = None

    @staticmethod
    def get_active_locale() -> str:
        """Возвращает BCP-47 тег языка текущей раскладки клавиатуры (ru-RU, en-US, fr-FR, it-IT, zh-CN...)."""
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            hwnd = user32.GetForegroundWindow()
            tid = user32.GetWindowThreadProcessId(hwnd, None)
            hkl = user32.GetKeyboardLayout(tid)
            lang_id = hkl & 0xFFFF

            buf = ctypes.create_unicode_buffer(85)
            if kernel32.LCIDToLocaleName(lang_id, buf, 85, 0) > 0:
                return buf.value
            if kernel32.GetUserDefaultLocaleName(buf, 85) > 0:
                return buf.value
        except Exception:
            pass
        return "en-US"

    def _get_checker(self, lang_tag: str):
        if not self._factory:
            return None
        if lang_tag in self._checkers:
            return self._checkers[lang_tag]

        try:
            vtable = ctypes.cast(
                ctypes.cast(self._factory, ctypes.POINTER(ctypes.c_void_p))[0],
                ctypes.POINTER(ctypes.c_void_p),
            )
            # ISpellCheckerFactory::IsSupported (index 4)
            is_supported_fn = ctypes.WINFUNCTYPE(
                ctypes.HRESULT, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(wintypes.BOOL)
            )(vtable[4])

            supported = wintypes.BOOL(0)
            is_supported_fn(self._factory, lang_tag, ctypes.byref(supported))
            if not supported.value:
                self._checkers[lang_tag] = None
                return None

            # ISpellCheckerFactory::CreateSpellChecker (index 5)
            create_fn = ctypes.WINFUNCTYPE(
                ctypes.HRESULT, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)
            )(vtable[5])

            checker_ptr = ctypes.c_void_p()
            hr = create_fn(self._factory, lang_tag, ctypes.byref(checker_ptr))
            if hr == 0 and checker_ptr.value:
                self._checkers[lang_tag] = checker_ptr
                return checker_ptr
        except Exception:
            pass

        self._checkers[lang_tag] = None
        return None

    def check_text(self, text: str) -> list[tuple[int, int]]:
        """Возвращает список (start_index, length) для слов с орфографическими ошибками."""
        if not text or not self._factory:
            return []

        lang_tag = self.get_active_locale()
        checker = self._get_checker(lang_tag)
        if not checker:
            return []

        errors: list[tuple[int, int]] = []
        try:
            c_vtable = ctypes.cast(
                ctypes.cast(checker, ctypes.POINTER(ctypes.c_void_p))[0],
                ctypes.POINTER(ctypes.c_void_p),
            )
            # ISpellChecker::Check (index 4)
            check_fn = ctypes.WINFUNCTYPE(
                ctypes.HRESULT, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)
            )(c_vtable[4])

            enum_ptr = ctypes.c_void_p()
            if check_fn(checker, text, ctypes.byref(enum_ptr)) != 0 or not enum_ptr.value:
                return []

            e_vtable = ctypes.cast(
                ctypes.cast(enum_ptr, ctypes.POINTER(ctypes.c_void_p))[0],
                ctypes.POINTER(ctypes.c_void_p),
            )
            # IEnumSpellingError::Next (index 3)
            next_fn = ctypes.WINFUNCTYPE(
                ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
            )(e_vtable[3])
            release_enum = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)(e_vtable[2])

            while True:
                err_ptr = ctypes.c_void_p()
                hr = next_fn(enum_ptr, ctypes.byref(err_ptr))
                if hr != 0 or not err_ptr.value:
                    break

                err_vtable = ctypes.cast(
                    ctypes.cast(err_ptr, ctypes.POINTER(ctypes.c_void_p))[0],
                    ctypes.POINTER(ctypes.c_void_p),
                )
                get_start = ctypes.WINFUNCTYPE(
                    ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(wintypes.ULONG)
                )(err_vtable[3])
                get_len = ctypes.WINFUNCTYPE(
                    ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(wintypes.ULONG)
                )(err_vtable[4])
                release_err = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)(err_vtable[2])

                start = wintypes.ULONG(0)
                length = wintypes.ULONG(0)
                get_start(err_ptr, ctypes.byref(start))
                get_len(err_ptr, ctypes.byref(length))
                if length.value > 0:
                    errors.append((start.value, length.value))
                release_err(err_ptr)

            release_enum(enum_ptr)
        except Exception:
            pass

        return errors

    def get_suggestions(self, word: str) -> list[str]:
        """Возвращает варианты исправления слова от системного словаря."""
        if not word or not self._factory:
            return []

        lang_tag = self.get_active_locale()
        checker = self._get_checker(lang_tag)
        if not checker:
            return []

        suggestions: list[str] = []
        try:
            c_vtable = ctypes.cast(
                ctypes.cast(checker, ctypes.POINTER(ctypes.c_void_p))[0],
                ctypes.POINTER(ctypes.c_void_p),
            )
            # ISpellChecker::Suggest (index 5)
            suggest_fn = ctypes.WINFUNCTYPE(
                ctypes.HRESULT, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)
            )(c_vtable[5])

            enum_ptr = ctypes.c_void_p()
            if suggest_fn(checker, word, ctypes.byref(enum_ptr)) != 0 or not enum_ptr.value:
                return []

            e_vtable = ctypes.cast(
                ctypes.cast(enum_ptr, ctypes.POINTER(ctypes.c_void_p))[0],
                ctypes.POINTER(ctypes.c_void_p),
            )
            next_fn = ctypes.WINFUNCTYPE(
                ctypes.HRESULT,
                ctypes.c_void_p,
                wintypes.ULONG,
                ctypes.POINTER(wintypes.LPWSTR),
                ctypes.POINTER(wintypes.ULONG),
            )(e_vtable[3])
            release_enum = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)(e_vtable[2])

            for _ in range(6):
                str_ptr = wintypes.LPWSTR()
                fetched = wintypes.ULONG(0)
                if next_fn(enum_ptr, 1, ctypes.byref(str_ptr), ctypes.byref(fetched)) != 0 or fetched.value == 0:
                    break
                if str_ptr.value:
                    suggestions.append(str_ptr.value)
                    ctypes.windll.ole32.CoTaskMemFree(str_ptr)

            release_enum(enum_ptr)
        except Exception:
            pass

        return suggestions


class SpellSyntaxHighlighter(QSyntaxHighlighter):
    """Подчеркивает слова с ошибками красной волнистой линией в поле ввода."""

    def __init__(self, document, checker: WindowsSpellChecker):
        super().__init__(document)
        self.checker = checker
        self.base_font = QFont("Segoe UI", 11)
        self.error_fmt = QTextCharFormat()
        self.error_fmt.setFont(self.base_font)
        self.error_fmt.setUnderlineColor(QColor("#FF3B30"))
        self.error_fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)

    def highlightBlock(self, text: str):
        base_fmt = QTextCharFormat()
        base_fmt.setFont(self.base_font)
        self.setFormat(0, len(text), base_fmt)

        for start, length in self.checker.check_text(text):
            self.setFormat(start, length, self.error_fmt)

