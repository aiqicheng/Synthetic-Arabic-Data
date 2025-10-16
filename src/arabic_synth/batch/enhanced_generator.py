"""
Enhanced Batch Generation Program with llm-batch-helper integration.

This module implements the strategy:
1. Sample 20 seeds (stratified or uniform)
2. Generate one item per seed using one-prompt-per-seed strategy
3. Use llm-batch-helper for parallel processing to speed up generation
4. Repeat the process with different random seeds
5. Combine all generated MCQs

Features:
- Varied random seeds for each iteration (no fixed seed=42)
- Configurable sampling strategy (stratified/uniform)
- Parallel processing with llm-batch-helper for speed
- Automatic output management and combination
- Progress tracking and statistics
"""

import json
import random
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import llm-batch-helper for parallel processing
try:
    from llm_batch_helper import LLMConfig, process_prompts_batch
    BATCH_HELPER_AVAILABLE = True
except ImportError:
    BATCH_HELPER_AVAILABLE = False

from ..utils.seed_manager import SeedManager, SeedConstraint
from ..prompts.templates import MMLU_TEACHER_PROMPT
from ..utils.diversity import create_diversity_manager
from ..utils.llm import call_llm


class EnhancedBatchGenerationProgram:
    """Enhanced batch generation program with llm-batch-helper integration."""
    
    def __init__(self, 
                 input_file: Path,
                 output_dir: Path,
                 model: str = "openai:gpt-4o",
                 sampling_mode: str = "stratified",
                 seeds_per_batch: int = 20,
                 total_batches: int = 5,
                 use_batch_helper: bool = True,
                 max_concurrent_requests: int = 10,
                 prioritize_diversity: bool = False):
        """
        Initialize the enhanced batch generation program.
        
        Args:
            input_file: Path to Arabic MMLU CSV file
            output_dir: Directory for outputs
            model: LLM model to use
            sampling_mode: "stratified" or "uniform"
            seeds_per_batch: Number of seeds per batch
            total_batches: Number of batches to run
            use_batch_helper: Whether to use llm-batch-helper for parallel processing
            max_concurrent_requests: Maximum concurrent requests for batch processing
            prioritize_diversity: If True, use sequential processing for full diversity per request
        """
        self.input_file = input_file
        self.output_dir = output_dir
        self.model = model
        self.sampling_mode = sampling_mode
        self.seeds_per_batch = seeds_per_batch
        self.total_batches = total_batches
        self.prioritize_diversity = prioritize_diversity
        # If prioritizing diversity, force sequential processing for full per-request diversity
        self.use_batch_helper = (use_batch_helper and BATCH_HELPER_AVAILABLE and not prioritize_diversity)
        self.max_concurrent_requests = max_concurrent_requests
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize tracking
        self.batch_results = []
        self.all_generated_items = []
        self.generation_stats = {
            "total_batches": total_batches,
            "seeds_per_batch": seeds_per_batch,
            "total_seeds_used": 0,
            "total_items_generated": 0,
            "start_time": None,
            "end_time": None,
            "batches_completed": 0,
            "use_batch_helper": self.use_batch_helper
        }
        
        # Initialize accumulated data for consolidated processing
        self.all_seeds = []
        self.all_metadata = []
        
        # Initialize diversity manager
        self.diversity_manager = create_diversity_manager(use_simhash=True, use_bloom=False)
        
        # Setup llm-batch-helper config if available
        if self.use_batch_helper:
            # Parse model and provider from model string
            self.model_name, self.provider = self._parse_model_provider(self.model)
            
            # Note: We'll create LLMConfig per request to apply diversity features
            # The base config will be updated with jittered parameters for each request
            self.base_llm_config = {
                "model_name": self.model_name,
                "max_completion_tokens": 1000,
                "max_concurrent_requests": self.max_concurrent_requests
            }
            print(f"✓ llm-batch-helper enabled with {self.max_concurrent_requests} concurrent requests")
            print(f"  Provider: {self.provider}, Model: {self.model_name}")
            print(f"  ✓ Diversity features will be applied (averaged per batch)")
        else:
            if self.prioritize_diversity:
                print("✓ Using sequential processing for full per-request diversity")
            elif not BATCH_HELPER_AVAILABLE:
                print("⚠️ llm-batch-helper not available, using sequential processing")
            else:
                print("✓ Using sequential processing")
    
    def _parse_model_provider(self, model_string: str) -> tuple[str, str]:
        """Parse model string to extract model name and provider for llm-batch-helper."""
        if model_string.startswith("openai:"):
            # OpenAI models: openai:gpt-4o -> (gpt-4o, openai)
            model_name = model_string.replace("openai:", "")
            provider = "openai"
        elif model_string.startswith("openrouter:"):
            # OpenRouter models: openrouter:openai/gpt-4o -> (openai/gpt-4o, openrouter)
            model_name = model_string.replace("openrouter:", "")
            provider = "openrouter"
        elif model_string.startswith("together:"):
            # Together.ai models: together:meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo -> (meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo, together)
            model_name = model_string.replace("together:", "")
            provider = "together"
        elif model_string.startswith("gemini:"):
            # Google Gemini models: gemini:gemini-1.5-pro -> (gemini-1.5-pro, gemini)
            model_name = model_string.replace("gemini:", "")
            provider = "gemini"
        elif model_string in ["gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]:
            # Direct OpenAI model names without prefix
            model_name = model_string
            provider = "openai"
        else:
            # Default to OpenAI for backward compatibility
            model_name = model_string
            provider = "openai"
        
        return model_name, provider

    def _clean_options_format(self, raw_options: List[str]) -> List[str]:
        """Clean options to ensure strict A. B. C. D. format."""
        cleaned_options = []
        letters = ["A", "B", "C", "D"]
        
        for i, option in enumerate(raw_options):
            if i >= 4:  # Only take first 4 options
                break
                
            option = option.strip()
            
            # If option doesn't start with letter, add it
            if not option.startswith(letters[i] + ".") and not option.startswith(letters[i] + ")"):
                # Remove any existing prefix and add proper format
                clean_text = option
                for prefix in ["A.", "B.", "C.", "D.", "A)", "B)", "C)", "D)", "(A)", "(B)", "(C)", "(D)"]:
                    if clean_text.startswith(prefix):
                        clean_text = clean_text[len(prefix):].strip()
                        break
                
                cleaned_options.append(f"{letters[i]}. {clean_text}")
            else:
                # Option already has proper format, just ensure consistency
                if option.startswith(letters[i] + ")"):
                    # Convert A) to A.
                    clean_text = option[2:].strip()
                    cleaned_options.append(f"{letters[i]}. {clean_text}")
                elif option.startswith("(" + letters[i] + ")"):
                    # Convert (A) to A.
                    clean_text = option[3:].strip()
                    cleaned_options.append(f"{letters[i]}. {clean_text}")
                else:
                    # Already in A. format
                    cleaned_options.append(option)
        
        # Ensure we have exactly 4 options
        while len(cleaned_options) < 4:
            cleaned_options.append(f"{letters[len(cleaned_options)]}. Option {len(cleaned_options) + 1}")
        
        return cleaned_options

    def generate_random_seed(self) -> int:
        """Generate a random seed for each batch."""
        return random.randint(1, 10000)
    
    def sample_seeds_for_batch(self, batch_num: int) -> Path:
        """Sample seeds for a specific batch using varied random seed."""
        random_seed = self.generate_random_seed()
        
        # Create batch-specific seed file
        seed_file = self.output_dir / f"batch_{batch_num:03d}_seeds.jsonl"
        
        print(f"Batch {batch_num}: Sampling {self.seeds_per_batch} seeds with random seed {random_seed}")
        
        # Import and use the sampling functionality
        import subprocess
        
        cmd = [
            "arabic-synth", "sample-and-convert", "mmlu",
            "--input-file", str(self.input_file),
            "--output-file", str(seed_file),
            "--n", str(self.seeds_per_batch),
            "--mode", self.sampling_mode
        ]
        
        if self.sampling_mode == "stratified":
            cmd.extend(["--stratify-col", "Subject"])
        
        cmd.extend(["--seed", str(random_seed)])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"  ✓ Sampled {self.seeds_per_batch} seeds to {seed_file}")
            return seed_file
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Error sampling seeds: {e}")
            print(f"  stderr: {e.stderr}")
            raise
    
    def load_seeds(self, seed_file: Path) -> List[Dict[str, Any]]:
        """Load seeds from JSONL file."""
        seeds = []
        with seed_file.open('r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    seeds.append(json.loads(line))
        return seeds
    
    def build_prompt_for_seed(self, seed: Dict[str, Any], seed_index: int, target_letter: str) -> str:
        """Build prompt for a specific seed."""
        # Get subject from seed or use default
        subject = seed.get("subject", seed.get("Subject", "الموضوع العام"))
        
        # Base prompt template with subject parameter resolved
        base_prompt = MMLU_TEACHER_PROMPT.replace("{target_answer_letter}", target_letter)
        base_prompt = base_prompt.replace("{subject}", subject)
        
        # Add seed examples
        seed_examples = []
        seed_examples.append(f'Example: {json.dumps({"question": seed.get("question", ""), "options": seed.get("options", []), "answer": seed.get("answer", "")}, ensure_ascii=False)}')
        
        if seed_examples:
            base_prompt += "\n\n**Seed Examples for Reference:**\n" + "\n".join(seed_examples)
            base_prompt += f"\n\n**Important**: Generate a NEW question in the same style and subject domain as the examples above, but with completely different content."
        
        # Apply prompt micro-variation if diversity manager is available
        if self.diversity_manager:
            base_prompt = self.diversity_manager.get_varied_prompt(base_prompt, seed_index)
        
        return base_prompt
    
    def accumulate_prompts_for_batch(self, batch_num: int, seed_file: Path) -> int:
        """Accumulate prompts from a batch without processing them yet."""
        print(f"Batch {batch_num}: Accumulating {self.seeds_per_batch} prompts")
        
        # Load seeds
        seeds = self.load_seeds(seed_file)
        
        # Add seeds to global collection
        for seed in seeds:
            self.all_seeds.append(seed)
        
        print(f"  ✓ Accumulated {len(seeds)} prompts (Total: {len(self.all_seeds)})")
        return len(seeds)
    
    def process_accumulated_prompts(self, force_process: bool = False) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Process accumulated prompts in batches limited by max_concurrent_requests."""
        if not self.all_seeds and not force_process:
            return [], []
        
        # Determine how many prompts to process
        if force_process:
            prompts_to_process = self.all_seeds
        else:
            # Process in chunks of max_concurrent_requests
            prompts_to_process = self.all_seeds[:self.max_concurrent_requests]
        
        if not prompts_to_process:
            return [], []
        
        print(f"Processing {len(prompts_to_process)} accumulated prompts (max_concurrent: {self.max_concurrent_requests})")
        
        # Prepare prompts and diversity parameters
        prompts = []
        target_letters = []
        diversity_params = []
        
        # Determine target letters based on quota
        letters = ["A", "B", "C", "D"]
        quotas = {l: len(prompts_to_process) // 4 for l in letters}
        remaining = len(prompts_to_process) % 4
        for i, l in enumerate(letters):
            if i < remaining:
                quotas[l] += 1
        
        produced = {l: 0 for l in letters}
        order = sorted(letters, key=lambda x: -quotas[x])
        idx = 0
        
        for i, seed in enumerate(prompts_to_process):
            # Determine target letter based on quota
            target_letter = order[idx % len(order)]
            if produced[target_letter] >= quotas[target_letter]:
                idx += 1
                target_letter = order[idx % len(order)]
            
            # Build prompt for this seed with diversity features
            prompt = self.build_prompt_for_seed(seed, i, target_letter)
            prompts.append(prompt)
            target_letters.append(target_letter)
            produced[target_letter] += 1
            idx += 1
            
            # Generate diversity parameters for this request
            if self.diversity_manager:
                jittered_params = self.diversity_manager.get_jittered_params()
                diversity_params.append(jittered_params)
            else:
                diversity_params.append({
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "presence_penalty": 0.0,
                    "frequency_penalty": 0.0
                })
        
        print(f"  ✓ Prepared {len(prompts)} prompts with diversity parameters for parallel processing")
        
        # Note: llm-batch-helper limitation - it uses a single config for all requests
        # We'll use the average diversity parameters for the batch
        # For full diversity per request, we'd need to fall back to sequential processing
        avg_temp = sum(p["temperature"] for p in diversity_params) / len(diversity_params)
        avg_top_p = sum(p["top_p"] for p in diversity_params) / len(diversity_params)
        avg_presence_penalty = sum(p["presence_penalty"] for p in diversity_params) / len(diversity_params)
        avg_frequency_penalty = sum(p["frequency_penalty"] for p in diversity_params) / len(diversity_params)
        
        print(f"  ℹ️ Using average diversity parameters: temp={avg_temp:.3f}, top_p={avg_top_p:.3f}")
        print(f"    presence_penalty={avg_presence_penalty:.3f}, frequency_penalty={avg_frequency_penalty:.3f}")
        
        # Create LLMConfig with average diversity parameters
        llm_config = LLMConfig(
            model_name=self.base_llm_config["model_name"],
            temperature=avg_temp,
            max_completion_tokens=self.base_llm_config["max_completion_tokens"],
            max_concurrent_requests=self.base_llm_config["max_concurrent_requests"],
            # Note: llm-batch-helper may not support presence_penalty and frequency_penalty
            # These would need to be handled at the provider level
        )
        
        # Process prompts in parallel using llm-batch-helper
        try:
            results = process_prompts_batch(
                config=llm_config,
                provider=self.provider,
                prompts=prompts,
                cache_dir=str(self.output_dir / "cache")
            )
            
            # Process responses with duplicate detection
            items = []
            metadata_items = []
            duplicates_detected = 0
            
            for i, (prompt_id, response) in enumerate(results.items()):
                try:
                    # Parse the JSON response
                    obj = json.loads(response['response_text'])
                    
                    # Clean and format options to ensure A. B. C. D. format
                    raw_options = obj.get("options", [])
                    cleaned_options = self._clean_options_format(raw_options)
                    
                    # Validate and format the clean item (only essential fields)
                    item = {
                        "question": obj.get("question", ""),
                        "options": cleaned_options,
                        "answer": obj.get("answer", "")
                    }
                    
                    # Check for duplicates using diversity manager
                    if self.diversity_manager and self.diversity_manager.check_duplicate(item):
                        print(f"  ⚠️ Duplicate detected for seed {i}, skipping")
                        duplicates_detected += 1
                        continue
                    
                    # Create metadata item (separate from main output)
                    # Use the actual ID from the seed data as the seed index
                    seed_id = prompts_to_process[i].get("ID", prompts_to_process[i].get("id", len(self.all_generated_items) + i))
                    metadata_item = {
                        "_seed_index": seed_id,
                        "_seed_question": prompts_to_process[i].get("question", "")[:100] + "..." if len(prompts_to_process[i].get("question", "")) > 100 else prompts_to_process[i].get("question", ""),
                        "_subject": prompts_to_process[i].get("subject", prompts_to_process[i].get("Subject", "الموضوع العام")),
                        "_generation_timestamp": datetime.now().isoformat(),
                        "_target_letter": target_letters[i],
                        "_raw_options": raw_options,  # Keep original options for reference
                        "_prompt_id": prompt_id,
                        "_diversity_params": diversity_params[i]  # Store the diversity params used
                    }
                    
                    items.append(item)
                    metadata_items.append(metadata_item)
                    
                except Exception as e:
                    print(f"  ⚠️ Error processing response for seed {i}: {e}")
                    continue
            
            if duplicates_detected > 0:
                print(f"  ℹ️ Detected and skipped {duplicates_detected} duplicates")
            
            # Remove processed seeds from the queue
            self.all_seeds = self.all_seeds[len(prompts_to_process):]
            
            print(f"  ✓ Generated {len(items)} items using parallel processing")
            print(f"  ℹ️ Note: llm-batch-helper uses average diversity parameters for the batch")
            print(f"    For full per-request diversity, consider using sequential processing")
            return items, metadata_items
            
        except Exception as e:
            print(f"  ❌ Error in batch processing: {e}")
            return [], []
    
    def generate_batch_sequential(self, batch_num: int, seed_file: Path) -> List[Dict[str, Any]]:
        """Generate items using sequential processing (fallback)."""
        print(f"Batch {batch_num}: Generating {self.seeds_per_batch} items using sequential processing")
        
        # Load seeds
        seeds = self.load_seeds(seed_file)
        
        # Create batch-specific output directory
        batch_output_dir = self.output_dir / f"batch_{batch_num:03d}"
        batch_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize seed manager
        seed_manager = SeedManager(SeedConstraint(max_seeds=len(seeds)))
        seed_manager.seeds = seeds
        
        items = []
        letters = ["A", "B", "C", "D"]
        quotas = {l: len(seeds) // 4 for l in letters}
        remaining = len(seeds) % 4
        for i, l in enumerate(letters):
            if i < remaining:
                quotas[l] += 1
        
        produced = {l: 0 for l in letters}
        order = sorted(letters, key=lambda x: -quotas[x])
        idx = 0
        
        for i, seed in enumerate(seeds):
            # Determine target letter based on quota
            target_letter = order[idx % len(order)]
            if produced[target_letter] >= quotas[target_letter]:
                idx += 1
                target_letter = order[idx % len(order)]
            
            # Build prompt for this seed
            prompt = self.build_prompt_for_seed(seed, i, target_letter)
            
            try:
                # Get jittered sampling parameters
                if self.diversity_manager:
                    jittered_params = self.diversity_manager.get_jittered_params()
                    gen_temp = jittered_params["temperature"]
                    gen_top_p = jittered_params["top_p"]
                    gen_presence_penalty = jittered_params["presence_penalty"]
                    gen_frequency_penalty = jittered_params["frequency_penalty"]
                else:
                    gen_temp = 0.7
                    gen_top_p = 0.95
                    gen_presence_penalty = 0.0
                    gen_frequency_penalty = 0.0
                
                # Generate item
                raw = call_llm(self.model, prompt, temperature=gen_temp, top_p=gen_top_p,
                             presence_penalty=gen_presence_penalty, frequency_penalty=gen_frequency_penalty)
                obj = json.loads(raw)
                
                # Clean and format options to ensure A. B. C. D. format
                raw_options = obj.get("options", [])
                cleaned_options = self._clean_options_format(raw_options)
                
                # Validate and format the clean item (only essential fields)
                item = {
                    "question": obj.get("question", ""),
                    "options": cleaned_options,
                    "answer": obj.get("answer", "")
                }
                
                items.append(item)
                produced[target_letter] += 1
                idx += 1
                
                if len(items) % 5 == 0:
                    print(f"    Generated {len(items)}/{len(seeds)} items")
                
            except Exception as e:
                print(f"    ⚠️ Error generating item for seed {i}: {e}")
                continue
        
        print(f"  ✓ Generated {len(items)} items using sequential processing")
        return items
    
    def generate_batch(self, batch_num: int, seed_file: Path):
        """Generate items for a specific batch."""
        if self.use_batch_helper:
            return self.generate_batch_with_batch_helper(batch_num, seed_file)
        else:
            return self.generate_batch_sequential(batch_num, seed_file)
    
    def append_to_consolidated_files(self, items: List[Dict[str, Any]], metadata_items: Optional[List[Dict[str, Any]]] = None):
        """Append items and metadata to consolidated files."""
        # Append to consolidated generated items file
        generated_file = self.output_dir / "generated_items.jsonl"
        with generated_file.open("a", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        
        print(f"  ✓ Appended {len(items)} items to {generated_file}")
        
        # Append to consolidated metadata file if available
        if metadata_items:
            metadata_file = self.output_dir / "metadata.jsonl"
            with metadata_file.open("a", encoding="utf-8") as f:
                for metadata_item in metadata_items:
                    f.write(json.dumps(metadata_item, ensure_ascii=False) + "\n")
            print(f"  ✓ Appended {len(metadata_items)} metadata items to {metadata_file}")
    
    def save_all_seeds(self):
        """Save all accumulated seeds to a single file."""
        if not self.all_seeds:
            return
        
        seeds_file = self.output_dir / "all_seeds.jsonl"
        with seeds_file.open("w", encoding="utf-8") as f:
            for seed in self.all_seeds:
                f.write(json.dumps(seed, ensure_ascii=False) + "\n")
        
        print(f"✓ Saved {len(self.all_seeds)} seeds to {seeds_file}")
    
    
    def create_summary_report(self):
        """Create a summary report of the generation process."""
        summary_file = self.output_dir / "generation_summary.json"
        
        # Calculate final statistics
        # For enhanced generator, we need to read from metadata file since seed indices are stored there
        total_unique_seeds = 0
        if self.use_batch_helper:
            metadata_file = self.output_dir / "metadata.jsonl"
            if metadata_file.exists():
                try:
                    seed_indices = []
                    with metadata_file.open("r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                metadata = json.loads(line)
                                seed_idx = metadata.get("_seed_index")
                                if seed_idx is not None:
                                    seed_indices.append(seed_idx)
                    total_unique_seeds = len(set(seed_indices))
                except Exception as e:
                    print(f"Warning: Could not read seed indices from metadata: {e}")
                    total_unique_seeds = 0
        else:
            # For sequential processing, seed indices should be in the items themselves
            total_unique_seeds = len(set(item.get("_seed_index", -1) for item in self.all_generated_items if "_seed_index" in item))
        
        self.generation_stats.update({
            "total_items_generated": len(self.all_generated_items),
            "total_unique_seeds_used": total_unique_seeds,
            "end_time": datetime.now().isoformat(),
            "batches_completed": len(self.batch_results),
            "success_rate": len(self.batch_results) / self.total_batches if self.total_batches > 0 else 0
        })
        
        # Add batch-specific statistics
        batch_stats = []
        if self.use_batch_helper:
            # For enhanced generator with batch_helper, we process in chunks, not traditional batches
            # Calculate chunk-based statistics from metadata file
            chunk_num = 1
            items_processed = 0
            for i, batch_items in enumerate(self.batch_results):
                # Calculate unique seeds for this chunk from metadata
                chunk_unique_seeds = 0
                metadata_file = self.output_dir / "metadata.jsonl"
                if metadata_file.exists():
                    try:
                        with metadata_file.open("r", encoding="utf-8") as f:
                            lines = f.readlines()
                            # Get the lines for this chunk (items_processed to items_processed + len(batch_items))
                            chunk_lines = lines[items_processed:items_processed + len(batch_items)]
                            seed_indices = []
                            for line in chunk_lines:
                                if line.strip():
                                    metadata = json.loads(line)
                                    seed_idx = metadata.get("_seed_index")
                                    if seed_idx is not None:
                                        seed_indices.append(seed_idx)
                            chunk_unique_seeds = len(set(seed_indices))
                    except Exception as e:
                        print(f"Warning: Could not read chunk seed indices from metadata: {e}")
                
                batch_stats.append({
                    "chunk_number": chunk_num,
                    "items_generated": len(batch_items),
                    "unique_seeds_used": chunk_unique_seeds
                })
                items_processed += len(batch_items)
                chunk_num += 1
        else:
            # Traditional batch processing
            for i, batch_items in enumerate(self.batch_results):
                batch_stats.append({
                    "batch_number": i + 1,
                    "items_generated": len(batch_items),
                    "unique_seeds_used": len(set(item.get("_seed_index", -1) for item in batch_items if "_seed_index" in item))
                })
        
        # Analyze subject composition from all_seeds.jsonl
        subject_composition = self._analyze_subject_composition()
        
        summary_data = {
            "configuration": {
                "input_file": str(self.input_file),
                "output_dir": str(self.output_dir),
                "model": self.model,
                "sampling_mode": self.sampling_mode,
                "seeds_per_batch": self.seeds_per_batch,
                "total_batches": self.total_batches,
                "use_batch_helper": self.use_batch_helper,
                "max_concurrent_requests": self.max_concurrent_requests
            },
            "generation_stats": self.generation_stats,
            "batch_statistics": batch_stats,
            "subject_composition": subject_composition
        }
        
        with summary_file.open("w", encoding="utf-8") as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Summary report saved to {summary_file}")
    
    def _analyze_subject_composition(self):
        """Analyze the subject composition from all_seeds.jsonl."""
        all_seeds_file = self.output_dir / "all_seeds.jsonl"
        
        if not all_seeds_file.exists():
            return {"error": "all_seeds.jsonl not found"}
        
        subject_counts = {}
        total_seeds = 0
        
        try:
            with all_seeds_file.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        seed = json.loads(line)
                        total_seeds += 1
                        
                        # Try different possible subject field names
                        subject = seed.get("subject") or seed.get("Subject") or seed.get("SUBJECT", "Unknown")
                        
                        if subject in subject_counts:
                            subject_counts[subject] += 1
                        else:
                            subject_counts[subject] = 1
            
            # Sort by count (descending) and calculate percentages
            sorted_subjects = sorted(subject_counts.items(), key=lambda x: x[1], reverse=True)
            
            composition = {
                "total_seeds_analyzed": total_seeds,
                "subject_distribution": {},
                "summary": []
            }
            
            for subject, count in sorted_subjects:
                percentage = (count / total_seeds * 100) if total_seeds > 0 else 0
                composition["subject_distribution"][subject] = {
                    "count": count,
                    "percentage": round(percentage, 2)
                }
                composition["summary"].append(f"{count} {subject} ({percentage:.1f}%)")
            
            return composition
            
        except Exception as e:
            return {"error": f"Failed to analyze subject composition: {str(e)}"}
    
    def run(self):
        """Run the complete enhanced batch generation process."""
        print(f"Starting enhanced batch generation program:")
        print(f"  Input file: {self.input_file}")
        print(f"  Output directory: {self.output_dir}")
        print(f"  Model: {self.model}")
        print(f"  Sampling mode: {self.sampling_mode}")
        print(f"  Seeds per batch: {self.seeds_per_batch}")
        print(f"  Total batches: {self.total_batches}")
        print(f"  Use batch helper: {self.use_batch_helper}")
        if self.use_batch_helper:
            print(f"  Max concurrent requests: {self.max_concurrent_requests}")
            print(f"  Processing strategy: Accumulate prompts and process in chunks of {self.max_concurrent_requests}")
        print(f"  Expected total items: {self.total_batches * self.seeds_per_batch}")
        print()
        
        self.generation_stats["start_time"] = datetime.now().isoformat()
        
        try:
            if self.use_batch_helper:
                # New approach: Accumulate all prompts first, then process in chunks
                print(f"\n{'='*60}")
                print("PHASE 1: ACCUMULATING PROMPTS FROM ALL BATCHES")
                print(f"{'='*60}")
                
                # Phase 1: Accumulate prompts from all batches
                for batch_num in range(1, self.total_batches + 1):
                    print(f"\nBatch {batch_num}: Sampling seeds...")
                    seed_file = self.sample_seeds_for_batch(batch_num)
                    self.accumulate_prompts_for_batch(batch_num, seed_file)
                
                print(f"\n✓ Accumulated {len(self.all_seeds)} total prompts")
                
                # Save all seeds before processing (since they get consumed)
                self.save_all_seeds()
                
                # Phase 2: Process prompts in chunks
                print(f"\n{'='*60}")
                print(f"PHASE 2: PROCESSING {len(self.all_seeds)} PROMPTS IN CHUNKS OF {self.max_concurrent_requests}")
                print(f"{'='*60}")
                
                chunk_num = 1
                while self.all_seeds:
                    print(f"\nProcessing chunk {chunk_num}...")
                    items, metadata_items = self.process_accumulated_prompts(force_process=False)
                    
                    if items:
                        # Append to consolidated files
                        self.append_to_consolidated_files(items, metadata_items)
                        
                        # Add to combined results
                        self.batch_results.append(items)
                        self.all_generated_items.extend(items)
                        
                        # Update statistics
                        self.generation_stats["total_seeds_used"] += len(items)
                        
                        print(f"  Chunk {chunk_num} completed: {len(items)} items generated")
                        print(f"  Remaining prompts: {len(self.all_seeds)}")
                    else:
                        print(f"  ❌ Chunk {chunk_num} failed - no items generated")
                        break
                    
                    chunk_num += 1
                
                # All seeds already saved before processing
                
            else:
                # Sequential processing (original approach)
                for batch_num in range(1, self.total_batches + 1):
                    print(f"\n{'='*60}")
                    print(f"PROCESSING BATCH {batch_num}/{self.total_batches}")
                    print(f"{'='*60}")
                    
                    # Step 1: Sample seeds for this batch
                    seed_file = self.sample_seeds_for_batch(batch_num)
                    
                    # Step 2: Generate items (sequential)
                    items = self.generate_batch(batch_num, seed_file)
                    
                    if items:
                        # Append to consolidated files
                        self.append_to_consolidated_files(items)
                        
                        # Add to combined results
                        self.batch_results.append(items)
                        self.all_generated_items.extend(items)
                        
                        # Update statistics
                        self.generation_stats["total_seeds_used"] += len(items)
                        
                        print(f"  Batch {batch_num} completed: {len(items)} items generated")
                    else:
                        print(f"  ❌ Batch {batch_num} failed - no items generated")
                    
                    # Small delay between batches
                    if batch_num < self.total_batches:
                        time.sleep(1)
            
            # Step 3: Create final summary
            if self.all_generated_items:
                self.create_summary_report()
                
                print(f"\n{'='*60}")
                print(f"ENHANCED BATCH GENERATION COMPLETED SUCCESSFULLY!")
                print(f"{'='*60}")
                print(f"Total batches completed: {len(self.batch_results)}/{self.total_batches}")
                print(f"Total items generated: {len(self.all_generated_items)}")
                print(f"Expected items: {self.total_batches * self.seeds_per_batch}")
                print(f"Success rate: {len(self.all_generated_items) / (self.total_batches * self.seeds_per_batch) * 100:.1f}%")
                print(f"Processing method: {'Parallel (llm-batch-helper)' if self.use_batch_helper else 'Sequential'}")
                
                print(f"\n📁 Output files:")
                print(f"  - generated_items.jsonl: {len(self.all_generated_items)} items (main output)")
                if self.use_batch_helper:
                    print(f"  - metadata.jsonl: Metadata for all items")
                    print(f"  - all_seeds.jsonl: All seeds used")
                print(f"  - generation_summary.json: Complete statistics")
                
            else:
                print("\n❌ No items were generated in any batch!")
                
        except KeyboardInterrupt:
            print(f"\n⚠️ Generation interrupted by user")
            if self.all_generated_items:
                self.create_summary_report()
                print(f"Partial results saved: {len(self.all_generated_items)} items")
        except Exception as e:
            print(f"\n❌ Error during batch generation: {e}")
            if self.all_generated_items:
                self.create_summary_report()
                print(f"Partial results saved: {len(self.all_generated_items)} items")
            raise
