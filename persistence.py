from __future__ import annotations
import json
from pathlib import Path
from typing import Dict

USAGE_FILE = Path(__file__).with_name("../usage.json").resolve()


def load_usage() -> Dict[str, float]:
    if USAGE_FILE.exists():
        try:
            return json.loads(USAGE_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def save_usage(data: Dict[str, float]):
    USAGE_FILE.write_text(json.dumps(data))