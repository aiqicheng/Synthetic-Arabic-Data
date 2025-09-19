from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
from collections import Counter
from statistics import mean, stdev

from arabic_synth.utils.io import read_jsonl


def _eval_style_exams(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    answer_counts = Counter(r.get("answer") for r in rows)
    question_lengths = [len(r.get("question", "").split()) for r in rows]
    avg_question_len = mean(question_lengths)
    question_len_stdev = stdev(question_lengths) if len(question_lengths) > 1 else 0
    return {
        "num_items": len(rows),
        "answer_distribution": dict(answer_counts),
        "avg_question_words": round(avg_question_len, 2),
        "question_length_stdev": round(question_len_stdev, 2),
    }


def _eval_style_sentiment(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    dist = Counter(r.get("sentiment") for r in rows)
    return {
        "num_items": len(rows),
        "sentiment_distribution": dict(dist),
        "missing_sentiments": sum(1 for r in rows if not r.get("sentiment")),
    }


def _eval_style_grammar(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    input_lengths = [len(r.get("input", "").split()) for r in rows]
    avg_input_len = mean(input_lengths)
    input_len_stdev = stdev(input_lengths) if len(input_lengths) > 1 else 0
    return {
        "num_items": len(rows),
        "avg_input_words": round(avg_input_len, 2),
        "input_length_stdev": round(input_len_stdev, 2),
    }


def run_evaluation(task: str, in_path: Path) -> Dict[str, Any]:
    rows = read_jsonl(in_path)
    if task == "exams":
        return _eval_style_exams(rows)
    if task == "sentiment":
        return _eval_style_sentiment(rows)
    if task == "grammar":
        return _eval_style_grammar(rows)
    raise ValueError("Unknown task")


def run_evaluate_style(task: str, in_path: Path) -> Dict[str, Any]:
    """Style Guide Pipeline evaluation with enhanced reporting for style consistency."""
    return run_evaluation(task, in_path)


def analyze_distributions(synthetic: List[Dict], real: List[Dict]) -> Dict:
    """Analyze distribution differences between synthetic and real data"""
    return {
        "question_length": compare_length_distributions(synthetic, real),
        "subject_distribution": compare_subject_distributions(synthetic, real),
        "answer_balance": compare_answer_balance(synthetic, real),
        "vocabulary_overlap": calculate_vocabulary_overlap(synthetic, real)
    }

# Placeholder functions for comparison

def compare_length_distributions(synthetic: List[Dict], real: List[Dict]) -> Dict:
    # Implement comparison logic
    return {}

def compare_subject_distributions(synthetic: List[Dict], real: List[Dict]) -> Dict:
    # Implement comparison logic
    return {}

def compare_answer_balance(synthetic: List[Dict], real: List[Dict]) -> Dict:
    # Implement comparison logic
    return {}

def calculate_vocabulary_overlap(synthetic: List[Dict], real: List[Dict]) -> float:
    # Implement overlap calculation
    return 0.0
