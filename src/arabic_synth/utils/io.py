from pathlib import Path
from typing import Iterable, Dict, Any, List, Optional
import json
import pandas as pd


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data.append(json.loads(line))
    return data


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def export_dataset(
    task: str,
    in_path: Path,
    out_format: str,
    out_dir: Path,
    meta_task_name: str,
    meta_persona: Optional[str],
    meta_batch_id: Optional[str],
):
    rows = read_jsonl(in_path)
    for r in rows:
        r["_task"] = meta_task_name
        if meta_persona:
            r["_persona"] = meta_persona
        if meta_batch_id:
            r["_batch_id"] = meta_batch_id
    if out_format == "jsonl":
        out_path = out_dir / f"{task}.jsonl"
        write_jsonl(out_path, rows)
    elif out_format == "csv":
        out_path = out_dir / f"{task}.csv"
        pd.DataFrame(rows).to_csv(out_path, index=False)
    else:
        raise ValueError("out_format must be jsonl|csv") 