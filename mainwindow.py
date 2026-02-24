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
from widgets import BlockCard, Arrow
from style import GLOBAL_CSS, patch_css, conn_css, PORT_COMBO_CSS


class GP100Editor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.midi = GP100MIDI()
        self.setWindowTitle("Valeton GP-100 Editor")
        self.setMinimumSize(600, 520)
        self.resize(1400, 660)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._mk_titlebar())
        root.addWidget(self._mk_connbar())
        root.addWidget(self._mk_patchbar())
        root.addWidget(self._mk_chain(), stretch=1)
        root.addWidget(self._mk_log())

        self._refresh_ports()

    # ── Title bar ──────────────────────────────────────────────────

    def _mk_titlebar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(
            """
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #0D0D14, stop:0.5 #131320, stop:1 #0D0D14);
            border-bottom:1px solid #191928;
        """
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)

        for txt, css in [
            ("●", "color:#E94560;font-size:14px;"),
            (
                "VALETON GP-100",
                "color:#E94560;font-family:'Courier New';"
                "font-size:20px;font-weight:bold;letter-spacing:4px;margin-left:6px;",
            ),
            (
                "/ PATCH EDITOR",
                "color:#222240;font-family:'Courier New';"
                "font-size:12px;letter-spacing:2px;margin-left:10px;",
            ),
        ]:
            lbl = QLabel(txt)
            lbl.setStyleSheet(css)
            lay.addWidget(lbl)

        lay.addStretch()
        ver = QLabel("PySide6  v2.1")
        ver.setStyleSheet("color:#1A1A30;font-family:'Courier New';font-size:10px;")
        lay.addWidget(ver)
        return bar

    # ── MIDI connection bar ────────────────────────────────────────

    def _mk_connbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(50)
        bar.setStyleSheet("background:#0E0E18;border-bottom:1px solid #161626;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(10)

        lbl = QLabel("MIDI PORT")
        lbl.setStyleSheet(
            "color:#2C2C48;font-family:'Courier New';font-size:11px;letter-spacing:2px;"
        )
        lay.addWidget(lbl)

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(260)
        self.port_combo.setStyleSheet(PORT_COMBO_CSS)
        lay.addWidget(self.port_combo)

        ref_btn = QPushButton("↺ REFRESH")
        ref_btn.setStyleSheet(
            "QPushButton{background:#181828;color:#555570;border:1px solid #252545;"
            "border-radius:4px;padding:5px 14px;font-family:'Courier New';font-size:11px;}"
            "QPushButton:hover{color:#A0A0C0;}"
        )
        ref_btn.clicked.connect(self._refresh_ports)
        lay.addWidget(ref_btn)

        self.conn_btn = QPushButton("CONNECT")
        self.conn_btn.setStyleSheet(conn_css(False))
        self.conn_btn.clicked.connect(self._toggle_connect)
        lay.addWidget(self.conn_btn)

        lay.addStretch()

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color:#222240;font-size:12px;")
        self.status_lbl = QLabel("DISCONNECTED")
        self.status_lbl.setStyleSheet(
            "color:#222240;font-family:'Courier New';font-size:11px;letter-spacing:2px;"
        )
        lay.addWidget(self.status_dot)
        lay.addWidget(self.status_lbl)
        return bar

    # ── Patch selector bar ─────────────────────────────────────────

    def _mk_patchbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(46)
        bar.setStyleSheet("background:#0C0C18;border-bottom:1px solid #131320;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(6)

        lbl = QLabel("PATCH")
        lbl.setStyleSheet(
            "color:#E94560;font-family:'Courier New';"
            "font-size:11px;letter-spacing:3px;margin-right:8px;"
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

    # ── Horizontal effect chain ────────────────────────────────────

    def _mk_chain(self) -> QScrollArea:
        """Blocks laid out left-to-right with arrow connectors between them."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{border:none;background:#0D0D14;}")

        container = QWidget()
        container.setStyleSheet("background:#0D0D14;")
        lay = QHBoxLayout(container)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.block_cards: dict[str, BlockCard] = {}
        names = list(BLOCKS.keys())

        for i, name in enumerate(names):
            card = BlockCard(name, self.midi)
            card.log_signal.connect(self._log)
            lay.addWidget(card)
            self.block_cards[name] = card
            if i < len(names) - 1:
                lay.addWidget(Arrow())

        lay.addStretch()
        scroll.setWidget(container)
        return scroll

    # ── SysEx log panel ────────────────────────────────────────────

    def _mk_log(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(88)
        w.setStyleSheet("background:#080912;border-top:1px solid #121220;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 4, 16, 4)
        lay.setSpacing(2)

        hdr = QHBoxLayout()
        lbl = QLabel("SYSEX LOG")
        lbl.setStyleSheet(
            "color:#202035;font-family:'Courier New';font-size:10px;letter-spacing:3px;"
        )
        hdr.addWidget(lbl)
        hdr.addStretch()

        clr_btn = QPushButton("CLEAR")
        clr_btn.setStyleSheet(
            "QPushButton{background:transparent;border:none;color:#202035;"
            "font-family:'Courier New';font-size:10px;}"
            "QPushButton:hover{color:#505070;}"
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

    # ── Helpers ────────────────────────────────────────────────────

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
            self.status_dot.setStyleSheet("color:#222240;font-size:12px;")
            self.status_lbl.setStyleSheet(
                "color:#222240;font-family:'Courier New';font-size:11px;"
            )
            self.status_lbl.setText("DISCONNECTED")
        else:
            idx = self.port_combo.currentIndex()
            if idx < 0:
                self._log("ERROR: No MIDI port selected")
                return
            if self.midi.connect(idx):
                self.conn_btn.setText("DISCONNECT")
                self.conn_btn.setStyleSheet(conn_css(True))
                self.status_dot.setStyleSheet("color:#2ECC71;font-size:12px;")
                self.status_lbl.setStyleSheet(
                    "color:#2ECC71;font-family:'Courier New';font-size:11px;"
                )
                self.status_lbl.setText(self.midi.port_name[:36])
                self._log(f"Connected -> {self.midi.port_name}")
            else:
                self._log("ERROR: Failed to connect")

    def _send_patch(self, idx: int):
        for i, btn in enumerate(self.patch_btns):
            btn.setStyleSheet(patch_css(i == idx))
        if self.midi.connected:
            self.midi.set_patch(idx)
        self._log(f"Patch -> {idx + 1}")
