# widgets.py — Knob, Arrow, PedalCard

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
    QListView,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QBrush,
    QRadialGradient,
    QPolygon,
)

from constants import BLOCK_COLORS, BLOCK_TYPES, get_type_params
from midi import GP100MIDI
from style import (
    pedal_css, faceplate_css, footswitch_css, pedal_combo_css,
    SURFACE, ELEVATED, BORDER, TEXT_DIM, TEXT_MUTED, FONT,
)


# ══════════════════════════════════════════════════════════════════════════════
#  Knob
# ══════════════════════════════════════════════════════════════════════════════


class Knob(QWidget):
    valueChanged = Signal(int)

    START_ANGLE = 225
    SPAN = 270
    SENSITIVITY = 1.0

    def __init__(self, color: str = "#61AFEF", parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self._value = 50
        self._drag_y = None
        self._drag_val = None
        self.setFixedSize(54, 54)
        self.setCursor(Qt.SizeVerCursor)
        self.setToolTip("Drag up/down or scroll")

    def value(self) -> int:
        return self._value

    def setValue(self, v: int):
        v = max(0, min(99, int(v)))
        if v != self._value:
            self._value = v
            self.update()
            self.valueChanged.emit(v)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_y = e.globalPosition().y()
            self._drag_val = self._value

    def mouseMoveEvent(self, e):
        if self._drag_y is None:
            return
        delta = self._drag_y - e.globalPosition().y()
        self.setValue(self._drag_val + int(delta / self.SENSITIVITY))

    def mouseReleaseEvent(self, _):
        self._drag_y = None

    def wheelEvent(self, e):
        self.setValue(self._value + (1 if e.angleDelta().y() > 0 else -1))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        ro = min(w, h) / 2 - 2
        ri = ro - 5
        ratio = self._value / 99.0

        # Track
        p.setPen(QPen(QColor(BORDER), 3.5, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(
            QRect(int(cx - ro), int(cy - ro), int(ro * 2), int(ro * 2)),
            int((90 + (360 - self.START_ANGLE)) * 16),
            int(-self.SPAN * 16),
        )

        # Value arc
        if ratio > 0:
            p.setPen(QPen(self.color, 3.5, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(
                QRect(int(cx - ro), int(cy - ro), int(ro * 2), int(ro * 2)),
                int((90 + (360 - self.START_ANGLE)) * 16),
                int(-self.SPAN * ratio * 16),
            )

        # Body
        grad = QRadialGradient(cx - ri * 0.2, cy - ri * 0.2, ri)
        grad.setColorAt(0, QColor(ELEVATED))
        grad.setColorAt(1, QColor(SURFACE))
        p.setPen(QPen(QColor(BORDER), 0.5))
        p.setBrush(QBrush(grad))
        p.drawEllipse(QRect(int(cx - ri), int(cy - ri), int(ri * 2), int(ri * 2)))

        # Indicator
        angle_rad = math.radians(self.START_ANGLE - ratio * self.SPAN)
        dist = ri * 0.55
        dx = cx + dist * math.cos(angle_rad)
        dy = cy - dist * math.sin(angle_rad)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(self.color))
        p.drawEllipse(QRect(int(dx - 3), int(dy - 3), 6, 6))

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
#  Arrow
# ══════════════════════════════════════════════════════════════════════════════


class Arrow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 30)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cy = self.height() // 2

        p.setPen(QPen(QColor(TEXT_MUTED), 1.5))
        p.drawLine(2, cy, self.width() - 9, cy)

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(TEXT_MUTED)))
        p.drawPolygon(QPolygon([
            QPoint(self.width() - 3, cy),
            QPoint(self.width() - 10, cy - 4),
            QPoint(self.width() - 10, cy + 4),
        ]))
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
#  PedalCard
# ══════════════════════════════════════════════════════════════════════════════

PEDAL_WIDTH = 154


class PedalCard(QFrame):
    log_signal = Signal(str)

    def __init__(self, block_name: str, midi: GP100MIDI, parent=None):
        super().__init__(parent)
        self.block_name = block_name
        self.midi = midi
        self.color = BLOCK_COLORS[block_name]
        self.enabled = False

        self.setObjectName("PedalCard")
        self.setFixedWidth(PEDAL_WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self.knobs: list[Knob] = []
        self._val_lbls: list[QLabel] = []

        self._build()
        self._apply_state()

    # ── Build ──────────────────────────────────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Faceplate
        self.faceplate = QLabel(self.block_name)
        self.faceplate.setFixedHeight(30)
        self.faceplate.setAlignment(Qt.AlignCenter)
        outer.addWidget(self.faceplate)

        # Body area
        body = QWidget()
        body.setStyleSheet("background:transparent;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(8, 6, 8, 8)
        body_lay.setSpacing(6)

        # Type combo
        self.type_combo = QComboBox()
        self.type_combo.addItems(list(BLOCK_TYPES.get(self.block_name, {}).keys()))
        self.type_combo.setStyleSheet(pedal_combo_css(self.color))
        self.type_combo.setView(QListView())
        self.type_combo.setMaxVisibleItems(8)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        body_lay.addWidget(self.type_combo)

        # Knob scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea{border:none;background:transparent;}"
            "QScrollArea>QWidget>QWidget{background:transparent;}"
        )

        self._knob_container = QWidget()
        self._knob_container.setStyleSheet("background:transparent;")
        self._knob_layout = QVBoxLayout(self._knob_container)
        self._knob_layout.setContentsMargins(2, 0, 2, 0)
        self._knob_layout.setSpacing(2)
        self._knob_layout.setAlignment(Qt.AlignTop)

        types = list(BLOCK_TYPES.get(self.block_name, {}).keys())
        if types:
            self._rebuild_knobs(types[0])

        scroll.setWidget(self._knob_container)
        body_lay.addWidget(scroll, stretch=1)

        # Footswitch
        self.footswitch = QPushButton("\u23FB  OFF")
        self.footswitch.setFixedHeight(34)
        self.footswitch.clicked.connect(self._toggle)
        body_lay.addWidget(self.footswitch)

        outer.addWidget(body, stretch=1)

        # Drop shadow (initially off)
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(20)
        self._shadow.setOffset(0, 0)
        self._shadow.setColor(QColor(self.color))
        self._shadow.setEnabled(False)
        self.setGraphicsEffect(self._shadow)

    # ── State ──────────────────────────────────────────────────────

    def _apply_state(self):
        self.setStyleSheet(pedal_css(self.color, self.enabled))
        self.faceplate.setStyleSheet(faceplate_css(self.color, self.enabled))
        self.footswitch.setStyleSheet(footswitch_css(self.color, self.enabled))
        self.footswitch.setText("\u23FB  ON" if self.enabled else "\u23FB  OFF")
        self._shadow.setEnabled(self.enabled)

        # Update knob colors — use block's own color, dimmed when OFF
        for knob in self.knobs:
            c = QColor(self.color)
            if not self.enabled:
                c.setAlpha(100)
            knob.color = c
            knob.update()

    # ── Knobs ──────────────────────────────────────────────────────

    def _rebuild_knobs(self, type_name: str):
        self.knobs.clear()
        self._val_lbls.clear()
        while self._knob_layout.count():
            item = self._knob_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not type_name:
            return

        params = get_type_params(self.block_name, type_name)
        knob_qcolor = QColor(self.color)
        if not self.enabled:
            knob_qcolor.setAlpha(100)

        for i, pname in enumerate(params):
            row_widget = QWidget()
            row_widget.setStyleSheet("background:transparent;")
            col = QVBoxLayout(row_widget)
            col.setSpacing(1)
            col.setContentsMargins(0, 2, 0, 2)

            # Label
            name_lbl = QLabel(pname.upper())
            name_lbl.setStyleSheet(
                f"color:{TEXT_MUTED}; font-family:{FONT}; font-size:9px; letter-spacing:1px;"
            )
            col.addWidget(name_lbl)

            # Knob + value
            row = QHBoxLayout()
            row.setSpacing(6)
            row.setContentsMargins(0, 0, 0, 0)

            knob = Knob(color=knob_qcolor)
            knob.setValue(50)
            knob.valueChanged.connect(lambda v, pid=i: self._on_knob(pid, v))
            self.knobs.append(knob)

            val_lbl = QLabel("50")
            val_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            val_lbl.setFixedWidth(28)
            val_lbl.setStyleSheet(
                f"color:{TEXT_DIM}; font-family:{FONT}; font-size:12px; font-weight:bold;"
            )
            self._val_lbls.append(val_lbl)

            row.addWidget(knob, alignment=Qt.AlignVCenter)
            row.addWidget(val_lbl, alignment=Qt.AlignVCenter)
            row.addStretch()
            col.addLayout(row)

            self._knob_layout.addWidget(row_widget)

    # ── Slots ──────────────────────────────────────────────────────

    def _toggle(self):
        self.enabled = not self.enabled
        self._apply_state()
        if self.midi.connected:
            self.midi.set_block_enabled(self.block_name, self.enabled)
        self.log_signal.emit(f"{self.block_name} -> {'ON' if self.enabled else 'OFF'}")

    def _on_type_changed(self, type_name: str):
        if not type_name:
            return
        self._rebuild_knobs(type_name)
        if self.midi.connected:
            self.midi.set_block_type(self.block_name, type_name)
        self.log_signal.emit(f"{self.block_name} type -> {type_name}")

    def _on_knob(self, param_id: int, value: int):
        if param_id < len(self._val_lbls):
            self._val_lbls[param_id].setText(str(value))
        if self.midi.connected:
            tn = self.type_combo.currentText()
            type_tup = BLOCK_TYPES.get(self.block_name, {}).get(tn, (0x00, 0x00, 0x00))
            self.midi.set_parameter(self.block_name, param_id, value, type_tup)
        self.log_signal.emit(f"{self.block_name} param[{param_id}]={value}")
