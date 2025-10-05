#!/usr/bin/env python3
"""
Example script demonstrating batch processing with llm_batch_helper.

This script shows how to use the batch processing capabilities for
synthetic Arabic data generation.
"""

import json
from pathlib import Path
from arabic_synth.generators.batch_generation import run_batch_generation, BatchGenerationConfig


def main():
    """Demonstrate batch processing for synthetic data generation."""
    
    # Configuration
    output_dir = Path("outputs/batch_example")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Batch processing configuration
    batch_config = BatchGenerationConfig(
        batch_size=5,              # Small batch for demonstration
        max_retries=3,
        delay_between_batches=1.0,
        timeout=30.0,
        temperature=0.7,
        top_p=0.95
    )
    
    print("🚀 Starting batch generation example...")
    print(f"Batch size: {batch_config.batch_size}")
    print(f"Output directory: {output_dir}")
    
    try:
        # Run batch generation
        results = run_batch_generation(
            task="exams",
            num_samples=20,  # Small number for demonstration
            model="openai:gpt-4o",
            batch_config=batch_config,
            seed_path=None,  # No seed file for this example
            output_dir=output_dir,
            subject="Physics"
        )
        
        # Save results
        output_file = output_dir / "batch_generation_results.jsonl"
        with output_file.open("w", encoding="utf-8") as f:
            for item in results:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        
        print(f"✅ Batch generation completed!")
        print(f"Generated {len(results)} samples")
        print(f"Results saved to: {output_file}")
        
        # Display sample results
        print("\n📋 Sample results:")
        for i, item in enumerate(results[:3]):  # Show first 3 items
            print(f"\n--- Sample {i+1} ---")
            print(f"Question: {item.get('question', 'N/A')[:100]}...")
            print(f"Answer: {item.get('answer', 'N/A')}")
            print(f"Options: {len(item.get('options', []))} options")
        
    except ImportError as e:
        print(f"❌ Error: {e}")
        print("Please install llm_batch_helper:")
        print("pip install git+https://github.com/TianyiPeng/LLM_batch_helper.git")
    except Exception as e:
        print(f"❌ Batch generation failed: {e}")


if __name__ == "__main__":
    main()
