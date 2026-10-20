"""Crash and error log: nothing fails silently any more.

Writes build/creator.log (kept small), and shows a message box on a crash so the window never just vanishes.
"""
from __future__ import annotations

import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
from types import TracebackType

from src.core.paths import WORK_DIR

LOG_PATH = WORK_DIR / "creator.log"
_logger = logging.getLogger("creator")


def install() -> None:
    """Start logging to build/creator.log and route uncaught exceptions (also from threads) into it."""
    try:
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(LOG_PATH, maxBytes=500_000, backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        _logger.addHandler(handler)
        _logger.setLevel(logging.INFO)
    except OSError as exc:
        print(f"Warning: Could not initialize log file at {LOG_PATH}: {exc}", file=sys.stderr)
    sys.excepthook = lambda kind, value, tb: report(kind, value, tb)
    try:
        import threading
        threading.excepthook = lambda args: report(args.exc_type, args.exc_value, args.exc_traceback)
    except (ImportError, AttributeError):
        pass


def info(text: str) -> None:
    _logger.info(text)


def report(kind: type[BaseException], value: BaseException, tb: TracebackType | None, show: bool = True) -> str:
    """Log an exception and (by default) tell the user where to find it. Returns the formatted traceback."""
    text = "".join(traceback.format_exception(kind, value, tb))
    _logger.error(text)
    print(text, file=sys.stderr)
    if show:
        _show(f"{getattr(kind, '__name__', 'Error')}: {value}\n\nFull details: {LOG_PATH}")
    return text


def _show(message: str) -> None:
    try:
        from tkinter import messagebox
        messagebox.showerror("Disney Infinity Creator", message)
    except (ImportError, RuntimeError) as exc:
        _logger.warning("Could not display GUI error dialog: %s", exc)
