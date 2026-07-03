#!/usr/bin/env python3
import os, sys, subprocess, threading, time
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
from send_palette_from_image import (
    image_to_pixels, filter_pixels, extract_palette,
    get_current_wallpaper, load_image, CAELESTIA_WALLPAPER_PATH,
)
from send_palette_from_screen import (
    grab_active_monitor, extract_dominant_palette, palette_distance,
)
from ambient_screen import capture_tiny, sample_zones, pick_palette
from viz_render import (
    N_BANDS, N_LEVELS,
    render_bars, render_center, render_waterdrop, WaterdropState,
)

# ── Audio constants ─────────────────────────────────────────────────────────
RATE        = 48000
CHANNELS    = 2
FPS         = 20
DECAY       = 15
AUTO_DECAY  = 0.995
AUTO_FLOOR  = 80.0
AUTO_LEVEL  = 0.85
CHUNK_BYTES = int(RATE * CHANNELS * 2 / FPS)
BAND_EDGES  = np.geomspace(60, 12000, N_BANDS + 1)

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
        self._kb           = kb
        self._monitor      = monitor
        self._running      = False
        self._palette      = list(DEFAULT_PALETTE)
        self._render_mode  = 0
        self._lock         = threading.Lock()
        self._display      = np.zeros(N_BANDS, dtype=np.float32)
        self._auto_max     = np.ones(N_BANDS,  dtype=np.float32) * AUTO_FLOOR
        self._drops        = WaterdropState()

    def set_palette(self, palette):
        with self._lock:
            self._palette = list(palette)

    def set_render_mode(self, mode):
        with self._lock:
            self._render_mode = mode
            if mode == 4:
                self._drops = WaterdropState()

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
        with self._lock:
            pal  = list(self._palette)
            mode = self._render_mode
        if mode == 1:
            return render_bars(self._display, pal, outline=True)
        if mode == 2:
            return render_center(self._display, pal, kitt=False)
        if mode == 3:
            return render_center(self._display, pal, kitt=True)
        if mode == 4:
            return render_waterdrop(self._display, pal, self._drops)
        return render_bars(self._display, pal, outline=False)

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


# ── Palette source workers ───────────────────────────────────────────────────

class WPWatchWorker(QThread):
    palette_ready = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self._running = False
        self._proc    = None

    def stop(self):
        self._running = False
        if self._proc:
            self._proc.terminate()

    def _fire(self):
        try:
            img = load_image(get_current_wallpaper())
            pal = pick_palette(sample_zones(img))
            self.palette_ready.emit([(int(c[0]), int(c[1]), int(c[2])) for c in pal])
        except Exception as e:
            print(f'WPWatch: {e}')

    def run(self):
        self._running = True
        self._fire()
        self._proc = subprocess.Popen(
            ['inotifywait', '-m', '-e', 'modify', str(CAELESTIA_WALLPAPER_PATH)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        for _ in self._proc.stdout:
            if not self._running:
                break
            self._fire()
        self._proc.terminate()


class AmbientWorker(QThread):
    palette_ready = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self._running = False

    def stop(self):
        self._running = False

    def run(self):
        self._running = True
        last = None
        while self._running:
            t0 = time.monotonic()
            try:
                img = capture_tiny(scale=0.15)
                pal = pick_palette(sample_zones(img))
                if last is None or palette_distance(last, pal) >= 8.0:
                    last = pal.copy()
                    self.palette_ready.emit([(int(c[0]), int(c[1]), int(c[2])) for c in pal])
            except Exception as e:
                print(f'Ambient: {e}')
            remaining = 0.5 - (time.monotonic() - t0)
            if remaining > 0:
                # sleep in small chunks for responsive stop
                for _ in range(int(remaining / 0.05)):
                    if not self._running:
                        break
                    time.sleep(0.05)


# ── Main window ─────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    _palette_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('M57 RGB Controller')
        self.palette      = list(DEFAULT_PALETTE)
        self.worker       = None
        self.kb           = None
        self._kb_paths    = []
        self.wp_worker    = None
        self.ambient_worker = None
        self._palette_signal.connect(self._apply_palette)

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
        self.btn_pyviz = QPushButton('Python Viz')
        for btn in (self.btn_key, self.btn_pyviz):
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            eff_row.addWidget(btn)
        root.addLayout(eff_row)

        grp = QButtonGroup(self)
        grp.setExclusive(True)
        grp.addButton(self.btn_key)
        grp.addButton(self.btn_pyviz)
        grp.buttonClicked.connect(self._on_effect)

        # ── Render mode buttons ─────────────────────────────────────────────
        root.addWidget(QLabel('<b>Render Mode</b>'))
        mode_row = QHBoxLayout()
        self._mode_btns = []
        for label in ('Bars', 'Dots', 'Center', 'Kitt', 'Waterdrop'):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            mode_row.addWidget(btn)
            self._mode_btns.append(btn)
        self._mode_btns[0].setChecked(True)
        mode_grp = QButtonGroup(self)
        mode_grp.setExclusive(True)
        for i, btn in enumerate(self._mode_btns):
            mode_grp.addButton(btn, i)
        mode_grp.idClicked.connect(self._on_render_mode)
        root.addLayout(mode_row)

        # ── Divider ─────────────────────────────────────────────────────────
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(line)

        # ── Palette source ──────────────────────────────────────────────────
        root.addWidget(QLabel('<b>Palette Source</b>'))
        src_row = QHBoxLayout()
        self.btn_shot = QPushButton('Color-Shot')
        self.btn_shot.setToolTip('One-shot: extract palette from active monitor')
        self.btn_shot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_shot.clicked.connect(self._color_shot)

        self.btn_wpwatch = QPushButton('WPWatch')
        self.btn_wpwatch.setCheckable(True)
        self.btn_wpwatch.setToolTip('Follow wallpaper changes (Caelestia/Hyprland)')
        self.btn_wpwatch.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_wpwatch.toggled.connect(self._toggle_wpwatch)

        self.btn_ambient = QPushButton('Ambient')
        self.btn_ambient.setCheckable(True)
        self.btn_ambient.setToolTip('Continuously track active monitor colors (~5s interval)')
        self.btn_ambient.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_ambient.toggled.connect(self._toggle_ambient)

        for btn in (self.btn_shot, self.btn_wpwatch, self.btn_ambient):
            src_row.addWidget(btn)
        root.addLayout(src_row)

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(line2)

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

    def _apply_palette(self, palette):
        self.palette = list(palette)
        for i in range(N_LEVELS):
            self._refresh_swatch(i)
        if self.worker and self.worker.isRunning():
            self.worker.set_palette(self.palette)

    def _on_preset(self, name):
        if name not in PRESETS:
            return
        self._apply_palette(list(PRESETS[name]))

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
        self._apply_palette(self.palette)

    def _color_shot(self):
        def _run():
            try:
                img = grab_active_monitor()
                pix = filter_pixels(image_to_pixels(img, size=96))
                pal = extract_dominant_palette(pix, gamma=1.5)
                self._palette_signal.emit([(int(c[0]), int(c[1]), int(c[2])) for c in pal])
            except Exception as e:
                print(f'Color-Shot: {e}')
        threading.Thread(target=_run, daemon=True).start()

    def _toggle_wpwatch(self, checked):
        if checked:
            if self.btn_ambient.isChecked():
                self.btn_ambient.setChecked(False)
            self.wp_worker = WPWatchWorker()
            self.wp_worker.palette_ready.connect(self._apply_palette)
            self.wp_worker.start()
        else:
            if self.wp_worker:
                self.wp_worker.stop()
                self.wp_worker.wait(2000)
                self.wp_worker = None

    def _toggle_ambient(self, checked):
        if checked:
            if self.btn_wpwatch.isChecked():
                self.btn_wpwatch.setChecked(False)
            self.ambient_worker = AmbientWorker()
            self.ambient_worker.palette_ready.connect(self._apply_palette)
            self.ambient_worker.start()
        else:
            if self.ambient_worker:
                self.ambient_worker.stop()
                self.ambient_worker.wait(2000)
                self.ambient_worker = None

    def _on_render_mode(self, mode_id):
        if self.worker and self.worker.isRunning():
            self.worker.set_render_mode(mode_id)

    def _on_effect(self, btn):
        if not self.kb:
            return
        if btn is not self.btn_pyviz:
            self._stop_viz()
        if btn is self.btn_key:
            self.kb.activate_dynamic_lights()
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
        mode = next((i for i, b in enumerate(self._mode_btns) if b.isChecked()), 0)
        self.worker = VizWorker(self.kb, monitor)
        self.worker.set_palette(self.palette)
        self.worker.set_render_mode(mode)
        self.worker.error.connect(lambda msg: print(f'worker error: {msg}'))
        self.worker.start()

    def _stop_viz(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
        self.worker = None

    def closeEvent(self, event):
        self._stop_viz()
        if self.wp_worker:
            self.wp_worker.stop()
            self.wp_worker.wait(2000)
        if self.ambient_worker:
            self.ambient_worker.stop()
            self.ambient_worker.wait(2000)
        if self.kb:
            self.kb.close()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
