# game_time_limiter.py
"""
Python daemon (Windows service‑ready) that enforces a daily game‑time limit for
Steam games. Detects when a new game (child of Steam) starts, logs it, counts
playtime, and when the limit is hit it terminates all running games first and
then Steam itself.

🛠️ **v0.6 – 2025‑05‑19**
• **Filtro de auxiliares**: ya no se registran ni cuentan procesos
  `steamwebhelper.exe`, `GameOverlayUI.exe`, etc.
  ‑ Evita la "avalancha" de logs y el tiempo fantasma cuando el juego ya salió.
• Estos auxiliares siguen cerrándose al agotar el tiempo.

Uso de prueba:
```
python Main.py --reset --limit 10min   # refresco 5 min (POLL_INTERVAL)
```
Dependencias: `pip install psutil win10toast pywin32`
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set

import psutil
from win10toast import ToastNotifier

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
DEFAULT_LIMIT = timedelta(hours=2)
POLL_INTERVAL = 300  # 5 min
USAGE_FILE = Path(__file__).with_name("usage.json")

# Procesos auxiliares que NO queremos contar ni loguear como juego
IGNORE_NAMES = {
    "steamwebhelper.exe",
    "gameoverlayui.exe",
}

# ---------------------------------------------------------------------------
# Toast helper
# ---------------------------------------------------------------------------

toaster = ToastNotifier()
_notify_ok = True  # se desactiva si win10toast falla


def notify(msg: str):
    global _notify_ok
    if not _notify_ok:
        return
    try:
        toaster.show_toast("Límite de juego", msg, threaded=True, duration=5)
    except Exception:
        _notify_ok = False

# ---------------------------------------------------------------------------
# Utilidades varias
# ---------------------------------------------------------------------------

def parse_timedelta(text: str) -> timedelta:
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
    raise ValueError("Formato de tiempo inválido. Ej: 2h, 90m, 45s, 10min")

# ---------------------------------------------------------------------------
# Persistencia uso diario
# ---------------------------------------------------------------------------

def load_usage() -> Dict[str, float]:
    if USAGE_FILE.exists():
        try:
            return json.loads(USAGE_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def save_usage(data: Dict[str, float]):
    USAGE_FILE.write_text(json.dumps(data))

# ---------------------------------------------------------------------------
# Detección y cierre de procesos
# ---------------------------------------------------------------------------

def has_steam_ancestor(proc: psutil.Process) -> bool:
    """True si cualquier ancestro del proceso se llama steam.exe."""
    try:
        parent = proc.parent()
        while parent:
            if parent.name().lower() == "steam.exe":
                return True
            parent = parent.parent()
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        pass
    return False


def is_game(proc: psutil.Process) -> bool:
    name = proc.name().lower()
    if name in IGNORE_NAMES:
        return False
    return has_steam_ancestor(proc)


def kill_proc(proc: psutil.Process):
    try:
        proc.terminate()
        proc.wait(timeout=8)
    except (psutil.NoSuchProcess, psutil.TimeoutExpired, psutil.AccessDenied):
        pass


def kill_steam_and_games():
    games: List[psutil.Process] = []
    steam_procs: List[psutil.Process] = []
    for proc in psutil.process_iter(["pid", "name"]):
        name = (proc.info["name"] or "").lower()
        if name in {"steam.exe", "steamwebhelper.exe", "gameoverlayui.exe"}:
            steam_procs.append(proc)
        elif is_game(proc):
            games.append(proc)
    for p in games:  # kill games first
        kill_proc(p)
    for p in steam_procs:
        kill_proc(p)

# ---------------------------------------------------------------------------
# Lógica principal
# ---------------------------------------------------------------------------

def main(limit: timedelta):
    usage = load_usage()
    today = date.today().isoformat()
    usage.setdefault(today, 0.0)

    if usage[today] >= limit.total_seconds() and not any(is_game(p) for p in psutil.process_iter()):
        usage[today] = 0.0
        save_usage(usage)

    print(f"Límite diario: {limit}. Poll {POLL_INTERVAL//60} min (Ctrl+C para salir)…")

    prev_active_pids: Set[int] = set()

    while True:
        if date.today().isoformat() != today:
            today = date.today().isoformat()
            usage[today] = 0.0
            save_usage(usage)

        active_procs = [p for p in psutil.process_iter() if is_game(p)]
        active_pids = {p.pid for p in active_procs}

        # Log de juegos iniciados (omitimos auxiliares)
        new_pids = active_pids - prev_active_pids
        if new_pids:
            for p in active_procs:
                if p.pid in new_pids:
                    now = datetime.now().strftime("%H:%M:%S")
                    print(f"[{now}] Juego iniciado: {p.name()} (PID {p.pid})")
        prev_active_pids = active_pids

        if active_procs:  # solo cuenta si hay un juego principal activo
            usage[today] += POLL_INTERVAL
            save_usage(usage)

        remaining = max(limit.total_seconds() - usage[today], 0)
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] Tiempo restante: {timedelta(seconds=int(remaining))}")

        if usage[today] >= limit.total_seconds():
            if active_procs or any(p.name().lower() == "steam.exe" for p in psutil.process_iter()):
                notify("Tiempo agotado. Cerrando juegos y Steam…")
            kill_steam_and_games()
        time.sleep(POLL_INTERVAL)

# ---------------------------------------------------------------------------
# CLI / Servicio Windows
# ---------------------------------------------------------------------------
SERVICE_NAME = "GameTimeLimiter"
SERVICE_DISPLAY = "Game Time Limiter (Steam)"

if os.name == "nt":
    try:
        import win32serviceutil  # type: ignore
        import win32service  # type: ignore
        import win32event  # type: ignore

        class GameTimeService(win32serviceutil.ServiceFramework):
            _svc_name_ = SERVICE_NAME
            _svc_display_name_ = SERVICE_DISPLAY
            _svc_description_ = "Limita el tiempo diario de juego en Steam (daemon Python)."

            def __init__(self, args):
                win32serviceutil.ServiceFramework.__init__(self, args)
                self.stop_event = win32event.CreateEvent(None, 0, 0, None)

            def SvcStop(self):
                self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
                win32event.SetEvent(self.stop_event)

            def SvcDoRun(self):
                main(DEFAULT_LIMIT)

    except ImportError:
        GameTimeService = None  # type: ignore


def cli():
    ap = argparse.ArgumentParser(description="Daemon de control de tiempo Steam.")
    ap.add_argument("--limit", default="2h", help="Ej: 2h, 90m, 10min")
    ap.add_argument("--reset", action="store_true", help="Reinicia contadores")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--remove", action="store_true")
    ap.add_argument("--start", action="store_true")
    ap.add_argument("--stop", action="store_true")
    args = ap.parse_args()

    if args.reset:
        try:
            USAGE_FILE.unlink(missing_ok=True)
            print("usage.json borrado.")
        except Exception as e:
            print(f"No se pudo resetear: {e}")

    if args.install and GameTimeService:
        win32serviceutil.InstallService(
            SERVICE_NAME,
            SERVICE_DISPLAY,
            SERVICE_DISPLAY,
            startType=win32service.SERVICE_AUTO_START,
            exeArgs=f"--limit {args.limit}",
        )
        print("Servicio instalado.")
        return
    if args.remove and GameTimeService:
        win32serviceutil.RemoveService(SERVICE_NAME)
        print("Servicio eliminado.")
        return
    if args.start and GameTimeService:
        win32serviceutil.StartService(SERVICE_NAME)
        return
    if args.stop and GameTimeService:
        win32serviceutil.StopService(SERVICE_NAME)
        return

    main(parse_timedelta(args.limit))


if __name__ == "__main__":
    cli()
