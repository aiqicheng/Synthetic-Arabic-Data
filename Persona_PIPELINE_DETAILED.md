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
│   └── templates_persona.py   # Persona prompt templates (was: src/prompts/templates_persona.py)
├── quality/                   # 📊 QUALITY VALIDATION PHASE
│   ├── __init__.py
│   └── quality_check.py       # Quality validation and reporting (was: quality_check.py)
├── generators/                # Core generation logic
│   ├── persona_augment.py     # ✅ Updated imports to new persona location
│   └── run.py
├── postprocess/               # 🧹 POST-PROCESSING PHASE
│   └── clean.py
├── evaluate/                  # 📊 EVALUATION PHASE
│   └── evaluate.py
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
- **`convert_csv.py`** - Convert CSV exam data to JSONL format
- **`personas_select.py`** - Select and filter personas from larger collections

### Phase 2: Persona Generation (`persona/`)
- **`build_requests.py`** - Create persona-augmented requests for LLM generation
- **`send_requests.py`** - Send requests to OpenAI API and collect responses
- **`templates_persona.py`** - Persona prompt templates and formatting

### Phase 3: Quality Validation (`quality/`)
- **`quality_check.py`** - Comprehensive quality assessment and reporting

## 🎯 New CLI Commands

All persona scripts are now available as CLI commands:

### Data Preparation Commands
```bash
# Convert CSV to JSONL
arabic-synth convert-csv \
  --input-file data/test-00000-of-00001.arabic.csv \
  --output-file data/exams.jsonl

# Select personas from collection
arabic-synth select-personas \
  --input-file data/personas/personas_all.jsonl \
  --output-file outputs/personas/selected_200.jsonl \
  --n 200 --seed 42
```

### Persona Generation Commands
```bash
# Build persona-augmented requests
arabic-synth build-persona-requests \
  --exams-path data/exams.jsonl \
  --personas-path data/personas/selected_200.jsonl \
  --output-path outputs/requests_persona_exams.jsonl \
  --per-item-personas 20 \
  --target-total 11000

# Send requests to OpenAI
arabic-synth send-persona-requests \
  --input-file outputs/requests_persona_exams.jsonl \
  --output-file outputs/exams_raw.jsonl \
  --error-file outputs/exams_errors.jsonl \
  --model gpt-4o
```

### Quality Validation Commands
```bash
# Run quality checks
arabic-synth quality-check \
  --input-file outputs/exams_raw.jsonl \
  --report-json outputs/quality_report.json \
  --flag-csv outputs/flagged_samples.csv \
  --arabic-ratio 0.90
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
from arabic_synth.quality.quality_check import main as quality_main
```

## ✅ Verification Status

All imports and CLI commands have been tested and verified:

- ✅ **Persona templates import**: `arabic_synth.persona.templates_persona`
- ✅ **Data prep imports**: `arabic_synth.data_prep.convert_csv`
- ✅ **Quality check imports**: `arabic_synth.quality.quality_check`
- ✅ **CLI commands**: All 5 new persona commands available
- ✅ **Package installation**: Working in virtual environment

## 🚀 Complete Persona Workflow (Updated)

### Phase 1: Data Preparation
```bash
# 1. Convert CSV data
arabic-synth convert-csv

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
arabic-synth quality-check --arabic-ratio 0.90
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

## 🎯 Benefits of Reorganization

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
