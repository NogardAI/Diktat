"""Ikona v systémové liště."""
from __future__ import annotations

import os
from typing import Callable

import pystray
from PIL import Image, ImageDraw

COLORS = {"ready": "#3ddc84", "recording": "#ff4d4f", "busy": "#f5a623", "error": "#9e9e9e"}


def _icon(color: str) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, 62, 62), fill="#1b1b1f")
    d.rounded_rectangle((24, 12, 40, 38), radius=8, fill=color)       # mikrofon
    d.arc((17, 22, 47, 46), start=0, end=180, fill=color, width=4)    # držák
    d.line((32, 46, 32, 53), fill=color, width=4)
    d.line((24, 53, 40, 53), fill=color, width=4)
    return img


class Tray:
    def __init__(
        self,
        get_cleanup: Callable[[], bool],
        set_cleanup: Callable[[bool], None],
        config_path: str,
        on_quit: Callable[[], None],
    ):
        self._get_cleanup = get_cleanup
        self._set_cleanup = set_cleanup
        self._status = "Načítám…"
        menu = pystray.Menu(
            pystray.MenuItem(lambda _: self._status, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Úprava textu (Gemma)",
                lambda: self._set_cleanup(not self._get_cleanup()),
                checked=lambda _: self._get_cleanup(),
            ),
            pystray.MenuItem("Otevřít nastavení", lambda: os.startfile(config_path)),
            pystray.MenuItem("Konec", lambda: on_quit()),
        )
        self.icon = pystray.Icon("diktat", _icon(COLORS["busy"]), "Diktát", menu)

    def set_state(self, state: str, status: str) -> None:
        self._status = status
        self.icon.icon = _icon(COLORS[state])
        self.icon.title = f"Diktát – {status}"
        self.icon.update_menu()

    def notify(self, message: str) -> None:
        try:
            self.icon.notify(message, "Diktát")
        except Exception:
            pass

    def run(self) -> None:
        self.icon.run_detached()

    def stop(self) -> None:
        self.icon.stop()
