from PySide6.QtCore import Qt, QRect, QPoint, QTimer
from PySide6.QtGui import QGuiApplication, QPixmap, QPainter, QCursor, QColor
from PySide6.QtWidgets import QWidget

from canvas_renderer import CanvasRenderer
from dialogs import SpellCommentEdit, HelpDialog
from localization import LocalizationManager
from storage import StorageManager
from toolbar import DraggableToolbar
from toast import DarkToast


class AnnotationOverlay(QWidget):
    def __init__(
        self,
        pixmap: QPixmap,
        loc: LocalizationManager,
        storage: StorageManager,
        on_clipboard_image,
        on_clipboard_text,
        img_format: str = "JPG",
        initial_annotations: list[dict] | None = None,
    ):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        # В __init__ класса AnnotationOverlay:
        self._mask_screen = False
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._esc_confirm_pending = False
        self.loc = loc
        self.storage = storage
        self.on_clipboard_image = on_clipboard_image
        self.on_clipboard_text = on_clipboard_text
        self.img_format = img_format

        self.tool_mode = "rect"
        self.layers: list[dict] = []
        self.current_layer_idx: int = -1

        self.drawing = False
        self.start_pt = QPoint()
        self.current_pt = QPoint()
        self.pending_item: dict | None = None
        self.editing_index: int | None = None

        self.toolbar = DraggableToolbar(self, loc)

        self.comment_input = SpellCommentEdit(self)
        self.comment_input.setPlaceholderText(loc.tr("ID12"))
        self.comment_input.setStyleSheet(
            """
            QTextEdit {
                background-color: #1E1E2E; color: #FFFFFF;
                border: 2px solid #F38BA8; border-radius: 6px;
                padding: 4px 10px;
            }
            """
        )

        self.comment_input.hide()
        self.comment_input.returnPressed.connect(self._commit_annotation)
        self.comment_input.escapePressed.connect(self._on_editor_escape)

        self._connect_toolbar()
        self.add_layer(pixmap, initial_annotations)
        
    def _on_editor_escape(self):
        self._commit_annotation()
        self.setFocus()

    @property
    def source_pixmap(self) -> QPixmap:
        return self.layers[self.current_layer_idx]["pixmap"]

    @property
    def annotations(self) -> list[dict]:
        return self.layers[self.current_layer_idx]["annotations"]

    @property
    def redo_stack(self) -> list[dict]:
        return self.layers[self.current_layer_idx]["redo_stack"]

    def add_layer(
        self, pixmap: QPixmap, initial_annotations: list[dict] | None = None
    ):
        if self.current_layer_idx >= 0 and (
            self.pending_item or self.editing_index is not None
        ):
            self._commit_annotation()

        layer = {
            "pixmap": pixmap,
            "annotations": list(initial_annotations) if initial_annotations else [],
            "redo_stack": [],
        }
        self.layers.append(layer)
        self._switch_layer(len(self.layers) - 1)

        if len(self.layers) == 6:
            self._toast = DarkToast(self, self.loc.tr("ID52"), 2800)
            self._toast.show()
            
    def prepare_for_next_snip(self):
        """Очищает буфер кадра перед скрытием, чтобы старый скрин не мелькал при возврате."""
        self._mask_screen = True
        self.toolbar.hide()
        self.comment_input.hide()
        self.repaint()
        self.hide()

    def _switch_layer(self, index: int):
        if not (0 <= index < len(self.layers)):
            return
        if self.current_layer_idx >= 0 and (
            self.pending_item or self.editing_index is not None
        ):
            self._commit_annotation()

        self.toolbar.tool_combo.hidePopup()
        self.current_layer_idx = index
        self.drawing = False
        self.pending_item = None
        self.editing_index = None
        self.comment_input.clearFocus()
        self.comment_input.hide()
        self.comment_input.setFixedHeight(36)
        self.setFocus()

        self._recalc_geometry()
        self.toolbar.update_layer_indicator(self.current_layer_idx, len(self.layers))
        self._position_toolbar()
        self._mask_screen = False
        self.toolbar.show()
        self.update()

    def _recalc_geometry(self):
        pixmap = self.source_pixmap
        active_screen = (
            QGuiApplication.screenAt(QCursor.pos())
            or QGuiApplication.primaryScreen()
        )
        screen_geo = active_screen.geometry()
        self.setGeometry(screen_geo)
        self.local_screen = QRect(0, 0, screen_geo.width(), screen_geo.height())

        max_w = screen_geo.width() - 24
        max_h = screen_geo.height() - 24

        if pixmap.width() > max_w or pixmap.height() > max_h:
            ratio = min(max_w / pixmap.width(), max_h / pixmap.height())
            disp_w = int(pixmap.width() * ratio)
            disp_h = int(pixmap.height() * ratio)
        else:
            disp_w = pixmap.width()
            disp_h = pixmap.height()

        self.scale_x = pixmap.width() / max(1, disp_w)
        self.scale_y = pixmap.height() / max(1, disp_h)

        x = (screen_geo.width() - disp_w) // 2
        y = (screen_geo.height() - disp_h) // 2
        self.image_rect = QRect(x, y, disp_w, disp_h)

    def _connect_toolbar(self):
        self.toolbar.btn_prev_layer.clicked.connect(
            lambda: self._switch_layer((self.current_layer_idx - 1) % len(self.layers))
        )
        self.toolbar.btn_next_layer.clicked.connect(
            lambda: self._switch_layer((self.current_layer_idx + 1) % len(self.layers))
        )
        self.toolbar.btn_del_layer.clicked.connect(self._delete_current_layer)
        self.toolbar.tool_combo.currentIndexChanged.connect(self._on_tool_changed)
        self.toolbar.btn_undo.clicked.connect(self._undo)
        self.toolbar.btn_redo.clicked.connect(self._redo)
        self.toolbar.btn_info.clicked.connect(self._open_help_dialog)
        self.toolbar.btn_save.clicked.connect(self._save_all)
        self.toolbar.btn_close.clicked.connect(self._close_overlay)

    def _on_tool_changed(self, index: int):
        mode = self.toolbar.tool_combo.itemData(index)
        if mode == "select_all":
            # Возвращаем список на "Прямоугольник" и сразу выделяем весь текущий кадр
            self.toolbar.tool_combo.blockSignals(True)
            self.toolbar.tool_combo.setCurrentIndex(0)
            self.toolbar.tool_combo.blockSignals(False)
            self.tool_mode = "rect"
            self._select_all_area()
        elif mode:
            self.tool_mode = mode

    def _delete_current_layer(self):
        if len(self.layers) <= 1:
            return
        self.pending_item = None
        self.editing_index = None
        self.comment_input.clearFocus()
        self.comment_input.hide()

        self.layers.pop(self.current_layer_idx)
        new_idx = min(self.current_layer_idx, len(self.layers) - 1)
        self.current_layer_idx = -1
        self._switch_layer(new_idx)

    def _position_toolbar(self):
        self.toolbar.adjustSize()
        tb_w = self.toolbar.width()
        tb_h = self.toolbar.height()
        margin = 12

        # Если снимок достаточно большой — ставим панель в правый верхний угол внутри снимка
        if self.image_rect.width() >= tb_w + 40 and self.image_rect.height() >= tb_h + 60:
            pos_x = self.image_rect.right() - tb_w - margin
            pos_y = self.image_rect.top() + margin
        else:
            # Для крошечных скринов (например, 10x30 px) ставим панель НАД скрином (или ПОД ним)
            pos_x = self.image_rect.center().x() - tb_w // 2
            pos_y = self.image_rect.top() - tb_h - margin
            if pos_y < margin:
                pos_y = self.image_rect.bottom() + margin

        # Всегда удерживаем панель в пределах видимого монитора
        max_x = max(margin, self.local_screen.right() - tb_w - margin)
        max_y = max(margin, self.local_screen.bottom() - tb_h - margin)

        self.toolbar.move(
            max(margin, min(max_x, pos_x)),
            max(margin, min(max_y, pos_y)),
        )
        self.toolbar.raise_()

    def _open_help_dialog(self):
        dlg = HelpDialog(self, self.loc)
        dlg.move(
            self.local_screen.center().x() - dlg.width() // 2,
            self.local_screen.center().y() - dlg.height() // 2,
        )
        dlg.exec()

    def _close_overlay(self):
        self.drawing = False
        self.pending_item = None
        self.editing_index = None
        self.comment_input.clearFocus()
        self.comment_input.hide()
        self.toolbar.hide()
        self.layers.clear()
        self.current_layer_idx = -1
        self.hide()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        QTimer.singleShot(0, self.close)

    def _get_layer_start_index(self) -> int:
        """Считает стартовый номер акцента для текущего слоя с учетом предыдущих кадров."""
        count = 1
        for i in range(self.current_layer_idx):
            for ann in self.layers[i]["annotations"]:
                if ann.get("type") != "blur":
                    count += 1
        return count

    def _scale_item(self, item: dict) -> dict:
        return {
            **item,
            "x1": int(item["x1"] / self.scale_x),
            "y1": int(item["y1"] / self.scale_y),
            "x2": int(item["x2"] / self.scale_x),
            "y2": int(item["y2"] / self.scale_y),
        }

    def _get_badge_rect(self, item: dict) -> QRect:
        occupied: list[QRect] = []
        for existing in self.annotations:
            if existing is item:
                break
            if existing.get("type") == "blur":
                continue
            r = CanvasRenderer.calc_badge_rect(
                self._scale_item(existing),
                self.image_rect.x(),
                self.image_rect.y(),
                self.image_rect.width(),
                self.image_rect.height(),
                occupied,
            )
            occupied.append(r)

        return CanvasRenderer.calc_badge_rect(
            item=self._scale_item(item),
            offset_x=self.image_rect.x(),
            offset_y=self.image_rect.y(),
            bounds_width=self.image_rect.width(),
            bounds_height=self.image_rect.height(),
            occupied_rects=occupied,
        )
    def _hit_test_badge(self, pos: QPoint) -> int:
        for idx in range(len(self.annotations) - 1, -1, -1):
            if self.annotations[idx].get("type") == "blur":
                continue
            rect = self._get_badge_rect(self.annotations[idx]).adjusted(-6, -6, 6, 6)
            if rect.contains(pos):
                return idx
        return -1

    def _open_inline_editor(self, anchor_x: int, below_y: int, above_y: int, text: str = ""):
        self.comment_input.setText(text)
        w = 340
        self.comment_input.setFixedWidth(w)
        margin = 10

        max_x = max(margin, self.local_screen.right() - w - margin)
        input_x = max(margin, min(max_x, anchor_x))

        # Выбираем позицию по вертикали в пределах всего экрана (не сжимая до 10x30)
        if below_y + 42 <= self.local_screen.bottom() - margin:
            input_y = max(margin, below_y)
        else:
            input_y = max(margin, above_y)

        # Защита от наложения панели инструментов и поля ввода друг на друга
        tb_rect = self.toolbar.geometry().adjusted(-4, -4, 4, 4)
        proposed_rect = QRect(input_x, input_y, w, 36)
        if proposed_rect.intersects(tb_rect):
            # Ставим поле ввода строго ПОД панелью инструментов (или НАД ней)
            if tb_rect.bottom() + 44 <= self.local_screen.bottom():
                input_y = tb_rect.bottom() + 6
            else:
                input_y = max(margin, tb_rect.top() - 42)

        self.comment_input.move(input_x, input_y)
        self.comment_input.show()
        self.comment_input.raise_()
        self.comment_input.activateWindow()
        self.comment_input.setFocus()
        self.comment_input.selectAll()

    def _cancel_inline_editor(self):
        self.pending_item = None
        self.editing_index = None
        self.comment_input.hide()
        self.update()

    def _start_edit_annotation(self, index: int):
        if self.pending_item:
            self._commit_annotation()
        self.editing_index = index
        item = self.annotations[index]
        badge_rect = self._get_badge_rect(item)

        input_w = min(360, max(200, self.image_rect.width() - 24))
        anchor_x = badge_rect.right() - input_w
        below_y = badge_rect.bottom() + 6
        above_y = badge_rect.top() - 42

        self._open_inline_editor(
            anchor_x=anchor_x,
            below_y=below_y,
            above_y=above_y,
            text=item.get("text", ""),
        )

    def _select_all_area(self):
        if self.pending_item or self.editing_index is not None:
            self._commit_annotation()

        raw_w = self.source_pixmap.width()
        raw_h = self.source_pixmap.height()
        if raw_w < 10 or raw_h < 10:
            return

        self.pending_item = {
            "type": "rect",
            "x1": 2,
            "y1": 2,
            "x2": raw_w - 3,
            "y2": raw_h - 3,
            "text": "",
        }
        badge_rect = self._get_badge_rect(self.pending_item)

        input_w = min(360, max(200, self.image_rect.width() - 60))
        anchor_x = badge_rect.left() - input_w - 8
        top_y = badge_rect.top()

        if self.toolbar.geometry().intersects(QRect(anchor_x, top_y, input_w + 40, 40)):
            self.toolbar.move(self.toolbar.x(), top_y + 46)

        self._open_inline_editor(
            anchor_x=anchor_x,
            below_y=top_y,
            above_y=top_y,
            text="",
        )
        self.update()

    @staticmethod
    def _snap_line(p1: QPoint, p2: QPoint) -> QPoint:
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = max(abs(dx), abs(dy))
        if dist == 0:
            return p2

        threshold = max(12, int(dist * 0.08))
        if abs(dy) <= threshold:
            return QPoint(p2.x(), p1.y())
        if abs(dx) <= threshold:
            return QPoint(p1.x(), p2.y())
        return p2

    def _reset_esc_confirm(self):
        self._esc_confirm_pending = False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            # Если открыт ввод новой метки или редактирование — сначала сохраняем её, а не удаляем
            if self.comment_input.isVisible():
                self._commit_annotation()
                self.setFocus()
                return

            has_work = len(self.layers) > 1 or any(
                len(layer["annotations"]) > 0 for layer in self.layers
            )
            if has_work and not self._esc_confirm_pending:
                self._esc_confirm_pending = True
                self._toast = DarkToast(self, self.loc.tr("ID51"), 2500)
                self._toast.show()
                QTimer.singleShot(2500, self._reset_esc_confirm)
                return

            self._close_overlay()
        elif event.key() == Qt.Key.Key_PageUp and len(self.layers) > 1:
            self._switch_layer((self.current_layer_idx - 1) % len(self.layers))
        elif event.key() == Qt.Key.Key_PageDown and len(self.layers) > 1:
            self._switch_layer((self.current_layer_idx + 1) % len(self.layers))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()

            hit_idx = self._hit_test_badge(pos)
            if hit_idx != -1:
                self._start_edit_annotation(hit_idx)
                return

            if self.image_rect.contains(pos):
                if self.pending_item or self.editing_index is not None:
                    self._commit_annotation()
                self.drawing = True
                self.start_pt = pos
                self.current_pt = pos
                self.repaint()

    def mouseMoveEvent(self, event):
        if self.drawing:
            pt = event.position().toPoint()
            if self.tool_mode in ("line", "arrow"):
                pt = self._snap_line(self.start_pt, pt)
            self.current_pt = pt
            self.repaint()

    def mouseReleaseEvent(self, event):
        if self.drawing and event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
            pt = event.position().toPoint()
            if self.tool_mode in ("line", "arrow"):
                pt = self._snap_line(self.start_pt, pt)
            self.current_pt = pt

            if self.tool_mode in ("rect", "blur"):
                disp_x1 = max(0, min(self.start_pt.x(), self.current_pt.x()) - self.image_rect.x())
                disp_y1 = max(0, min(self.start_pt.y(), self.current_pt.y()) - self.image_rect.y())
                disp_x2 = min(self.image_rect.width(), max(self.start_pt.x(), self.current_pt.x()) - self.image_rect.x())
                disp_y2 = min(self.image_rect.height(), max(self.start_pt.y(), self.current_pt.y()) - self.image_rect.y())
            else:
                disp_x1 = max(0, min(self.image_rect.width(), self.start_pt.x() - self.image_rect.x()))
                disp_y1 = max(0, min(self.image_rect.height(), self.start_pt.y() - self.image_rect.y()))
                disp_x2 = max(0, min(self.image_rect.width(), self.current_pt.x() - self.image_rect.x()))
                disp_y2 = max(0, min(self.image_rect.height(), self.current_pt.y() - self.image_rect.y()))

            if abs(disp_x2 - disp_x1) < 4 and abs(disp_y2 - disp_y1) < 4:
                self.update()
                return

            new_item = {
                "type": self.tool_mode,
                "x1": int(disp_x1 * self.scale_x),
                "y1": int(disp_y1 * self.scale_y),
                "x2": int(disp_x2 * self.scale_x),
                "y2": int(disp_y2 * self.scale_y),
                "text": "",
            }

            if self.tool_mode == "blur":
                self.annotations.append(new_item)
                self.redo_stack.clear()
                self.update()
                return

            self.pending_item = new_item

            low_y = max(disp_y1, disp_y2)
            high_y = min(disp_y1, disp_y2)
            left_x = min(disp_x1, disp_x2)

            self._open_inline_editor(
                anchor_x=self.image_rect.x() + left_x,
                below_y=self.image_rect.y() + low_y + 8,
                above_y=self.image_rect.y() + high_y - 44,
                text="",
            )
            self.update()

    def _commit_annotation(self):
        text = self.comment_input.text().strip()
        if self.editing_index is not None:
            if 0 <= self.editing_index < len(self.annotations):
                self.annotations[self.editing_index]["text"] = text
            self.editing_index = None
            self.comment_input.hide()
            self.update()
            return

        if not self.pending_item:
            return
        self.pending_item["text"] = text
        self.annotations.append(self.pending_item)
        self.redo_stack.clear()
        self.pending_item = None
        self.comment_input.hide()
        self.update()

    def _undo(self):
        if self.pending_item is not None:
            self.pending_item = None
            self.editing_index = None
            self.comment_input.clearFocus()
            self.comment_input.hide()
            self.setFocus()
            self.update()
            return

        if self.editing_index is not None:
            self.editing_index = None
            self.comment_input.clearFocus()
            self.comment_input.hide()
            self.setFocus()
            self.update()
            return

        if self.annotations:
            self.redo_stack.append(self.annotations.pop())
            self.update()


    def _redo(self):
        if self.redo_stack:
            self.annotations.append(self.redo_stack.pop())
            self.update()

    def paintEvent(self, event):
        if self._mask_screen or not self.layers or self.current_layer_idx < 0:
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 220))
            return
        painter = QPainter(self)
        CanvasRenderer.draw_overlay_scene(
            painter=painter,
            full_rect=self.rect(),
            image_rect=self.image_rect,
            source_pixmap=self.source_pixmap,
            annotations=self.annotations,
            pending_item=self.pending_item,
            is_drawing=self.drawing,
            tool_mode=self.tool_mode,
            start_pt=self.start_pt,
            current_pt=self.current_pt,
            start_index=self._get_layer_start_index(),
        )

    def _save_all(self):
        try:
            if self.pending_item or self.editing_index is not None:
                self._commit_annotation()

            result_pixmap = CanvasRenderer.compose_multi_layer_image(self.layers)

            prompt_parts: list[str] = []
            for idx, layer in enumerate(self.layers, 1):
                raw_pix: QPixmap = layer["pixmap"]
                anns: list[dict] = layer["annotations"]

                single_marked = CanvasRenderer.compose_final_image(raw_pix, anns)
                self.storage.save_capture(
                    raw_pixmap=raw_pix,
                    rendered_pixmap=single_marked,
                    annotations=anns,
                    img_format=self.img_format,
                )
                prompt_parts.append(
                    self.storage.build_ai_prompt(
                        raw_pix.width(), raw_pix.height(), anns
                    )
                )

            full_prompt = "\n\n".join(prompt_parts)
            self.on_clipboard_image(result_pixmap, full_prompt)
        finally:
            self._close_overlay()
