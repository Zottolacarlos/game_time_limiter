# game_time_limiter/persistence.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict

# --------------------------------------------------------------------------- #
# Raíz del proyecto (nivel superior al paquete) para usage.json en el repo
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parent.parent
USAGE_FILE   = PROJECT_ROOT / "usage.json"

# --------------------------------------------------------------------------- #
# Carga / guardado del uso diario
# --------------------------------------------------------------------------- #

def load_usage() -> Dict[str, float]:
    """Lee usage.json; si no existe o falla, inicia en {} y crea el archivo."""
    if USAGE_FILE.exists():
        try:
            return json.loads(USAGE_FILE.read_text())
        except json.JSONDecodeError:
            pass
    # No existe o JSON corrupto -> inicializa y guarda
    save_usage({})
    return {}


def save_usage(data: Dict[str, float]) -> None:
    """Escribe el dict en usage.json; crea el archivo si falta."""
    try:
        text = json.dumps(data, indent=2)
        USAGE_FILE.write_text(text)
    except Exception as exc:
        print(f"[WARN] No se pudo escribir {USAGE_FILE}: {exc}")
