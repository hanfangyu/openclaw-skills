from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def run_dir(base_dir: Path, run_id: str) -> Path:
    return base_dir / "runs" / run_id


def ensure_run(base_dir: Path, run_id: str) -> Path:
    rd = run_dir(base_dir, run_id)
    rd.mkdir(parents=True, exist_ok=True)
    return rd


def load_json(path: Path, default: Any):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def save_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2))


def append_event(events_path: Path, event: dict) -> None:
    with events_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
