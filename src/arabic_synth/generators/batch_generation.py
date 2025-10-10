"""
Enhanced generation module with llm_batch_helper integration for efficient batch processing.

This module provides batch processing capabilities for synthetic data generation,
leveraging the llm_batch_helper package for optimized LLM API calls.
"""

from __future__ import annotations

import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    from llm_batch_helper import process_prompts_batch, LLMConfig
except ImportError:
    print("Warning: llm_batch_helper not installed. Install with: pip install git+https://github.com/TianyiPeng/LLM_batch_helper.git")
    process_prompts_batch = None
    LLMConfig = None

from arabic_synth.prompts.templates import EXAMS_TEACHER_PROMPT, SENTIMENT_PROMPT, GRAMMAR_QA_PROMPT, MMLU_TEACHER_PROMPT
from arabic_synth.schemas.exams import ExamItem
from arabic_synth.schemas.sentiment import SentimentItem
from arabic_synth.schemas.grammar import GrammarItem
from arabic_synth.utils.seed_manager import SeedManager, SeedConstraint
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from schemas.mmlu import MMLUItem

# Configure logging
logger = logging.getLogger(__name__)


def verify_api_key(provider: str = "openai"):
    """Verify that the appropriate API key is accessible."""
    if provider == "openai":
        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('openai_api_key')
        if not api_key:
            logger.warning("OpenAI API key not found in environment variables")
            logger.warning("Please ensure OPENAI_API_KEY is set in your .env file")
            return False
        else:
            # Ensure the API key is set in the environment for llm_batch_helper
            os.environ['OPENAI_API_KEY'] = api_key
            logger.info("OpenAI API key found and accessible")
            return True
    elif provider == "openrouter":
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            logger.warning("OpenRouter API key not found in environment variables")
            logger.warning("Please ensure OPENROUTER_API_KEY is set in your .env file")
            return False
        else:
            # Ensure the API key is set in the environment for llm_batch_helper
            os.environ['OPENROUTER_API_KEY'] = api_key
            logger.info("OpenRouter API key found and accessible")
            return True
    else:
        logger.error(f"Unknown provider: {provider}")
        return False


class BatchGenerationConfig:
    """Configuration for batch generation processing."""
    
    def __init__(
        self,
        batch_size: int = 10,
        max_retries: int = 3,
        delay_between_batches: float = 1.0,
        timeout: float = 30.0,
        temperature: float = 0.7,
        top_p: float = 0.95,
        max_tokens: Optional[int] = None
    ):
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.delay_between_batches = delay_between_batches
        self.timeout = timeout
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
    
    def to_llm_config(self, model_name: str) -> 'LLMConfig':
        """Convert to LLMConfig for llm_batch_helper."""
        if LLMConfig is None:
            raise ImportError("llm_batch_helper not available")
        
        # Remove provider prefix to get clean model name
        if model_name.startswith('openai:'):
            clean_model_name = model_name.replace('openai:', '')
        elif model_name.startswith('openrouter:'):
            clean_model_name = model_name.replace('openrouter:', '')
        else:
            clean_model_name = model_name
        
        return LLMConfig(
            model_name=clean_model_name,
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
            timeout=self.timeout
        )


def _build_prompt(task: str, persona_override: Optional[str], seed_manager: Optional[SeedManager] = None, 
                 target_answer_letter: Optional[str] = None, subject: Optional[str] = None, 
                 seed_subject: Optional[str] = None) -> str:
    """Build prompt for the given task with optional seed guidance."""
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
        effective_subject = subject or seed_subject or "Computer Science"
        base_prompt = base_prompt.replace("{subject}", effective_subject)
    else:
        raise ValueError(f"Unknown task: {task}")
    
    if seed_manager:
        style_guidance = seed_manager.get_style_guidance(task)
        if style_guidance:
            if task == "mmlu":
                base_prompt = style_guidance + "\n\n" + base_prompt
            else:
                base_prompt += f"\n\n{style_guidance}"
        
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
        # Add actual seed examples for other tasks
        elif seed_manager.seeds and task != "mmlu":
            base_prompt += "\n\n**Original Questions for Reference:**\n"
            for i, seed in enumerate(seed_manager.seeds[:3], 1):  # Include up to 3 seed examples
                question = seed.get("question", "")
                options = seed.get("options", [])
                answer = seed.get("answer", "")
                base_prompt += f"\nExample {i}:\n"
                base_prompt += f"Question: {question}\n"
                base_prompt += f"Options: {', '.join(options)}\n"
                base_prompt += f"Answer: {answer}\n"
    return base_prompt


def _remap_answer_to_target(exam_item: Dict[str, Any], target_letter: str) -> Dict[str, Any]:
    """Remap answer options to target letter."""
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


def _parse_generation_response(raw_response: str, task: str) -> Dict[str, Any]:
    """Parse LLM response into structured format."""
    try:
        # Clean the response - remove markdown code blocks if present
        cleaned_response = raw_response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]  # Remove ```json
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]   # Remove ```
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]  # Remove trailing ```
        cleaned_response = cleaned_response.strip()
        
        obj = json.loads(cleaned_response)
        
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
                logger.error(f"MMLU validation error: {e}")
                logger.error(f"Generated object: {obj}")
                raise ValueError(f"MMLU validation failed: {e}")
        else:
            raise ValueError(f"Unknown task: {task}")
    except Exception as e:
        logger.error(f"Failed to parse response: {e}")
        logger.error(f"Raw response: {raw_response}")
        raise


def run_batch_generation(
    task: str,
    num_samples: int,
    model: str,
    batch_config: BatchGenerationConfig,
    persona_override: Optional[str] = None,
    seed_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    seed_constraint: Optional[SeedConstraint] = None,
    target_answer_distribution: Optional[Dict[str, float]] = None,
    subject: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Run batch generation using llm_batch_helper for efficient processing.
    
    Args:
        task: Task type (exams, sentiment, grammar)
        num_samples: Number of samples to generate
        model: Model name for generation
        batch_config: Batch processing configuration
        persona_override: Optional persona override
        seed_path: Optional path to seed examples
        output_dir: Output directory for logs
        seed_constraint: Seed constraint configuration
        target_answer_distribution: Target answer distribution
        subject: Optional subject for exams
        
    Returns:
        List of generated items
    """
    if process_prompts_batch is None:
        raise ImportError("llm_batch_helper not installed. Install with: pip install git+https://github.com/TianyiPeng/LLM_batch_helper.git")
    
    # Determine provider from model name
    if model.startswith("openrouter:"):
        provider = "openrouter"
    elif model.startswith("openai:"):
        provider = "openai"
    else:
        # Default to openai for backward compatibility
        provider = "openai"
    
    # Verify API key is accessible
    if not verify_api_key(provider):
        raise ValueError(f"{provider.upper()} API key not found. Please set {provider.upper()}_API_KEY in your .env file")
    
    logger.info(f"Starting batch generation: {num_samples} samples for {task} using {provider}")
    
    # Initialize seed manager
    seed_manager = None
    if seed_path and seed_path.exists():
        seed_constraint = seed_constraint or SeedConstraint(max_seeds=10)
        seed_manager = SeedManager(seed_constraint)
        seeds_loaded = seed_manager.load_seeds_from_testset(seed_path, task)
        logger.info(f"Loaded {len(seeds_loaded)} seed examples from {seed_path}")
        if seeds_loaded and output_dir:
            audit_path = output_dir / f"{task}_{subject}_seeds_audit.json"
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            seed_manager.export_seed_info(audit_path)
            logger.info(f"Seed audit info exported to {audit_path}")
    
    # Answer quota scheduling
    letters = ["A", "B", "C", "D"]
    if target_answer_distribution:
        total = sum(target_answer_distribution.get(l, 0.0) for l in letters) or 1.0
        targets = {l: target_answer_distribution.get(l, 0.0) / total for l in letters}
    else:
        targets = {l: 0.25 for l in letters}
    quotas = {l: int(round(targets[l] * num_samples)) for l in letters}
    # Adjust total
    delta = num_samples - sum(quotas.values())
    for l in letters:
        if delta == 0:
            break
        quotas[l] += 1
        delta -= 1
    
    # Extract seed subject for MMLU if available
    seed_subject = None
    if task == "mmlu" and seed_manager and seed_manager.seeds:
        import random
        random_seed = random.choice(seed_manager.seeds)
        seed_subject = random_seed.get("subject")
    
    # Prepare prompts for batch processing
    prompts = []
    target_letters = []
    
    for letter in letters:
        for _ in range(quotas[letter]):
            prompt = _build_prompt(task, persona_override, seed_manager, 
                                 target_answer_letter=letter, subject=subject, seed_subject=seed_subject)
            prompts.append(prompt)
            target_letters.append(letter)
    
    logger.info(f"Prepared {len(prompts)} prompts for batch processing")
    
    # Configure LLM for batch processing
    llm_config = batch_config.to_llm_config(model)
    
    # Run batch generation
    try:
        logger.info(f"Starting batch generation with {batch_config.batch_size} batch size using {provider}")
        responses_dict = process_prompts_batch(
            prompts=prompts,
            config=llm_config,
            provider=provider
        )
        logger.info(f"Batch generation completed: {len(responses_dict)} responses")
        
    except Exception as e:
        logger.error(f"Batch generation failed: {e}")
        raise
    
    # Process responses
    results = []
    failed_count = 0
    
    # Convert responses_dict to ordered list
    responses = []
    response_values = list(responses_dict.values())
    for i, prompt in enumerate(prompts):
        # Get response by index since keys are hashed
        if i < len(response_values):
            response_data = response_values[i]
            if isinstance(response_data, dict):
                # Check for error responses first
                if 'error' in response_data:
                    logger.warning(f"Response {i} has error: {response_data['error']}")
                    response = ""
                else:
                    # Extract the actual response text from the response data
                    response = response_data.get('response_text', '')
            else:
                response = str(response_data) if response_data else ""
        else:
            response = ""
        responses.append(response)
    
    for i, (response, target_letter) in enumerate(zip(responses, target_letters)):
        try:
            # Parse the response
            item = _parse_generation_response(response, task)
            
            # Validate against seed constraints if available
            if seed_manager and not seed_manager.validate_generation(item, task):
                logger.warning(f"Generated content too similar to seed data for item {i}")
                failed_count += 1
                continue
            
            # Handle answer remapping for exams and mmlu
            if task in ["exams", "mmlu"] and item.get("answer") != target_letter:
                item = _remap_answer_to_target(item, target_letter)
            
            results.append(item)
            
            if len(results) % 50 == 0:
                logger.info(f"Processed {len(results)}/{num_samples} samples")
                
        except Exception as e:
            logger.error(f"Failed to process response {i}: {e}")
            failed_count += 1
            continue
    
    success_rate = (len(results) / num_samples) * 100 if num_samples > 0 else 0
    logger.info(f"Batch generation complete: {len(results)}/{num_samples} samples (Success rate: {success_rate:.1f}%)")
    
    if failed_count > 0:
        logger.warning(f"Failed to process {failed_count} responses")
    
    return results




def log_batch_generation_session(
    task: str,
    model: str,
    num_samples: int,
    batch_config: BatchGenerationConfig,
    generation_time: float,
    success_rate: float,
    output_dir: Optional[Path] = None
):
    """Log batch generation session details."""
    session_log = {
        "timestamp": datetime.now().isoformat(),
        "task": task,
        "model": model,
        "num_samples": num_samples,
        "batch_config": {
            "batch_size": batch_config.batch_size,
            "max_retries": batch_config.max_retries,
            "delay_between_batches": batch_config.delay_between_batches,
            "timeout": batch_config.timeout,
            "temperature": batch_config.temperature,
            "top_p": batch_config.top_p,
            "max_tokens": batch_config.max_tokens
        },
        "generation_time": generation_time,
        "success_rate": success_rate,
        "version": "2.0.0-batch"
    }
    
    if output_dir:
        log_file = output_dir / f"batch_generation_{task}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("w", encoding="utf-8") as f:
            json.dump(session_log, f, ensure_ascii=False, indent=2)
        logger.info(f"Batch generation session logged to {log_file}")
    
    logger.info(f"Batch generation session: {session_log}")
