# style.py — Qt stylesheets and palette for GP-100 Editor

from PySide6.QtGui import QColor, QPalette

# ── Global stylesheet ──────────────────────────────────────────────────────────

GLOBAL_CSS = """
QMainWindow, QWidget { background:#0D0D14; color:#C0C0D8; }

QScrollBar:horizontal { background:#0D0D14; height:6px; border:none; }
QScrollBar::handle:horizontal { background:#2A2A45; border-radius:3px; min-width:30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0; }

QScrollBar:vertical { background:#0D0D14; width:5px; border:none; }
QScrollBar::handle:vertical { background:#2A2A45; border-radius:2px; min-height:20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }

QTextEdit#log {
    background:#080810; color:#00CC66;
    border:1px solid #1A1A2E; border-radius:4px;
    font-family:'Courier New'; font-size:11px; padding:3px;
}
"""

# ── Per-state CSS helpers ──────────────────────────────────────────────────────


def patch_css(active: bool) -> str:
    bg, fg, bd, hv = (
        ("#E94560", "white", "#E94560", "#FF5577")
        if active
        else ("#1A1A2E", "#606080", "#2A2A45", "#222240")
    )
    return (
        f"QPushButton{{background:{bg};color:{fg};border:1px solid {bd};"
        f"border-radius:4px;padding:4px 11px;font-family:'Courier New';"
        f"font-size:13px;font-weight:bold;min-width:32px;}}"
        f"QPushButton:hover{{background:{hv};color:white;}}"
    )


def conn_css(connected: bool) -> str:
    bg, hv = ("#27AE60", "#2ECC71") if connected else ("#E94560", "#FF5577")
    return (
        f"QPushButton{{background:{bg};color:white;border:none;"
        f"border-radius:4px;padding:6px 18px;"
        f"font-family:'Courier New';font-size:11px;font-weight:bold;}}"
        f"QPushButton:hover{{background:{hv};}}"
    )


def card_css(color: str, active: bool) -> str:
    if active:
        return f"""
            QFrame#BlockCard {{
                background:#14142A;
                border:1px solid {color}50;
                border-top:3px solid {color};
                border-radius:8px;
            }}
        """
    return f"""
        QFrame#BlockCard {{
            background:#111120;
            border:1px solid #1C1C30;
            border-top:3px solid {color}28;
            border-radius:8px;
        }}
    """


def led_css(color: str, active: bool) -> str:
    c = color if active else "#2A2A45"
    return (
        f"QPushButton{{background:transparent;border:none;"
        f"color:{c};font-size:16px;padding:0;}}"
        f"QPushButton:hover{{color:{color}99;}}"
    )


def knob_combo_css(color: str) -> str:
    """
    Dropdown list height is capped at ~120px so it scrolls
    instead of expanding the card when there are many items.
    """
    return f"""
        QComboBox {{
            background:#181828; color:#A0A0C0;
            border:1px solid {color}38;
            border-radius:3px; padding:2px 6px;
            font-family:'Courier New'; font-size:10px; min-height:20px;
        }}
        QComboBox:hover {{ border-color:{color}66; color:#C8C8E0; }}
        QComboBox::drop-down {{ border:none; width:14px; }}
        QComboBox QAbstractItemView {{
            background:#181828; color:#A0A0C0;
            selection-background-color:#252545;
            font-family:'Courier New'; font-size:10px;
            max-height:120px;
        }}
    """


PORT_COMBO_CSS = """
    QComboBox{background:#14142A;color:#9090B8;border:1px solid #252545;
              border-radius:4px;padding:3px 10px;
              font-family:'Courier New';font-size:11px;min-height:22px;}
    QComboBox:hover{border-color:#353560;}
    QComboBox::drop-down{border:none;width:18px;}
    QComboBox QAbstractItemView{background:#14142A;color:#9090B8;
        selection-background-color:#252545;
        font-family:'Courier New';font-size:11px;
        max-height:160px;}
"""

# ── Palette ────────────────────────────────────────────────────────────────────


def apply_dark_palette(app):
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor("#0D0D14"))
    pal.setColor(QPalette.WindowText, QColor("#C0C0D8"))
    pal.setColor(QPalette.Base, QColor("#12121E"))
    pal.setColor(QPalette.Text, QColor("#C0C0D8"))
    pal.setColor(QPalette.Button, QColor("#1A1A2E"))
    pal.setColor(QPalette.ButtonText, QColor("#C0C0D8"))
    pal.setColor(QPalette.Highlight, QColor("#E94560"))
    pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(pal)
