# midi.py — MIDI communication for GP-100

import struct

import rtmidi

from constants import (
    BLOCK_DEFAULT_PARAMS,
    BLOCK_TYPES,
    BLOCKS,
    HEADER,
    TYPE_CONTROLS,
    Control,
)


def get_type_controls(block_name: str, type_name: str) -> tuple[Control, ...]:
    controls = TYPE_CONTROLS.get((block_name, type_name))
    if controls is not None:
        return controls
    names = BLOCK_DEFAULT_PARAMS.get(block_name, ["P1", "P2", "P3"])
    return tuple(Control(n, default=50) for n in names)


def get_type_params(block_name: str, type_name: str) -> list[str]:
    return [c.name for c in get_type_controls(block_name, type_name)]


def nibbles(value: int, n_bytes: int) -> list[int]:
    out = []
    for i in range(n_bytes):
        b = (value >> (8 * i)) & 0xFF
        out += [b >> 4, b & 0xF]
    return out


def param_value(value: float) -> list[int]:
    """
    Encode a parameter value

    The device takes the top 16 bits of the IEEE-754 float32
    and splits them into four nibbles, low byte first, high nibble first within
    each byte:

        99.0 -> 0x42C6 -> [0x0C, 0x06, 0x04, 0x02]

    """
    hi, lo = struct.pack(">f", float(value))[:2]
    return nibbles((hi << 8) | lo, 2)


class GP100MIDI:
    def __init__(self):
        self.midi_out = None
        self.midi_in = None
        self.connected = False
        self.port_name = None

    def list_ports(self):
        tmp = rtmidi.MidiOut()
        ports = tmp.get_ports()
        del tmp
        return ports

    def connect(self, port_index):
        try:
            self.midi_out = rtmidi.MidiOut()
            self.midi_in = rtmidi.MidiIn()
            out_ports = self.midi_out.get_ports()
            in_ports = self.midi_in.get_ports()
            self.midi_out.open_port(port_index)
            for i, name in enumerate(in_ports):
                if out_ports[port_index].split(":")[0] in name:
                    self.midi_in.open_port(i)
                    self.midi_in.ignore_types(sysex=False)
                    break
            self.connected = True
            self.port_name = out_ports[port_index]
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def disconnect(self):
        if self.midi_out:
            self.midi_out.close_port()
        if self.midi_in:
            self.midi_in.close_port()
        self.connected = False

    def send_sysex(self, data):
        msg = HEADER + data + [0xF7]
        try:
            self.midi_out.send_message(msg)
        except Exception as e:
            print(f"Send error: {e}")

    def set_patch(self, patch_number: int):
        self.send_sysex(
            [
                0x00,
                0x02,
                0x00,
                0x00,
                0x00,
                0x00,  # TODO: support F(default patches), extending it to 0x01
                0x00,
                0x00,
            ]
            + nibbles(patch_number, 1)
            + [0x00, 0x00]
        )

    def set_block_enabled(self, block_name: str, enabled: bool):
        self.send_sysex(
            [0x10, BLOCKS[block_name], 0x00, 0x00] + nibbles(int(enabled), 2)
        )

    def set_block_type(self, block_name: str, type_name: str):
        code = BLOCK_TYPES[block_name][type_name]
        self.send_sysex([0x10, BLOCKS[block_name], 0x00, 0x01] + nibbles(code, 4))
        self.set_block_enabled(block_name, True)

    def set_parameter(self, block_name: str, param_id: int, value: float, code: int):
        data = [0x10, BLOCKS[block_name], 0x00, 0x02]
        data += nibbles(code, 4)
        data += nibbles(param_id, 4)
        data += param_value(value)
        self.send_sysex(data)
