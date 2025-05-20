from __future__ import annotations
import argparse
import os
import sys

from .utils import parse_timedelta
from .monitor import Monitor

SERVICE_AVAILABLE = os.name == "nt"

if SERVICE_AVAILABLE:
    from .service import GameTimeService  # noqa: WPS433
    import win32serviceutil  # type: ignore


def main():  # console‑script entrypoint
    parser = argparse.ArgumentParser(description="Control de tiempo de juego Steam.")
    parser.add_argument("--limit", default="2h", help="Ej: 2h, 90m, 10min")
    parser.add_argument("--reset", action="store_true", help="Borra usage.json")

    if SERVICE_AVAILABLE:
        parser.add_argument("--install", action="store_true")
        parser.add_argument("--remove", action="store_true")
        parser.add_argument("--start", action="store_true")
        parser.add_argument("--stop", action="store_true")

    args = parser.parse_args()

    if args.reset:
        from .persistence import USAGE_FILE  # lazy import

        USAGE_FILE.unlink(missing_ok=True)
        print("usage.json borrado.")

    limit_td = parse_timedelta(args.limit)

    if SERVICE_AVAILABLE and (args.install or args.remove or args.start or args.stop):
        if args.install:
            win32serviceutil.InstallService(
                GameTimeService._svc_name_,  # type: ignore
                GameTimeService._svc_display_name_,  # type: ignore
                GameTimeService._svc_description_,  # type: ignore
                startType=win32service.SERVICE_AUTO_START,
                exeArgs=f"--limit {args.limit}",
            )
            print("Servicio instalado.")
        elif args.remove:
            win32serviceutil.RemoveService(GameTimeService._svc_name_)  # type: ignore
            print("Servicio eliminado.")
        elif args.start:
            win32
