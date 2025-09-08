from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any
import random
import re

from arabic_synth.utils.io import read_jsonl

ARABIC_NAMES = ["أحمد", "محمد", "سارة", "ليلى", "فاطمة", "خالد", "نور"]
CITIES = ["الرياض", "جدة", "دبي", "الدوحة", "القاهرة", "الرباط"]
YEARS = ["2018", "2019", "2020", "2021", "2022", "2023"]


def _replace_entities(text: str) -> str:
    text = re.sub(r"\b20\d{2}\b", random.choice(YEARS), text)
    for city in CITIES:
        if city in text:
            text = text.replace(city, random.choice(CITIES))
    for name in ARABIC_NAMES:
        if name in text:
            text = text.replace(name, random.choice(ARABIC_NAMES))
    return text


def _paraphrase(text: str) -> str:
    replacements = {
        "لكن": "ولكن",
        "لأن": "بسبب",
        "جداً": "للغاية",
        "جدا": "للغاية",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


def _shuffle_options_and_answer(options: List[str], answer_letter: str) -> (List[str], str):
    parsed = []
    correct_text = None
    for opt in options:
        try:
            letter, text = opt.split(".", 1)
            letter = letter.strip()
            text = text.strip()
        except ValueError:
            letter = opt[:1]
            text = opt[2:].strip()
        parsed.append((letter, text))
        if letter == answer_letter:
            correct_text = text
    random.shuffle(parsed)
    new_options: List[str] = []
    new_answer_letter = None
    letters = ["A", "B", "C", "D"]
    for idx, (_, text) in enumerate(parsed):
        new_letter = letters[idx]
        new_options.append(f"{new_letter}. {text}")
        if text == correct_text:
            new_answer_letter = new_letter
    return new_options, (new_answer_letter or answer_letter)


def _augment_item(task: str, item: Dict[str, Any]) -> List[Dict[str, Any]]:
    variants: List[Dict[str, Any]] = []
    if task == "sentiment":
        for _ in range(2):
            t = _replace_entities(item["text"]) 
            t = _paraphrase(t)
            variants.append({"text": t, "sentiment": item["sentiment"]})
    elif task == "exams":
        v = dict(item)
        v["question"] = _paraphrase(_replace_entities(v["question"]))
        new_opts, new_ans = _shuffle_options_and_answer(v["options"], v["answer"])
        v["options"] = new_opts
        v["answer"] = new_ans
        variants.append(v)
    elif task == "grammar":
        v = dict(item)
        v["input"] = _replace_entities(v["input"]) 
        v["correction"] = _replace_entities(v["correction"]) 
        variants.append(v)
    return variants


def run_augmentation(task: str, in_path: Path, num_variants: int) -> List[Dict[str, Any]]:
    rows = read_jsonl(in_path)
    augmented: List[Dict[str, Any]] = []
    for r in rows:
        variants = _augment_item(task, r)
        augmented.append(r)
        augmented.extend(variants[:max(0, num_variants)])
    return augmented 