"""Nahrávání z mikrofonu do paměti (16 kHz mono float32)."""
from __future__ import annotations

import threading

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000


class Recorder:
    def __init__(self) -> None:
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self.level = 0.0  # aktuální hlasitost 0..1 pro indikátor

    def _callback(self, indata, frames, time_info, status) -> None:
        mono = indata[:, 0].copy()
        with self._lock:
            self._chunks.append(mono)
        rms = float(np.sqrt(np.mean(mono**2))) if len(mono) else 0.0
        self.level = min(1.0, rms * 12)

    def start(self) -> None:
        with self._lock:
            self._chunks = []
        self.level = 0.0
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=self._callback
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self.level = 0.0
        with self._lock:
            if not self._chunks:
                return np.zeros(0, dtype=np.float32)
            return np.concatenate(self._chunks)

    @property
    def recording(self) -> bool:
        return self._stream is not None
