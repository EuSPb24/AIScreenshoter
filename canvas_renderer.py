import math
from PySide6.QtCore import Qt, QRect, QPoint, QPointF, QByteArray
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPolygonF, QPixmap, QFont, QFontMetrics
)
from PySide6.QtSvg import QSvgRenderer

from assets import get_badge_svg


class CanvasRenderer:
    @staticmethod
    def _draw_arrow(painter: QPainter, x1: int, y1: int, x2: int, y2: int, color: QColor):
        painter.drawLine(x1, y1, x2, y2)

        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length < 6:
            return

        angle = math.atan2(dy, dx)
        arrow_len = 14.0
        arrow_angle = math.radians(26)

        p2 = QPointF(x2, y2)
        p_left = QPointF(
            x2 - arrow_len * math.cos(angle - arrow_angle),
            y2 - arrow_len * math.sin(angle - arrow_angle),
        )
        p_right = QPointF(
            x2 - arrow_len * math.cos(angle + arrow_angle),
            y2 - arrow_len * math.sin(angle + arrow_angle),
        )

        painter.save()
        painter.setBrush(QBrush(color))
        painter.drawPolygon(QPolygonF([p2, p_left, p_right]))
        painter.restore()

    @staticmethod
    def _apply_blur(
        painter: QPainter,
        source_pixmap: QPixmap,
        src_rect: QRect,
        dst_rect: QRect,
    ):
        clean_src = src_rect.intersected(source_pixmap.rect())
        if clean_src.width() < 2 or clean_src.height() < 2:
            return

        cropped = source_pixmap.copy(clean_src)
        # Сильное сжатие с последующим растяжением надежно скрывает текст и цифры
        factor = 14
        small_w = max(1, clean_src.width() // factor)
        small_h = max(1, clean_src.height() // factor)

        tiny = cropped.scaled(
            small_w,
            small_h,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        blurred = tiny.scaled(
            dst_rect.width(),
            dst_rect.height(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawPixmap(dst_rect.topLeft(), blurred)


    @staticmethod
    def calc_badge_rect(
        item: dict,
        offset_x: int,
        offset_y: int,
        bounds_width: int = 0,
        bounds_height: int = 0,
        occupied_rects: list[QRect] | None = None,
    ) -> QRect:
        badge_size = 24
        half = badge_size // 2
        x1, y1 = offset_x + item["x1"], offset_y + item["y1"]
        x2, y2 = offset_x + item["x2"], offset_y + item["y2"]

        if item["type"] in ("line", "arrow"):
            dx = x2 - x1
            dy = y2 - y1
            length = math.hypot(dx, dy)
            if length > 0:
                shift = 16.0
                bx = int(x1 - (dx / length) * shift) - half
                by = int(y1 - (dy / length) * shift) - half - 4
            else:
                bx = x1 - half
                by = y1 - badge_size - 4
        else:
            bx = x2 - half
            by = y1 - badge_size - 4
            if bounds_height > 0 and by < offset_y + 4:
                bx = x2 - badge_size - 4
                by = y1 + 4

        if bounds_width > 0 and bounds_height > 0:
            bx = max(offset_x + 4, min(offset_x + bounds_width - badge_size - 4, bx))
            by = max(offset_y + 4, min(offset_y + bounds_height - badge_size - 4, by))

        candidate = QRect(bx, by, badge_size, badge_size)

        # Защита от наложения меток: если слот занят — сдвигаем влево
        if occupied_rects:
            for _ in range(15):
                if not any(candidate.intersects(r) for r in occupied_rects):
                    break
                candidate.moveLeft(candidate.left() - (badge_size + 4))
                if bounds_width > 0 and candidate.left() < offset_x + 4:
                    candidate.moveTo(bx, candidate.top() + badge_size + 4)

        return candidate

    @classmethod
    def draw_annotations(
        cls,
        painter: QPainter,
        annotations: list[dict],
        pending_item: dict | None,
        offset_x: int,
        offset_y: int,
        bounds_width: int = 0,
        bounds_height: int = 0,
        source_pixmap: QPixmap | None = None,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        start_index: int = 1,
    ):

        items = list(annotations)
        if pending_item:
            items.append(pending_item)

        # 1. Сначала отрисовываем все слои размытия (блюр) без номеров акцентов
        if source_pixmap is not None:
            for item in items:
                if item.get("type") == "blur":
                    dx1 = offset_x + item["x1"]
                    dy1 = offset_y + item["y1"]
                    dx2 = offset_x + item["x2"]
                    dy2 = offset_y + item["y2"]
                    dst_rect = QRect(QPoint(dx1, dy1), QPoint(dx2, dy2)).normalized()

                    src_rect = QRect(
                        int(item["x1"] * scale_x),
                        int(item["y1"] * scale_y),
                        max(1, int((item["x2"] - item["x1"]) * scale_x)),
                        max(1, int((item["y2"] - item["y1"]) * scale_y)),
                    ).normalized()
                    cls._apply_blur(painter, source_pixmap, src_rect, dst_rect)

        # 2. Затем отрисовываем рамки, линии, стрелки и их порядковые номера
        main_color = QColor("#FF3B30")
        pen = QPen(main_color, 2)
        painter.setPen(pen)

        occupied: list[QRect] = []
        badge_idx = start_index - 1

        for item in items:
            item_type = item["type"]
            if item_type == "blur":
                continue

            badge_idx += 1
            x1, y1 = offset_x + item["x1"], offset_y + item["y1"]
            x2, y2 = offset_x + item["x2"], offset_y + item["y2"]

            if item_type == "rect":
                painter.drawRect(QRect(QPoint(x1, y1), QPoint(x2, y2)))
            elif item_type == "arrow":
                cls._draw_arrow(painter, x1, y1, x2, y2, main_color)
            else:
                painter.drawLine(x1, y1, x2, y2)

            badge_rect = cls.calc_badge_rect(
                item, offset_x, offset_y, bounds_width, bounds_height, occupied
            )
            occupied.append(badge_rect)

            svg_bytes = QByteArray(get_badge_svg(badge_idx).encode("utf-8"))
            renderer = QSvgRenderer(svg_bytes)
            renderer.render(painter, badge_rect)

    @classmethod
    def draw_overlay_scene(
        cls,
        painter: QPainter,
        full_rect: QRect,
        image_rect: QRect,
        source_pixmap: QPixmap,
        annotations: list[dict],
        pending_item: dict | None,
        is_drawing: bool,
        tool_mode: str,
        start_pt: QPoint,
        current_pt: QPoint,
        start_index: int = 1,
    ):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Усиленное затенение фона (220 из 255), чтобы ничто не отвлекало от скрина
        painter.fillRect(full_rect, QColor(0, 0, 0, 220))
        painter.drawPixmap(image_rect, source_pixmap)

        # Тонкая нейтральная рамка по периметру снимка для четкой границы на темном фоне
        painter.save()
        painter.setPen(QPen(QColor("#585B70"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(image_rect.adjusted(0, 0, -1, -1))
        painter.restore()


        sx = image_rect.width() / max(1, source_pixmap.width())
        sy = image_rect.height() / max(1, source_pixmap.height())
        inv_sx = source_pixmap.width() / max(1, image_rect.width())
        inv_sy = source_pixmap.height() / max(1, image_rect.height())

        scaled_anns = [
            {
                **a,
                "x1": int(a["x1"] * sx),
                "y1": int(a["y1"] * sy),
                "x2": int(a["x2"] * sx),
                "y2": int(a["y2"] * sy),
            }
            for a in annotations
        ]
        scaled_pending = None
        if pending_item:
            scaled_pending = {
                **pending_item,
                "x1": int(pending_item["x1"] * sx),
                "y1": int(pending_item["y1"] * sy),
                "x2": int(pending_item["x2"] * sx),
                "y2": int(pending_item["y2"] * sy),
            }

        cls.draw_annotations(
            painter=painter,
            annotations=scaled_anns,
            pending_item=scaled_pending,
            offset_x=image_rect.x(),
            offset_y=image_rect.y(),
            bounds_width=image_rect.width(),
            bounds_height=image_rect.height(),
            source_pixmap=source_pixmap,
            scale_x=inv_sx,
            scale_y=inv_sy,
            start_index=start_index,
        )

        if is_drawing:
            preview_color = QColor("#F9E2AF") if tool_mode == "blur" else QColor("#38BDF8")
            painter.setPen(QPen(preview_color, 2, Qt.PenStyle.DashLine))
            if tool_mode in ("rect", "blur"):
                painter.drawRect(QRect(start_pt, current_pt))
            elif tool_mode == "arrow":
                painter.setPen(QPen(preview_color, 2, Qt.PenStyle.SolidLine))
                cls._draw_arrow(
                    painter,
                    start_pt.x(),
                    start_pt.y(),
                    current_pt.x(),
                    current_pt.y(),
                    preview_color,
                )
            else:
                painter.drawLine(start_pt, current_pt)

    @classmethod
    def compose_final_image(
        cls, source_pixmap: QPixmap, annotations: list[dict]
    ) -> QPixmap:
        base_pix = source_pixmap.copy()
        p = QPainter(base_pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cls.draw_annotations(
            painter=p,
            annotations=annotations,
            pending_item=None,
            offset_x=0,
            offset_y=0,
            bounds_width=base_pix.width(),
            bounds_height=base_pix.height(),
            source_pixmap=source_pixmap,
        )
        p.end()

        visible_anns = [a for a in annotations if a.get("type") != "blur"]
        text_items = [
            (idx, ann) for idx, ann in enumerate(visible_anns, 1) if ann.get("text")
        ]
        if not text_items:
            return base_pix

        final_w = max(base_pix.width(), 560)

        ui_scale = max(1.0, final_w / 1280.0)
        font_pt = max(12, int(12 * ui_scale))
        badge_size = max(26, int(26 * ui_scale))
        padding = max(14, int(14 * ui_scale))
        gap = max(12, int(12 * ui_scale))
        row_spacing = max(10, int(10 * ui_scale))

        font = QFont("Segoe UI", font_pt)
        metrics = QFontMetrics(font)
        text_max_w = final_w - (padding * 2 + badge_size + gap)

        rows: list[tuple[int, str, int]] = []
        total_footer_h = padding * 2

        for idx, ann in text_items:
            txt = ann["text"]
            bound = metrics.boundingRect(
                QRect(0, 0, text_max_w, 4000),
                Qt.TextFlag.TextWordWrap,
                txt,
            )
            row_h = max(badge_size, bound.height())
            rows.append((idx, txt, row_h))
            total_footer_h += row_h + row_spacing

        total_footer_h -= row_spacing

        final_pix = QPixmap(final_w, base_pix.height() + total_footer_h)
        final_pix.fill(QColor("#1E1E2E"))

        fp = QPainter(final_pix)
        fp.setRenderHint(QPainter.RenderHint.Antialiasing)
        fp.drawPixmap(0, 0, base_pix)

        fp.setPen(QPen(QColor("#45475A"), max(2, int(2 * ui_scale))))
        fp.drawLine(0, base_pix.height(), final_w, base_pix.height())

        fp.setFont(font)
        cur_y = base_pix.height() + padding

        for idx, txt, row_h in rows:
            svg_bytes = QByteArray(get_badge_svg(idx).encode("utf-8"))
            renderer = QSvgRenderer(svg_bytes)
            badge_y = cur_y + max(0, (row_h - badge_size) // 2)
            renderer.render(fp, QRect(padding, badge_y, badge_size, badge_size))

            fp.setPen(QColor("#CDD6F4"))
            text_rect = QRect(
                padding + badge_size + gap, cur_y, text_max_w, row_h + 6
            )
            fp.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter
                | Qt.TextFlag.TextWordWrap,
                txt,
            )
            cur_y += row_h + row_spacing

        fp.end()
        return final_pix
    @classmethod
    def compose_multi_layer_image(cls, layers: list[dict]) -> QPixmap:
        """Склеивает все слои (кадры) в единое изображение со сквозной нумерацией и общим подвалом."""
        if not layers:
            return QPixmap()
        if len(layers) == 1:
            return cls.compose_final_image(
                layers[0]["pixmap"], layers[0]["annotations"]
            )

        rendered_parts: list[QPixmap] = []
        all_text_items: list[tuple[int, str]] = []
        current_badge_num = 1

        for layer in layers:
            raw_pix: QPixmap = layer["pixmap"]
            anns: list[dict] = layer["annotations"]

            part_pix = raw_pix.copy()
            p = QPainter(part_pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            cls.draw_annotations(
                painter=p,
                annotations=anns,
                pending_item=None,
                offset_x=0,
                offset_y=0,
                bounds_width=part_pix.width(),
                bounds_height=part_pix.height(),
                source_pixmap=raw_pix,
                start_index=current_badge_num,
            )
            p.end()
            rendered_parts.append(part_pix)

            for ann in anns:
                if ann.get("type") == "blur":
                    continue
                txt = ann.get("text", "").strip()
                if txt:
                    all_text_items.append((current_badge_num, txt))
                current_badge_num += 1

        gap_between_layers = 8
        final_w = max(max(p.width() for p in rendered_parts), 560)
        total_images_h = (
            sum(p.height() for p in rendered_parts)
            + gap_between_layers * (len(rendered_parts) - 1)
        )

        # Собираем единый холст кадров
        stitched = QPixmap(final_w, total_images_h)
        stitched.fill(QColor("#11111B"))
        sp = QPainter(stitched)
        cur_y = 0
        for part in rendered_parts:
            x_off = (final_w - part.width()) // 2
            sp.drawPixmap(x_off, cur_y, part)
            cur_y += part.height() + gap_between_layers
        sp.end()

        if not all_text_items:
            return stitched

        ui_scale = max(1.0, final_w / 1280.0)
        font_pt = max(12, int(12 * ui_scale))
        badge_size = max(26, int(26 * ui_scale))
        padding = max(14, int(14 * ui_scale))
        gap = max(12, int(12 * ui_scale))
        row_spacing = max(10, int(10 * ui_scale))

        font = QFont("Segoe UI", font_pt)
        metrics = QFontMetrics(font)
        text_max_w = final_w - (padding * 2 + badge_size + gap)

        rows: list[tuple[int, str, int]] = []
        total_footer_h = padding * 2

        for idx, txt in all_text_items:
            bound = metrics.boundingRect(
                QRect(0, 0, text_max_w, 4000),
                Qt.TextFlag.TextWordWrap,
                txt,
            )
            row_h = max(badge_size, bound.height())
            rows.append((idx, txt, row_h))
            total_footer_h += row_h + row_spacing

        total_footer_h -= row_spacing

        final_pix = QPixmap(final_w, stitched.height() + total_footer_h)
        final_pix.fill(QColor("#1E1E2E"))

        fp = QPainter(final_pix)
        fp.setRenderHint(QPainter.RenderHint.Antialiasing)
        fp.drawPixmap(0, 0, stitched)

        fp.setPen(QPen(QColor("#89B4FA"), max(2, int(2 * ui_scale))))
        fp.drawLine(0, stitched.height(), final_w, stitched.height())

        fp.setFont(font)
        cur_y = stitched.height() + padding

        for idx, txt, row_h in rows:
            svg_bytes = QByteArray(get_badge_svg(idx).encode("utf-8"))
            renderer = QSvgRenderer(svg_bytes)
            badge_y = cur_y + max(0, (row_h - badge_size) // 2)
            renderer.render(fp, QRect(padding, badge_y, badge_size, badge_size))

            fp.setPen(QColor("#CDD6F4"))
            text_rect = QRect(
                padding + badge_size + gap, cur_y, text_max_w, row_h + 6
            )
            fp.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter
                | Qt.TextFlag.TextWordWrap,
                txt,
            )
            cur_y += row_h + row_spacing

        fp.end()
        return final_pix
