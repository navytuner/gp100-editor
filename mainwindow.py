# mainwindow.py — GP-100 Editor main window

import time

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QTextEdit,
    QScrollArea,
)
from PySide6.QtCore import Qt

from constants import BLOCKS
from midi import GP100MIDI
from widgets import PedalCard, Arrow
from style import (
    patch_css, conn_css, rgba, PORT_COMBO_CSS,
    BG, SURFACE, ELEVATED, BORDER, TEXT, TEXT_DIM, TEXT_MUTED, ACCENT, FONT,
)


class GP100Editor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.midi = GP100MIDI()
        self.setWindowTitle("Valeton GP-100 Editor")
        self.setMinimumSize(700, 480)
        self.resize(1720, 640)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._mk_header())
        root.addWidget(self._mk_patchbar())
        root.addWidget(self._mk_chain(), stretch=1)
        root.addWidget(self._mk_log())

        self._refresh_ports()

    # ── Header — brand + MIDI controls in one compact row ─────────

    def _mk_header(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(
            f"background:{SURFACE}; border-bottom:1px solid {BORDER};"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(10)

        # Brand
        dot = QLabel("\u25CF")
        dot.setStyleSheet(f"color:{ACCENT}; font-size:12px;")
        lay.addWidget(dot)

        title = QLabel("GP-100 EDITOR")
        title.setStyleSheet(
            f"color:{ACCENT}; font-family:{FONT};"
            "font-size:15px; font-weight:bold; letter-spacing:3px;"
        )
        lay.addWidget(title)

        lay.addStretch()

        # MIDI controls
        midi_lbl = QLabel("MIDI")
        midi_lbl.setStyleSheet(
            f"color:{TEXT_MUTED}; font-family:{FONT}; font-size:10px; letter-spacing:2px;"
        )
        lay.addWidget(midi_lbl)

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(240)
        self.port_combo.setStyleSheet(PORT_COMBO_CSS)
        lay.addWidget(self.port_combo)

        ref_btn = QPushButton("\u21BB")
        ref_btn.setFixedSize(28, 28)
        ref_btn.setStyleSheet(
            f"QPushButton{{background:{ELEVATED};color:{TEXT_DIM};border:1px solid {BORDER};"
            f"border-radius:4px;font-size:14px;}}"
            f"QPushButton:hover{{background:#3A3C52;color:{TEXT};}}"
        )
        ref_btn.setToolTip("Refresh MIDI ports")
        ref_btn.clicked.connect(self._refresh_ports)
        lay.addWidget(ref_btn)

        self.conn_btn = QPushButton("CONNECT")
        self.conn_btn.setStyleSheet(conn_css(False))
        self.conn_btn.clicked.connect(self._toggle_connect)
        lay.addWidget(self.conn_btn)

        self.status_dot = QLabel("\u25CF")
        self.status_dot.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px;")
        lay.addWidget(self.status_dot)

        self.status_lbl = QLabel("OFFLINE")
        self.status_lbl.setStyleSheet(
            f"color:{TEXT_MUTED}; font-family:{FONT}; font-size:10px; letter-spacing:1px;"
        )
        lay.addWidget(self.status_lbl)

        return bar

    # ── Patch bar ─────────────────────────────────────────────────

    def _mk_patchbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(40)
        bar.setStyleSheet(f"background:{BG}; border-bottom:1px solid {rgba(BORDER, 0.19)};")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(5)

        lbl = QLabel("PATCH")
        lbl.setStyleSheet(
            f"color:{ACCENT}; font-family:{FONT};"
            "font-size:10px; letter-spacing:3px; margin-right:6px;"
        )
        lay.addWidget(lbl)

        self.patch_btns: list[QPushButton] = []
        for i in range(8):
            btn = QPushButton(str(i + 1))
            btn.setStyleSheet(patch_css(i == 0))
            btn.clicked.connect(lambda _, idx=i: self._send_patch(idx))
            self.patch_btns.append(btn)
            lay.addWidget(btn)

        lay.addStretch()
        return bar

    # ── Pedal chain ───────────────────────────────────────────────

    def _mk_chain(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea{{border:none;background:{BG};}}")

        container = QWidget()
        container.setStyleSheet(f"background:{BG};")
        lay = QHBoxLayout(container)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.pedal_cards: dict[str, PedalCard] = {}
        names = list(BLOCKS.keys())

        for i, name in enumerate(names):
            card = PedalCard(name, self.midi)
            card.log_signal.connect(self._log)
            lay.addWidget(card)
            self.pedal_cards[name] = card
            if i < len(names) - 1:
                arrow = Arrow()
                lay.addWidget(arrow, alignment=Qt.AlignVCenter)

        lay.addStretch()
        scroll.setWidget(container)
        return scroll

    # ── Log ───────────────────────────────────────────────────────

    def _mk_log(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(80)
        w.setStyleSheet(f"background:{BG}; border-top:1px solid {rgba(BORDER, 0.19)};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 4, 16, 6)
        lay.setSpacing(2)

        hdr = QHBoxLayout()
        lbl = QLabel("LOG")
        lbl.setStyleSheet(
            f"color:{TEXT_MUTED}; font-family:{FONT}; font-size:9px; letter-spacing:3px;"
        )
        hdr.addWidget(lbl)
        hdr.addStretch()

        clr_btn = QPushButton("CLEAR")
        clr_btn.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;color:{TEXT_MUTED};"
            f"font-family:{FONT};font-size:9px;letter-spacing:1px;}}"
            f"QPushButton:hover{{color:{TEXT_DIM};}}"
        )
        clr_btn.clicked.connect(lambda: self.log_text.clear())
        hdr.addWidget(clr_btn)
        lay.addLayout(hdr)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("log")
        self.log_text.setReadOnly(True)
        self.log_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lay.addWidget(self.log_text)
        return w

    # ── Helpers ───────────────────────────────────────────────────

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{ts}]  {msg}")
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _refresh_ports(self):
        ports = self.midi.list_ports()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        if ports:
            for i, p in enumerate(ports):
                if any(k in p for k in ("GP", "Valeton", "valeton")):
                    self.port_combo.setCurrentIndex(i)
                    return
            self.port_combo.setCurrentIndex(0)

    def _toggle_connect(self):
        if self.midi.connected:
            self.midi.disconnect()
            self.conn_btn.setText("CONNECT")
            self.conn_btn.setStyleSheet(conn_css(False))
            self.status_dot.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px;")
            self.status_lbl.setStyleSheet(
                f"color:{TEXT_MUTED}; font-family:{FONT}; font-size:10px;"
            )
            self.status_lbl.setText("OFFLINE")
        else:
            idx = self.port_combo.currentIndex()
            if idx < 0:
                self._log("No MIDI port selected")
                return
            if self.midi.connect(idx):
                self.conn_btn.setText("DISCONNECT")
                self.conn_btn.setStyleSheet(conn_css(True))
                self.status_dot.setStyleSheet("color:#3D9; font-size:10px;")
                self.status_lbl.setStyleSheet(
                    f"color:#3D9; font-family:{FONT}; font-size:10px;"
                )
                self.status_lbl.setText(self.midi.port_name[:30])
                self._log(f"Connected -> {self.midi.port_name}")
            else:
                self._log("Failed to connect")

    def _send_patch(self, idx: int):
        for i, btn in enumerate(self.patch_btns):
            btn.setStyleSheet(patch_css(i == idx))
        if self.midi.connected:
            self.midi.set_patch(idx)
        self._log(f"Patch -> {idx + 1}")
