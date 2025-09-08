# Arabic Synthetic Dataset Pipeline

A comprehensive pipeline for generating high-quality Arabic synthetic datasets using persona-based LLM generation with seed constraints and quality validation.

## 🎯 Tasks

- **EXAMS**: Multi-subject MCQ questions (10,000 target)
- **Alghafa Sentiment**: Sentiment classification (positive:negative:neutral = 4:4:2, 10,000 target)  
- **Madinah QA Grammar**: Grammar error correction triplets (10,000 target)

## 🚀 Features

- **Persona-based Generation**: Role-playing prompts for authentic Arabic content
- **Seed Constraint System**: Uses ≤10 test samples as style guidance only (prevents data leakage)
- **Distribution Alignment**: Controlled answer distribution with quota scheduling
- **Quality Validation**: Fidelity, utility (TSTR), and privacy metrics
- **Data Augmentation**: Rule-based transformations and diversity filtering
- **CLI Interface**: Full pipeline orchestration with Typer

## 🏗️ Architecture

```
src/arabic_synth/
├── cli.py              # Command-line interface
├── generators/run.py   # Core generation logic
├── postprocess/clean.py # Data cleaning & deduplication
├── evaluate/evaluate.py # Quality evaluation
├── schemas/            # Pydantic validation schemas
├── prompts/templates.py # LLM prompt templates
└── utils/              # Core utilities
    ├── llm.py         # LLM API integration
    ├── seed_manager.py # Seed constraint system
    ├── quality_validator.py # Quality metrics
    └── anonymizer.py  # Data anonymization
```

## ⚙️ Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package
pip install -e .

# Set OpenAI API key
export OPENAI_API_KEY="your-api-key-here"
```

## 📖 Usage

### Generate Data

```bash
# Generate EXAMS with seed constraints and distribution control
arabic-synth generate exams \
  --num-samples 200 \
  --model openai:gpt-4o \
  --seed-file data/seeds/exams_seeds_from_testset.jsonl \
  --temperature 0.9 \
  --top-p 0.95

# Generate sentiment data
arabic-synth generate sentiment --num-samples 100 --model openai:gpt-4o

# Generate grammar data  
arabic-synth generate grammar --num-samples 100 --model openai:gpt-4o
```

### Clean & Process

```bash
# Clean generated data (schema validation, deduplication, TTR filtering)
arabic-synth clean exams \
  --in-path outputs/exams_raw.jsonl \
  --out-path outputs/exams_clean.jsonl

# Evaluate quality metrics
arabic-synth evaluate exams --in-path outputs/exams_clean.jsonl
```

### Export

```bash
# Export to various formats with metadata
arabic-synth export exams \
  --in-path outputs/exams_clean.jsonl \
  --out-format csv \
  --meta-batch-id pilot-001
```

## 🔒 Seed Constraint System

The pipeline uses a sophisticated seed constraint system to prevent data leakage:

- **Max Seeds**: ≤10 test samples allowed
- **Style Only**: Seeds provide style guidance, not content replication
- **Diversity Check**: Ensures seed variety across subjects
- **Similarity Validation**: Prevents generated content from being too similar to seeds
- **Audit Trail**: Full logging of seed usage and constraints

## 📊 Quality Metrics

### Fidelity
- Length distribution comparison (mean, std dev)
- Answer balance (L1 distance from target)
- Vocabulary diversity (Type-Token Ratio)
- Content overlap analysis (Jaccard similarity)

### Utility  
- **TSTR (Train on Synthetic, Test on Real)**: Trains classifier on synthetic data, tests on real data
- Performance comparison metrics

### Privacy
- Re-identification risk assessment
- Token overlap analysis
- Differential privacy considerations

## 🎛️ Advanced Controls

- **Temperature & Top-p**: Control generation diversity
- **Answer Distribution**: Target specific answer letter ratios
- **TTR Filtering**: Remove low-diversity samples (default threshold: 0.18)
- **Batch Processing**: Configurable batch sizes for large-scale generation

## 📁 Project Structure

```
Synthetic Data/
├── src/arabic_synth/          # Core package
├── data/seeds/                # Seed data (≤10 samples)
├── outputs/                   # Generated datasets
├── test-00000-of-00001.arabic.csv  # Original test set
├── pyproject.toml            # Package configuration
├── README.md                 # This file
└── SEED_CONSTRAINTS.md       # Detailed constraint documentation
```

## 🔄 Pipeline Flow

1. **Seed Loading**: Extract style guidance from ≤10 test samples
2. **Generation**: LLM generation with persona prompts and distribution control
3. **Cleaning**: Schema validation, deduplication, quality filtering
4. **Evaluation**: Comprehensive quality assessment
5. **Export**: Format conversion with metadata

## 🚦 Scaling Strategy

- **Pilot**: 100-200 samples for validation
- **Small Scale**: 1K samples for quality assessment  
- **Full Scale**: 10K samples with monitoring
- **Continuous**: Quality checks and retraining

## 🛠️ Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
```

## 📝 Notes

- **Model Selection**: Currently supports OpenAI models via `openai:MODEL_NAME`
- **Mock Mode**: Use `--model mock` for testing without API calls
- **Seed Diversity**: Ensure seeds cover different subjects and difficulty levels
- **Quality Thresholds**: Adjust TTR and similarity thresholds as needed

## 🤝 Contributing

1. Follow the seed constraint system
2. Maintain quality metrics
3. Test with mock mode first
4. Document any prompt or parameter changes 