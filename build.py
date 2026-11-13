import subprocess
import sys
import os
import shutil
from pathlib import Path
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QGuiApplication, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

from assets import SVG_APP_ICON


def generate_ico(ico_path: Path):
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    pix = QPixmap(256, 256)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    QSvgRenderer(QByteArray(SVG_APP_ICON.encode("utf-8"))).render(painter)
    painter.end()
    pix.save(str(ico_path), "ICO")
    print(f"Icon saved: {ico_path}")


def find_iscc() -> Path | None:
    which_iscc = shutil.which("ISCC") or shutil.which("iscc")
    if which_iscc:
        return Path(which_iscc)

    local_app = Path(os.getenv("LOCALAPPDATA", ""))
    candidates = [
        Path(r"C:\Program Files\Inno Setup 7\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 7\ISCC.exe"),
        local_app / "Programs" / "Inno Setup 7" / "ISCC.exe",
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        local_app / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None



def build_exe():
    root = Path(__file__).resolve().parent
    ico_path = root / "app_icon.ico"
    generate_ico(ico_path)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "AIScreenshoter",
        "--icon",
        str(ico_path),
        "--add-data",
        f"{root / 'RU.ini'};.",
        "--add-data",
        f"{root / 'EN.ini'};.",
        "--add-data",
        f"{root / 'ZH.ini'};.",
        str(root / "main.py"),
    ]
    subprocess.run(cmd, check=True)
    print(f"\nBuild complete! Single-file executable: {root / 'dist' / 'AIScreenshoter.exe'}")

    iscc_path = find_iscc()
    iss_file = root / "installer.iss"
    if not iscc_path:
        print("Inno Setup (ISCC.exe) not found. Skipping installer build.")
        return

    if iss_file.exists():
        # Гарантируем кодировку UTF-8 с BOM для корректной компиляции кириллицы в Inno Setup
        content = iss_file.read_text(encoding="utf-8-sig")
        iss_file.write_bytes(content.encode("utf-8-sig"))

        print("\nBuilding Windows Installer...")
        res = subprocess.run([str(iscc_path), str(iss_file)])
        if res.returncode == 0:
            print(f"Installer ready: {root / 'dist_setup' / 'AIScreenshoter_Setup_1.2.4.exe'}")
        else:
            print(f"Inno Setup failed with exit code {res.returncode}")


if __name__ == "__main__":
    build_exe()
