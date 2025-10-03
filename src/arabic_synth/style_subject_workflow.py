#!/usr/bin/env python3
"""
Style-Subject Workflow Orchestrator

This script orchestrates the complete workflow for generating synthetic Arabic data
using style guides for individual subjects, as described in Synthetic_from_StyleAndSubject.md.

Workflow:
1. Sample seeds from test dataset for each subject
2. Generate synthetic data using style guides for each subject  
3. Clean and evaluate the generated data

Usage:
    python -m arabic_synth.style_subject_workflow --output-dir outputs/style_subject
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
from datetime import datetime
import time


class StyleSubjectWorkflow:
    """Orchestrates the complete style-subject workflow for synthetic data generation."""
    
    def __init__(self, output_dir: Path, input_csv: Path, model: str = "openai:gpt-4o", seed: int = 101, 
                 config_file: Optional[Path] = None):
        """
        Initialize the workflow orchestrator.
        
        Args:
            output_dir: Directory to store all intermediate and final outputs
            input_csv: Path to the input CSV file (test dataset)
            model: LLM model to use for generation
            seed: Random seed for reproducibility
            config_file: Path to configuration file (defaults to built-in config)
        """
        self.output_dir = Path(output_dir)
        self.input_csv = Path(input_csv)
        self.model = model
        self.seed = seed
        
        # Load configuration
        self.config = self._load_config(config_file)
        
        # Extract configuration values
        self.subjects_config = {subject: data["n_seeds"] for subject, data in self.config["subjects"].items()}
        self.subjects_samples = {subject: data["num_samples"] for subject, data in self.config["subjects"].items()}
        self.use_batch_processing = self.config["generation"]["use_batch_processing"]
        self.batch_size = self.config["generation"]["batch_size"]
        
        # Create output directory first
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging after directory is created
        self._setup_logging()
        
    def _load_config(self, config_file: Optional[Path] = None) -> Dict:
        """
        Load configuration from file or use default.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        if config_file is None:
            # Use default config file
            config_file = Path(__file__).parent / "configs" / "style_subject_config.json"
        
        if config_file.exists():
            with config_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # Fallback to hardcoded config if file doesn't exist
            return {
                "subjects": {
                    "Social": {"n_seeds": 10, "num_samples": 500},
                    "Physics": {"n_seeds": 6, "num_samples": 500},
                    "Biology": {"n_seeds": 6, "num_samples": 500},
                    "Science": {"n_seeds": 5, "num_samples": 500},
                    "Islamic Studies": {"n_seeds": 4, "num_samples": 500}
                },
                "generation": {
                    "default_num_samples": 500,
                    "use_batch_processing": True,
                    "batch_size": 10,
                    "max_retries": 3,
                    "delay_between_batches": 1.0,
                    "timeout": 30.0,
                    "temperature": 0.7,
                    "top_p": 0.95
                },
                "filtering": {
                    "grades": "9,10,11,12",
                    "mode": "stratified",
                    "stratify_col": "grade"
                }
            }
        
    def _setup_logging(self):
        """Setup logging configuration."""
        log_file = self.output_dir / "workflow.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def _run_command(self, cmd: List[str], description: str) -> Tuple[bool, str]:
        """
        Run a command and return success status and output.
        
        Args:
            cmd: Command to run as list of strings
            description: Description of what the command does
            
        Returns:
            Tuple of (success: bool, output: str)
        """
        self.logger.info(f"Running: {description}")
        self.logger.info(f"Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            self.logger.info(f"✅ {description} completed successfully")
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ {description} failed with exit code {e.returncode}")
            self.logger.error(f"Error output: {e.stderr}")
            return False, e.stderr
            
    def step1_sample_seeds(self) -> Dict[str, Path]:
        """
        Step 1: Sample seeds from test dataset for each subject.
        
        Returns:
            Dictionary mapping subject names to their seed file paths
        """
        self.logger.info("🚀 Step 1: Sampling seeds for each subject")
        
        seed_files = {}
        
        for subject, n_seeds in self.subjects_config.items():
            self.logger.info(f"Sampling {n_seeds} seeds for {subject}")
            
            # Create subject-specific output file
            seed_file = self.output_dir / f"{subject.lower().replace(' ', '_')}_seeds.jsonl"
            
            # Build command for arabic-synth sample-and-convert
            cmd = [
                "arabic-synth", "sample-and-convert",
                "--input-file", str(self.input_csv),
                "--output-file", str(seed_file),
                "--n", str(n_seeds),
                "--filter-grade", self.config["filtering"]["grades"],
                "--filter-subject", subject,
                "--mode", self.config["filtering"]["mode"],
                "--stratify-col", self.config["filtering"]["stratify_col"],
                "--seed", str(self.seed)
            ]
            
            success, output = self._run_command(cmd, f"Sampling {n_seeds} seeds for {subject}")
            
            if success:
                seed_files[subject] = seed_file
                self.logger.info(f"✅ {subject} seeds saved to {seed_file}")
            else:
                self.logger.error(f"❌ Failed to sample seeds for {subject}")
                raise RuntimeError(f"Failed to sample seeds for {subject}")
                
        return seed_files
        
    def step2_generate_synthetic_data(self, seed_files: Dict[str, Path]) -> Dict[str, Path]:
        """
        Step 2: Generate synthetic data using style guides for each subject.
        
        Args:
            seed_files: Dictionary mapping subjects to their seed file paths
            
        Returns:
            Dictionary mapping subjects to their generated data file paths
        """
        self.logger.info("🎨 Step 2: Generating synthetic data using style guides")
        
        generated_files = {}
        
        for subject, seed_file in seed_files.items():
            n_seeds = self.subjects_config[subject]
            num_samples = self.subjects_samples[subject]
            
            self.logger.info(f"Generating {num_samples} samples for {subject} using {n_seeds} seeds")
            
            # Create subject-specific output file
            output_file = self.output_dir / f"generate_style_{subject.lower().replace(' ', '_')}_{num_samples}.jsonl"
            
            if self.use_batch_processing:
                # Use batch processing with llm_batch_helper
                success = self._run_batch_generation(subject, seed_file, num_samples, output_file)
            else:
                # Use traditional CLI approach
                success = self._run_cli_generation(subject, seed_file, num_samples, output_file)
            
            if success:
                generated_files[subject] = output_file
                self.logger.info(f"✅ {subject} synthetic data saved to {output_file}")
            else:
                self.logger.error(f"❌ Failed to generate synthetic data for {subject}")
                raise RuntimeError(f"Failed to generate synthetic data for {subject}")
                
        return generated_files
    
    def _run_batch_generation(self, subject: str, seed_file: Path, num_samples: int, output_file: Path) -> bool:
        """Run batch generation using llm_batch_helper."""
        try:
            from arabic_synth.generators.batch_generation import run_batch_generation, BatchGenerationConfig
            
            self.logger.info(f"Using batch processing for {subject} with batch size {self.batch_size}")
            
            # Configure batch processing
            batch_config = BatchGenerationConfig(
                batch_size=self.batch_size,
                max_retries=self.config["generation"]["max_retries"],
                delay_between_batches=self.config["generation"]["delay_between_batches"],
                timeout=self.config["generation"]["timeout"],
                temperature=self.config["generation"]["temperature"],
                top_p=self.config["generation"]["top_p"]
            )
            
            # Run batch generation
            start_time = time.time()
            results = run_batch_generation(
                task="exams",
                num_samples=num_samples,
                model=self.model,
                batch_config=batch_config,
                seed_path=seed_file,
                output_dir=self.output_dir,
                subject=subject
            )
            generation_time = time.time() - start_time
            
            # Save results
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with output_file.open("w", encoding="utf-8") as f:
                for item in results:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
            success_rate = (len(results) / num_samples) * 100 if num_samples > 0 else 0
            self.logger.info(f"Batch generation for {subject}: {len(results)}/{num_samples} samples in {generation_time:.1f}s (Success rate: {success_rate:.1f}%)")
            
            return True
            
        except ImportError as e:
            self.logger.warning(f"llm_batch_helper not available, falling back to CLI: {e}")
            return self._run_cli_generation(subject, seed_file, num_samples, output_file)
        except Exception as e:
            self.logger.error(f"Batch generation failed for {subject}: {e}")
            return False
    
    def _run_cli_generation(self, subject: str, seed_file: Path, num_samples: int, output_file: Path) -> bool:
        """Run generation using traditional CLI approach."""
        # Build command for arabic-synth generate
        cmd = [
            "arabic-synth", "generate", "exams",
            "--output-dir", str(self.output_dir),
            "--seed-file", str(seed_file),
            "--model", self.model,
            "--num-samples", str(num_samples),
            "--subject", subject
        ]
        
        success, output = self._run_command(cmd, f"Generating {num_samples} samples for {subject}")
        
        if success:
            # The CLI creates the file with a specific naming convention
            # We need to find the actual generated file
            expected_file = self.output_dir / f"generate_style_{subject}_{num_samples}.jsonl"
            if expected_file.exists():
                # Move/rename to our expected output file
                if expected_file != output_file:
                    expected_file.rename(output_file)
                return True
            else:
                # Try to find the actual generated file
                pattern_files = list(self.output_dir.glob(f"generate_style_{subject}*.jsonl"))
                if pattern_files:
                    if pattern_files[0] != output_file:
                        pattern_files[0].rename(output_file)
                    return True
                else:
                    self.logger.error(f"❌ Generated file not found for {subject}")
                    return False
        else:
            return False
        
    def step3_clean_and_evaluate(self, generated_files: Dict[str, Path]) -> Dict[str, Dict[str, Path]]:
        """
        Step 3: Clean and evaluate the generated data for each subject.
        
        Args:
            generated_files: Dictionary mapping subjects to their generated data file paths
            
        Returns:
            Dictionary mapping subjects to their cleaned and evaluation file paths
        """
        self.logger.info("🧹 Step 3: Cleaning and evaluating generated data")
        
        results = {}
        
        for subject, generated_file in generated_files.items():
            self.logger.info(f"Cleaning and evaluating data for {subject}")
            
            # Clean the data
            clean_file = self.output_dir / f"{subject.lower().replace(' ', '_')}_clean.jsonl"
            
            clean_cmd = [
                "arabic-synth", "clean", "exams",
                "--in-path", str(generated_file),
                "--out-path", str(clean_file)
            ]
            
            success, output = self._run_command(clean_cmd, f"Cleaning data for {subject}")
            
            if not success:
                self.logger.error(f"❌ Failed to clean data for {subject}")
                continue
                
            # Evaluate the cleaned data
            eval_cmd = [
                "arabic-synth", "evaluate-style", "exams",
                "--in-path", str(clean_file)
            ]
            
            success, output = self._run_command(eval_cmd, f"Evaluating data for {subject}")
            
            if success:
                results[subject] = {
                    "generated": generated_file,
                    "cleaned": clean_file,
                    "evaluation": output
                }
                self.logger.info(f"✅ {subject} data cleaned and evaluated")
            else:
                self.logger.warning(f"⚠️ Evaluation failed for {subject}, but cleaning succeeded")
                results[subject] = {
                    "generated": generated_file,
                    "cleaned": clean_file,
                    "evaluation": None
                }
                
        return results
        
    def create_workflow_summary(self, seed_files: Dict[str, Path], 
                              generated_files: Dict[str, Path], 
                              results: Dict[str, Dict[str, Path]]) -> Path:
        """
        Create a comprehensive workflow summary.
        
        Args:
            seed_files: Dictionary mapping subjects to seed file paths
            generated_files: Dictionary mapping subjects to generated file paths  
            results: Dictionary mapping subjects to their processing results
            
        Returns:
            Path to the summary file
        """
        summary = {
            "workflow": "style-subject-synthetic-generation",
            "timestamp": datetime.now().isoformat(),
            "input_csv": str(self.input_csv),
            "output_dir": str(self.output_dir),
            "model": self.model,
            "seed": self.seed,
            "subjects_config": self.subjects_config,
            "results": {
                "seed_files": {subject: str(path) for subject, path in seed_files.items()},
                "generated_files": {subject: str(path) for subject, path in generated_files.items()},
                "processed_results": {
                    subject: {
                        "generated": str(data["generated"]),
                        "cleaned": str(data["cleaned"]),
                        "evaluation_success": data["evaluation"] is not None
                    }
                    for subject, data in results.items()
                }
            }
        }
        
        summary_file = self.output_dir / "workflow_summary.json"
        with summary_file.open("w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
            
        self.logger.info(f"📋 Workflow summary saved to {summary_file}")
        return summary_file
        
    def run_complete_workflow(self) -> Dict:
        """
        Run the complete style-subject workflow.
        
        Returns:
            Dictionary containing workflow results and summary
        """
        self.logger.info("🚀 Starting Complete Style-Subject Workflow")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"Input CSV: {self.input_csv}")
        self.logger.info(f"Model: {self.model}")
        self.logger.info(f"Seed: {self.seed}")
        
        try:
            # Step 1: Sample seeds for each subject
            seed_files = self.step1_sample_seeds()
            
            # Step 2: Generate synthetic data using style guides
            generated_files = self.step2_generate_synthetic_data(seed_files)
            
            # Step 3: Clean and evaluate the generated data
            results = self.step3_clean_and_evaluate(generated_files)
            
            # Create workflow summary
            summary_file = self.create_workflow_summary(seed_files, generated_files, results)
            
            # Final summary
            self.logger.info("🎉 Workflow Complete!")
            self.logger.info(f"📊 Processed {len(self.subjects_config)} subjects:")
            for subject in self.subjects_config.keys():
                if subject in results:
                    self.logger.info(f"  ✅ {subject}: Generated → Cleaned → Evaluated")
                else:
                    self.logger.info(f"  ❌ {subject}: Failed")
                    
            self.logger.info(f"📋 Summary saved to: {summary_file}")
            
            return {
                "success": True,
                "seed_files": seed_files,
                "generated_files": generated_files,
                "results": results,
                "summary_file": summary_file
            }
            
        except Exception as e:
            self.logger.error(f"❌ Workflow failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Style-Subject Workflow Orchestrator for Synthetic Arabic Data Generation"
    )
    parser.add_argument(
        "--output-dir", 
        type=Path, 
        default=Path("outputs/style_subject"),
        help="Output directory for all workflow results"
    )
    parser.add_argument(
        "--input-csv",
        type=Path, 
        default=Path("data/test-00000-of-00001.arabic.csv"),
        help="Input CSV file (test dataset)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="openai:gpt-4o",
        help="LLM model to use for generation"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=101,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--config-file",
        type=Path,
        help="Path to configuration file (defaults to built-in config)"
    )
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not args.input_csv.exists():
        print(f"❌ Error: Input CSV file not found: {args.input_csv}")
        sys.exit(1)
        
    # Create and run workflow
    workflow = StyleSubjectWorkflow(
        output_dir=args.output_dir,
        input_csv=args.input_csv,
        model=args.model,
        seed=args.seed,
        config_file=args.config_file
    )
    
    result = workflow.run_complete_workflow()
    
    if result["success"]:
        print("🎉 Workflow completed successfully!")
        print(f"📋 Summary: {result['summary_file']}")
        sys.exit(0)
    else:
        print(f"❌ Workflow failed: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
