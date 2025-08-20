from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import json

from rapidfuzz.distance import Levenshtein
from arabic_synth.utils.io import read_jsonl
from arabic_synth.schemas.exams import ExamItem
from arabic_synth.schemas.sentiment import SentimentItem
from arabic_synth.schemas.grammar import GrammarItem


def _canonicalize(item: Dict[str, Any]) -> str:
    try:
        return json.dumps(item, ensure_ascii=False, sort_keys=True)
    except Exception:  # noqa: BLE001
        return str(item)


def _is_valid(task: str, item: Dict[str, Any]) -> bool:
    try:
        if task == "exams":
            ExamItem(**item)
        elif task == "sentiment":
            SentimentItem(**item)
        elif task == "grammar":
            GrammarItem(**item)
        else:
            return False
        return True
    except Exception:
        return False


def _length_ok(task: str, item: Dict[str, Any]) -> bool:
    if task == "sentiment":
        words = item.get("text", "").split()
        return 20 <= len(words) <= 70
    if task == "exams":
        q_words = item.get("question", "").split()
        return 5 <= len(q_words) <= 60
    if task == "grammar":
        return 3 <= len(item.get("input", "").split()) <= 60
    return True


def _ttr_ok(task: str, item: Dict[str, Any], threshold: float = 0.18) -> bool:
    if task not in {"exams", "sentiment"}:
        return True
    text = item.get("text") or item.get("question") or ""
    tokens = [t for t in str(text).split() if t]
    if not tokens:
        return False
    ttr = len(set(tokens)) / len(tokens)
    return ttr >= threshold


def _deduplicate(items: List[Dict[str, Any]], threshold: float = 0.93) -> List[Dict[str, Any]]:
    kept: List[Dict[str, Any]] = []
    seen: List[str] = []
    for it in items:
        s = _canonicalize(it)
        is_dup = False
        for prev in seen:
            if Levenshtein.normalized_similarity(s, prev) >= threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append(it)
            seen.append(s)
    return kept


def run_cleaning(task: str, in_path: Path) -> List[Dict[str, Any]]:
    raw = read_jsonl(in_path)
    filtered_len = [it for it in raw if _is_valid(task, it) and _length_ok(task, it)]
    filtered_ttr = [it for it in filtered_len if _ttr_ok(task, it)]
    deduped = _deduplicate(filtered_ttr)
    return deduped 