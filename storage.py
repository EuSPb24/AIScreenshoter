import json
import base64
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QBuffer, QIODevice, QByteArray, QStandardPaths
from PySide6.QtGui import QPixmap
from localization import LocalizationManager

class StorageManager:
    def __init__(self, loc: LocalizationManager, app_name: str = "AIScreenshoter"):
        self.loc = loc
        self.app_name = app_name
        self.custom_save_dir: Path | None = None

    def get_default_root(self) -> Path:
        pics_loc = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.PicturesLocation
        )
        base = Path(pics_loc) if pics_loc else (Path.home() / "Pictures")
        return base / self.app_name

    def get_save_dir(self) -> Path:
        root = self.custom_save_dir if self.custom_save_dir else self.get_default_root()
        month_folder = datetime.now().strftime("%Y-%m")
        target = root / month_folder
        target.mkdir(parents=True, exist_ok=True)
        return target

    def build_ai_prompt(self, width: int, height: int, annotations: list[dict]) -> str:
        header = self.loc.tr("ID18").format(w=width, h=height)
        lines = [header]
        obj_map = {"rect": "ID20", "line": "ID21", "arrow": "ID29"}
        visible_anns = [a for a in annotations if a.get("type") != "blur"]

        for idx, ann in enumerate(visible_anns, 1):
            obj_key = obj_map.get(ann["type"], "ID20")
            obj_name = self.loc.tr(obj_key)
            line = self.loc.tr("ID19").format(
                idx=idx,
                x1=ann["x1"],
                x2=ann["x2"],
                y1=ann["y1"],
                y2=ann["y2"],
                obj=obj_name,
                text=ann["text"],
            )
            lines.append(line)
        return "\n".join(lines)

    def save_capture(
        self,
        raw_pixmap: QPixmap,
        rendered_pixmap: QPixmap,
        annotations: list[dict],
        img_format: str = "JPG",
        target_dir: Path | None = None,
    ) -> tuple[Path, Path, Path]:
        save_dir = target_dir if target_dir else self.get_save_dir()
        save_dir.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        fmt = img_format.upper()
        ext = "jpg" if fmt == "JPG" else "png"

        # 1. Сохраняем основной скриншот ЧИСТЫМ (без слоев и меток)
        clean_path = save_dir / f"shot_{stamp}_clean.{ext}"
        if not raw_pixmap.save(str(clean_path), fmt, 95):
            clean_path = save_dir / f"shot_{stamp}_clean.png"
            raw_pixmap.save(str(clean_path), "PNG")

        # 2. Сохраняем скриншот с нанесенными акцентами
        marked_path = save_dir / f"shot_{stamp}_marked.{ext}"
        if not rendered_pixmap.save(str(marked_path), fmt, 95):
            marked_path = save_dir / f"shot_{stamp}_marked.png"
            rendered_pixmap.save(str(marked_path), "PNG")

        # 3. Сохраняем технический .ai файл для редактирования слоев
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        raw_pixmap.save(buf, "PNG")
        b64_img = base64.b64encode(buf.data().data()).decode("ascii")

        ai_payload = {
            "version": 1,
            "width": raw_pixmap.width(),
            "height": raw_pixmap.height(),
            "prompt": self.build_ai_prompt(raw_pixmap.width(), raw_pixmap.height(), annotations),
            "annotations": annotations,
            "image_base64": b64_img,
        }
        ai_path = save_dir / f"shot_{stamp}.ai"
        ai_path.write_text(json.dumps(ai_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return clean_path, marked_path, ai_path


    @staticmethod
    def load_ai_file(ai_path: str | Path) -> tuple[QPixmap, list[dict]]:
        data = json.loads(Path(ai_path).read_text(encoding="utf-8"))
        raw_bytes = base64.b64decode(data["image_base64"])
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(raw_bytes), "PNG")
        annotations = data.get("annotations", [])
        return pixmap, annotations
