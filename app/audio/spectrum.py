"""Real-time audio spectrum from PulseAudio monitor (parec + FFT)."""

from __future__ import annotations

import logging
import os
import subprocess
from typing import List, Optional

from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)

DEFAULT_MONITOR = os.environ.get(
    "RADIO_MONITOR_SOURCE",
    "alsa_output.platform-bcm2835_audio.analog-stereo.monitor",
)
SAMPLE_RATE = 44100
CHUNK = 2048
BANDS = 24
FREQ_MIN_HZ = 80
FREQ_MAX_HZ = 10_000
FREQ_LABELS_HZ = (80, 200, 500, 1000, 2000, 5000, 10_000)


class SpectrumAnalyzer(QThread):
    """Capture PCM from PulseAudio monitor and emit normalized band levels."""

    levels_ready = pyqtSignal(list)

    def __init__(self, monitor: str = DEFAULT_MONITOR, parent=None) -> None:
        super().__init__(parent)
        self._monitor = monitor
        self._running = False
        self._proc: Optional[subprocess.Popen] = None
        self._smooth: List[float] = [0.08] * BANDS
        self._numpy = None

    def stop(self) -> None:
        self._running = False
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None

    def run(self) -> None:
        try:
            import numpy as np
        except ImportError:
            logger.warning("numpy not available — spectrum disabled")
            return

        self._numpy = np
        self._running = True
        try:
            self._proc = subprocess.Popen(
                [
                    "parec",
                    f"--device={self._monitor}",
                    "--format=s16le",
                    f"--rate={SAMPLE_RATE}",
                    "--channels=1",
                    "--latency-msec=80",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            logger.error("parec failed: %s", exc)
            return

        assert self._proc.stdout is not None
        edges = np.logspace(np.log10(FREQ_MIN_HZ), np.log10(FREQ_MAX_HZ), BANDS + 1)
        freqs = np.fft.rfftfreq(CHUNK, 1.0 / SAMPLE_RATE)
        window = np.hanning(CHUNK)

        while self._running and self._proc.poll() is None:
            raw = self._proc.stdout.read(CHUNK * 2)
            if len(raw) < CHUNK * 2:
                continue
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            spectrum = np.abs(np.fft.rfft(samples * window))
            bands: List[float] = []
            for i in range(BANDS):
                mask = (freqs >= edges[i]) & (freqs < edges[i + 1])
                val = float(spectrum[mask].mean()) if mask.any() else 0.0
                bands.append(val)

            peak = max(bands) or 1e-9
            for i, val in enumerate(bands):
                norm = min(1.0, (val / peak) * 0.72 + 0.06)
                self._smooth[i] += (norm - self._smooth[i]) * 0.38

            self.levels_ready.emit(list(self._smooth))

        self.stop()
