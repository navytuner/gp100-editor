# style.py — Theme and stylesheets for GP-100 Editor

from PySide6.QtGui import QColor, QPalette

# ── Color tokens ──────────────────────────────────────────────────────────────

BG = "#1C1D2B"
SURFACE = "#262838"
ELEVATED = "#2F3148"
BORDER = "#3A3D55"
TEXT = "#E2E4F0"
TEXT_DIM = "#8B8EA8"
TEXT_MUTED = "#555770"
ACCENT = "#FF6B6B"
LOG_GREEN = "#7FD68A"

FONT = "'JetBrains Mono','Cascadia Code','Consolas','Courier New',monospace"

# ── Global stylesheet ──────────────────────────────────────────────────────────

GLOBAL_CSS = f"""
QMainWindow, QWidget {{ background:{BG}; color:{TEXT}; }}

QScrollBar:horizontal {{
    background:{BG}; height:8px; border:none; border-radius:4px;
}}
QScrollBar::handle:horizontal {{
    background:{BORDER}; border-radius:4px; min-width:40px;
}}
QScrollBar::handle:horizontal:hover {{ background:{TEXT_MUTED}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width:0; }}

QScrollBar:vertical {{
    background:transparent; width:5px; border:none; border-radius:2px;
}}
QScrollBar::handle:vertical {{
    background:{BORDER}; border-radius:2px; min-height:20px;
}}
QScrollBar::handle:vertical:hover {{ background:{TEXT_MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}

QTextEdit#log {{
    background:{SURFACE}; color:{LOG_GREEN};
    border:1px solid {BORDER}; border-radius:6px;
    font-family:{FONT}; font-size:11px; padding:4px 8px;
}}
"""

# ── Helpers ────────────────────────────────────────────────────────────────────


def _rgb(hex_color: str) -> tuple[int, int, int]:
    return int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)


def rgba(hex_color: str, alpha: float) -> str:
    """Convert '#RRGGBB' + alpha (0.0–1.0) to 'rgba(r,g,b,a)' for Qt CSS."""
    r, g, b = _rgb(hex_color)
    return f"rgba({r},{g},{b},{alpha})"


def lighten(hex_color: str, amount: float = 0.2) -> str:
    """Lighten a hex color by mixing with white."""
    r, g, b = _rgb(hex_color)
    r = min(255, int(r + (255 - r) * amount))
    g = min(255, int(g + (255 - g) * amount))
    b = min(255, int(b + (255 - b) * amount))
    return f"#{r:02X}{g:02X}{b:02X}"


def patch_css(active: bool) -> str:
    if active:
        return (
            f"QPushButton{{background:{ACCENT};color:white;border:none;"
            f"border-radius:4px;padding:4px 12px;font-family:{FONT};"
            f"font-size:12px;font-weight:bold;min-width:30px;}}"
            f"QPushButton:hover{{background:#FF8585;}}"
        )
    return (
        f"QPushButton{{background:{SURFACE};color:{TEXT_DIM};border:1px solid {BORDER};"
        f"border-radius:4px;padding:4px 12px;font-family:{FONT};"
        f"font-size:12px;font-weight:bold;min-width:30px;}}"
        f"QPushButton:hover{{background:{ELEVATED};color:{TEXT};}}"
    )


def conn_css(connected: bool) -> str:
    if connected:
        return (
            f"QPushButton{{background:#3D9;color:#1C1D2B;border:none;"
            f"border-radius:4px;padding:5px 14px;"
            f"font-family:{FONT};font-size:11px;font-weight:bold;}}"
            f"QPushButton:hover{{background:#5EB;}}"
        )
    return (
        f"QPushButton{{background:{ACCENT};color:white;border:none;"
        f"border-radius:4px;padding:5px 14px;"
        f"font-family:{FONT};font-size:11px;font-weight:bold;}}"
        f"QPushButton:hover{{background:#FF8585;}}"
    )


def pedal_css(color: str, active: bool) -> str:
    if active:
        return f"""
            QFrame#PedalCard {{
                background:{SURFACE};
                border:1px solid {rgba(color, 0.44)};
                border-radius:10px;
            }}
        """
    return f"""
        QFrame#PedalCard {{
            background:{SURFACE};
            border:1px solid {rgba(color, 0.19)};
            border-radius:10px;
        }}
    """


def faceplate_css(color: str, active: bool) -> str:
    if active:
        return (
            f"background:{color}; color:#1C1D2B; font-family:{FONT};"
            f"font-size:13px; font-weight:bold; letter-spacing:3px;"
            f"border-top-left-radius:9px; border-top-right-radius:9px;"
            f"padding:0 10px;"
        )
    return (
        f"background:{rgba(color, 0.25)}; color:{TEXT_DIM}; font-family:{FONT};"
        f"font-size:13px; font-weight:bold; letter-spacing:3px;"
        f"border-top-left-radius:9px; border-top-right-radius:9px;"
        f"padding:0 10px;"
    )


def footswitch_css(color: str, active: bool) -> str:
    if active:
        hover_color = lighten(color, 0.25)
        return (
            f"QPushButton{{background:{color};color:#1C1D2B;border:none;"
            f"border-radius:6px;padding:8px;font-family:{FONT};"
            f"font-size:11px;font-weight:bold;letter-spacing:1px;}}"
            f"QPushButton:hover{{background:{hover_color};}}"
        )
    return (
        f"QPushButton{{background:{rgba(color, 0.12)};color:{rgba(color, 0.56)};border:1px solid {rgba(color, 0.19)};"
        f"border-radius:6px;padding:8px;font-family:{FONT};"
        f"font-size:11px;font-weight:bold;letter-spacing:1px;}}"
        f"QPushButton:hover{{background:{rgba(color, 0.19)};color:{rgba(color, 0.73)};}}"
    )


def pedal_combo_css(color: str) -> str:
    return f"""
        QComboBox {{
            background:{BG}; color:{TEXT};
            border:1px solid {BORDER};
            border-radius:4px; padding:3px 8px;
            font-family:{FONT}; font-size:10px; min-height:20px;
        }}
        QComboBox:hover {{ border-color:{rgba(color, 0.5)}; }}
        QComboBox::drop-down {{ border:none; width:16px; }}
        QComboBox QAbstractItemView {{
            background:{SURFACE}; color:{TEXT};
            selection-background-color:{rgba(color, 0.19)};
            font-family:{FONT}; font-size:10px;
            border:1px solid {BORDER}; border-radius:4px;
            outline:none;
        }}
    """


PORT_COMBO_CSS = f"""
    QComboBox{{background:{SURFACE};color:{TEXT};border:1px solid {BORDER};
              border-radius:4px;padding:4px 10px;
              font-family:{FONT};font-size:11px;min-height:20px;}}
    QComboBox:hover{{border-color:{TEXT_MUTED};}}
    QComboBox::drop-down{{border:none;width:18px;}}
    QComboBox QAbstractItemView{{background:{SURFACE};color:{TEXT};
        selection-background-color:{ELEVATED};
        font-family:{FONT};font-size:11px;
        border:1px solid {BORDER};}}
"""

# ── Palette ────────────────────────────────────────────────────────────────────


def apply_dark_palette(app):
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(BG))
    pal.setColor(QPalette.WindowText, QColor(TEXT))
    pal.setColor(QPalette.Base, QColor(SURFACE))
    pal.setColor(QPalette.Text, QColor(TEXT))
    pal.setColor(QPalette.Button, QColor(ELEVATED))
    pal.setColor(QPalette.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(pal)
