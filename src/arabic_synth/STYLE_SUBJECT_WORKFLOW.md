# Style-Subject Workflow

This module provides a complete workflow for generating synthetic Arabic data using style guides for individual subjects, as described in `Synthetic_from_StyleAndSubject.md`.

## Overview

The workflow follows these steps:

1. **Sample seeds** from test dataset for each subject with specific n_seeds per subject
2. **Generate synthetic data** using style guides for each subject
3. **Clean** the generated data to remove invalid/duplicate samples
4. **Evaluate** the cleaned data for quality assessment

## Configuration

The workflow uses a JSON configuration file to define subject settings and generation parameters. The default configuration is located at `src/arabic_synth/configs/style_subject_config.json`.

### Default Subject Configuration

| Subject | n_seeds | num_samples |
|---------|---------|-------------|
| Social | 10 | 500 |
| Physics | 6 | 500 |
| Biology | 6 | 500 |
| Science | 5 | 500 |
| Islamic Studies | 4 | 500 |

### Configuration File Structure

```json
{
  "subjects": {
    "Social": {
      "n_seeds": 10,
      "num_samples": 500
    },
    "Physics": {
      "n_seeds": 6,
      "num_samples": 500
    }
  },
  "generation": {
    "default_num_samples": 500,
    "use_batch_processing": true,
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
```

### Custom Configuration

You can create custom configuration files to:
- Adjust the number of seeds per subject
- Change the number of samples generated per subject
- Modify generation parameters (temperature, batch size, etc.)
- Update filtering criteria (grades, mode, etc.)

## Usage

### Command Line Interface

```bash
# Run the complete workflow with default settings
arabic-synth style-subject-workflow

# Run with custom output directory
arabic-synth style-subject-workflow --output-dir outputs/my_experiment

# Run with custom input CSV and model
arabic-synth style-subject-workflow \
    --input-csv data/my_test_data.csv \
    --model openai:gpt-4 \
    --seed 42

# Run with custom configuration file
arabic-synth style-subject-workflow \
    --config-file configs/my_custom_config.json \
    --output-dir outputs/custom_experiment
```

### Programmatic Usage

```python
from arabic_synth.style_subject_workflow import StyleSubjectWorkflow
from pathlib import Path

# Initialize workflow with default config
workflow = StyleSubjectWorkflow(
    output_dir=Path("outputs/style_subject"),
    input_csv=Path("data/test-00000-of-00001.arabic.csv"),
    model="openai:gpt-4o",
    seed=101
)

# Initialize workflow with custom config
workflow = StyleSubjectWorkflow(
    output_dir=Path("outputs/style_subject"),
    input_csv=Path("data/test-00000-of-00001.arabic.csv"),
    model="openai:gpt-4o",
    seed=101,
    config_file=Path("configs/my_custom_config.json")
)

# Run complete workflow (includes: sample → generate → clean → evaluate)
result = workflow.run_complete_workflow()

if result["success"]:
    print("Workflow completed successfully!")
    print(f"Summary: {result['summary_file']}")
else:
    print(f"Workflow failed: {result['error']}")
```

### Individual Steps

You can also run individual steps:

```python
# Step 1: Sample seeds
seed_files = workflow.step1_sample_seeds()

# Step 2: Generate synthetic data
generated_files = workflow.step2_generate_synthetic_data(seed_files)

# Step 3: Clean and evaluate
results = workflow.step3_clean_and_evaluate(generated_files)
```

## Output Structure

The workflow creates the following files in the output directory:

```
outputs/style_subject/
├── workflow.log                           # Detailed execution log
├── workflow_summary.json                  # Complete workflow summary
├── social_seeds.jsonl                     # Seeds for Social subject
├── physics_seeds.jsonl                    # Seeds for Physics subject
├── biology_seeds.jsonl                    # Seeds for Biology subject
├── science_seeds.jsonl                    # Seeds for Science subject
├── islamic_studies_seeds.jsonl            # Seeds for Islamic Studies subject
├── generate_style_social_6000.jsonl       # Generated data for Social
├── generate_style_physics_3600.jsonl      # Generated data for Physics
├── generate_style_biology_3600.jsonl      # Generated data for Biology
├── generate_style_science_2400.jsonl      # Generated data for Science
├── generate_style_islamic_studies_1800.jsonl # Generated data for Islamic Studies
├── social_clean.jsonl                     # Cleaned Social data
├── physics_clean.jsonl                    # Cleaned Physics data
├── biology_clean.jsonl                    # Cleaned Biology data
├── science_clean.jsonl                    # Cleaned Science data
└── islamic_studies_clean.jsonl            # Cleaned Islamic Studies data
```

## Requirements

- The input CSV file must contain exam data with columns: `grade`, `subject`, etc.
- The workflow filters for grades 9, 10, 11, 12 only
- Requires `arabic-synth` CLI to be available in PATH
- Requires OpenAI API access for generation (when using OpenAI models)

## Error Handling

The workflow includes comprehensive error handling:

- Validates input file existence
- Logs all operations with timestamps
- Continues processing other subjects if one fails
- Creates detailed error logs
- Provides summary of successful/failed operations

## Logging

All operations are logged to both:
- Console output (with emojis for easy reading)
- `workflow.log` file in the output directory

Log levels include INFO for normal operations and ERROR for failures.
