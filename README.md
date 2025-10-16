# Arabic Synthetic Dataset Pipeline

A comprehensive pipeline for generating high-quality Arabic synthetic datasets using persona-based LLM generation with seed constraints and quality validation.

## 🎯 Tasks

- **EXAMS**: Multi-subject MCQ questions (10,000 target)
- **MMLU**: Massive Multitask Language Understanding questions with subject generalization
- **Alghafa Sentiment**: Sentiment classification (positive:negative:neutral = 4:4:2, 10,000 target)  
- **Madinah QA Grammar**: Grammar error correction triplets (10,000 target)

## 🚀 Features

- **Persona-based Generation**: Role-playing prompts for authentic Arabic content
- **Seed Constraint System**: Uses ≤10 test samples as style guidance only (prevents data leakage)
- **Subject Generalization**: Dynamic MMLU support for any subject domain
- **Distribution Alignment**: Controlled answer distribution with quota scheduling
- **Quality Validation**: Fidelity, utility (TSTR), and privacy metrics
- **Data Augmentation**: Rule-based transformations and diversity filtering
- **CLI Interface**: Full pipeline orchestration with Typer

## 🏗️ Architecture

```
src/arabic_synth/
├── cli.py                     # 🎯 Main CLI interface (Typer-based) with MMLU support
├── batch/                     # 🚀 ENHANCED BATCH PROCESSING
│   └── enhanced_generator.py  # EnhancedBatchGenerationProgram with llm-batch-helper
├── data_prep/                 # 📊 DATA PREPARATION PHASE
│   ├── exam_processor.py      # Exam CSV processing and conversion
│   ├── mmlu_processor.py      # MMLU CSV processing with subject generalization
│   └── personas_select.py     # Persona selection and filtering
├── generators/                # 🚀 GENERATION PHASE
│   ├── run.py                 # Core generation logic with seed constraints & MMLU support
│   └── persona_augment.py     # Persona-augmented generation utilities
├── persona/                   # 👤 PERSONA PIPELINE
│   ├── build_requests.py      # Build persona-augmented requests
│   ├── send_requests.py       # Send requests to LLM APIs
│   └── templates_persona.py   # Persona-specific prompt templates
├── postprocess/               # 🧹 POST-PROCESSING PHASE
│   └── clean.py               # Data cleaning with MMLU support & deduplication
├── evaluate/                  # 📊 EVALUATION PHASE
│   ├── evaluate_style.py      # Style evaluation with MMLU support
│   └── evaluate_persona.py    # Persona-augmented quality assessment
├── augment/                   # 🔄 AUGMENTATION PHASE
│   └── augment.py             # Data augmentation and variant generation
├── prompts/                   # 📝 PROMPT TEMPLATES
│   └── templates.py           # LLM templates with MMLU subject generalization
├── configs/                   # ⚙️ CONFIGURATION FILES
│   ├── style_subject_config.json  # Default style-subject workflow config
│   └── small_batch.json       # Small batch configuration template
└── utils/                     # 🛠️ CORE UTILITIES
    ├── llm.py                 # LLM API integration (OpenAI, etc.)
    ├── seed_manager.py        # Seed constraint system with MMLU support
    ├── quality_validator.py   # Quality metrics and validation
    ├── io.py                  # File I/O operations
    ├── anonymizer.py          # Data anonymization utilities
    ├── similarity.py          # Similarity checking and deduplication
    └── diversity.py           # Diversity features for enhanced generation

src/schemas/                   # 🔍 VALIDATION SCHEMAS
├── exams.py                   # Exam data structure validation
├── sentiment.py               # Sentiment analysis schemas
├── grammar.py                 # Grammar correction schemas
└── mmlu.py                    # MMLU data validation with unified schema
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

## 📖 Workflows

The pipeline supports three main workflows for Arabic synthetic data generation:

### 🚀 Enhanced Batch Generation Workflow (Updated Oct. 16)
**Purpose**: Large-scale Arabic MMLU question generation with parallel processing
1. **Input Processing**: Uses multiple CSV files (`arabicmmlu_1.csv` through `arabicmmlu_5.csv`)
2. **Parallel Generation**: 5-10x faster via `llm-batch-helper` concurrent API calls
3. **Production Scale**: 100 batches × 20 seeds × 5 runs = 10,000 MCQs total
4. **Automated Pipeline**: Combines, cleans, and evaluates all results

```bash
# Run complete production workflow
./run_production_batch.sh

# Manual single run
arabic-synth generate-enhanced-batch --input-file data/arabicmmlu/arabicmmlu_1.csv --output-dir outputs/run1 --total-batches 100 --seeds-per-batch 20
```

### 🎨 Style Guide Workflow
**Purpose**: Generate data following consistent style patterns from seed examples

#### Manual Style Guide Pipeline
1. **Seed Selection**: Extract/sample representative examples
2. **Style-Based Generation**: Use `generators/run.py` with style templates (`prompts/templates.py`)
   - **Template Location**: `./src/arabic_synth/prompts/templates.py`
   - **Process**: Generate → Review → Tune → Repeat until quality targets met
3. **Post-Processing**: Clean, validate, and evaluate quality

```bash
# Quick start - Manual Style Guide Pipeline
arabic-synth sample-and-convert exams --input-file data/test-*.csv --output-file outputs/seeds.jsonl --n 10 --mode stratified

# Check outputs and refine prompts/templates.py as needed
arabic-synth generate exams --output-dir outputs/style_guide_test --seed-file outputs/seeds.jsonl --model openai:gpt-4o --num-samples 200

arabic-synth clean exams --in-path outputs/style_guide_test/generate_style_200.jsonl --out-path outputs/exams_clean.jsonl
arabic-synth evaluate-style exams --in-path outputs/exams_clean.jsonl
```

#### Automated Style-Subject Workflow (Sep.28 Update)
**Purpose**: Automated subject-specific generation with style guides
1. **Sample seeds** from test dataset for each subject (configurable via JSON config)
2. **Generate synthetic data** using style guides for each subject (configurable samples per subject)
3. **Clean** generated data to remove invalid/duplicate samples
4. **Evaluate** cleaned data for quality assessment

```bash
# Complete automated workflow with default config
arabic-synth style-subject-workflow --output-dir outputs/style_subject

# With custom configuration file
arabic-synth style-subject-workflow --config-file configs/my_config.json --output-dir outputs/custom

# Programmatic usage
from arabic_synth.style_subject_workflow import StyleSubjectWorkflow
workflow = StyleSubjectWorkflow(output_dir=Path("outputs/style_subject"))
result = workflow.run_complete_workflow()
```

### 👤 Persona Enhanced Workflow  
**Purpose**: Generate diverse data using persona-based perspectives
1. **Seed Selection**: Prepare base examples for persona augmentation
2. **Persona Requests**: Build requests with persona templates (`persona/templates_persona.py`)
   - **Template Location**: `./src/arabic_synth/persona/templates_persona.py`
   - **Process**: Generate → Review → Tune → Repeat until persona consistency achieved
3. **Post-Processing**: Quality assessment and evaluation

```bash
# Quick start - Persona Pipeline
arabic-synth sample-and-convert exams --input-file data/test-*.csv --output-file outputs/seeds.jsonl --n 20
arabic-synth select-personas --input-file data/personas/personas_all.jsonl --output-file outputs/personas.jsonl --n 200

# Check outputs and refine persona/templates_persona.py as needed
arabic-synth build-persona-requests --exams-path outputs/seeds.jsonl --personas-path outputs/personas.jsonl
arabic-synth send-persona-requests --model openai:gpt-4o

arabic-synth evaluate-persona --input-file outputs/exams_pers_raw.jsonl
```

### 🔄 Combined Style-Persona Workflow
**Purpose**: Best of both worlds - style consistency with persona diversity
1. **Stratified Sampling**: Extract balanced seeds from original test data
2. **Style Guide Generation**: Create styled examples using seed constraints  
3. **Persona Selection**: Choose diverse personas for augmentation
4. **Combined Generation**: Apply personas to styled seeds for maximum diversity

```bash
# Quick start - Combined Workflow (RECOMMENDED)
arabic-synth style-persona-workflow \
  --input-csv data/test-00000-of-00001.arabic.csv \
  --personas-path data/personas/selected_200.jsonl \
  --n-seeds 20 \
  --n-styled 100 \
  --per-item-personas 5 \
  --model openai:gpt-4o
```

**📋 Detailed Guides**: 
- Style Guide: `docs/StyleGuide_PIPELINE_DETAILED.md`
- Persona Pipeline: `docs/Persona_PIPELINE_DETAILED.md`  
- Combined Workflow: `docs/STYLE_PERSONA_WORKFLOW_GUIDE.md`
- Style-Subject Workflow: `docs/STYLE_SUBJECT_WORKFLOW.md`
- MMLU Workflow: `Style_ArbMMLU_Workflow.md`
- Enhanced Batch Generation: `ENHANCED_BATCH_GENERATION_GUIDE.md`

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
- **Diversity Features**: Low-overhead diversity enhancement with sampling jitter, prompt micro-variation, and fast duplicate detection (SimHash-based)

## 📁 Project Structure

```
Synthetic-Arabic-Data-persona/
├── src/arabic_synth/          # Core package
├── data/                      # Input data and seeds
│   ├── arabicmmlu/           # Arabic MMLU CSV files for production
│   ├── personas/             # Persona data
│   └── seeds/                # Seed data (≤10 samples)
├── outputs/                   # Generated datasets
│   ├── production/           # Production batch results
│   ├── mmlu_10k/            # Large-scale MMLU generation
│   └── style_workflow/       # Style-based generation results
├── docs/                      # Documentation
├── run_production_batch.sh    # Production batch script
├── ENHANCED_BATCH_GENERATION_GUIDE.md  # Enhanced batch guide
├── pyproject.toml            # Package configuration
└── README.md                 # This file
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