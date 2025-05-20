from __future__ import annotations
import time
from datetime import date, datetime, timedelta
from typing import Set

import psutil

from .persistence import load_usage, save_usage
from .process_utils import is_game, kill_steam_and_games
from .notifier import notify
from .utils import parse_timedelta

DEFAULT_LIMIT = timedelta(hours=2)
POLL_INTERVAL = 300  # 5 min


class Monitor:
    def __init__(self, limit: timedelta = DEFAULT_LIMIT):
        self.limit = limit
        self.usage = load_usage()
        self.today = date.today().isoformat()
        self.usage.setdefault(self.today, 0.0)
        self.prev_active_pids: Set[int] = set()

    def _reset_day(self):
        if date.today().isoformat() != self.today:
            self.today = date.today().isoformat()
            self.usage[self.today] = 0.0
            save_usage(self.usage)

    def _log_new_games(self, active_pids: Set[int]):
        new_pids = active_pids - self.prev_active_pids
        if new_pids:
            for p in psutil.process_iter():
                if p.pid in new_pids:
                    now = datetime.now().strftime("%H:%M:%S")
                    print(f"[{now}] Juego iniciado: {p.name()} (PID {p.pid})")
        self.prev_active_pids = active_pids

    def loop(self):
        print(
            f"Límite diario: {self.limit}. Poll {POLL_INTERVAL//60} min (Ctrl+C para salir)…"
        )
        while True:
            self._reset_day()

            active = [p for p in psutil.process_iter() if is_game(p)]
            pids = {p.pid for p in active}
            self._log_new_games(pids)

            if active:
                self.usage[self.today] += POLL_INTERVAL
                save_usage(self.usage)

            remaining = max(self.limit.total_seconds() - self.usage[self.today], 0)
            now = datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] Tiempo restante: {timedelta(seconds=int(remaining))}")

            if self.usage[self.today] >= self.limit.total_seconds():
                if active:
                    notify("Tiempo agotado. Cerrando juegos y Steam…")
                kill_steam_and_games()
            time.sleep(POLL_INTERVAL)