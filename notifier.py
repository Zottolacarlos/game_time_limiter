from __future__ import annotations
from win10toast import ToastNotifier

toaster = ToastNotifier()
_notify_ok = True


def notify(msg: str):
    """Show Windows toast, swallow errors."""
    global _notify_ok
    if not _notify_ok:
        return
    try:
        toaster.show_toast("Límite de juego", msg, threaded=True, duration=5)
    except Exception:
        _notify_ok = False
