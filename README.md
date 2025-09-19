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
├── cli.py                     # 🎯 Main CLI interface (Typer-based)
├── data_prep/                 # 📊 DATA PREPARATION PHASE
│   ├── exam_processor.py      # Combined sampling & CSV-to-JSONL conversion
│   └── personas_select.py     # Persona selection and filtering
├── generators/                # 🚀 GENERATION PHASE
│   ├── run.py                 # Core generation logic with seed constraints
│   └── persona_augment.py     # Persona-augmented generation utilities
├── persona/                   # 👤 PERSONA PIPELINE
│   ├── build_requests.py      # Build persona-augmented requests
│   ├── send_requests.py       # Send requests to LLM APIs
│   └── templates_persona.py   # Persona-specific prompt templates
├── postprocess/               # 🧹 POST-PROCESSING PHASE
│   └── clean.py               # Data cleaning, validation & deduplication
├── evaluate/                  # 📊 EVALUATION PHASE
│   ├── evaluate_style.py      # Style Guide Pipeline evaluation
│   └── evaluate_persona.py    # Persona-augmented quality assessment
├── augment/                   # 🔄 AUGMENTATION PHASE
│   └── augment.py             # Data augmentation and variant generation
├── prompts/                   # 📝 PROMPT TEMPLATES
│   └── templates.py           # LLM prompt templates (Style Guide)
├── schemas/                   # 🔍 VALIDATION SCHEMAS
│   ├── exams.py               # Exam data structure validation
│   ├── sentiment.py           # Sentiment analysis schemas
│   └── grammar.py             # Grammar correction schemas
└── utils/                     # 🛠️ CORE UTILITIES
    ├── llm.py                 # LLM API integration (OpenAI, etc.)
    ├── seed_manager.py        # Seed constraint system
    ├── quality_validator.py   # Quality metrics and validation
    ├── io.py                  # File I/O operations
    └── anonymizer.py          # Data anonymization utilities
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

### 🎨 Style Guide Workflow
**Purpose**: Generate data following consistent style patterns from seed examples
1. **Seed Selection**: Extract/sample representative examples
2. **🎯 Style-Based Generation** ⚠️ **CURRENT FOCUS**: Use `generators/run.py` with style templates (`prompts/templates.py`)
   - **Iterative Prompt Tuning**: Manual output checks and template refinement required
   - **Template Location**: `./src/arabic_synth/prompts/templates.py`
   - **Process**: Generate → Review → Tune → Repeat until quality targets met
3. **Post-Processing**: Clean, validate, and evaluate quality

```bash
# Quick start - Style Guide Pipeline
arabic-synth sample-and-convert --input-file data/test-*.csv --output-file outputs/seeds.jsonl --n 10 --mode stratified

# ⚠️ ITERATIVE TUNING REQUIRED: Check outputs and refine prompts/templates.py
arabic-synth generate exams --seed-file outputs/seeds.jsonl --model openai:gpt-4o --num-samples 200

arabic-synth clean exams --in-path outputs/exams_raw.jsonl --out-path outputs/exams_clean.jsonl
arabic-synth evaluate-style exams --in-path outputs/exams_clean.jsonl
```

### 👤 Persona Enhanced Workflow  
**Purpose**: Generate diverse data using persona-based perspectives
1. **Seed Selection**: Prepare base examples for persona augmentation
2. **🎯 Persona Requests** ⚠️ **CURRENT FOCUS**: Build requests with persona templates (`persona/templates_persona.py`)
   - **Iterative Prompt Tuning**: Manual output checks and template refinement required
   - **Template Location**: `./src/arabic_synth/persona/templates_persona.py`
   - **Process**: Generate → Review → Tune → Repeat until persona consistency achieved
3. **Post-Processing**: Quality assessment and evaluation

```bash
# Quick start - Persona Pipeline
arabic-synth sample-and-convert --input-file data/test-*.csv --output-file outputs/seeds.jsonl --n 20
arabic-synth select-personas --input-file data/personas/personas_all.jsonl --output-file outputs/personas.jsonl --n 200

# ⚠️ ITERATIVE TUNING REQUIRED: Check outputs and refine persona/templates_persona.py
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
- Style Guide: `StyleGuide_PIPELINE_DETAILED.md`
- Persona Pipeline: `Persona_PIPELINE_DETAILED.md`  
- Combined Workflow: `STYLE_PERSONA_WORKFLOW_GUIDE.md`

---

## ⚠️ **CURRENT DEVELOPMENT FOCUS**

The following components require **active iterative prompt tuning** through manual output review:

### 🎯 **Priority Tasks:**
1. **Style Guide Templates** (`src/arabic_synth/prompts/templates.py`)
   - Fine-tune `EXAMS_TEACHER_PROMPT` for better Arabic naturalness
   - Optimize style consistency and content diversity balance
   - Target: 95%+ quality scores in style evaluation

2. **Persona Templates** (`src/arabic_synth/persona/templates_persona.py`) 
   - Refine `ARABIC_EXAM_REWRITE_V1` for authentic persona perspectives
   - Ensure persona consistency while maintaining content accuracy
   - Target: Diverse yet coherent persona-based variations

### 🔄 **Iterative Process:**
```
Generate Sample → Manual Review → Identify Issues → Tune Prompts → Repeat
```

**Evaluation Commands for Tuning:**
```bash
# Test style guide outputs
arabic-synth evaluate-style exams --in-path outputs/exams_clean.jsonl

# Test persona outputs  
arabic-synth evaluate-persona --input-file outputs/exams_pers_raw.jsonl
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