"""Plovoucí "pilulka" dole uprostřed obrazovky. Neukrádá fokus."""
from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from typing import Callable

W, H = 220, 44
BG = "#1b1b1f"
TRANSPARENT = "#ff00ff"

STATES = {
    "recording": ("#ff4d4f", "Nahrávám"),
    "processing": ("#f5a623", "Zpracovávám…"),
    "loading": ("#5b8def", "Načítám model…"),
    "error": ("#ff4d4f", ""),
}


def _no_activate(root: tk.Tk) -> None:
    """WS_EX_NOACTIVATE + TOOLWINDOW: okno se nikdy nestane aktivním a není na liště."""
    if sys.platform != "win32":
        return
    GWL_EXSTYLE, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW, WS_EX_TOPMOST = -20, 0x08000000, 0x80, 0x8
    hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(
        hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
    )


class Overlay:
    def __init__(self, root: tk.Tk, level_source: Callable[[], float]):
        self.root = root
        self.level_source = level_source
        self.state: str | None = None
        self._hide_job = None
        self._phase = 0

        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=TRANSPARENT)
        try:
            root.attributes("-transparentcolor", TRANSPARENT)
        except tk.TclError:
            pass
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{W}x{H}+{(sw - W) // 2}+{sh - H - 70}")

        self.canvas = tk.Canvas(root, width=W, height=H, bg=TRANSPARENT, highlightthickness=0)
        self.canvas.pack()
        self._pill(2, 2, W - 2, H - 2, (H - 4) // 2, fill=BG, outline="#3a3a40")
        self.dot = self.canvas.create_oval(16, H // 2 - 6, 28, H // 2 + 6, fill="#ff4d4f", outline="")
        self.label = self.canvas.create_text(40, H // 2, anchor="w", fill="#f2f2f2",
                                             font=("Segoe UI", 11), text="")
        self.bars = [self.canvas.create_rectangle(0, 0, 0, 0, fill="#ff4d4f", outline="")
                     for _ in range(5)]

        root.update_idletasks()
        _no_activate(root)
        root.withdraw()
        self._tick()

    def _pill(self, x1, y1, x2, y2, r, **kw):
        c = self.canvas
        c.create_oval(x1, y1, x1 + 2 * r, y2, **kw)
        c.create_oval(x2 - 2 * r, y1, x2, y2, **kw)
        c.create_rectangle(x1 + r, y1, x2 - r, y2, fill=kw["fill"], outline="")
        c.create_line(x1 + r, y1, x2 - r, y1, fill=kw["outline"])
        c.create_line(x1 + r, y2, x2 - r, y2, fill=kw["outline"])

    def show(self, state: str, text: str | None = None, hide_after_ms: int | None = None) -> None:
        if self._hide_job:
            self.root.after_cancel(self._hide_job)
            self._hide_job = None
        self.state = state
        color, default = STATES[state]
        self.canvas.itemconfigure(self.dot, fill=color)
        self.canvas.itemconfigure(self.label, text=text or default)
        for b in self.bars:
            self.canvas.coords(b, 0, 0, 0, 0)
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        if hide_after_ms:
            self._hide_job = self.root.after(hide_after_ms, self.hide)

    def hide(self) -> None:
        self.state = None
        self.root.withdraw()

    def _tick(self) -> None:
        self._phase += 1
        if self.state == "recording":
            lvl = self.level_source()
            x0 = W - 70
            for i, b in enumerate(self.bars):
                wobble = 0.55 + 0.45 * ((self._phase + i * 3) % 7) / 6
                h = 4 + int(22 * lvl * wobble)
                x = x0 + i * 10
                self.canvas.coords(b, x, H // 2 - h // 2, x + 5, H // 2 + h // 2)
        elif self.state in ("processing", "loading"):
            on = (self._phase // 6) % 2 == 0
            self.canvas.itemconfigure(self.dot, fill=STATES[self.state][0] if on else BG)
        self.root.after(50, self._tick)
