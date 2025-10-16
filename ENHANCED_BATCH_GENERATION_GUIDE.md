# Enhanced Batch Generation Guide

## Overview

The Enhanced Batch Generation Program integrates `llm-batch-helper` for parallel processing while maintaining one-prompt-per-seed strategy. It's used by `run_production_batch.sh` for large-scale Arabic MMLU question generation.

## Key Features

- ✅ **Parallel Processing**: 5-10x faster via llm-batch-helper concurrent API calls
- ✅ **One-Prompt-Per-Seed**: Each seed generates exactly one MCQ item
- ✅ **Production Ready**: Used in automated 5-run production batches
- ✅ **Automatic Fallback**: Falls back to sequential if batch helper unavailable

## Dependencies

### Core Dependencies (from pyproject.toml)
- `llm_batch_helper` - Parallel API processing
- `typer` - CLI interface
- `pydantic` - Data validation
- `python-dotenv` - Environment management

### Installation
```bash
# Install package with dependencies
pip install -e .

# Setup API keys (create .env file)
echo "OPENAI_API_KEY=your-key" >> .env
```

## Production Workflow

### Automated Production Runs (run_production_batch.sh)
```bash
# Run 5 production runs with different input files
./run_production_batch.sh
```

**What it does:**
1. Runs 5 separate generation runs using `arabic-synth generate-enhanced-batch`
2. Each run processes 100 batches × 20 seeds = 2000 MCQs
3. Combines all results into `combine_mcq.jsonl`
4. Cleans combined dataset using `arabic-synth clean mmlu`
5. Evaluates final dataset using `arabic-synth evaluate mmlu`

### Manual Usage
```bash
# Single run with enhanced batch processing
arabic-synth generate-enhanced-batch \
    --input-file data/arabicmmlu/arabicmmlu_1.csv \
    --output-dir outputs/my_run \
    --total-batches 100 \
    --seeds-per-batch 20 \
    --max-concurrent-requests 100 \
    --model openai:gpt-4o-mini
```

## File Structure

### Input Files (Production)
```
data/arabicmmlu/
├── arabicmmlu_1.csv    # Input for run 1
├── arabicmmlu_2.csv    # Input for run 2
├── arabicmmlu_3.csv    # Input for run 3
├── arabicmmlu_4.csv    # Input for run 4
└── arabicmmlu_5.csv    # Input for run 5
```

### Output Structure
```
outputs/production/
├── run1/
│   ├── generated_items.jsonl      # Generated MCQs for run 1
│   ├── generation_summary.json    # Statistics for run 1
│   ├── metadata.jsonl            # Generation metadata
│   └── cache/                    # llm-batch-helper cache
├── run2/ ... run5/               # Same structure for other runs
├── combine_mcq.jsonl             # All 10,000 items combined
├── combine_mcq_cleaned.jsonl     # Cleaned final dataset
└── combine_summaries.json        # Combined statistics
```

### Core Program Files
```
src/arabic_synth/
├── cli.py                        # CLI interface with generate_enhanced_batch command
├── batch/
│   └── enhanced_generator.py     # EnhancedBatchGenerationProgram class
├── utils/
│   ├── llm.py                    # LLM API integration
│   ├── seed_manager.py           # Seed constraint system
│   └── diversity.py              # Diversity features
└── prompts/
    └── templates.py              # MMLU_TEACHER_PROMPT template
```

## Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--input-file` | Required | Path to Arabic MMLU CSV file |
| `--output-dir` | Required | Output directory for results |
| `--model` | `openai:gpt-4o` | LLM model (OpenAI, OpenRouter, Together.ai, Gemini) |
| `--sampling-mode` | `stratified` | Seed sampling: `stratified` or `uniform` |
| `--seeds-per-batch` | `20` | Number of seeds per batch |
| `--total-batches` | `100` | Number of batches (production: 100) |
| `--max-concurrent-requests` | `100` | Concurrent API requests (production: 100) |

## How It Works

### Processing Flow
```
For each batch (1-100):
├── Sample 20 seeds with varied random seed
├── Generate 20 prompts using MMLU_TEACHER_PROMPT template
├── Send all 20 prompts in parallel via llm-batch-helper
├── Process 20 responses concurrently
└── Generate 20 MCQ items (one per seed)

Final: Combine all batches → Clean → Evaluate
```

### Key Components
- **SeedManager**: Samples seeds from input CSV with stratification
- **LLM Integration**: Uses `llm_batch_helper` for parallel API calls
- **Template System**: `MMLU_TEACHER_PROMPT` generates Arabic MCQs
- **Diversity Features**: Jitter, prompt variation, duplicate screening

### Performance
- **Speed**: 5-10x faster than sequential processing
- **Production Scale**: 100 batches × 20 seeds = 2000 MCQs per run
- **Total Production**: 5 runs × 2000 = 10,000 MCQs

## Generated Item Format

```json
{
  "question": "السؤال باللغة العربية",
  "options": ["A. الخيار الأول", "B. الخيار الثاني", "C. الخيار الثالث", "D. الخيار الرابع"],
  "answer": "A",
  "_seed_index": 15,
  "_seed_question": "السؤال الأصلي المستخدم كبذرة...",
  "_batch_number": 3,
  "_generation_timestamp": "2024-01-15T10:30:45.123456",
  "_target_letter": "A"
}
```

## Production Commands

### Run Full Production Pipeline
```bash
# Execute the complete production workflow
./run_production_batch.sh
```

### Individual Commands (for debugging)
```bash
# Generate items
arabic-synth generate-enhanced-batch --input-file data/arabicmmlu/arabicmmlu_1.csv --output-dir outputs/production/run1 --total-batches 100 --seeds-per-batch 20

# Clean dataset
arabic-synth clean mmlu --in-path outputs/production/combine_mcq.jsonl --out-path outputs/production/combine_mcq_cleaned.jsonl

# Evaluate quality
arabic-synth evaluate mmlu --in-path outputs/production/combine_mcq_cleaned.jsonl
```

## Troubleshooting

### Common Issues
1. **Missing API Key**: Ensure `.env` file exists with `OPENAI_API_KEY`
2. **Rate Limiting**: Reduce `--max-concurrent-requests` 
3. **Memory Issues**: Reduce `--seeds-per-batch` or `--total-batches`

### Performance Tips
- Use `openai:gpt-4o-mini` for cost-effective generation
- Monitor cache directory size (can grow large with many runs)
- Production runs generate ~10,000 items total (5 runs × 2000 each)
