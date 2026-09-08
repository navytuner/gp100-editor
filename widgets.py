# widgets.py — Knob, Arrow, PedalCard

import math

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPen,
    QPolygon,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QListView,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from constants import BLOCK_COLORS, BLOCK_TYPES
from midi import GP100MIDI, get_type_controls
from style import (
    BORDER,
    ELEVATED,
    FONT,
    SURFACE,
    TEXT_DIM,
    TEXT_MUTED,
    faceplate_css,
    footswitch_css,
    pedal_combo_css,
    pedal_css,
)

# ══════════════════════════════════════════════════════════════════════════════
#  Knob
# ══════════════════════════════════════════════════════════════════════════════


class Knob(QWidget):
    valueChanged = Signal(float)

    START_ANGLE = 225
    SPAN = 270
    DRAG_PIXELS = 100  # pixels of drag for a full sweep

    def __init__(
        self,
        color: str = "#61AFEF",
        lo: float = 0.0,
        hi: float = 99.0,
        step: float = 1.0,
        parent=None,
    ):
        super().__init__(parent)
        self.color = QColor(color)
        self.lo = float(lo)
        self.hi = float(hi)
        self.step = float(step) or 1.0
        self._value = self.lo
        self._drag_y = None
        self._drag_val = None
        self.setFixedSize(54, 54)
        self.setCursor(Qt.SizeVerCursor)
        self.setToolTip("Drag up/down or scroll")

    def value(self) -> float:
        return self._value

    def setValue(self, v: float):
        v = self.lo + round((v - self.lo) / self.step) * self.step
        low, high = sorted((self.lo, self.hi))
        v = round(max(low, min(high, v)), 3)
        if v != self._value:
            self._value = v
            self.update()
            self.valueChanged.emit(v)

    def ratio(self) -> float:
        span = self.hi - self.lo
        if not span:
            return 0.0
        return max(0.0, min(1.0, (self._value - self.lo) / span))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_y = e.globalPosition().y()
            self._drag_val = self._value

    def mouseMoveEvent(self, e):
        if self._drag_y is None:
            return
        delta = self._drag_y - e.globalPosition().y()
        self.setValue(self._drag_val + delta * (self.hi - self.lo) / self.DRAG_PIXELS)

    def mouseReleaseEvent(self, _):
        self._drag_y = None

    def wheelEvent(self, e):
        d = math.copysign(self.step, self.hi - self.lo)
        self.setValue(self._value + (d if e.angleDelta().y() > 0 else -d))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        ro = min(w, h) / 2 - 2
        ri = ro - 5
        ratio = self.ratio()

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
        p.drawPolygon(
            QPolygon(
                [
                    QPoint(self.width() - 3, cy),
                    QPoint(self.width() - 10, cy - 4),
                    QPoint(self.width() - 10, cy + 4),
                ]
            )
        )
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
#  PedalCard
# ══════════════════════════════════════════════════════════════════════════════

PEDAL_WIDTH = 154


def fmt_value(control, value) -> str:
    """Render a control's value the way it should read next to the control."""
    if control.options:
        for label, val in control.options:
            if val == value:
                return label
        return str(value)
    return f"{value:.1f}" if control.step < 1 else f"{int(value)}"


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
        self._val_lbls: dict[int, QLabel] = {}

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
        self.footswitch = QPushButton("\u23fb  OFF")
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
        self.footswitch.setText("\u23fb  ON" if self.enabled else "\u23fb  OFF")
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

        controls = get_type_controls(self.block_name, type_name)
        knob_qcolor = QColor(self.color)
        if not self.enabled:
            knob_qcolor.setAlpha(100)

        for i, ctl in enumerate(controls):
            row_widget = QWidget()
            row_widget.setStyleSheet("background:transparent;")
            col = QVBoxLayout(row_widget)
            col.setSpacing(1)
            col.setContentsMargins(0, 2, 0, 2)

            # Label
            name_lbl = QLabel(ctl.name.upper())
            name_lbl.setStyleSheet(
                f"color:{TEXT_MUTED}; font-family:{FONT}; font-size:9px; letter-spacing:1px;"
            )
            col.addWidget(name_lbl)

            row = QHBoxLayout()
            row.setSpacing(6)
            row.setContentsMargins(0, 0, 0, 0)

            if ctl.kind == "knob":
                knob = Knob(color=knob_qcolor, lo=ctl.lo, hi=ctl.hi, step=ctl.step)
                knob.setValue(ctl.default)  # set before connecting, so it doesn't send
                knob.valueChanged.connect(lambda v, pid=i: self._on_param(pid, v))
                self.knobs.append(knob)

                val_lbl = QLabel(fmt_value(ctl, knob.value()))
                val_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                val_lbl.setFixedWidth(38)
                val_lbl.setStyleSheet(
                    f"color:{TEXT_DIM}; font-family:{FONT}; font-size:12px; font-weight:bold;"
                )
                self._val_lbls[i] = val_lbl

                row.addWidget(knob, alignment=Qt.AlignVCenter)
                row.addWidget(val_lbl, alignment=Qt.AlignVCenter)
            else:
                # switches and dropdowns are both option lists on the wire
                box = QComboBox()
                box.addItems([label for label, _ in ctl.options])
                box.setStyleSheet(pedal_combo_css(self.color))
                box.setView(QListView())
                box.setCurrentIndex(
                    next(
                        (n for n, (_, v) in enumerate(ctl.options) if v == ctl.default),
                        0,
                    )
                )
                box.currentIndexChanged.connect(
                    lambda n, pid=i, c=ctl: self._on_param(pid, c.options[n][1])
                )
                row.addWidget(box)

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

    def _on_param(self, param_id: int, value: float):
        tn = self.type_combo.currentText()
        controls = get_type_controls(self.block_name, tn)
        lbl = self._val_lbls.get(param_id)
        if lbl is not None and param_id < len(controls):
            lbl.setText(fmt_value(controls[param_id], value))
        if self.midi.connected:
            code = BLOCK_TYPES.get(self.block_name, {}).get(tn, 0)
            self.midi.set_parameter(self.block_name, param_id, value, code)
        self.log_signal.emit(f"{self.block_name} param[{param_id}]={value}")
