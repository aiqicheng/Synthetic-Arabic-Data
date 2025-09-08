# -*- coding: utf-8 -*-
from __future__ import annotations
import json, random
from pathlib import Path
from typing import Dict, Any, List, Iterable

try:
    from ...prompts import templates_persona as TPL
except Exception:
    import importlib
    TPL = importlib.import_module('src.prompts.templates_persona')

def _read_jsonl(path: str) -> List[dict]:
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return data

def _read_any_exams(path: str) -> List[Dict[str, Any]]:
    if path.endswith(".jsonl"):
        arr = _read_jsonl(path)
    else:
        arr = json.load(open(path, "r", encoding="utf-8"))
        if isinstance(arr, dict):
            arr = arr.get("data", [])
    out = []
    for i, ex in enumerate(arr):
        q = ex.get("question") or ex.get("stem") or ex.get("prompt")
        if isinstance(q, str) and q.strip():
            ex["_idx"] = ex.get("id", i)
            out.append(ex)
    return out

def _read_personas(path: str) -> List[str]:
    personas = []
    for obj in _read_jsonl(path):
        p = obj.get("persona") or obj.get("text") or obj.get("description")
        if p:
            personas.append(str(p).strip())
    return personas

def build_prompt(original_item: Dict[str, Any], persona: str) -> str:
    src = {
        "question": original_item.get("question") or original_item.get("stem") or original_item.get("prompt"),
        "options": original_item.get("options"),
        "answer": original_item.get("answer") or original_item.get("label"),
        "explanation": original_item.get("explanation") or original_item.get("rationale"),
    }
    return TPL.ARABIC_EXAM_REWRITE_V1.format(
        persona=persona,
        original_json=json.dumps(src, ensure_ascii=False)
    )

def iter_requests(
    exams_path: str,
    personas_path: str,
    per_item_personas: int = 3,
    target_total: int = 20000,
    seed: int = 123
):
    random.seed(seed)
    items = _read_any_exams(exams_path)
    personas = _read_personas(personas_path)
    if not items:
        raise ValueError("No exam items found.")
    if not personas:
        raise ValueError("No personas found.")
    total_plan = len(items) * per_item_personas
    scale = min(1.0, float(target_total) / float(total_plan)) if total_plan > 0 else 1.0

    count = 0
    for it in items:
        k = min(per_item_personas, len(personas))
        chosen = random.sample(personas, k=k)
        for p in chosen:
            if random.random() > scale:
                continue
            yield {
                "source_id": it.get("_idx"),
                "persona": p,
                "prompt": build_prompt(it, p),
                "gen_config": {"temperature": 0.9, "top_p": 0.95},
            }
            count += 1
            if count >= target_total:
                return

def write_requests_jsonl(out_path: str, requests):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out_path, "w", encoding="utf-8") as w:
        for req in requests:
            w.write(json.dumps(req, ensure_ascii=False) + "\n")
            n += 1
    return n
