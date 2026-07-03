#!/usr/bin/env python3
import os, sys, subprocess, threading
sys.path.insert(0, '/usr/lib/python3.14/site-packages')
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QButtonGroup, QFrame, QColorDialog, QSizePolicy,
    QComboBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from m57_hid import M57

# ── Audio / visualizer constants (mirrors viz_matrix.py) ───────────────────
RATE       = 48000
CHANNELS   = 2
FPS        = 20
DECAY      = 15
AUTO_DECAY = 0.995
AUTO_FLOOR = 80.0
AUTO_LEVEL = 0.85
N_BANDS    = 12
N_LEVELS   = 5
CHUNK_BYTES = int(RATE * CHANNELS * 2 / FPS)
BAND_EDGES  = np.geomspace(60, 12000, N_BANDS + 1)

LED_POS = [
    (0,12),(16,12),(32,12),(48,12),(64,12),(80,12),
    (0,25),(16,25),(32,25),(48,25),(64,25),(80,25),(96,25),
    (0,38),(16,38),(32,38),(48,38),(64,38),(80,38),(96,38),
    (0,51),(16,51),(32,51),(48,51),(64,51),(80,51),
    (32,63),(48,63),(64,63),
    (128,12),(144,12),(160,12),(178,12),(194,12),(210,12),
    (112,25),(128,25),(144,25),(160,25),(178,25),(194,25),(210,25),
    (112,38),(128,38),(144,38),(160,38),(178,38),(194,38),(210,38),
    (128,51),(144,51),(160,51),(178,51),(194,51),(210,51),
    (112,63),(128,63),(144,63),
]
LED_MAP = [
    (min(x * N_BANDS // 224, N_BANDS - 1),
     (N_LEVELS - 1) - min(y * N_LEVELS // 64, N_LEVELS - 1))
    for x, y in LED_POS
]

PRESETS = {
    'Winamp': [(0,255,0),(160,255,0),(255,220,0),(255,80,0),(255,0,0)],
    'Purple': [(76,0,153),(180,0,255),(0,0,255),(0,255,255),(255,255,255)],
    'Ice':    [(0,80,255),(0,180,255),(0,255,255),(120,255,255),(255,255,255)],
    'Fire':   [(120,0,0),(255,0,0),(255,80,0),(255,180,0),(255,255,0)],
    'Neon':   [(255,0,128),(180,0,255),(0,0,255),(0,255,128),(255,255,0)],
    'Ocean':  [(0,10,60),(0,40,160),(0,120,255),(0,210,255),(180,255,255)],
}

DEFAULT_PALETTE = list(PRESETS['Winamp'])


def _get_default_monitor():
    result = subprocess.run(['pactl', 'info'], capture_output=True, text=True, check=True)
    for line in result.stdout.splitlines():
        if line.startswith('Default Sink:'):
            return line.split(':', 1)[1].strip() + '.monitor'
    return None

def _list_audio_sources():
    """Return list of (name, description) for all PulseAudio/PipeWire sources."""
    result = subprocess.run(['pactl', 'list', 'sources'], capture_output=True, text=True)
    sources, name, desc = [], None, None
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith('Name:'):
            name = line.split(':', 1)[1].strip()
        elif line.startswith('Description:'):
            desc = line.split(':', 1)[1].strip()
            if name and desc:
                sources.append((name, desc))
            name = desc = None
    return sources


# ── Viz worker thread ───────────────────────────────────────────────────────

class VizWorker(QThread):
    error = pyqtSignal(str)

    def __init__(self, kb, monitor):
        super().__init__()
        self._kb      = kb
        self._monitor = monitor
        self._running = False
        self._palette = list(DEFAULT_PALETTE)
        self._lock    = threading.Lock()
        self._display  = np.zeros(N_BANDS, dtype=np.float32)
        self._auto_max = np.ones(N_BANDS,  dtype=np.float32) * AUTO_FLOOR

    def set_palette(self, palette):
        with self._lock:
            self._palette = list(palette)

    def stop(self):
        self._running = False

    def _calc_frame(self, samples):
        windowed = samples * np.hanning(samples.size)
        fft      = np.abs(np.fft.rfft(windowed))
        freqs    = np.fft.rfftfreq(samples.size, d=1.0 / RATE)
        raw = np.array([
            np.sqrt(np.mean(fft[mask])) if np.any(mask) else 0.0
            for mask in ((freqs >= lo) & (freqs < hi)
                         for lo, hi in zip(BAND_EDGES[:-1], BAND_EDGES[1:]))
        ], dtype=np.float32)
        self._auto_max[:] = np.maximum(raw, self._auto_max * AUTO_DECAY)
        self._auto_max[:] = np.maximum(self._auto_max, AUTO_FLOOR)
        normalized        = np.clip(raw / self._auto_max * 255 * AUTO_LEVEL, 0, 255)
        self._display[:]  = np.maximum(normalized, self._display - DECAY)
        heights = np.minimum((self._display * (N_LEVELS + 1) / 256).astype(int), N_LEVELS)
        with self._lock:
            pal = list(self._palette)
        frame = [(0, 0, 0)] * 58
        for led, (band, level) in enumerate(LED_MAP):
            if level < heights[band]:
                frame[led] = pal[level]
        return frame

    def run(self):
        self._running = True
        self._display[:]  = 0
        self._auto_max[:] = AUTO_FLOOR
        proc = subprocess.Popen(
            ['parec', '-d', self._monitor, '--format=s16le',
             f'--rate={RATE}', f'--channels={CHANNELS}', '--latency-msec=20'],
            stdout=subprocess.PIPE,
        )
        try:
            while self._running:
                data = proc.stdout.read(CHUNK_BYTES)
                if not data:
                    break
                samples = np.frombuffer(data, dtype=np.int16).reshape(-1, CHANNELS).mean(axis=1)
                self._kb.send_frame(self._calc_frame(samples))
        finally:
            proc.terminate()
            try:
                self._kb.send_frame([(0, 0, 0)] * 58)
            except Exception:
                pass


# ── Main window ─────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('M57 RGB Controller')
        self.palette  = list(DEFAULT_PALETTE)
        self.worker   = None
        self.kb       = None
        self._kb_paths = []   # (path, label) list

        self._build_ui()
        self._refresh_kb()
        self._refresh_audio()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        # ── Keyboard selector ───────────────────────────────────────────────
        kb_row = QHBoxLayout()
        kb_row.addWidget(QLabel('<b>Keyboard</b>'))
        self.kb_combo = QComboBox()
        self.kb_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        kb_row.addWidget(self.kb_combo)
        self.kb_connect_btn = QPushButton('Connect')
        self.kb_connect_btn.clicked.connect(self._connect_kb)
        kb_row.addWidget(self.kb_connect_btn)
        root.addLayout(kb_row)

        # ── Audio source selector ────────────────────────────────────────────
        audio_row = QHBoxLayout()
        audio_row.addWidget(QLabel('<b>Audio Source</b>'))
        self.audio_combo = QComboBox()
        self.audio_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        audio_row.addWidget(self.audio_combo)
        refresh_btn = QPushButton('↺')
        refresh_btn.setFixedWidth(32)
        refresh_btn.clicked.connect(self._refresh_audio)
        audio_row.addWidget(refresh_btn)
        root.addLayout(audio_row)
        self.audio_combo.currentIndexChanged.connect(self._on_audio_changed)

        line0 = QFrame()
        line0.setFrameShape(QFrame.Shape.HLine)
        line0.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(line0)

        # ── Effect buttons ──────────────────────────────────────────────────
        root.addWidget(QLabel('<b>Effect</b>'))
        eff_row = QHBoxLayout()
        self.btn_key   = QPushButton('Key Lighting')
        self.btn_fwviz = QPushButton('FW Visualizer')
        self.btn_pyviz = QPushButton('Python Viz')
        for btn in (self.btn_key, self.btn_fwviz, self.btn_pyviz):
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            eff_row.addWidget(btn)
        root.addLayout(eff_row)

        grp = QButtonGroup(self)
        grp.setExclusive(True)
        grp.addButton(self.btn_key)
        grp.addButton(self.btn_fwviz)
        grp.addButton(self.btn_pyviz)
        grp.buttonClicked.connect(self._on_effect)

        # ── Divider ─────────────────────────────────────────────────────────
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(line)

        # ── Palette editor ──────────────────────────────────────────────────
        pal_header = QHBoxLayout()
        pal_header.addWidget(QLabel('<b>Palette</b>  (click swatch to edit)'))
        pal_header.addStretch()
        pal_header.addWidget(QLabel('Preset:'))
        self.preset_box = QComboBox()
        self.preset_box.addItems(PRESETS.keys())
        self.preset_box.currentTextChanged.connect(self._on_preset)
        pal_header.addWidget(self.preset_box)
        root.addLayout(pal_header)
        pal_row = QHBoxLayout()
        pal_row.setSpacing(8)
        self._pal_btns = []
        level_labels = ['Low (0)', '1', '2', '3', 'High (4)']
        for i, label in enumerate(level_labels):
            col = QVBoxLayout()
            col.setSpacing(4)
            btn = QPushButton()
            btn.setFixedSize(56, 56)
            btn.clicked.connect(lambda _checked, idx=i: self._pick_color(idx))
            self._pal_btns.append(btn)
            self._refresh_swatch(i)
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            col.addWidget(btn)
            col.addWidget(lbl)
            pal_row.addLayout(col)
        root.addLayout(pal_row)

        root.addStretch()
        self.setMinimumWidth(520)
        self.adjustSize()

    def _on_audio_changed(self):
        if self.worker and self.worker.isRunning():
            self._start_viz()

    def _refresh_kb(self):
        self._kb_paths = M57.list_devices()
        self.kb_combo.blockSignals(True)
        self.kb_combo.clear()
        if self._kb_paths:
            for _, label in self._kb_paths:
                self.kb_combo.addItem(label)
            self._connect_kb()
        else:
            self.kb_combo.addItem('No device found')
        self.kb_combo.blockSignals(False)

    def _connect_kb(self):
        idx = self.kb_combo.currentIndex()
        if idx < 0 or idx >= len(self._kb_paths):
            return
        self._stop_viz()
        if self.kb:
            try:
                self.kb.close()
            except Exception:
                pass
        path, _ = self._kb_paths[idx]
        try:
            self.kb = M57(path=path)
            self.kb_connect_btn.setText('Connected ✓')
        except Exception as e:
            self.kb = None
            self.kb_connect_btn.setText('Error')
            print(f'connect error: {e}')

    def _refresh_audio(self):
        sources = _list_audio_sources()   # [(name, desc), ...]
        default = _get_default_monitor()
        self.audio_combo.blockSignals(True)
        self.audio_combo.clear()
        for name, desc in sources:
            self.audio_combo.addItem(desc, userData=name)
        # pre-select default sink monitor
        if default:
            for i in range(self.audio_combo.count()):
                if self.audio_combo.itemData(i) == default:
                    self.audio_combo.setCurrentIndex(i)
                    break
        self.audio_combo.blockSignals(False)

    def _on_preset(self, name):
        if name not in PRESETS:
            return
        self.palette = list(PRESETS[name])
        for i in range(N_LEVELS):
            self._refresh_swatch(i)
        if self.worker and self.worker.isRunning():
            self.worker.set_palette(self.palette)

    def _refresh_swatch(self, idx):
        r, g, b = self.palette[idx]
        luma = 0.299*r + 0.587*g + 0.114*b
        text_color = '#000' if luma > 128 else '#fff'
        self._pal_btns[idx].setStyleSheet(
            f'background-color: rgb({r},{g},{b}); color: {text_color}; '
            f'border: 2px solid #555; border-radius: 4px;'
        )

    def _pick_color(self, idx):
        r, g, b = self.palette[idx]
        color = QColorDialog.getColor(QColor(r, g, b), self, f'Level {idx} Color')
        if not color.isValid():
            return
        self.palette[idx] = (color.red(), color.green(), color.blue())
        self._refresh_swatch(idx)
        if self.worker and self.worker.isRunning():
            self.worker.set_palette(self.palette)

    def _on_effect(self, btn):
        if not self.kb:
            return
        if btn is not self.btn_pyviz:
            self._stop_viz()
        if btn is self.btn_key:
            self.kb.activate_dynamic_lights()
        elif btn is self.btn_fwviz:
            self.kb.activate_fw_visualizer()
        elif btn is self.btn_pyviz:
            self.kb.activate_viz_frame()
            self._start_viz()

    def _start_viz(self):
        self._stop_viz()
        if not self.kb:
            return
        monitor = self.audio_combo.currentData()
        if not monitor:
            return
        self.worker = VizWorker(self.kb, monitor)
        self.worker.set_palette(self.palette)
        self.worker.error.connect(lambda msg: print(f'worker error: {msg}'))
        self.worker.start()

    def _stop_viz(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
        self.worker = None

    def closeEvent(self, event):
        self._stop_viz()
        if self.kb:
            self.kb.close()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
