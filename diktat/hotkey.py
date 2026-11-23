"""Globální push-to-talk klávesa.

Držení klávesy = nahrávání. Pokud během držení zmáčkneš jinou klávesu
(např. pravý Ctrl+C), bere se to jako běžná zkratka a nahrávka se zruší.
"""
from __future__ import annotations

from typing import Callable

import keyboard


class PushToTalk:
    def __init__(
        self,
        key: str,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        on_cancel: Callable[[], None],
    ):
        self.key = key
        self._codes = set(keyboard.key_to_scan_codes(key))
        self.on_start, self.on_stop, self.on_cancel = on_start, on_stop, on_cancel
        self._held = False
        self._cancelled = False
        self._hook = None

    def _is_ours(self, event: keyboard.KeyboardEvent) -> bool:
        return event.scan_code in self._codes and (event.name or "").lower() == self.key.lower()

    def _handle(self, event: keyboard.KeyboardEvent) -> None:
        ours = self._is_ours(event)
        if event.event_type == keyboard.KEY_DOWN:
            if ours:
                if not self._held:  # ignoruj autorepeat při držení
                    self._held = True
                    self._cancelled = False
                    self.on_start()
            elif self._held and not self._cancelled:
                self._cancelled = True
                self.on_cancel()
        elif event.event_type == keyboard.KEY_UP and ours and self._held:
            self._held = False
            if not self._cancelled:
                self.on_stop()

    def start(self) -> None:
        self._hook = keyboard.hook(self._handle)

    def stop(self) -> None:
        if self._hook is not None:
            keyboard.unhook(self._hook)
            self._hook = None
