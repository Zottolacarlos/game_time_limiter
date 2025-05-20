from __future__ import annotations
from datetime import timedelta


def parse_timedelta(text: str) -> timedelta:
    """Convert strings like '2h', '90m', '45s', '10min' → timedelta."""
    text = text.strip().lower()
    units = {
        "h": 3600,
        "hr": 3600,
        "hour": 3600,
        "m": 60,
        "min": 60,
        "minute": 60,
        "s": 1,
        "sec": 1,
        "second": 1,
    }
    for suf, factor in units.items():
        if text.endswith(suf):
            try:
                val = float(text[: -len(suf)])
            except ValueError:
                break
            return timedelta(seconds=int(val * factor))
    raise ValueError("Tiempo inválido (ej. 2h, 90m, 45s, 10min)")