import tkinter as tk
from tkinter import ttk, messagebox
import time
import rtmidi
from constants import HEADER, BLOCKS, BLOCK_TYPES, BLOCK_COLORS

# ─────────────────────────────────────────────────────────────
# MIDI Communication
# ─────────────────────────────────────────────────────────────

class GP100MIDI:
    def __init__(self):
        self.midi_out = None
        self.midi_in  = None
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
            self.midi_in  = rtmidi.MidiIn()

            out_ports = self.midi_out.get_ports()
            in_ports  = self.midi_in.get_ports()

            self.midi_out.open_port(port_index)
            # Try to open matching IN port
            for i, name in enumerate(in_ports):
                if out_ports[port_index].split(':')[0] in name:
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
        """Send raw SysEx bytes"""
        msg = HEADER + data + [0xF7]
        try:
            self.midi_out.send_message(msg)
        except Exception as e:
            print(f"Send error: {e}")

    def set_block_enabled(self, block_name, enabled):
        """Turn a block ON or OFF"""
        block_id = BLOCKS[block_name]
        data = [
            0x10, block_id, 0x00, 0x00, 0x00,
            0x01 if enabled else 0x00,
            0x00, 0x00, 0x00
        ]
        self.send_sysex(data)

    def set_block_type(self, block_name, type_name, state_byte=0x01):
        """Set effect type for a block"""
        block_id = BLOCKS[block_name]
        types = BLOCK_TYPES[block_name]
        type_tup = types[type_name]
        settype_header = [
            [0x00, 0x00, 0x10, 0x00, 0x0F, 0x0F, 0x0F, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
            [0x00, 0x00, 0x10, 0x03, 0x0F, 0x0F, 0x0F, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
            [0x00, 0x00, 0x10, 0x06, 0x0F, 0x0F, 0x0F, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        ]
        data = [
            [0x10, block_id, 0x00, 0x01, type_tup[0], type_tup[1], 0x00, 0x00, 0x00, 0x00, 0x00, type_tup[2]],
            [0x10, block_id, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00]
        ]
        self.send_sysex(settype_header[0])
        self.send_sysex(settype_header[1])
        self.send_sysex(settype_header[2])
        self.send_sysex(data[0])
        self.send_sysex(data[1])

    def set_patch(self, patch_number):
        """Switch to a patch (1-based)"""
        data = [
            0x00, 0x02, 
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
            patch_number, 0x00, 0x00
        ]
        self.send_sysex(data)

    @staticmethod
    def encode_value(value):
        """
        Encode a 0-99 parameter value into GP-100 nibble format.
        Returns (p, q, r):
          r = value // 4   (upper group)
          p = (value % 4) * 4  (lower group, multiples of 4)
          q = 0x00         (sub-step, always 0 when sending)

        Verified from capture:
          val=0 → p=00, q=00, r=00  ✓
          val=1 → p=04, q=00, r=00  ✓
          val=4 → p=00, q=00, r=01  ✓
          val=8 → p=00, q=00, r=02  ✓
        """
        r = value // 4
        p = (value % 4) * 4
        q = 0x00
        return p, q, r

    def set_parameter(self, block_name, param_id, value, type_cat, type_sub):
        """
        Set a parameter value (0-99) for a block.

        Confirmed param_ids (same index for every block):
          0x00 = Param 1 (e.g. AMP VOL,  DST Gain)
          0x01 = Param 2 (e.g. AMP Tone)
          0x02 = Param 3 (e.g. AMP Balance)
          ... increments per knob

        type_cat, type_sub: current effect type (from BLOCK_TYPES dict)
        value: 0-99
        """
        block_id = BLOCKS[block_name]
        p, q, r = self.encode_value(value)
        # Full confirmed structure:
        # 10 [block] 00 02 [cat] [sub] 00 00 00 00 00 08 00 [param_id] 00 ...zeros... [p] [q] 04 [r]
        # Note: AMP has 08 at pos+11, DST has 00 — depends on block
        filler = 0x08 if block_name == 'AMP' else 0x00
        data = [
            0x10, block_id, 0x00, 0x02,
            type_cat, type_sub,
            0x00, 0x00, 0x00, 0x00, 0x00, filler,
            0x00, param_id,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            p, q, 0x04, r
        ]
        self.send_sysex(data)

# ─────────────────────────────────────────────────────────────
# GUI
# ─────────────────────────────────────────────────────────────

class GP100Editor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.midi = GP100MIDI()
        self.block_states = {b: tk.BooleanVar(value=False) for b in BLOCKS}
        self.block_types  = {b: tk.StringVar() for b in BLOCKS}
        for b in BLOCKS:
            types = list(BLOCK_TYPES[b].keys())
            self.block_types[b].set(types[0])

        self.title("Valeton GP-100 Editor")
        self.configure(bg='#1A1A2E')
        self.resizable(True, True)
        self._build_ui()

    def _build_ui(self):
        # ── Title bar ──────────────────────────────────────
        title_frame = tk.Frame(self, bg='#0F3460', pady=10)
        title_frame.pack(fill='x')

        tk.Label(title_frame, text="● VALETON GP-100",
                 font=('Courier', 18, 'bold'),
                 fg='#E94560', bg='#0F3460').pack(side='left', padx=20)

        tk.Label(title_frame, text="Linux Editor",
                 font=('Courier', 12),
                 fg='#A0A0C0', bg='#0F3460').pack(side='left')

        # ── Connection bar ─────────────────────────────────
        conn_frame = tk.Frame(self, bg='#16213E', pady=6)
        conn_frame.pack(fill='x', padx=10, pady=(5, 0))

        tk.Label(conn_frame, text="MIDI Port:",
                 fg='#A0A0C0', bg='#16213E',
                 font=('Courier', 10)).pack(side='left', padx=(10, 5))

        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var,
                                       width=35, state='readonly')
        self.port_combo.pack(side='left', padx=5)

        tk.Button(conn_frame, text="Refresh",
                  command=self._refresh_ports,
                  bg='#0F3460', fg='#A0A0C0',
                  font=('Courier', 9), relief='flat',
                  padx=8, pady=3).pack(side='left', padx=5)

        self.connect_btn = tk.Button(conn_frame, text="Connect",
                                     command=self._toggle_connect,
                                     bg='#E94560', fg='white',
                                     font=('Courier', 10, 'bold'),
                                     relief='flat', padx=12, pady=3)
        self.connect_btn.pack(side='left', padx=5)

        self.status_label = tk.Label(conn_frame, text="● Disconnected",
                                     fg='#E94560', bg='#16213E',
                                     font=('Courier', 10))
        self.status_label.pack(side='right', padx=10)

        # ── Patch selector ─────────────────────────────────
        patch_frame = tk.Frame(self, bg='#1A1A2E', pady=8)
        patch_frame.pack(fill='x', padx=10)

        tk.Label(patch_frame, text="PATCH:",
                 fg='#E94560', bg='#1A1A2E',
                 font=('Courier', 11, 'bold')).pack(side='left', padx=(10, 5))

        self.patch_var = tk.IntVar(value=1)
        for i in range(1, 9):
            tk.Radiobutton(patch_frame, text=str(i),
                          variable=self.patch_var, value=i,
                          command=lambda p=i: self._send_patch(p-1),
                          bg='#1A1A2E', fg='#C0C0E0',
                          selectcolor='#0F3460',
                          font=('Courier', 11),
                          activebackground='#1A1A2E').pack(side='left', padx=3)

        # ── Effect blocks ──────────────────────────────────
        blocks_frame = tk.Frame(self, bg='#1A1A2E')
        blocks_frame.pack(fill='both', expand=True, padx=10, pady=10)

        block_list = list(BLOCKS.keys())
        for i, block_name in enumerate(block_list):
            col = i % 3
            row = i // 3
            self._build_block(blocks_frame, block_name, row, col)

        # ── Log ────────────────────────────────────────────
        log_frame = tk.Frame(self, bg='#0F3460')
        log_frame.pack(fill='x', padx=10, pady=(0, 10))

        tk.Label(log_frame, text="SysEx Log",
                 fg='#A0A0C0', bg='#0F3460',
                 font=('Courier', 9)).pack(anchor='w', padx=5, pady=2)

        self.log_text = tk.Text(log_frame, height=4, bg='#0A0A1A',
                                fg='#00FF88', font=('Courier', 9),
                                relief='flat', state='disabled')
        self.log_text.pack(fill='x', padx=5, pady=(0, 5))

        self._refresh_ports()

    def _build_block(self, parent, block_name, row, col):
        color = BLOCK_COLORS[block_name]
        types = list(BLOCK_TYPES[block_name].keys())

        frame = tk.Frame(parent, bg='#16213E',
                         highlightbackground=color,
                         highlightthickness=2,
                         padx=8, pady=8)
        frame.grid(row=row, column=col, padx=6, pady=6, sticky='nsew')
        parent.columnconfigure(col, weight=1)
        parent.rowconfigure(row, weight=1)

        # Block title + toggle
        header = tk.Frame(frame, bg='#16213E')
        header.pack(fill='x')

        tk.Label(header, text=block_name,
                 font=('Courier', 13, 'bold'),
                 fg=color, bg='#16213E').pack(side='left')

        led_btn = tk.Button(header, text="○",
                            font=('Courier', 14),
                            fg='#444466', bg='#16213E',
                            relief='flat', bd=0,
                            command=lambda b=block_name: self._toggle_block(b))
        led_btn.pack(side='right')
        self.__dict__[f'led_{block_name}'] = led_btn

        # Type dropdown
        tk.Label(frame, text="Type:",
                 fg='#888899', bg='#16213E',
                 font=('Courier', 9)).pack(anchor='w', pady=(6, 0))

        combo = ttk.Combobox(frame, textvariable=self.block_types[block_name],
                             values=types, state='readonly',
                             font=('Courier', 9))
        combo.pack(fill='x', pady=2)
        combo.bind('<<ComboboxSelected>>',
                   lambda e, b=block_name: self._send_type(b))

        # Parameter sliders (param_id 0, 1, 2 confirmed)
        PARAM_NAMES = ['Param 1', 'Param 2', 'Param 3']
        for param_id in range(3):
            tk.Label(frame, text=PARAM_NAMES[param_id],
                     fg='#888899', bg='#16213E',
                     font=('Courier', 8)).pack(anchor='w', pady=(4, 0))

            param_var = tk.IntVar(value=50)
            slider = tk.Scale(frame, from_=0, to=99,
                              orient='horizontal',
                              variable=param_var,
                              bg='#16213E', fg=color,
                              troughcolor='#0A0A1A',
                              highlightthickness=0,
                              font=('Courier', 8),
                              command=lambda v, b=block_name, pid=param_id:
                                  self._send_param(b, pid, int(float(v))))
            slider.pack(fill='x')

    def _toggle_block(self, block_name):
        state = self.block_states[block_name]
        new_state = not state.get()
        state.set(new_state)
        color = BLOCK_COLORS[block_name]
        led = self.__dict__[f'led_{block_name}']
        if new_state:
            led.config(text="●", fg=color)
        else:
            led.config(text="○", fg='#444466')

        self.midi.set_block_enabled(block_name, new_state)
        self._log(f"{block_name} → {'ON' if new_state else 'OFF'}")

    def _send_type(self, block_name):
        type_name = self.block_types[block_name].get()
        self.midi.set_block_type(block_name, type_name)
        self._log(f"{block_name} type → {type_name}")

    def _send_param(self, block_name, param_id, value):
        type_name = self.block_types[block_name].get()
        cat, sub = BLOCK_TYPES[block_name].get(type_name, (0x00, 0x00))
        self.midi.set_parameter(block_name, param_id, value, cat, sub)
        self._log(f"{block_name} param[{param_id}]={value} (type {type_name})")

    def _send_patch(self, patch_num):
        self.midi.set_patch(patch_num)
        self._log(f"Patch → {patch_num}")

    def _log(self, msg):
        self.log_text.config(state='normal')
        self.log_text.insert('end', f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_text.see('end')
        self.log_text.config(state='disabled')

    def _refresh_ports(self):
        ports = self.midi.list_ports()
        self.port_combo['values'] = ports
        if ports:
            # Auto-select GP-100 if found
            for i, p in enumerate(ports):
                if 'GP' in p or 'Valeton' in p or 'valeton' in p:
                    self.port_combo.current(i)
                    return
            self.port_combo.current(0)

    def _toggle_connect(self):
        if self.midi.connected:
            self.midi.disconnect()
            self.connect_btn.config(text="Connect", bg='#E94560')
            self.status_label.config(text="● Disconnected", fg='#E94560')
        else:
            ports = self.midi.list_ports()
            selected = self.port_combo.current()
            if selected < 0:
                messagebox.showerror("Error", "No MIDI port selected")
                return
            if self.midi.connect(selected):
                self.connect_btn.config(text="Disconnect", bg='#2ECC71')
                self.status_label.config(
                    text=f"● {self.midi.port_name[:30]}", fg='#2ECC71')
                self._log(f"Connected to {self.midi.port_name}")
            else:
                messagebox.showerror("Error", "Failed to connect to MIDI port")


if __name__ == '__main__':
    app = GP100Editor()
    app.mainloop()