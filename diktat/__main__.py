"""Spuštění: python -m diktat"""
from __future__ import annotations

import logging
import queue
import threading
import time
import tkinter as tk

from . import config as cfgmod
from .config import CONFIG_PATH, ROOT
from .hotkey import PushToTalk
from .overlay import Overlay
from .recorder import SAMPLE_RATE, Recorder
from .tray import Tray

log = logging.getLogger("diktat")


def save_wav(audio, path) -> None:
    """Uloží poslední nahrávku (pro ladění přesnosti přepisu)."""
    import wave

    import numpy as np

    try:
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    except OSError:
        pass


class App:
    def __init__(self) -> None:
        self.cfg = cfgmod.load()
        self.recorder = Recorder()
        self.transcriber = None
        self.cleaner = None
        self.ui: queue.Queue = queue.Queue()  # (metoda, args) pro Tk vlákno
        self.jobs: queue.Queue = queue.Queue()  # nahrávky ke zpracování
        self.ready = False

        self.root = tk.Tk()
        self.overlay = Overlay(self.root, lambda: self.recorder.level)
        self.tray = Tray(
            get_cleanup=lambda: self.cfg.cleanup_enabled,
            set_cleanup=self.set_cleanup,
            config_path=str(CONFIG_PATH),
            on_quit=lambda: self.ui.put((self.quit, ())),
        )
        self.ptt = PushToTalk(self.cfg.hotkey, self.on_start, self.on_stop, self.on_cancel)

    # --- vlákno UI -------------------------------------------------------
    def _pump(self) -> None:
        while True:
            try:
                fn, args = self.ui.get_nowait()
            except queue.Empty:
                break
            fn(*args)
        self.root.after(30, self._pump)

    def show(self, *args, **kw) -> None:
        self.ui.put((lambda: self.overlay.show(*args, **kw), ()))

    def hide(self) -> None:
        self.ui.put((self.overlay.hide, ()))

    # --- klávesa ---------------------------------------------------------
    def on_start(self) -> None:
        if not self.ready:
            self.show("loading", hide_after_ms=1500)
            return
        try:
            self.recorder.start()
        except Exception as exc:
            log.exception("Mikrofon nejde spustit")
            self.show("error", f"Mikrofon: {exc.__class__.__name__}", hide_after_ms=3000)
            return
        self._t0 = time.perf_counter()
        self.show("recording")
        self.tray.set_state("recording", "Nahrávám")

    def on_cancel(self) -> None:
        if self.recorder.recording:
            self.recorder.stop()
            self.hide()
            self.tray.set_state("ready", "Připraveno")

    def on_stop(self) -> None:
        if not self.recorder.recording:
            return
        audio = self.recorder.stop()
        if len(audio) < self.cfg.min_seconds * SAMPLE_RATE:
            self.hide()
            self.tray.set_state("ready", "Připraveno")
            return
        self.show("processing")
        self.tray.set_state("busy", "Zpracovávám")
        self.jobs.put(audio)

    # --- zpracování ------------------------------------------------------
    def worker(self) -> None:
        from .cleanup import Cleaner
        from .inserter import paste
        from .transcriber import Transcriber

        c = self.cfg
        self.cleaner = Cleaner(c.ollama_url, c.cleanup_model, c.cleanup_timeout, c.keep_alive)
        if c.cleanup_enabled:
            threading.Thread(target=self.cleaner.warmup, daemon=True).start()
        try:
            self.transcriber = Transcriber(c.whisper_model, c.language, c.device, c.compute_type, c.vocabulary)
        except Exception as exc:
            log.exception("Whisper se nenačetl")
            self.tray.set_state("error", "Chyba načtení modelu")
            self.tray.notify(f"Whisper se nenačetl: {exc}")
            return
        if self.transcriber.warning:
            self.tray.notify(self.transcriber.warning)
        self.ready = True
        self.tray.set_state("ready", f"Připraveno ({c.hotkey}, {self.transcriber.device})")
        log.info("Připraveno")

        while True:
            audio = self.jobs.get()
            if audio is None:
                return
            try:
                save_wav(audio, ROOT / "last.wav")
                t0 = time.perf_counter()
                raw = text = self.transcriber.transcribe(audio)
                t1 = time.perf_counter()
                if text and self.cfg.cleanup_enabled:
                    text = self.cleaner.polish(text)
                t2 = time.perf_counter()
                log.info("whisper %.2fs: %s", t1 - t0, raw)
                log.info("cleanup %.2fs: %s", t2 - t1, text)
                if text:
                    paste(text + (" " if self.cfg.trailing_space else ""))
                    self.hide()
                else:
                    self.show("error", "Nic jsem neslyšel", hide_after_ms=1500)
            except Exception as exc:
                log.exception("Zpracování selhalo")
                self.show("error", f"Chyba: {exc.__class__.__name__}", hide_after_ms=3000)
            self.tray.set_state("ready", f"Připraveno ({self.cfg.hotkey}, {self.transcriber.device})")

    def set_cleanup(self, enabled: bool) -> None:
        self.cfg.cleanup_enabled = enabled
        cfgmod.save_cleanup_enabled(enabled)
        if enabled and self.cleaner:
            threading.Thread(target=self.cleaner.warmup, daemon=True).start()

    def quit(self) -> None:
        self.ptt.stop()
        self.jobs.put(None)
        self.tray.stop()
        self.root.destroy()

    def run(self) -> None:
        self.tray.run()
        self.tray.set_state("busy", "Načítám model…")
        self.ptt.start()
        threading.Thread(target=self.worker, daemon=True).start()
        self.root.after(30, self._pump)
        self.root.mainloop()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(ROOT / "diktat.log", encoding="utf-8"), logging.StreamHandler()],
    )
    App().run()


if __name__ == "__main__":
    main()
