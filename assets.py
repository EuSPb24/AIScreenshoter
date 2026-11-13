from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

SVG_APP_ICON = """
<svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://w3.org">
  <rect x="0" y="0" width="64" height="64" rx="14" fill="#1E1E2E"/>
  <path d="M10 22V10H22M42 10H54V22M54 42V54H42M22 54H10V42" stroke="#38BDF8" stroke-width="6.5" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="32" cy="32" r="11" fill="#FF3B30"/>
</svg>
"""

SVG_ICONS = {
    "grip": """
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://w3.org">
      <circle cx="9" cy="6" r="1.8" fill="#7F849C"/>
      <circle cx="15" cy="6" r="1.8" fill="#7F849C"/>
      <circle cx="9" cy="12" r="1.8" fill="#7F849C"/>
      <circle cx="15" cy="12" r="1.8" fill="#7F849C"/>
      <circle cx="9" cy="18" r="1.8" fill="#7F849C"/>
      <circle cx="15" cy="18" r="1.8" fill="#7F849C"/>
    </svg>
    """,
    "undo": """
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://w3.org">
      <path d="M9 14L4 9L9 4" stroke="#CDD6F4" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M4 9H14.5C17.5376 9 20 11.4624 20 14.5C20 17.5376 17.5376 20 14.5 20H11" stroke="#CDD6F4" stroke-width="2.2" stroke-linecap="round"/>
    </svg>
    """,
    "redo": """
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://w3.org">
      <path d="M15 14L20 9L15 4" stroke="#CDD6F4" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M20 9H9.5C6.46243 9 4 11.4624 4 14.5C4 17.5376 6.46243 20 9.5 20H13" stroke="#CDD6F4" stroke-width="2.2" stroke-linecap="round"/>
    </svg>
    """,
    "select_all": """
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://w3.org">
      <path d="M4 8V6C4 4.89543 4.89543 4 6 4H8" stroke="#F9E2AF" stroke-width="2.2" stroke-linecap="round"/>
      <path d="M16 4H18C19.1046 4 20 4.89543 20 6V8" stroke="#F9E2AF" stroke-width="2.2" stroke-linecap="round"/>
      <path d="M20 16V18C20 19.1046 19.1046 20 18 20H16" stroke="#F9E2AF" stroke-width="2.2" stroke-linecap="round"/>
      <path d="M8 20H6C4.89543 20 4 19.1046 4 18V16" stroke="#F9E2AF" stroke-width="2.2" stroke-linecap="round"/>
      <rect x="8" y="8" width="8" height="8" rx="1.5" stroke="#F9E2AF" stroke-width="1.8" stroke-dasharray="2 2"/>
    </svg>
    """,
    "prev_layer": """
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://w3.org">
      <path d="M15 18L9 12L15 6" stroke="#FF3B30" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """,
    "next_layer": """
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://w3.org">
      <path d="M9 18L15 12L9 6" stroke="#FF3B30" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """,
    "del_layer": """
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" xmlns="http://w3.org">
      <path d="M3 6H21M8 6V4C8 3.44772 8.44772 3 9 3H15C15.5523 3 16 3.44772 16 4V6M19 6L18.1 19.1C18.04 20.16 17.16 21 16.1 21H7.9C6.84 21 5.96 20.16 5.9 19.1L5 6" stroke="#F38BA8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """,
    "info": """
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://w3.org">
      <circle cx="12" cy="12" r="9" stroke="#89B4FA" stroke-width="2.2"/>
      <path d="M12 11V16" stroke="#89B4FA" stroke-width="2.2" stroke-linecap="round"/>
      <circle cx="12" cy="7.8" r="1.2" fill="#89B4FA"/>
    </svg>
    """,
    "prev_layer": """
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://w3.org">
      <path d="M15 18L9 12L15 6" stroke="#FF3B30" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """,
    "next_layer": """
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://w3.org">
      <path d="M9 18L15 12L9 6" stroke="#FF3B30" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """,   
    "ok": """
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://w3.org">
      <path d="M5 13L9.5 17.5L19 7" stroke="#11111B" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """,
    "close": """
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://w3.org">
      <path d="M6 6L18 18M18 6L6 18" stroke="#F38BA8" stroke-width="2.2" stroke-linecap="round"/>
    </svg>
    """,
}

def get_badge_svg(index: int) -> str:
    return f"""
    <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://w3.org">
      <circle cx="12" cy="12" r="10.5" fill="#FF3B30" stroke="#FFFFFF" stroke-width="2"/>
      <text x="12" y="16" font-family="Arial, sans-serif" font-size="12" font-weight="bold" fill="#FFFFFF" text-anchor="middle">{index}</text>
    </svg>
    """

def render_svg_icon(svg_xml: str, size: int = 18) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    QSvgRenderer(QByteArray(svg_xml.encode("utf-8"))).render(painter)
    painter.end()
    return QIcon(pix)

def create_app_icon() -> QIcon:
    icon = QIcon()
    renderer = QSvgRenderer(QByteArray(SVG_APP_ICON.encode("utf-8")))
    for sz in (16, 20, 24, 32, 48, 64, 128, 256):
        pix = QPixmap(sz, sz)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pix)
    return icon

def get_ui_icon(name: str, size: int = 18) -> QIcon:
    return render_svg_icon(SVG_ICONS[name], size)
