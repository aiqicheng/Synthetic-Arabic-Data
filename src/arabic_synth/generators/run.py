from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from arabic_synth.prompts.templates import EXAMS_TEACHER_PROMPT, SENTIMENT_PROMPT, GRAMMAR_QA_PROMPT, MMLU_TEACHER_PROMPT
from arabic_synth.schemas.exams import ExamItem
from arabic_synth.schemas.sentiment import SentimentItem
from arabic_synth.schemas.grammar import GrammarItem
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from schemas.mmlu import MMLUItem
from arabic_synth.utils.llm import call_llm
from arabic_synth.utils.seed_manager import SeedManager, SeedConstraint

import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    filename='generation.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def _build_prompt(task: str, persona_override: Optional[str], seed_manager: Optional[SeedManager] = None, target_answer_letter: Optional[str] = None, subject: Optional[str] = None, seed_subject: Optional[str] = None) -> str:
    base_prompt = ""
    if task == "exams":
        tmpl = persona_override or EXAMS_TEACHER_PROMPT
        # Safely substitute placeholders to avoid JSON brace formatting issues
        base_prompt = tmpl.replace("{target_answer_letter}", (target_answer_letter or "A"))
        
        # Handle subject placeholder
        if subject:
            # Replace the subject placeholder line
            original_line = "   {subject}**Subject Focus**: Generate questions specifically in the subject area: {subject}{/subject}"
            new_line = f"   **Subject Focus**: Generate questions specifically in the subject area: {subject}"
            base_prompt = base_prompt.replace(original_line, new_line)
        else:
            # Remove the subject line if no subject specified
            original_line = "   {subject}**Subject Focus**: Generate questions specifically in the subject area: {subject}{/subject}\n"
            base_prompt = base_prompt.replace(original_line, "")
    elif task == "sentiment":
        base_prompt = SENTIMENT_PROMPT if not persona_override else persona_override
    elif task == "grammar":
        base_prompt = GRAMMAR_QA_PROMPT if not persona_override else persona_override
    elif task == "mmlu":
        tmpl = persona_override or MMLU_TEACHER_PROMPT
        # Safely substitute placeholders to avoid JSON brace formatting issues
        base_prompt = tmpl.replace("{target_answer_letter}", (target_answer_letter or "A"))
        
        # Handle subject placeholder - replace all {subject} occurrences
        effective_subject = subject or seed_subject or "General"
        base_prompt = base_prompt.replace("{subject}", effective_subject)
    else:
        raise ValueError(f"Unknown task: {task}")
    
    if seed_manager:
        style_guidance = seed_manager.get_style_guidance(task)
        if style_guidance:
            base_prompt = style_guidance + "\n\n" + base_prompt
        
        # Add seed examples for MMLU
        if task == "mmlu" and seed_manager.seeds:
            # Filter seeds by subject if specified
            effective_subject = subject or seed_subject
            relevant_seeds = seed_manager.seeds
            if effective_subject:
                relevant_seeds = [s for s in seed_manager.seeds if s.get("subject") == effective_subject]
                # If no seeds match the subject, use all seeds but warn
                if not relevant_seeds:
                    relevant_seeds = seed_manager.seeds
            
            seed_examples = []
            for seed in relevant_seeds[:2]:  # Use first 2 relevant seeds as examples
                seed_examples.append(f'Example: {json.dumps({"question": seed.get("question", ""), "options": seed.get("options", []), "answer": seed.get("answer", "")}, ensure_ascii=False)}')
            
            if seed_examples:
                base_prompt += "\n\n**Seed Examples for Reference:**\n" + "\n".join(seed_examples)
                base_prompt += f"\n\n**Important**: Generate a NEW question in the same style and subject domain ({effective_subject or 'as shown in examples'}) as the examples above, but with completely different content."
    
    
    return base_prompt


def _remap_answer_to_target(exam_item: Dict[str, Any], target_letter: str) -> Dict[str, Any]:
    # Keep correct text, remap option letters so correct becomes target_letter
    options = exam_item.get("options", [])
    answer = exam_item.get("answer", "").strip()
    try:
        # parse to map
        parsed = []
        correct_text = None
        for opt in options:
            letter, text = opt.split(".", 1)
            letter = letter.strip()
            text = text.strip()
            parsed.append((letter, text))
            if letter == answer:
                correct_text = text
        if not correct_text:
            return exam_item
        # assign new letters
        letters = ["A", "B", "C", "D"]
        # ensure correct_text lands at target_letter index
        new_order = []
        # place correct first
        new_order.append((target_letter, correct_text))
        # add other texts with remaining letters
        remaining_letters = [l for l in letters if l != target_letter]
        for _, text in parsed:
            if text == correct_text:
                continue
            new_letter = remaining_letters.pop(0)
            new_order.append((new_letter, text))
        new_options = [f"{l}. {t}" for l, t in new_order]
        return {"question": exam_item["question"], "options": new_options, "answer": target_letter}
    except Exception:
        return exam_item


def _generate_one(task: str, prompt: str, model: str, seed_manager: Optional[SeedManager] = None, temperature: float = 0.7, top_p: float = 0.95) -> Dict[str, Any]:
    raw = call_llm(model, prompt, temperature=temperature, top_p=top_p)
    obj = json.loads(raw)
    
    if seed_manager and not seed_manager.validate_generation(obj, task):
        raise ValueError("Generated content too similar to seed data")
    
    if task == "exams":
        return ExamItem(**obj).model_dump()
    elif task == "sentiment":
        return SentimentItem(**obj).model_dump()
    elif task == "grammar":
        return GrammarItem(**obj).model_dump()
    elif task == "mmlu":
        try:
            # Validate with MMLUItem schema but only return required fields
            mmlu_item = MMLUItem(**obj)
            # Return only the three required fields
            return {
                "question": mmlu_item.question,
                "options": mmlu_item.options,
                "answer": mmlu_item.answer
            }
        except Exception as e:
            print(f"MMLU validation error: {e}")
            print(f"Generated object: {obj}")
            raise ValueError(f"MMLU validation failed: {e}")
    else:
        raise ValueError(f"Unknown task: {task}")


def run_generation(
    task: str, 
    num_samples: int, 
    model: str, 
    batch_size: int, 
    persona_override: Optional[str], 
    seed_path: Optional[Path],
    output_dir: Path,
    seed_constraint: Optional[SeedConstraint] = None,
    temperature: float = 0.7,
    top_p: float = 0.95,
    target_answer_distribution: Optional[Dict[str, float]] = None,
    subject: Optional[str] = None,
) -> List[Dict[str, Any]]:
    # 初始化种子管理器
    seed_manager = None
    if seed_path and seed_path.exists():
        seed_constraint = seed_constraint or SeedConstraint(max_seeds=10)
        seed_manager = SeedManager(seed_constraint)
        seeds_loaded = seed_manager.load_seeds_from_testset(seed_path, task)
        print(f"Loaded {len(seeds_loaded)} seed examples from {seed_path}")
        if seeds_loaded:
            audit_path = output_dir / f"{task}_{subject}_seeds_audit.json"
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            seed_manager.export_seed_info(audit_path)
            print(f"Seed audit info exported to {audit_path}")
    
    # 答案配额调度
    letters = ["A", "B", "C", "D"]
    if target_answer_distribution:
        total = sum(target_answer_distribution.get(l, 0.0) for l in letters) or 1.0
        targets = {l: target_answer_distribution.get(l, 0.0) / total for l in letters}
    else:
        targets = {l: 0.25 for l in letters}
    quotas = {l: int(round(targets[l] * num_samples)) for l in letters}
    # 修正总和
    delta = num_samples - sum(quotas.values())
    for l in letters:
        if delta == 0:
            break
        quotas[l] += 1
        delta -= 1
    produced = {l: 0 for l in letters}

    results: List[Dict[str, Any]] = []
    # 循环按配额生成
    order = sorted(letters, key=lambda x: -quotas[x])
    idx = 0
    while len(results) < num_samples:
        target_letter = order[idx % len(order)]
        if produced[target_letter] >= quotas[target_letter]:
            idx += 1
            continue
        
        # For MMLU, extract subject from seed if available
        seed_subject = None
        if task == "mmlu" and seed_manager and seed_manager.seeds:
            # Use a random seed to get its subject
            import random
            random_seed = random.choice(seed_manager.seeds)
            seed_subject = random_seed.get("subject")
        
        prompt = _build_prompt(task, persona_override, seed_manager, target_answer_letter=target_letter, subject=subject, seed_subject=seed_subject)
        try:
            item = _generate_one(task, prompt, model, seed_manager, temperature=temperature, top_p=top_p)
            if task in ["exams", "mmlu"] and item.get("answer") != target_letter:
                item = _remap_answer_to_target(item, target_letter)
            results.append(item)
            produced[target_letter] += 1
            if len(results) % 10 == 0:
                print(f"Generated {len(results)}/{num_samples} samples")
        except Exception as e:
            print(f"Failed to generate sample {len(results)+1}: {e}")
        idx += 1
    
    print(f"Successfully generated {len(results)}/{num_samples} samples")
    return results




def log_generation_session(
    task: str,
    model: str,
    num_samples: int,
    seed_constraints: Dict,
    generation_time: float,
    success_rate: float
):
    """Log the complete parameters of a generation session"""
    session_log = {
        "timestamp": datetime.now().isoformat(),
        "task": task,
        "model": model,
        "num_samples": num_samples,
        "seed_constraints": seed_constraints,
        "generation_time": generation_time,
        "success_rate": success_rate,
        "version": "1.0.0"
    }
    # Save to log file
    logging.info(f"Session log: {session_log}") 