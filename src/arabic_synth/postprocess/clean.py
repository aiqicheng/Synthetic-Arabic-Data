from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import json
import re, unicodedata
from rapidfuzz.distance import Levenshtein
from arabic_synth.utils.io import read_jsonl
from arabic_synth.schemas.exams import ExamItem
from arabic_synth.schemas.sentiment import SentimentItem
from arabic_synth.schemas.grammar import GrammarItem
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from schemas.mmlu import MMLUItem


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
        elif task == "mmlu":
            MMLUItem(**item)
        else:
            return False
        return True
    except Exception:
        return False


def _length_ok(task: str, item: Dict[str, Any]) -> bool:
    if task == "sentiment":
        words = item.get("text", "").split()
        return 20 <= len(words) <= 70
    if task == "exams" or task == "mmlu":
        q_words = item.get("question", "").split()
        return 5 <= len(q_words) <= 60
    if task == "grammar":
        return 3 <= len(item.get("input", "").split()) <= 60
    return True


def _ttr_ok(task: str, item: Dict[str, Any], threshold: float = 0.18) -> bool:
    if task not in {"exams", "sentiment", "mmlu"}:
        return True
    text = item.get("text") or item.get("question") or ""
    tokens = [t for t in str(text).split() if t]
    if not tokens:
        return False
    ttr = len(set(tokens)) / len(tokens)
    return ttr >= threshold


# --- NEW: light normalization for Arabic ---
_DIACRITICS = r"[\u064B-\u065F\u0670\u0640]"  # harakat + tatweel

def _norm_arabic(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s))
    s = re.sub(_DIACRITICS, "", s)
    # common canonicals (tweak as you like)
    s = (s.replace("أ","ا").replace("إ","ا").replace("آ","ا")
           .replace("ى","ي").replace("ة","ه"))
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _near_dup_text(a: str, b: str, thr: float = 0.92) -> bool:
    return Levenshtein.normalized_similarity(_norm_arabic(a), _norm_arabic(b)) >= thr

# --- NEW: near-duplicate pass (content-level) ---
def _near_dedup(items: List[Dict[str, Any]], task: str, thr: float = 0.92) -> List[Dict[str, Any]]:
    """
    For MCQ exams: consider two items duplicates if question texts are near-identical
    *and* the correct answer is the same. For other tasks, compare the main text.
    """
    kept: List[Dict[str, Any]] = []
    # simple pre-bucketing to avoid full O(n^2)
    buckets: Dict[str, List[int]] = {}

    def key_for(it: Dict[str, Any]) -> str:
        if task == "exams" or task == "mmlu":
            q = it.get("question", "")
        elif task == "sentiment":
            q = it.get("text", "")
        elif task == "grammar":
            q = it.get("input", "")
        else:
            q = json.dumps(it, ensure_ascii=False, sort_keys=True)
        n = _norm_arabic(q)
        return n[:32]  # prefix bucket

    for idx, it in enumerate(items):
        k = key_for(it)
        buckets.setdefault(k, []).append(idx)

    seen = []  # store representatives
    for k, idxs in buckets.items():
        for i in idxs:
            cur = items[i]
            cur_q = cur.get("question") or cur.get("text") or cur.get("input") or ""
            cur_ans = cur.get("answer")
            is_dup = False
            for rep in seen:
                rep_q = rep.get("question") or rep.get("text") or rep.get("input") or ""
                # exams: require same answer to call them duplicates
                if task == "exams" and cur_ans != rep.get("answer"):
                    continue
                if _near_dup_text(cur_q, rep_q, thr=thr):
                    is_dup = True
                    break
            if not is_dup:
                kept.append(cur)
                seen.append(cur)
    return kept

def _deduplicate(items: List[Dict[str, Any]], threshold: float = 0.98) -> List[Dict[str, Any]]:
    """
    Hard Deduplicate items based on their canonicalized representation.
    """
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
    hard = _deduplicate(filtered_ttr, threshold=0.98)           # stricter hard dedup
    deduped = _near_dedup(hard, task=task, thr=0.92)            # NEW: content-level pass
    return deduped