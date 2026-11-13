from PySide6.QtCore import Qt, QSize, QByteArray, QTimer, QRectF
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QPen, QBrush, QConicalGradient
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QPushButton, QComboBox, QLabel
)
from assets import get_ui_icon, SVG_ICONS
from localization import LocalizationManager


class DraggableToolbar(QFrame):
    def __init__(self, parent, loc: LocalizationManager):
        super().__init__(parent)
        self.loc = loc
        self._drag_pos = None
        self._gradient_angle = 0.0

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(
            """
            QComboBox {
                background-color: #313244;
                color: #CDD6F4;
                border: 1px solid #45475A;
                border-radius: 5px;
                padding: 5px 8px;
                font-size: 12px;
                min-width: 125px;
            }
            QComboBox::drop-down { border: none; width: 18px; }
            QComboBox QAbstractItemView {
                background-color: #1E1E2E;
                color: #CDD6F4;
                selection-background-color: #89B4FA;
                selection-color: #11111B;
                border: 1px solid #45475A;
            }
            QPushButton {
                background-color: #313244;
                border: none;
                padding: 5px 8px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #45475A; }
            QPushButton:disabled { opacity: 0.35; background-color: #252536; }
            QLabel#LayerCounter {
                color: #FF3B30;
                font-size: 12px;
                font-weight: bold;
                padding: 0 3px;
            }
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(5)

        self.drag_handle = QLabel()
        grip_pix = QPixmap(16, 16)
        grip_pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(grip_pix)
        QSvgRenderer(QByteArray(SVG_ICONS["grip"].encode("utf-8"))).render(p)
        p.end()
        self.drag_handle.setPixmap(grip_pix)
        self.drag_handle.setCursor(Qt.CursorShape.SizeAllCursor)
        layout.addWidget(self.drag_handle)

        # Блок управления слоями: < 1/1 > [корзина]
        self.btn_prev_layer = self._make_icon_btn("prev_layer", 15)
        self.lbl_layer = QLabel("1/1")
        self.lbl_layer.setObjectName("LayerCounter")
        self.btn_next_layer = self._make_icon_btn("next_layer", 15)
        self.btn_del_layer = self._make_icon_btn("del_layer", 15)

        layout.addWidget(self.btn_prev_layer)
        layout.addWidget(self.lbl_layer)
        layout.addWidget(self.btn_next_layer)
        layout.addWidget(self.btn_del_layer)

        # Выпадающий список инструментов (включая "Выделить всё")
        self.tool_combo = QComboBox()
        layout.addWidget(self.tool_combo)

        self.btn_undo = self._make_icon_btn("undo")
        self.btn_redo = self._make_icon_btn("redo")
        self.btn_info = self._make_icon_btn("info")

        self.btn_save = self._make_icon_btn("ok")
        self.btn_save.setStyleSheet(
            "background-color: #A6E3A1; padding: 5px 10px; border-radius: 5px;"
        )

        self.btn_close = self._make_icon_btn("close")

        for btn in (
            self.btn_undo,
            self.btn_redo,
            self.btn_info,
            self.btn_save,
            self.btn_close,
        ):
            layout.addWidget(btn)

        self.retranslate()

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._step_gradient)
        self._anim_timer.start(45)

    def update_layer_indicator(self, current_idx: int, total: int):
        self.lbl_layer.setText(f"{current_idx + 1}/{total}")
        self.lbl_layer.setToolTip(
            self.loc.tr("ID47").format(cur=current_idx + 1, total=total)
        )
        has_multi = total > 1
        self.btn_prev_layer.setEnabled(has_multi)
        self.btn_next_layer.setEnabled(has_multi)
        self.btn_del_layer.setEnabled(has_multi)
        self.adjustSize()

    def _step_gradient(self):
        if self.isVisible():
            self._gradient_angle = (self._gradient_angle + 4.0) % 360.0
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)

        painter.setBrush(QBrush(QColor("#1E1E2E")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 9.0, 9.0)

        grad = QConicalGradient(rect.center(), self._gradient_angle)
        grad.setColorAt(0.00, QColor("#FF3B30"))
        grad.setColorAt(0.25, QColor("#FF9500"))
        grad.setColorAt(0.50, QColor("#FF2D55"))
        grad.setColorAt(0.75, QColor("#38BDF8"))
        grad.setColorAt(1.00, QColor("#FF3B30"))

        pen = QPen(QBrush(grad), 2.5)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 9.0, 9.0)

    @staticmethod
    def _make_icon_btn(icon_name: str, size: int = 18) -> QPushButton:
        btn = QPushButton()
        btn.setIcon(get_ui_icon(icon_name, size))
        btn.setIconSize(QSize(size, size))
        return btn

    def retranslate(self):
        current_idx = max(0, self.tool_combo.currentIndex())
        self.tool_combo.blockSignals(True)
        self.tool_combo.clear()
        self.tool_combo.addItem(self.loc.tr("ID2"), "rect")
        self.tool_combo.addItem(self.loc.tr("ID3"), "line")
        self.tool_combo.addItem(self.loc.tr("ID28"), "arrow")
        self.tool_combo.addItem(self.loc.tr("ID31"), "blur")
        self.tool_combo.addItem(self.loc.tr("ID30"), "select_all")
        if current_idx < self.tool_combo.count():
            self.tool_combo.setCurrentIndex(current_idx)
        self.tool_combo.blockSignals(False)

        self.btn_prev_layer.setToolTip(self.loc.tr("ID45"))
        self.btn_next_layer.setToolTip(self.loc.tr("ID46"))
        self.btn_del_layer.setToolTip(self.loc.tr("ID48"))
        self.btn_undo.setToolTip(self.loc.tr("ID4"))
        self.btn_redo.setToolTip(self.loc.tr("ID5"))
        self.btn_info.setToolTip(self.loc.tr("ID10"))
        self.btn_save.setToolTip(self.loc.tr("ID7"))
        self.btn_close.setToolTip(self.loc.tr("ID11"))
        self.adjustSize()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            if hasattr(self.parent(), "image_rect"):
                bounds = self.parent().local_screen
                min_x = bounds.left()
                max_x = max(min_x, bounds.right() - self.width())
                min_y = bounds.top()
                max_y = max(min_y, bounds.bottom() - self.height())
                new_pos.setX(max(min_x, min(max_x, new_pos.x())))
                new_pos.setY(max(min_y, min(max_y, new_pos.y())))
            self.move(new_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
