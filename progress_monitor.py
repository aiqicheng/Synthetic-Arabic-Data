#!/usr/bin/env python3
"""
Real-time progress monitor for arabic-synth style-subject-workflow
Shows progress bars and file counts as the workflow runs
"""

import time
import os
from pathlib import Path
import sys

def get_file_count(file_path):
    """Get line count of a file, return 0 if file doesn't exist"""
    try:
        return sum(1 for _ in file_path.open())
    except:
        return 0

def create_progress_bar(current, total, width=30):
    """Create a visual progress bar"""
    if total == 0:
        return "[" + " " * width + "] 0%"
    
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    percent = int(100 * current / total)
    return f"[{bar}] {percent}%"

def monitor_progress(output_dir="outputs/style_workflow"):
    """Monitor workflow progress with progress bars"""
    
    output_path = Path(output_dir)
    
    # Expected workflow steps and files
    workflow_steps = [
        {
            "name": "Step 1: Seed Sampling",
            "files": [
                ("social_seeds.jsonl", 10),
                ("physics_seeds.jsonl", 6),
                ("biology_seeds.jsonl", 6),
                ("science_seeds.jsonl", 4),
                ("islamic_studies_seeds.jsonl", 3)
            ]
        },
        {
            "name": "Step 2: Data Generation", 
            "files": [
                ("generate_style_social_500.jsonl", 500),
                ("generate_style_physics_500.jsonl", 500),
                ("generate_style_biology_500.jsonl", 500),
                ("generate_style_science_500.jsonl", 500),
                ("generate_style_islamic_studies_500.jsonl", 500)
            ]
        },
        {
            "name": "Step 3: Cleaning & Evaluation",
            "files": [
                ("social_clean.jsonl", 500),
                ("physics_clean.jsonl", 500),
                ("biology_clean.jsonl", 500),
                ("science_clean.jsonl", 500),
                ("islamic_studies_clean.jsonl", 500)
            ]
        }
    ]
    
    print("🔍 Arabic-Synth Workflow Progress Monitor")
    print("=" * 60)
    print(f"📁 Monitoring: {output_dir}")
    print("💡 Press Ctrl+C to stop monitoring")
    print()
    
    try:
        while True:
            # Clear screen
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print("🔍 Arabic-Synth Workflow Progress Monitor")
            print("=" * 60)
            print(f"📁 Monitoring: {output_dir}")
            print(f"⏰ Time: {time.strftime('%H:%M:%S')}")
            print()
            
            total_expected = 0
            total_actual = 0
            
            for step in workflow_steps:
                print(f"📋 {step['name']}")
                print("-" * 40)
                
                step_expected = sum(count for _, count in step['files'])
                step_actual = 0
                
                for filename, expected_count in step['files']:
                    file_path = output_path / filename
                    actual_count = get_file_count(file_path)
                    step_actual += actual_count
                    
                    # Status emoji
                    if actual_count >= expected_count:
                        status = "✅"
                    elif actual_count > 0:
                        status = "🔄"
                    else:
                        status = "⏳"
                    
                    # Progress bar for individual file
                    progress_bar = create_progress_bar(actual_count, expected_count, 20)
                    print(f"{status} {filename:<35} {progress_bar} {actual_count:>3}/{expected_count}")
                
                # Step summary
                step_progress = create_progress_bar(step_actual, step_expected, 30)
                print(f"📊 Step Total: {step_progress} {step_actual:>3}/{step_expected}")
                print()
                
                total_expected += step_expected
                total_actual += step_actual
            
            # Overall progress
            print("📈 Overall Progress")
            print("-" * 40)
            overall_progress = create_progress_bar(total_actual, total_expected, 40)
            print(f"🎯 Total: {overall_progress} {total_actual:>3}/{total_expected}")
            
            # Check if workflow is complete
            workflow_summary = output_path / "workflow_summary.json"
            if workflow_summary.exists():
                print()
                print("🎉 Workflow Complete!")
                print("📋 Summary file found: workflow_summary.json")
                break
            
            print()
            print("🔄 Refreshing in 3 seconds... (Ctrl+C to stop)")
            
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "outputs/style_workflow"
    monitor_progress(output_dir)
