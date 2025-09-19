# Reorganized Persona Pipeline Structure

## ✅ Successfully Reorganized Structure

The persona scripts have been successfully reorganized following the StyleGuide_PIPELINE_DETAILED.md structure. All scripts are now properly organized under `/src/arabic_synth/` with appropriate CLI commands.

## 📁 New Project Structure

```
src/arabic_synth/
├── cli.py                     # Enhanced CLI with persona commands
├── data_prep/                 # 🔍 DATA PREPARATION PHASE
│   ├── __init__.py
│   ├── convert_csv.py         # Convert CSV exam data to JSONL (was: convert_exams_csv.py)
│   └── personas_select.py     # Select and filter personas (was: scripts/personas_select.py)
├── persona/                   # 🚀 PERSONA GENERATION PHASE
│   ├── __init__.py
│   ├── build_requests.py      # Build persona-augmented requests (was: build_persona_requests.py)
│   ├── send_requests.py       # Send requests to OpenAI API (was: send_persona_requests.py)
│   └── templates_persona.py   # Persona prompt templates
├── generators/                # Core generation logic
│   ├── persona_augment.py     # ✅ Updated imports to new persona location
│   └── run.py
├── postprocess/               # 🧹 POST-PROCESSING PHASE
│   └── clean.py
├── evaluate/                  # 📊 EVALUATION PHASE
│   ├── evaluate_style.py      # Style Guide Pipeline 
│   └── evaluate_persona.py    # Persona-augmented quality validation and reporting
├── utils/                     # Core utilities
│   ├── llm.py
│   ├── seed_manager.py
│   ├── quality_validator.py
│   ├── anonymizer.py
│   └── io.py
├── schemas/                   # Pydantic validation schemas
│   ├── exams.py
│   ├── grammar.py
│   └── sentiment.py
├── prompts/                   # LLM prompt templates
│   └── templates.py
└── augment/                   # Data augmentation
    └── augment.py
```

## 🔄 Pipeline Phases For Persona incorporation

### Phase 1: Data Preparation (`data_prep/`)
- **`exam_processor.py`** - Combined CSV processing: sampling (uniform/stratified) + conversion to JSONL
- **`personas_select.py`** - Select and filter personas from larger collections

### Phase 2: Persona Generation (`persona/`)
- **`build_requests.py`** - Create persona-augmented requests for LLM generation
- **`send_requests.py`** - Send requests to OpenAI API and collect responses
- **`templates_persona.py`** - Persona prompt templates and formatting

### Phase 3: Quality Validation (`quality/`)
- **`evaluate_persona.py`** - Persona-augmented comprehensive quality assessment and reporting

## 🎯 New CLI Commands

All persona scripts are now available as CLI commands:

### Data Preparation Commands
```bash
# Combined sampling and conversion (RECOMMENDED - one-step process)
arabic-synth sample-and-convert \
  --input-file data/test-00000-of-00001.arabic.csv \
  --output-file outputs/balanced_seeds.jsonl \
  --n 10 \
  --mode stratified \
  --stratify-col subject \
  --seed 123

# Alternative: Individual steps (legacy support)
# Step 1: Sample data
arabic-synth sample-stratified \
  --input-file data/test-00000-of-00001.arabic.csv \
  --output-file outputs/balanced_seed.csv \
  --n 10 --stratify-col subject --seed 123

# Step 2: Convert CSV to JSONL
arabic-synth convert-csv \
  --input-file outputs/balanced_seed_exams.csv \
  --output-file outputs/balanced_seeds.jsonl

# Select personas from collection
arabic-synth select-personas \
  --input-file data/personas/personas_all.jsonl \
  --output-file outputs/personas_selected.jsonl \
  --n 200 --seed 42
```

### Persona Generation Commands
```bash
# Build persona-augmented requests (using balanced seed data)
arabic-synth build-persona-requests \
  --exams-path data/seeds/balanced_seeds.jsonl \
  --personas-path outputs/personas_selected.jsonl \
  --output-path outputs/requests_persona_exams.jsonl \
  --per-item-personas 20 \
  --target-total 5000

# Send requests to OpenAI
arabic-synth send-persona-requests \
  --input-file outputs/requests_persona_exams.jsonl \
  --output-file outputs/exams_pers_raw.jsonl \
  --error-file outputs/exams__pers_err.jsonl \
  --model gpt-4o
```

### Quality Validation Commands
```bash
# Run quality checks
arabic-synth evaluate-persona \
  --input-file outputs/exams_pers_raw.jsonl \
  --report-json outputs/quality_report.json \
  --flag-csv outputs/flagged_samples.csv \
  --arabic-ratio 0.7
```

## 🔗 Updated Import Structure

### Fixed Import Paths
- **`persona_augment.py`**: Updated to import from `..persona.templates_persona`
- **`build_requests.py`**: Updated to import from `arabic_synth.generators.persona_augment`

### Import Examples
```python
# Persona templates
from arabic_synth.persona.templates_persona import ARABIC_EXAM_REWRITE_V1

# Data preparation
from arabic_synth.data_prep.convert_csv import main as convert_main
from arabic_synth.data_prep.personas_select import main as select_main

# Persona generation
from arabic_synth.persona.build_requests import main as build_main
from arabic_synth.persona.send_requests import main as send_main

# Quality validation
from arabic_synth.evaluate.evaluate_persona import main as evaluate_persona
```

## ✅ Verification Status

All imports and CLI commands have been tested and verified:

- ✅ **Persona templates import**: `arabic_synth.persona.templates_persona`
- ✅ **Data prep imports**: `arabic_synth.data_prep.convert_csv`
- ✅ **Persona evaluation imports**: `arabic_synth.evaluate.evaluate_persona`
- ✅ **CLI commands**: All 5 new persona commands available
- ✅ **Package installation**: Working in virtual environment

## 🚀 Complete Persona Workflow (Updated)

### Phase 1: Data Preparation
```bash
# 1. Sample and convert CSV data in one step (RECOMMENDED)
arabic-synth sample-and-convert \
  --input-file data/test-00000-of-00001.arabic.csv \
  --output-file data/exams.jsonl \
  --n 100 \
  --mode stratified \
  --stratify-col subject

# Alternative: Convert entire CSV (legacy approach)
# arabic-synth convert-csv

# 2. Select personas (if needed)
arabic-synth select-personas --n 200
```

### Phase 2: Persona Generation
```bash
# 3. Build persona-augmented requests
arabic-synth build-persona-requests --target-total 11000

# 4. Send requests to OpenAI (requires OPENAI_API_KEY)
export OPENAI_API_KEY="your-api-key-here"
arabic-synth send-persona-requests --model gpt-4o
```

### Phase 3: Quality Validation
```bash
# 5. Run quality checks
arabic-synth evaluate-persona --arabic-ratio 0.80
```

### Phase 4: Standard Pipeline (Optional)
```bash
# 6. Clean generated data
arabic-synth clean exams --in-path outputs/exams_raw.jsonl

# 7. Evaluate quality metrics
arabic-synth evaluate exams --in-path outputs/exams_clean.jsonl

# 8. Export final dataset
arabic-synth export exams --out-format csv
```

## 🔬 Enhanced Persona Pipeline with Scientific Sampling

The integration of `exam_processor.py` brings scientific rigor to the persona pipeline, enabling combined sampling and conversion operations:

### **1. Balanced Seed Data Creation**
```bash
# Create stratified seed data and convert in one step (RECOMMENDED)
arabic-synth sample-and-convert \
  --input-file data/test-00000-of-00001.arabic.csv \
  --output-file data/seeds/scientific_seeds.jsonl \
  --n 10 \
  --mode stratified \
  --stratify-col subject \
  --seed 123
```

### **2. Quality Test Set Generation**
```bash
# Create representative test sets for validation
arabic-synth sample-and-convert \
  --input-file data/test-00000-of-00001.arabic.csv \
  --output-file outputs/validation_set.jsonl \
  --n 100 \
  --mode stratified \
  --stratify-col grade \
  --seed 456
```

### **3. Domain-Specific Persona Generation**
```bash
# Sample specific subjects for targeted generation and convert in one step
arabic-synth sample-and-convert \
  --input-file data/test-00000-of-00001.arabic.csv \
  --output-file data/science_seeds.jsonl \
  --n 20 \
  --mode stratified \
  --stratify-col subject \
  --seed 789

# Generate persona requests for science domain
arabic-synth build-persona-requests --exams-path data/science_seeds.jsonl --target-total 2000
```

### **4. Reproducible Experimental Workflows**
```bash
# Create multiple test conditions with different seeds
for experiment in exp1 exp2 exp3; do
  arabic-synth sample-and-convert \
    --input-file data/test-00000-of-00001.arabic.csv \
    --output-file "outputs/${experiment}_test.jsonl" \
    --n 25 \
    --mode uniform \
    --seed $((RANDOM))
done
```

## 🎯 Benefits of Enhanced Pipeline

### 1. **Clear Phase Separation**
- Data preparation scripts in `data_prep/`
- Persona generation scripts in `persona/`
- Quality validation scripts in `quality/`

### 2. **Consistent CLI Interface**
- All scripts accessible via `arabic-synth` commands
- Consistent parameter naming and help text
- Integrated with existing pipeline commands

### 3. **Proper Import Structure**
- All imports follow Python package conventions
- No more root-level script dependencies
- Easier testing and maintenance

### 4. **StyleGuide Compliance**
- Matches the structure outlined in StyleGuide_PIPELINE_DETAILED.md
- Follows the same organizational principles
- Maintains consistency with existing codebase

## 📝 Migration Notes

### For Existing Users
- **Old script calls**: Replace direct Python calls with CLI commands
- **Import paths**: Update any custom imports to use new paths
- **File locations**: Scripts moved from root to organized folders

### Backward Compatibility
- All functionality preserved
- Same input/output file paths
- Same configuration parameters
- Enhanced with CLI convenience

---

*The persona pipeline is now fully integrated into the main arabic_synth package structure, providing a clean, organized, and maintainable codebase that follows established conventions.*
