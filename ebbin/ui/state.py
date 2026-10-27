"""Module-level holders shared by UI tasks (no aqt imports)."""
from __future__ import annotations

_engine = None
pending_popup: dict | None = None  # session-summary payload waiting to be shown by ui/popup.py


def get_engine():
    return _engine


def set_engine(engine) -> None:
    global _engine
    _engine = engine


def set_pending_popup(payload: dict | None) -> None:
    global pending_popup
    pending_popup = payload


def take_pending_popup() -> dict | None:
    global pending_popup
    payload, pending_popup = pending_popup, None
    return payload
