from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QLineEdit,
    QPushButton,
    QWidget,
    QLabel,
    QFrame,
    QTextEdit,
    QMenu,
    QApplication,
)
from localization import LocalizationManager
from spellchecker import WindowsSpellChecker, SpellSyntaxHighlighter


class SpellCommentEdit(QTextEdit):
    """Однострочное поле ввода с нативной проверкой орфографии и подсказками по ПКМ."""

    returnPressed = Signal()
    escapePressed = Signal()

    def _adjust_height(self):
        doc_height = int(self.document().size().height())
        # Минимум 36 px (1 строка), максимум 116 px (до 5 строк текста)
        new_h = max(36, min(116, doc_height + 12))
        if self.height() != new_h:
            self.setFixedHeight(new_h)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(36)
        self.setTabChangesFocus(True)
        self.textChanged.connect(self._adjust_height)
        font = QFont("Segoe UI", 11)
        self.setFont(font)
        self.document().setDefaultFont(font)
        self._adjust_height()
        self.checker = WindowsSpellChecker()
        self.highlighter = SpellSyntaxHighlighter(self.document(), self.checker)

    def text(self) -> str:
        return self.toPlainText()

    def setText(self, val: str):
        self.setPlainText(val)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self._adjust_height()
        
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                self.returnPressed.emit()
                return
        if event.key() == Qt.Key.Key_Escape:
            self.escapePressed.emit()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        word = cursor.selectedText().strip()

        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #1E1E2E;
                color: #CDD6F4;
                border: 1px solid #45475A;
                padding: 4px;
            }
            QMenu::item { padding: 5px 14px; border-radius: 4px; }
            QMenu::item:selected { background-color: #89B4FA; color: #11111B; }
            """
        )

        if word:
            suggestions = self.checker.get_suggestions(word)
            if suggestions:
                for sugg in suggestions:
                    act = menu.addAction(sugg)
                    act.triggered.connect(
                        lambda checked=False, s=sugg, c=QTextCursor(cursor): self._replace_word(c, s)
                    )
                menu.addSeparator()

        std_menu = self.createStandardContextMenu()
        for act in std_menu.actions():
            menu.addAction(act)

        menu.exec(event.globalPos())

    def _replace_word(self, cursor: QTextCursor, replacement: str):
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(replacement)
        cursor.endEditBlock()
        self.setTextCursor(cursor)

class HelpDialog(QDialog):
    """Окно подробной справки, закрывающееся по крестику или клику вне окна."""

    def __init__(self, parent: QWidget | None, loc: LocalizationManager):
        super().__init__(parent)
        self.loc = loc
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
        )
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.resize(660, 580)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame(self)
        card.setObjectName("HelpCard")
        card.setStyleSheet(
            """
            QFrame#HelpCard {
                background-color: #1E1E2E;
                border: 2px solid #89B4FA;
                border-radius: 12px;
            }
            QLabel#TitleLabel {
                color: #89B4FA;
                font-size: 16px;
                font-weight: bold;
            }
            QLabel#ItemLabel {
                color: #CDD6F4;
                font-size: 13px;
                padding: 3px 0;
            }
            QLabel#FooterLabel {
                color: #A6ADC8;
                font-size: 12px;
                background-color: #181825;
                border-radius: 6px;
                padding: 8px 12px;
            }
            QPushButton#CloseBtn {
                background-color: #313244;
                color: #F38BA8;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 4px 10px;
            }
            QPushButton#CloseBtn:hover {
                background-color: #F38BA8;
                color: #11111B;
            }
            """
        )
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # Верхняя шапка справки с заголовком и крестиком
        header_row = QHBoxLayout()
        title_lbl = QLabel(self.loc.tr("ID32"))
        title_lbl.setObjectName("TitleLabel")
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setObjectName("CloseBtn")
        btn_close.setToolTip(self.loc.tr("ID44"))
        btn_close.clicked.connect(self.accept)
        header_row.addWidget(btn_close)
        layout.addLayout(header_row)

        line_top = QFrame()
        line_top.setFrameShape(QFrame.Shape.HLine)
        line_top.setStyleSheet("color: #45475A;")
        layout.addWidget(line_top)

        for key in (
            "ID33", "ID34", "ID35", "ID36", "ID37",
            "ID38", "ID39", "ID40", "ID41", "ID42",
            "ID49", "ID50",
        ):
            lbl = QLabel(f"• {self.loc.tr(key)}")
            lbl.setObjectName("ItemLabel")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)


        layout.addStretch()

        # Нижний блок: автор, участие ИИ, год, версия (ID43)
        footer_lbl = QLabel(self.loc.tr("ID43"))
        footer_lbl.setObjectName("FooterLabel")
        footer_lbl.setWordWrap(True)
        footer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_lbl.setOpenExternalLinks(True)
        layout.addWidget(footer_lbl)

        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == event.Type.MouseButtonPress and self.isVisible():
            global_pos = event.globalPosition().toPoint()
            if not self.geometry().contains(global_pos):
                self.accept()
                return True
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self)
        super().closeEvent(event)

    def accept(self):
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self)
        super().accept()


class EditAnnotationsDialog(QDialog):
    def __init__(self, parent: QWidget, loc: LocalizationManager, annotations: list[dict]):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.loc = loc
        self.annotations = annotations

        self.setWindowTitle(self.loc.tr("ID6"))
        self.resize(480, 280)

        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        for idx, ann in enumerate(self.annotations, 1):
            obj_key = "ID20" if ann["type"] == "rect" else "ID21"
            obj_name = self.loc.tr(obj_key)
            self.list_widget.addItem(
                f"#{idx} [{obj_name}] X:{ann['x1']}..{ann['x2']} Y:{ann['y1']}..{ann['y2']} — {ann['text']}"
            )
        layout.addWidget(self.list_widget)

        self.edit_box = QLineEdit()
        layout.addWidget(self.edit_box)

        self.list_widget.currentRowChanged.connect(self._on_row_change)
        if self.annotations:
            self.list_widget.setCurrentRow(0)

        btn_save = QPushButton(self.loc.tr("ID22"))
        btn_save.clicked.connect(self._save_and_close)
        layout.addWidget(btn_save)

    def _on_row_change(self, row: int):
        if 0 <= row < len(self.annotations):
            self.edit_box.setText(self.annotations[row]["text"])

    def _save_and_close(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.annotations):
            self.annotations[row]["text"] = self.edit_box.text().strip()
        self.accept()
