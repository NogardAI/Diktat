"""Načtení a uložení config.toml."""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.toml"


@dataclass
class Config:
    hotkey: str = "right ctrl"
    min_seconds: float = 0.3
    whisper_model: str = "large-v3-turbo"
    language: str = "cs"
    device: str = "cuda"
    compute_type: str = "float16"
    vocabulary: str = ""
    cleanup_enabled: bool = True
    ollama_url: str = "http://127.0.0.1:11434"
    cleanup_model: str = "gemma4:e4b"
    cleanup_timeout: float = 8.0
    keep_alive: str = "30m"
    trailing_space: bool = True


def load(path: Path = CONFIG_PATH) -> Config:
    if not path.exists():
        return Config()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    hk, wh, cl, ins = (data.get(k, {}) for k in ("hotkey", "whisper", "cleanup", "insert"))
    d = Config()
    return Config(
        hotkey=hk.get("key", d.hotkey),
        min_seconds=float(hk.get("min_seconds", d.min_seconds)),
        whisper_model=wh.get("model", d.whisper_model),
        language=wh.get("language", d.language),
        device=wh.get("device", d.device),
        compute_type=wh.get("compute_type", d.compute_type),
        vocabulary=wh.get("vocabulary", d.vocabulary),
        cleanup_enabled=bool(cl.get("enabled", d.cleanup_enabled)),
        ollama_url=cl.get("ollama_url", d.ollama_url).rstrip("/"),
        cleanup_model=cl.get("model", d.cleanup_model),
        cleanup_timeout=float(cl.get("timeout_seconds", d.cleanup_timeout)),
        keep_alive=str(cl.get("keep_alive", d.keep_alive)),
        trailing_space=bool(ins.get("trailing_space", d.trailing_space)),
    )


def save_cleanup_enabled(enabled: bool, path: Path = CONFIG_PATH) -> None:
    """Přepíše jen hodnotu [cleanup] enabled, komentáře v souboru zůstanou."""
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r"(\[cleanup\][^\[]*?^enabled\s*=\s*)(true|false)", re.M | re.S)
    new = pattern.sub(lambda m: m.group(1) + ("true" if enabled else "false"), text, count=1)
    path.write_text(new, encoding="utf-8")
