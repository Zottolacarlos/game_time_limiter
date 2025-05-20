from __future__ import annotations
import json
from pathlib import Path
from typing import Dict

# Guarda usage.json en la MISMA carpeta raíz del proyecto, sin depender de
# rutas relativas "../" que fallan tras mover el paquete.
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # .../game_time_limiter
USAGE_FILE = PROJECT_ROOT / "usage.json"


def load_usage() -> Dict[str, float]:
    if USAGE_FILE.exists():
        try:
            return json.loads(USAGE_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def save_usage(data: Dict[str, float]):
    USAGE_FILE.write_text(json.dumps(data))
