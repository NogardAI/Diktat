"""Vložení textu do aktivního okna přes schránku (původní obsah schránky se obnoví)."""
from __future__ import annotations

import time

import keyboard
import pyperclip


def paste(text: str) -> None:
    if not text:
        return
    try:
        previous = pyperclip.paste()
    except pyperclip.PyperclipException:
        previous = None
    pyperclip.copy(text)
    time.sleep(0.05)
    keyboard.send("ctrl+v")
    time.sleep(0.25)  # cílová aplikace musí stihnout vložit, než schránku vrátíme
    if previous is not None:
        try:
            pyperclip.copy(previous)
        except pyperclip.PyperclipException:
            pass
