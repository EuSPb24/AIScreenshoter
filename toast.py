from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QGuiApplication, QCursor
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QFrame


class DarkToast(QWidget):
    """Неблокирующее темное всплывающее уведомление с гладкими скругленными углами."""

    def __init__(self, parent: QWidget | None, text: str, duration_ms: int = 2400):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame(self)
        card.setObjectName("ToastCard")
        card.setStyleSheet(
            """
            QFrame#ToastCard {
                background-color: #1E1E2E;
                border: 2px solid #FF3B30;
                border-radius: 12px;
            }
            QLabel {
                color: #CDD6F4;
                background: transparent;
                border: none;
                padding: 14px 22px;
                font-family: "Segoe UI";
                font-size: 14px;
                font-weight: bold;
            }
            """
        )
        layout.addWidget(card)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(text, card)
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setMinimumWidth(340)
        lbl.setMaximumWidth(480)
        card_layout.addWidget(lbl)

        self.adjustSize()
        self._position_on_active_screen()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.close)
        self._timer.start(duration_ms)

    def _position_on_active_screen(self):
        screen = (
            QGuiApplication.screenAt(QCursor.pos())
            or QGuiApplication.primaryScreen()
        )
        geo: QRect = screen.availableGeometry()
        x = geo.center().x() - self.width() // 2
        y = geo.center().y() - self.height() // 2
        self.move(x, y)

    def mousePressEvent(self, event):
        self.close()
