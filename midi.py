# midi.py — MIDI communication for GP-100

import rtmidi
from constants import HEADER, BLOCKS, BLOCK_TYPES, PARAM_VALUE


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

    def set_block_enabled(self, block_name, enabled):
        block_id = BLOCKS[block_name]
        data = [
            0x10,
            block_id,
            0x00,
            0x00,
            0x00,
            0x01 if enabled else 0x00,
            0x00,
            0x00,
            0x00,
        ]
        self.send_sysex(data)

    def set_block_type(self, block_name, type_name):
        block_id = BLOCKS[block_name]
        type_tup = BLOCK_TYPES[block_name][type_name]
        headers = [
            [
                0x00,
                0x00,
                0x10,
                0x00,
                0x0F,
                0x0F,
                0x0F,
                0x0F,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
            ],
            [
                0x00,
                0x00,
                0x10,
                0x03,
                0x0F,
                0x0F,
                0x0F,
                0x0F,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
            ],
            [
                0x00,
                0x00,
                0x10,
                0x06,
                0x0F,
                0x0F,
                0x0F,
                0x0F,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
            ],
        ]
        for h in headers:
            self.send_sysex(h)
        self.send_sysex(
            [
                0x10,
                block_id,
                0x00,
                0x01,
                type_tup[0],
                type_tup[1],
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                type_tup[2],
            ]
        )
        self.send_sysex([0x10, block_id, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00])

    def set_patch(self, patch_number):
        self.send_sysex(
            [
                0x00,
                0x02,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                patch_number,
                0x00,
                0x00,
            ]
        )

    def set_parameter(self, block_name, param_id, value, type_tup):
        block_id = BLOCKS[block_name]
        data = [
            0x10,
            block_id,
            0x00,
            0x02,
            type_tup[0],
            type_tup[1],
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            type_tup[2],
        ]
        data += [
            0x00,
            param_id,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ]
        data += PARAM_VALUE[value]
        print(data)
        self.send_sysex(data)
        return 0
