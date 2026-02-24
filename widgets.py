# widgets.py — Custom Qt widgets: Knob, Arrow, BlockCard

import math

from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QSizePolicy,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QBrush,
    QRadialGradient,
    QPolygon,
)

from constants import BLOCK_COLORS, BLOCK_TYPES, PARAM_NAMES
from midi import GP100MIDI
from style import card_css, led_css, knob_combo_css


# ══════════════════════════════════════════════════════════════════════════════
#  Knob — drag up/down to change value
# ══════════════════════════════════════════════════════════════════════════════


class Knob(QWidget):
    valueChanged = Signal(int)

    START_ANGLE = 225  # 7 o'clock position (degrees)
    SPAN = 270  # total clockwise sweep (degrees)
    SENSITIVITY = 1.0  # pixels per 1 unit; lower = more sensitive

    def __init__(self, color: str = "#00D4FF", parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self._value = 50
        self._drag_y = None
        self._drag_val = None
        self.setFixedSize(58, 58)
        self.setCursor(Qt.SizeVerCursor)
        self.setToolTip("Drag up/down or use scroll wheel")

    # ── Value ──────────────────────────────────────────────────────

    def value(self) -> int:
        return self._value

    def setValue(self, v: int):
        v = max(0, min(99, int(v)))
        if v != self._value:
            self._value = v
            self.update()
            self.valueChanged.emit(v)

    # ── Mouse / wheel ──────────────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_y = e.globalPosition().y()
            self._drag_val = self._value

    def mouseMoveEvent(self, e):
        if self._drag_y is None:
            return
        delta = self._drag_y - e.globalPosition().y()  # up = increase
        self.setValue(self._drag_val + int(delta / self.SENSITIVITY))

    def mouseReleaseEvent(self, _):
        self._drag_y = None

    def wheelEvent(self, e):
        self.setValue(self._value + (1 if e.angleDelta().y() > 0 else -1))

    # ── Paint ──────────────────────────────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        ro = min(w, h) / 2 - 2  # outer arc radius
        ri = ro - 6  # inner knob body radius
        ratio = self._value / 99.0

        # background track arc
        p.setPen(QPen(QColor("#1A1A30"), 4, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(
            QRect(int(cx - ro), int(cy - ro), int(ro * 2), int(ro * 2)),
            int((90 + (360 - self.START_ANGLE)) * 16),
            int(-self.SPAN * 16),
        )

        # value arc
        if ratio > 0:
            p.setPen(QPen(self.color, 4, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(
                QRect(int(cx - ro), int(cy - ro), int(ro * 2), int(ro * 2)),
                int((90 + (360 - self.START_ANGLE)) * 16),
                int(-self.SPAN * ratio * 16),
            )

        # knob body with radial gradient
        grad = QRadialGradient(cx - ri * 0.25, cy - ri * 0.25, ri)
        grad.setColorAt(0, QColor("#2C2C44"))
        grad.setColorAt(1, QColor("#0C0C16"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QRect(int(cx - ri), int(cy - ri), int(ri * 2), int(ri * 2)))

        # indicator dot
        angle_rad = math.radians(self.START_ANGLE - ratio * self.SPAN)
        dist = ri * 0.58
        dx = cx + dist * math.cos(angle_rad)
        dy = cy - dist * math.sin(angle_rad)
        p.setBrush(QBrush(self.color))
        p.drawEllipse(QRect(int(dx - 2), int(dy - 2), 5, 5))

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
#  Arrow — signal-flow connector between blocks
# ══════════════════════════════════════════════════════════════════════════════


class Arrow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 30)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx = self.width() // 2
        cy = self.height() // 2

        p.setPen(QPen(QColor("#2A2A45"), 1, Qt.DotLine))
        p.drawLine(cx, 0, cx, cy - 5)
        p.drawLine(cx, cy + 5, cx, self.height())

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#2A2A45")))
        p.drawPolygon(
            QPolygon(
                [
                    QPoint(cx, cy + 6),
                    QPoint(cx - 5, cy - 3),
                    QPoint(cx + 5, cy - 3),
                ]
            )
        )
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
#  BlockCard — single effect block card, fixed size
# ══════════════════════════════════════════════════════════════════════════════

CARD_WIDTH = 148
CARD_HEIGHT = 400  # fixed card height; inner scroll if content overflows

# Max visible items in the type dropdown before it scrolls
COMBO_MAX_VISIBLE = 4


class BlockCard(QFrame):
    log_signal = Signal(str)

    def __init__(self, block_name: str, midi: GP100MIDI, parent=None):
        super().__init__(parent)
        self.block_name = block_name
        self.midi = midi
        self.color = BLOCK_COLORS[block_name]
        self.enabled = False

        self.setObjectName("BlockCard")
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._apply_card_style(False)
        self._build()

    # ── Style helpers ──────────────────────────────────────────────

    def _apply_card_style(self, active: bool):
        self.setStyleSheet(card_css(self.color, active))

    def _apply_led_style(self, active: bool):
        self.led.setStyleSheet(led_css(self.color, active))

    # ── Build ──────────────────────────────────────────────────────

    def _build(self):
        # Outer layout: fixed header + scrollable knob area
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header section (always visible, outside scroll)
        header_widget = QWidget()
        header_widget.setStyleSheet("background:transparent;")
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 8, 10, 6)
        header_layout.setSpacing(5)
        header_layout.addLayout(self._make_header())
        header_layout.addWidget(self._make_divider())
        header_layout.addWidget(self._make_type_combo())
        outer.addWidget(header_widget)

        # Scrollable knob section
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            """
            QScrollArea { border:none; background:transparent; }
            QScrollArea > QWidget > QWidget { background:transparent; }
        """
        )

        knob_container = QWidget()
        knob_container.setStyleSheet("background:transparent;")
        knob_layout = QVBoxLayout(knob_container)
        knob_layout.setContentsMargins(10, 6, 10, 10)
        knob_layout.setSpacing(8)
        knob_layout.setAlignment(Qt.AlignTop)

        self.knobs: list[Knob] = []
        self._val_lbls: list[QLabel] = []
        for i, pname in enumerate(PARAM_NAMES.get(self.block_name, ["P1", "P2", "P3"])):
            knob_layout.addLayout(self._make_knob_row(i, pname))

        scroll.setWidget(knob_container)
        outer.addWidget(scroll, stretch=1)

    def _make_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()
        hdr.setSpacing(4)

        name_lbl = QLabel(self.block_name)
        name_lbl.setStyleSheet(
            f"color:{self.color}; font-family:'Courier New'; "
            "font-size:14px; font-weight:bold; letter-spacing:2px;"
        )
        hdr.addWidget(name_lbl)
        hdr.addStretch()

        self.led = QPushButton("○")
        self.led.setFixedSize(22, 22)
        self._apply_led_style(False)
        self.led.clicked.connect(self._toggle)
        hdr.addWidget(self.led)
        return hdr

    def _make_divider(self) -> QFrame:
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background:{self.color}25;")
        return div

    def _make_type_combo(self) -> QComboBox:
        self.type_combo = QComboBox()
        self.type_combo.addItems(list(BLOCK_TYPES[self.block_name].keys()))
        self.type_combo.setStyleSheet(knob_combo_css(self.color))
        # Cap visible rows so the dropdown scrolls instead of growing unbounded
        self.type_combo.setMaxVisibleItems(COMBO_MAX_VISIBLE)
        self.type_combo.currentTextChanged.connect(self._send_type)
        return self.type_combo

    def _make_knob_row(self, param_id: int, pname: str) -> QVBoxLayout:
        """One parameter row: label on top, then knob + value side by side."""
        col = QVBoxLayout()
        col.setSpacing(3)
        col.setContentsMargins(0, 0, 0, 0)

        # Parameter name label
        name_lbl = QLabel(pname.upper())
        name_lbl.setAlignment(Qt.AlignLeft)
        name_lbl.setStyleSheet(
            "color:#484868; font-family:'Courier New'; font-size:9px; letter-spacing:1px;"
        )
        col.addWidget(name_lbl)

        # Knob + value display side by side
        row = QHBoxLayout()
        row.setSpacing(8)
        row.setContentsMargins(0, 0, 0, 0)

        knob = Knob(color=self.color)
        knob.setValue(50)
        knob.valueChanged.connect(lambda v, pid=param_id: self._on_knob(pid, v))
        self.knobs.append(knob)

        val_lbl = QLabel("50")
        val_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        val_lbl.setFixedWidth(30)
        val_lbl.setStyleSheet(
            f"color:{self.color}; font-family:'Courier New'; font-size:13px; font-weight:bold;"
        )
        self._val_lbls.append(val_lbl)

        row.addWidget(knob, alignment=Qt.AlignVCenter)
        row.addWidget(val_lbl, alignment=Qt.AlignVCenter)
        row.addStretch()
        col.addLayout(row)

        # Thin separator line
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{self.color}12;")
        col.addWidget(sep)

        return col

    # ── Slots ──────────────────────────────────────────────────────

    def _toggle(self):
        self.enabled = not self.enabled
        self.led.setText("●" if self.enabled else "○")
        self._apply_led_style(self.enabled)
        self._apply_card_style(self.enabled)
        if self.midi.connected:
            self.midi.set_block_enabled(self.block_name, self.enabled)
        self.log_signal.emit(f"{self.block_name} -> {'ON' if self.enabled else 'OFF'}")

    def _send_type(self, type_name: str):
        if self.midi.connected and type_name:
            self.midi.set_block_type(self.block_name, type_name)
        self.log_signal.emit(f"{self.block_name} type -> {type_name}")

    def _on_knob(self, param_id: int, value: int):
        self._val_lbls[param_id].setText(str(value))
        if self.midi.connected:
            tn = self.type_combo.currentText()
            tup = BLOCK_TYPES[self.block_name].get(tn, (0x00, 0x00, 0x00))
            self.midi.set_parameter(self.block_name, param_id, value, tup[0], tup[1])
        self.log_signal.emit(f"{self.block_name} param[{param_id}]={value}")
