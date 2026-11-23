"""Přepis řeči přes faster-whisper. Model se načte jednou a drží v paměti."""
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)


def _add_cuda_dll_dirs() -> None:
    """Na Windows zpřístupní DLL z pip balíčků nvidia-cublas-cu12 / nvidia-cudnn-cu12."""
    if sys.platform != "win32":
        return
    for base in map(Path, sys.path):
        nvidia = base / "nvidia"
        if not nvidia.is_dir():
            continue
        for bin_dir in nvidia.glob("*/bin"):
            try:
                os.add_dll_directory(str(bin_dir))
            except OSError:
                pass
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")


def _stub_av_if_blocked() -> None:
    """PyAV (dekódování souborů) Smart App Control blokuje. Audio předáváme jako numpy,
    takže av nepotřebujeme - nahradíme ho prázdným modulem, aby šel faster_whisper importovat."""
    try:
        import av  # noqa: F401
    except ImportError:
        import types

        for name in list(sys.modules):
            if name == "av" or name.startswith("av."):
                del sys.modules[name]
        sys.modules["av"] = types.ModuleType("av")


_add_cuda_dll_dirs()
_stub_av_if_blocked()

from faster_whisper import WhisperModel  # noqa: E402


class Transcriber:
    def __init__(self, model: str, language: str, device: str, compute_type: str, vocabulary: str = ""):
        self.language = language
        self.vocabulary = vocabulary.strip()
        self.warning: str | None = None
        self.device = device
        try:
            self._model = self._load(model, device, compute_type)
        except Exception as exc:  # GPU nedostupná / nepodporovaná -> CPU
            if device == "cpu":
                raise
            log.exception("Načtení na %s selhalo, přepínám na CPU", device)
            self.warning = f"GPU nefunguje ({exc.__class__.__name__}), běžím na CPU – pomalejší."
            self.device = "cpu"
            self._model = self._load(model, "cpu", "int8")

    def _load(self, model: str, device: str, compute_type: str) -> WhisperModel:
        if device == "cpu" and compute_type == "float16":
            compute_type = "int8"
        m = WhisperModel(model, device=device, compute_type=compute_type)
        # zahřátí - odhalí chybějící CUDA knihovny hned při startu, ne při prvním diktátu
        list(m.transcribe(np.zeros(16000, dtype=np.float32), language=self.language)[0])
        return m

    def transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self._model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=self.vocabulary or None,
        )
        return " ".join(s.text.strip() for s in segments).strip()


if __name__ == "__main__":
    # python -m diktat.transcriber soubor.wav
    import wave

    from .config import load

    logging.basicConfig(level=logging.INFO)
    cfg = load()
    t0 = time.perf_counter()
    tr = Transcriber(cfg.whisper_model, cfg.language, cfg.device, cfg.compute_type, cfg.vocabulary)
    print(f"Model načten za {time.perf_counter() - t0:.1f} s, device={tr.device}")
    if tr.warning:
        print("VAROVÁNÍ:", tr.warning)
    if len(sys.argv) > 1:
        with wave.open(sys.argv[1], "rb") as w:
            raw = w.readframes(w.getnframes())
            rate, ch = w.getframerate(), w.getnchannels()
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
        if ch > 1:
            audio = audio.reshape(-1, ch).mean(axis=1)
        if rate != 16000:
            idx = np.linspace(0, len(audio) - 1, int(len(audio) * 16000 / rate))
            audio = np.interp(idx, np.arange(len(audio)), audio).astype(np.float32)
        t0 = time.perf_counter()
        print("Text:", tr.transcribe(audio))
        print(f"Přepis za {time.perf_counter() - t0:.2f} s")
