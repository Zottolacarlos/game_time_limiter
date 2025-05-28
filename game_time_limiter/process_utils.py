from __future__ import annotations
from typing import List
import psutil
import subprocess, platform

IGNORE_NAMES = {
    "steamwebhelper.exe",
    "gameoverlayui.exe",
}


def has_steam_ancestor(proc: psutil.Process) -> bool:
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
    return proc.name().lower() not in IGNORE_NAMES and has_steam_ancestor(proc)


def kill_proc(proc: psutil.Process):
    try:
        proc.terminate()
        proc.wait(timeout=8)
    except (psutil.NoSuchProcess, psutil.TimeoutExpired, psutil.AccessDenied):
        # segundo intento más agresivo
        try:
            proc.kill()                 # señal SIGKILL / TerminateProcess
            proc.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            # Windows – usa taskkill /F /T
            if platform.system() == "Windows":
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/F", "/T"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )


def kill_steam_and_games():
    games: List[psutil.Process] = []
    steam_procs: List[psutil.Process] = []
    for proc in psutil.process_iter(["pid", "name"]):
        name = (proc.info["name"] or "").lower()
        if name in {"steam.exe", *IGNORE_NAMES}:
            steam_procs.append(proc)
        elif is_game(proc):
            games.append(proc)
    for p in games:
        kill_proc(p)
    for p in steam_procs:
        kill_proc(p)