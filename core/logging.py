# core/logging.py
import json
import pathlib
from datetime import datetime
from typing import Dict, Any

def log(role: str, type_: str, data: Dict[str, Any], log_file: pathlib.Path):
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.utcnow().isoformat() + "Z",
            "role": role,
            "type": type_,
            "data": data
        }) + "\n")
