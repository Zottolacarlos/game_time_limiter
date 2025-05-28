from __future__ import annotations
import time
from datetime import date, datetime, timedelta
from typing import Set

import psutil

from .persistence import load_usage, save_usage
from .process_utils import is_game, kill_steam_and_games
from .notifier import notify
from .utils import parse_timedelta
from datetime import date
from .persistence import load_usage, save_usage

DEFAULT_LIMIT = timedelta(hours=2)
POLL_INTERVAL = 300  # 5 min


class Monitor:
    def __init__(self, limit: timedelta = DEFAULT_LIMIT):
        self.limit = limit
        self.usage = load_usage()
        self.today = date.today().isoformat()
        self.usage.setdefault(self.today, 0.0)
        self.prev_active_pids: Set[int] = set()
        self._last_ts = None        # instante desde el que contamos
        self._was_active = False    # había juego en el paso anterior

        if self.today not in self.usage:
                self.usage[self.today] = 0.0
                save_usage(self.usage)
    
    def _reset_day(self):
        if date.today().isoformat() != self.today:
            self.today = date.today().isoformat()
            self.usage[self.today] = 0.0
            save_usage(self.usage)

    def _log_new_games(self, active_pids: Set[int]):
        new_pids = active_pids - self.prev_active_pids
        seen_names = set() 
        if new_pids:
            for p in psutil.process_iter():
                if p.pid in new_pids:
                    now = datetime.now().strftime("%H:%M:%S")
                    print(f"[{now}] Juego iniciado: {p.name()} (PID {p.pid})")
                    seen_names.add(p.name()) 
        self.prev_active_pids = active_pids

    def loop_step(self):
        now_ts = time.time()
        self._reset_day()

        # --- detectar procesos ---
        active_procs = [p for p in psutil.process_iter() if is_game(p)]
        pids = {p.pid for p in active_procs}
        self._log_new_games(pids)
        is_active = bool(active_procs)

        # ----------------- contabilizar tiempo -----------------
        if is_active:
            # Si antes no había juego, arrancamos cronómetro
            if not self._was_active:
                self._last_ts = now_ts
            # Sumar sólo la diferencia con el último instante
            delta = now_ts - (self._last_ts or now_ts)
            self.usage[self.today] += delta
            self._last_ts = now_ts
        else:
            # Sin juego → reseteamos _last_ts
            self._last_ts = now_ts

        self._was_active = is_active

        # ----------------- imprimir / acciones -----------------
        remaining = max(self.limit.total_seconds() - self.usage[self.today], 0)
        print(f"[{datetime.now():%H:%M:%S}] Tiempo restante: {timedelta(seconds=int(remaining))}")

        if remaining <= 0:
            if is_active:
                print(f"Tiempo agotado. Cerrando juegos y Steam…")
            kill_steam_and_games()
            
    def loop(self):
        print(
            f"Límite diario: {self.limit}. Poll {POLL_INTERVAL//60} min (Ctrl+C para salir)…"
        )
        while True:
            self.loop_step()           # ← llamada al paso único
            time.sleep(POLL_INTERVAL)  # ← pausa fija