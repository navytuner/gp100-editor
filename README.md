# GP-100 Editor

A desktop editor for the **Valeton GP-100** guitar multi-effects pedal. Communicates over MIDI to control patches, effect blocks, and parameters in real time.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Qt](https://img.shields.io/badge/GUI-PySide6-green)
![License](https://img.shields.io/badge/License-GPL--3.0-orange)

## Features

- **Signal chain view** — visual pedal board with PRE, DST, AMP, NR, CAB, EQ, MOD, DLY, RVB blocks
- **Knob controls** — adjust effect parameters with interactive knobs
- **Block type selection** — switch between effect types within each block
- **Patch switching** — select between 8 patches
- **MIDI auto-detection** — finds Valeton ports automatically
- **Activity log** — real-time MIDI event logging

## Requirements

- Python 3.10+
- A Valeton GP-100 connected via USB

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## License

This project is licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html).
