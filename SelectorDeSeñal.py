"""
OsciLink — Generador de señales para STM32
Arquitectura de 3 capas: OsciLink (UI) → FrameLink (protocolo) → UART (pyserial)
Paleta: rosa / magenta
"""

import struct
import threading
import math
import time
import tkinter as tk
import customtkinter as ctk

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


# ─────────────────────────────────────────────
#  Capa 2 — FrameLink (protocolo)
# ─────────────────────────────────────────────

CMD_SET_CONFIG    = 0x10
CMD_OUTPUT_ENABLE = 0x11
WAVEFORM_LABELS   = {0: "SINE", 1: "SQUARE", 2: "TRIANGLE", 3: "SAWTOOTH"}


def _crc16_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1) & 0xFFFF
    return crc


def _cobs_encode(data: bytes) -> bytes:
    out = bytearray()
    data = bytearray(data)
    code_idx = 0
    out.append(0x00)
    code = 1
    for b in data:
        if b == 0x00:
            out[code_idx] = code
            code_idx = len(out)
            out.append(0x00)
            code = 1
        else:
            out.append(b)
            code += 1
            if code == 0xFF:
                out[code_idx] = code
                code_idx = len(out)
                out.append(0x00)
                code = 1
    out[code_idx] = code
    return bytes(out)


class TxResult:
    def __init__(self, seq, cmd, frame_hex, sent, error=None):
        self.seq = seq
        self.cmd = cmd
        self.frame_hex = frame_hex
        self.sent = sent
        self.error = error


class FrameLink:
    def __init__(self, on_event=None):
        self._seq = 0
        self._serial = None
        self._lock = threading.Lock()
        self._on_event = on_event

    def connect(self, port: str, baudrate: int = 115200) -> bool:
        if not SERIAL_AVAILABLE:
            return False
        try:
            with self._lock:
                if self._serial and self._serial.is_open:
                    self._serial.close()
                self._serial = serial.Serial(
                    port=port, baudrate=baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1.0,
                )
            return True
        except Exception:
            self._serial = None
            return False

    def disconnect(self):
        with self._lock:
            if self._serial and self._serial.is_open:
                self._serial.close()
            self._serial = None

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._serial is not None and self._serial.is_open

    def send_set_config(self, frequency_hz: int, waveform: int) -> TxResult:
        payload = struct.pack("<IB", frequency_hz & 0xFFFFFFFF, waveform & 0xFF)
        return self._transmit(CMD_SET_CONFIG, payload)

    def send_output_enable(self, enable: bool) -> TxResult:
        payload = struct.pack("B", 0x01 if enable else 0x00)
        return self._transmit(CMD_OUTPUT_ENABLE, payload)

    def _transmit(self, cmd: int, payload: bytes) -> TxResult:
        with self._lock:
            seq = self._seq
            header = bytes([seq, cmd, len(payload)])
            raw = header + payload
            crc = _crc16_ccitt(raw)
            raw = raw + struct.pack("<H", crc)
            encoded = _cobs_encode(raw) + b"\x00"
            sent, error = False, None
            if self._serial and self._serial.is_open:
                try:
                    self._serial.write(encoded)
                    sent = True
                except Exception as e:
                    error = str(e)
            self._seq = (self._seq + 1) % 256

        result = TxResult(
            seq=seq, cmd=cmd,
            frame_hex=" ".join(f"{b:02X}" for b in encoded),
            sent=sent, error=error,
        )
        if self._on_event:
            self._on_event("tx", result)
        return result


# ─────────────────────────────────────────────
#  Paleta — rosa / magenta
# ─────────────────────────────────────────────

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")
"""
C_BG        = "#f3a2df"   # fondo profundo — casi negro morado
C_PANEL     = "#f0d5ed"   # panel superficial
C_BORDER    = "#f880e4"   # bordes normales
C_PINK      = "#e040fb"   # magenta brillante (acento principal)
C_PINK_MED  = "#ab47bc"   # violeta-rosa medio
C_PINK_DIM  = "#d687d0"   # rosa muy oscuro (fill de botones inactivos)
C_PINK_HVR  = "#E75BD9"   # hover
C_TEXT      = "#f3c6f5"   # texto principal — rosa muy claro
C_MUTED     = "#8d578d"   # texto secundario — malva
C_SCOPE_BG  = "#F7CFF1"   # fondo del scope — negro rosado
C_GRID      = "#AA79A4"   # grilla del scope
C_WAVE_ON   = "#d877c0"   # onda activa
C_WAVE_DIM  = "#4c1c52"   # onda inactiva
C_ACCENT    = "#ffffff"   # rosa claro para selección activa
C_ERR       = "#f06292"   # error / desconexión
"""
C_BG        = "#120a10"   # fondo profundo — casi negro morado
C_PANEL     = "#1a0d18"   # panel superficial
C_BORDER    = "#3d1f38"   # bordes normales
C_PINK      = "#e040fb"   # magenta brillante (acento principal)
C_PINK_MED  = "#ab47bc"   # violeta-rosa medio
C_PINK_DIM  = "#2a1228"   # rosa muy oscuro (fill de botones inactivos)
C_PINK_HVR  = "#331530"   # hover
C_TEXT      = "#f3c6f5"   # texto principal — rosa muy claro
C_MUTED     = "#7a4a7a"   # texto secundario — malva
C_SCOPE_BG  = "#0c060b"   # fondo del scope — negro rosado
C_GRID      = "#1a0a18"   # grilla del scope
C_WAVE_ON   = "#e040fb"   # onda activa
C_WAVE_DIM  = "#2d1030"   # onda inactiva
C_ACCENT    = "#f48fb1"   # rosa claro para selección activa
C_ERR       = "#f06292"   # error / desconexión"""

MONO = "Courier New"


def _sample_wave(t: float, waveform: int) -> float:
    t = t % 1.0
    if waveform == 0: return math.sin(2 * math.pi * t)
    if waveform == 1: return 1.0 if t < 0.5 else -1.0
    if waveform == 2: return (4 * t - 1) if t < 0.5 else (3 - 4 * t)
    if waveform == 3: return 2 * t - 1
    return 0.0


# ─────────────────────────────────────────────
#  ScopeCanvas
# ─────────────────────────────────────────────

class ScopeCanvas:
    FPS = 30

    def __init__(self, parent):
        self._waveform  = 0
        self._output_on = False
        self._phase     = 0.0
        self._running   = True
        self._freq_hz   = 1000

        self.canvas = tk.Canvas(
            parent, bg=C_SCOPE_BG, highlightthickness=0, height=150,
        )
        self.canvas.pack(fill="x")
        self._animate()

    def set_waveform(self, w): self._waveform = w
    def set_output(self, on):  self._output_on = on
    def set_freq(self, hz):    self._freq_hz = hz
    def stop(self):            self._running = False

    def _animate(self):
        if not self._running:
            return
        if self._output_on:
            self._phase += 0.015
        self._draw()
        self.canvas.after(int(1000 / self.FPS), self._animate)

    def _draw(self):
        c = self.canvas
        W, H = c.winfo_width(), c.winfo_height()
        if W < 2 or H < 2:
            return
        c.delete("all")

        # Fondo
        c.create_rectangle(0, 0, W, H, fill=C_SCOPE_BG, outline="")

        # Cuadrícula
        for i in range(1, 4):
            c.create_line(0, H * i // 4, W, H * i // 4, fill=C_GRID, width=1)
        for i in range(1, 8):
            c.create_line(W * i // 8, 0, W * i // 8, H, fill=C_GRID, width=1)

        # Línea central punteada
        c.create_line(0, H // 2, W, H // 2, fill="#2a0d28", width=1, dash=(4, 6))

        # Onda — sin smooth=True en ningún caso para que todas avancen igual
        color  = C_WAVE_ON if self._output_on else C_WAVE_DIM
        margin = 14
        pts    = []
        steps  = W * 2          # doble resolución: el seno queda suave sin splines
        for i in range(steps + 1):
            t  = (i / max(steps, 1)) * 2.5 + self._phase
            px = i * W / steps
            py = H / 2 - _sample_wave(t, self._waveform) * (H / 2 - margin)
            pts += [px, py]

        if len(pts) >= 4:
            c.create_line(*pts, fill=color,
                        width=2 if self._output_on else 1)

        # Brillo difuso bajo la onda (solo cuando ON)
        if self._output_on and len(pts) >= 4:
            c.create_line(*pts, fill="#5a0060", width=6)
            c.create_line(*pts, fill=color, width=2)

        # Overlay texto
        hz_str = f"{self._freq_hz:,} Hz".replace(",", ".")
        c.create_text(8, 10, anchor="nw", text=hz_str,
                    fill=C_MUTED, font=(MONO, 9))
        c.create_text(W - 8, 10, anchor="ne",
                    text=WAVEFORM_LABELS.get(self._waveform, ""),
                    fill=C_MUTED, font=(MONO, 9))

        # Punto ON/OFF
        dot = C_PINK if self._output_on else C_MUTED
        c.create_oval(W - 18, H - 18, W - 8, H - 8, fill=dot, outline="")


# ─────────────────────────────────────────────
#  PortPanel — selector de puerto + baudrate
# ─────────────────────────────────────────────

class PortPanel(ctk.CTkFrame):
    BAUDRATES = ["9600", "57600", "115200", "230400", "921600"]

    def __init__(self, parent, on_connect, on_disconnect):
        super().__init__(parent, fg_color=C_PANEL, corner_radius=0)
        self._on_connect    = on_connect
        self._on_disconnect = on_disconnect
        self._connected     = False
        self._build()

    def _build(self):
        # Label UART
        ctk.CTkLabel(
            self, text="UART",
            font=ctk.CTkFont(family=MONO, size=10),
            text_color=C_MUTED, width=40,
        ).pack(side="left", padx=(10, 6))

        # ── Puerto ──────────────────────
        self._port_var = tk.StringVar(value="")
        self._port_menu = ctk.CTkOptionMenu(
            self,
            variable=self._port_var,
            values=self._list_ports(),
            font=ctk.CTkFont(family=MONO, size=10),
            fg_color=C_PINK_DIM,
            button_color=C_BORDER,
            button_hover_color=C_PINK_HVR,
            text_color=C_TEXT,
            dropdown_fg_color=C_PANEL,
            dropdown_text_color=C_TEXT,
            dropdown_hover_color=C_PINK_HVR,
            width=120, height=28,
            corner_radius=6,
        )
        self._port_menu.pack(side="left", padx=(0, 4), pady=8)

        # ── Baudrate ────────────────────
        self._baud_var = tk.StringVar(value="115200")
        self._baud_menu = ctk.CTkOptionMenu(
            self,
            variable=self._baud_var,
            values=self.BAUDRATES,
            font=ctk.CTkFont(family=MONO, size=10),
            fg_color=C_PINK_DIM,
            button_color=C_BORDER,
            button_hover_color=C_PINK_HVR,
            text_color=C_TEXT,
            dropdown_fg_color=C_PANEL,
            dropdown_text_color=C_TEXT,
            dropdown_hover_color=C_PINK_HVR,
            width=90, height=28,
            corner_radius=6,
        )
        self._baud_menu.pack(side="left", padx=(0, 4), pady=8)

        # ── Refresh ─────────────────────
        self._refresh_btn = ctk.CTkButton(
            self, text="↺",
            font=ctk.CTkFont(family=MONO, size=13),
            fg_color="transparent",
            hover_color=C_PINK_HVR,
            text_color=C_MUTED,
            border_color=C_BORDER, border_width=1,
            width=30, height=28, corner_radius=6,
            command=self._refresh_ports,
        )
        self._refresh_btn.pack(side="left", padx=(0, 8))

        # ── Botón CONNECT / DISCONNECT ──
        self._conn_btn = ctk.CTkButton(
            self, text="CONNECT",
            font=ctk.CTkFont(family=MONO, size=10, weight="bold"),
            fg_color=C_PINK_DIM,
            hover_color=C_PINK_HVR,
            text_color=C_ACCENT,
            border_color=C_PINK_MED, border_width=1,
            width=90, height=28, corner_radius=6,
            command=self._toggle_connect,
        )
        self._conn_btn.pack(side="left", padx=(0, 10))

        # ── Indicador de estado ─────────
        self._status_lbl = ctk.CTkLabel(
            self, text="● DISCONNECTED",
            font=ctk.CTkFont(family=MONO, size=9),
            text_color=C_MUTED,
        )
        self._status_lbl.pack(side="left")

    # ── helpers ──────────────────────────────

    def _list_ports(self):
        if not SERIAL_AVAILABLE:
            return ["(pyserial no instalado)"]
        ports = [p.device for p in serial.tools.list_ports.comports()]
        return ports if ports else ["(sin puertos)"]

    def _refresh_ports(self):
        ports = self._list_ports()
        self._port_menu.configure(values=ports)
        if ports:
            self._port_var.set(ports[0])

    def _toggle_connect(self):
        if self._connected:
            self._on_disconnect()
            self.set_connected(False)
        else:
            port  = self._port_var.get()
            baud  = int(self._baud_var.get())
            ok    = self._on_connect(port, baud)
            self.set_connected(ok, port if ok else None)

    def set_connected(self, connected: bool, port: str = None):
        self._connected = connected
        if connected:
            self._conn_btn.configure(
                text="DISCONNECT",
                border_color=C_PINK,
                text_color=C_PINK,
            )
            self._status_lbl.configure(
                text=f"● {port}",
                text_color=C_PINK,
            )
            self._port_menu.configure(state="disabled")
            self._baud_menu.configure(state="disabled")
        else:
            self._conn_btn.configure(
                text="CONNECT",
                border_color=C_PINK_MED,
                text_color=C_ACCENT,
            )
            self._status_lbl.configure(
                text="● DISCONNECTED",
                text_color=C_MUTED,
            )
            self._port_menu.configure(state="normal")
            self._baud_menu.configure(state="normal")

    def set_error(self, msg: str):
        self._status_lbl.configure(text=f"✗ {msg}", text_color=C_ERR)


# ─────────────────────────────────────────────
#  FrequencyRow
# ─────────────────────────────────────────────

class FrequencyRow(ctk.CTkFrame):
    PRESETS = [("5Hz", 5), ("10Hz", 10), ("50Hz", 50),
            ("500Hz", 500), ("1kHz", 1000)]

    def __init__(self, parent, on_change):
        super().__init__(parent, fg_color=C_PANEL, corner_radius=0)
        self._on_change = on_change
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="FREQ",
            font=ctk.CTkFont(family=MONO, size=10),
            text_color=C_MUTED, width=40,
        ).pack(side="left", padx=(10, 6))

        inp = ctk.CTkFrame(self, fg_color=C_BG,
                        border_color=C_BORDER, border_width=1,
                        corner_radius=6)
        inp.pack(side="left", fill="x", expand=True, pady=8)

        self._var = tk.StringVar(value="1000")
        self._var.trace_add("write", self._on_var_change)

        ctk.CTkEntry(
            inp, textvariable=self._var,
            font=ctk.CTkFont(family=MONO, size=17, weight="bold"),
            text_color=C_TEXT,
            fg_color="transparent", border_width=0,
            justify="right",
        ).pack(side="left", fill="x", expand=True, padx=(8, 0))

        ctk.CTkLabel(
            inp, text=" Hz ",
            font=ctk.CTkFont(family=MONO, size=11),
            text_color=C_MUTED,
        ).pack(side="right", padx=(0, 8))

        pf = ctk.CTkFrame(self, fg_color="transparent")
        pf.pack(side="left", padx=(8, 6))

        for label, hz in self.PRESETS:
            ctk.CTkButton(
                pf, text=label,
                font=ctk.CTkFont(family=MONO, size=9),
                fg_color="transparent",
                hover_color=C_PINK_HVR,
                text_color=C_MUTED,
                border_color=C_BORDER, border_width=1,
                corner_radius=4, width=44, height=24,
                command=lambda h=hz: self.set_freq(h),
            ).pack(side="left", padx=2)

    def _on_var_change(self, *_):
        try:
            self._on_change(max(1, min(4294967295, int(self._var.get()))))
        except ValueError:
            pass

    def get_freq(self) -> int:
        try:
            return max(1, min(4294967295, int(self._var.get())))
        except ValueError:
            return 1000

    def set_freq(self, hz: int):
        self._var.set(str(hz))


# ─────────────────────────────────────────────
#  ControlPanel
# ─────────────────────────────────────────────

class ControlPanel(ctk.CTkFrame):
    def __init__(self, parent, on_wave_change, on_set_config, on_output_toggle):
        super().__init__(parent, fg_color=C_PANEL, corner_radius=0)
        self._on_wave_change   = on_wave_change
        self._on_set_config    = on_set_config
        self._on_output_toggle = on_output_toggle
        self._waveform  = 0
        self._output_on = False
        self._wave_btns = {}
        self._build()

    def _build(self):
        self.grid_columnconfigure(list(range(7)), weight=1)

        waves = [(0, "∿", "SINE"), (1, "⊓", "SQR"), (2, "⋀", "TRI"), (3, "⊿", "SAW")]
        for col, (wid, icon, lbl) in enumerate(waves):
            b = ctk.CTkButton(
                self, text=f"{icon}\n{lbl}",
                font=ctk.CTkFont(family=MONO, size=11),
                fg_color=C_PINK_DIM, hover_color=C_PINK_HVR,
                text_color=C_MUTED,
                border_color=C_BORDER, border_width=1,
                corner_radius=6, height=56,
                command=lambda w=wid: self._select_wave(w),
            )
            b.grid(row=0, column=col,
                padx=(6 if col == 0 else 3, 3), pady=8, sticky="ew")
            self._wave_btns[wid] = b

        # Separador
        ctk.CTkFrame(self, width=1, fg_color=C_BORDER,
                    corner_radius=0).grid(row=0, column=4, padx=4, pady=8, sticky="ns")

        # SET
        self._set_btn = ctk.CTkButton(
            self, text="SET\n0x10",
            font=ctk.CTkFont(family=MONO, size=11),
            fg_color=C_PINK_DIM, hover_color=C_PINK_HVR,
            text_color=C_MUTED,
            border_color=C_BORDER, border_width=1,
            corner_radius=6, height=56,
            command=self._on_set_config,
        )
        self._set_btn.grid(row=0, column=5, padx=3, pady=8, sticky="ew")

        # OUTPUT
        self._out_btn = ctk.CTkButton(
            self, text="OUT\nOFF",
            font=ctk.CTkFont(family=MONO, size=11, weight="bold"),
            fg_color=C_PINK_DIM, hover_color=C_PINK_HVR,
            text_color=C_MUTED,
            border_color=C_BORDER, border_width=1,
            corner_radius=6, height=56,
            command=self._toggle_output,
        )
        self._out_btn.grid(row=0, column=6, padx=(3, 6), pady=8, sticky="ew")

        self._select_wave(0, notify=False)

    def _select_wave(self, w: int, notify=True):
        self._waveform = w
        for wid, btn in self._wave_btns.items():
            if wid == w:
                btn.configure(border_color=C_PINK, text_color=C_ACCENT)
            else:
                btn.configure(border_color=C_BORDER, text_color=C_MUTED)
        if notify:
            self._on_wave_change(w)

    def _toggle_output(self):
        self._output_on = not self._output_on
        if self._output_on:
            self._out_btn.configure(text="OUT\nON",
                                    border_color=C_PINK, text_color=C_PINK)
        else:
            self._out_btn.configure(text="OUT\nOFF",
                                    border_color=C_BORDER, text_color=C_MUTED)
        self._on_output_toggle(self._output_on)

    def flash_set(self):
        self._set_btn.configure(border_color=C_PINK, text_color=C_PINK,
                                text="SET\n✓ OK")
        self.after(700, lambda: self._set_btn.configure(
            border_color=C_BORDER, text_color=C_MUTED, text="SET\n0x10"))


# ─────────────────────────────────────────────
#  LogBar
# ─────────────────────────────────────────────

class LogBar(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self._lbl = ctk.CTkLabel(
            self, text="—  listo",
            font=ctk.CTkFont(family=MONO, size=10),
            text_color=C_MUTED, anchor="w",
        )
        self._lbl.pack(fill="x", padx=10, pady=6)

    def push(self, text: str, hex_str: str = "", ok: bool = True):
        now   = time.strftime("%H:%M:%S")
        color = C_PINK if ok else C_ERR
        short = hex_str[:54] + ("…" if len(hex_str) > 54 else "")
        msg   = f"{now}  {text}"
        if short:
            msg += f"   {short}"
        self._lbl.configure(text=msg, text_color=color)


# ─────────────────────────────────────────────
#  WaveformApp — ventana raíz
# ─────────────────────────────────────────────

class WaveformApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OsciLink")
        self.resizable(False, False)
        self.configure(fg_color=C_BG)

        self._link      = FrameLink(on_event=self._on_frame_event)
        self._waveform  = 0
        self._output_on = False

        self._build_ui()

    def _sep(self):
        ctk.CTkFrame(self, height=1, fg_color=C_BORDER,
                    corner_radius=0).pack(fill="x")

    def _build_ui(self):
        # ── Header ──────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C_PANEL, corner_radius=0)
        hdr.pack(fill="x")

        ctk.CTkLabel(
            hdr, text="OSCILINK",
            font=ctk.CTkFont(family=MONO, size=13, weight="bold"),
            text_color=C_PINK,
        ).pack(side="left", padx=12, pady=8)

        ctk.CTkLabel(
            hdr, text="STM32 Signal Generator  //  FrameLink 3-Layer",
            font=ctk.CTkFont(family=MONO, size=9),
            text_color=C_MUTED,
        ).pack(side="left")

        self._hdr_status = ctk.CTkLabel(
            hdr, text="● NO PORT",
            font=ctk.CTkFont(family=MONO, size=9),
            text_color=C_MUTED,
        )
        self._hdr_status.pack(side="right", padx=12)

        self._sep()

        # ── Fila 1: Scope ────────────────────────────
        sf = ctk.CTkFrame(self, fg_color=C_SCOPE_BG, corner_radius=0)
        sf.pack(fill="x")
        self._scope = ScopeCanvas(sf)

        self._sep()

        # ── Fila 2: Puerto UART ──────────────────────
        self._port_panel = PortPanel(
            self,
            on_connect=self._do_connect,
            on_disconnect=self._do_disconnect,
        )
        self._port_panel.pack(fill="x")

        self._sep()

        # ── Fila 3: Frecuencia ───────────────────────
        self._freq_row = FrequencyRow(self, on_change=self._on_freq_change)
        self._freq_row.pack(fill="x")

        self._sep()

        # ── Fila 4: Controles ────────────────────────
        self._ctrl = ControlPanel(
            self,
            on_wave_change=self._on_wave_change,
            on_set_config=self._on_set_config,
            on_output_toggle=self._on_output_toggle,
        )
        self._ctrl.pack(fill="x")

        self._sep()

        # ── Fila 5: Log ──────────────────────────────
        self._log = LogBar(self)
        self._log.pack(fill="x")

        self.update_idletasks()
        self.minsize(580, self.winfo_height())

    # ── Conexión ─────────────────────────────────────

    def _do_connect(self, port: str, baudrate: int) -> bool:
        if not port or port.startswith("("):
            self._port_panel.set_error("puerto inválido")
            return False
        ok = self._link.connect(port, baudrate)
        if ok:
            self._hdr_status.configure(text=f"● {port}", text_color=C_PINK)
            self._log.push(f"CONNECTED  {port}  {baudrate} baud", ok=True)
        else:
            self._port_panel.set_error("no se pudo abrir")
            self._hdr_status.configure(text="● ERROR", text_color=C_ERR)
            self._log.push(f"ERROR  no se pudo abrir {port}", ok=False)
        return ok

    def _do_disconnect(self):
        self._link.disconnect()
        self._hdr_status.configure(text="● NO PORT", text_color=C_MUTED)
        self._log.push("DISCONNECTED", ok=False)

    # ── Callbacks UI ─────────────────────────────────

    def _on_freq_change(self, hz):
        self._scope.set_freq(hz)

    def _on_wave_change(self, w):
        self._waveform = w
        self._scope.set_waveform(w)

    def _on_set_config(self):
        hz = self._freq_row.get_freq()
        self._link.send_set_config(hz, self._waveform)
        self._ctrl.flash_set()

    def _on_output_toggle(self, enable):
        self._output_on = enable
        self._scope.set_output(enable)
        self._link.send_output_enable(enable)

    # ── Callback FrameLink ───────────────────────────

    def _on_frame_event(self, event_type, result: TxResult):
        self.after(0, lambda: self._update_from_result(result))

    def _update_from_result(self, result: TxResult):
        cmd_name = {
            CMD_SET_CONFIG:    "SET_CONFIG",
            CMD_OUTPUT_ENABLE: "OUTPUT_ENABLE",
        }.get(result.cmd, f"CMD_{result.cmd:02X}")

        status = "TX" if result.sent else "BUILD"
        self._log.push(f"{status}  {cmd_name}  SEQ={result.seq:03d}",
                    result.frame_hex, ok=True)

        if result.sent:
            self._hdr_status.configure(text="● TX OK", text_color=C_PINK)
            self.after(1200, lambda: self._hdr_status.configure(
                text=f"● CONNECTED", text_color=C_PINK))

    def on_destroy(self):
        self._scope.stop()
        self._link.disconnect()


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

def main():
    app = WaveformApp()
    app.protocol("WM_DELETE_WINDOW", lambda: (app.on_destroy(), app.destroy()))
    app.mainloop()


if __name__ == "__main__":
    main()
