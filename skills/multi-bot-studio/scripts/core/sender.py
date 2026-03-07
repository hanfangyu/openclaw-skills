from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List


def emit_outbound(run_dir: Path, outbound: List[Dict]) -> Path:
    out = run_dir / "outbound.jsonl"
    with out.open("a", encoding="utf-8") as f:
        for m in outbound:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    return out
