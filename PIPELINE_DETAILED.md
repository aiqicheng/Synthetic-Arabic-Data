# Arabic Synthetic Data Generation Pipeline - Detailed Flow

## 🎯 Overview

This document provides a comprehensive, step-by-step breakdown of the Arabic synthetic data generation pipeline, from initial setup to final quality validation and export.

## 🔄 Complete Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              ARABIC SYNTHETIC DATA PIPELINE                        │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   1. SETUP PHASE                                   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                             2. DATA PREPARATION PHASE                              │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                3. GENERATION PHASE                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              4. POST-PROCESSING PHASE                              │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                5. EVALUATION PHASE                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                  6. EXPORT PHASE                                   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 📋 1. SETUP PHASE

### 1.1 Environment Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package
pip install -e .

# Set environment variables
export OPENAI_API_KEY="your-api-key-here"
```

### 1.2 Project Structure Verification
```
Synthetic Data/
├── src/arabic_synth/          # Core package
├── data/seeds/                # Seed data directory
├── outputs/                   # Output directory
├── test-00000-of-00001.arabic.csv  # Original test set
├── pyproject.toml            # Package configuration
└── README.md                 # Documentation
```

## 🔍 2. DATA PREPARATION PHASE

### 2.1 Seed Data Extraction
**Purpose**: Extract ≤10 diverse samples from test set for style guidance only

**Process**:
1. **Load Original Test Set**: `test-00000-of-00001.arabic.csv`
2. **Parse Complex Format**: Handle nested dictionary strings, numpy arrays
3. **Subject Diversity Check**: Ensure seeds cover multiple subjects
4. **Quality Filtering**: Remove malformed or incomplete samples
5. **Export Seeds**: Save as `data/seeds/exams_seeds_from_testset.jsonl`

**Seed Constraint Rules**:
- Maximum 10 seeds allowed
- Must cover ≥3 different subjects
- No content replication, only style guidance
- Diversity in question length and complexity

**Output**: `data/seeds/exams_seeds_from_testset.jsonl` (≤10 samples)

### 2.2 Seed Manager Initialization
**Components**:
- `SeedConstraint` configuration
- `SeedManager` instance
- Style guidance extraction
- Similarity validation setup

**Configuration**:
```python
SeedConstraint(
    max_seeds=10,
    min_seed_diversity=3,
    max_generation_similarity=0.3
)
```

## 🚀 3. GENERATION PHASE

### 3.1 Generation Configuration
**Parameters**:
- Task type: `exams` | `sentiment` | `grammar`
- Number of samples: Target count (e.g., 200 for pilot)
- Model: `openai:gpt-4o` | `mock` (for testing)
- Batch size: Processing chunks (default: 50)
- Temperature: 0.7-0.9 (diversity control)
- Top-p: 0.95 (nucleus sampling)

### 3.2 Answer Distribution Planning
**Process**:
1. **Calculate Quotas**: Based on target distribution or uniform (25% each)
2. **Schedule Generation**: Prioritize letters with higher quotas
3. **Dynamic Assignment**: Assign target answer letter for each sample

**Example Quota Calculation**:
```python
# For 200 samples, uniform distribution
quotas = {
    'A': 50,  # 25%
    'B': 50,  # 25%
    'C': 50,  # 25%
    'D': 50   # 25%
}
```

### 3.3 Prompt Building
**Process**:
1. **Template Selection**: Choose task-specific prompt template
2. **Persona Integration**: Apply role-playing context
3. **Target Letter Injection**: Insert `{target_answer_letter}` placeholder
4. **Style Guidance**: Prepend seed-derived style hints

**EXAMS Template Example**:
```
[Role: Arabic high school teacher]
Write a multiple-choice exam question in Arabic.
Constraints:
- Question length: 12-30 words
- Use varied vocabulary and avoid repetitive phrasing
- Options must be concise and plausible
- The correct answer MUST be letter {target_answer_letter}
Return ONLY a valid JSON object:
{
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "answer": "{target_answer_letter}"
}
```

### 3.4 LLM Generation Loop
**Process**:
1. **Iterative Generation**: Generate one sample at a time
2. **Target Letter Assignment**: Pick next target based on quotas
3. **Prompt Building**: Create prompt with specific target letter
4. **LLM Call**: Send to OpenAI API with temperature/top-p
5. **Response Parsing**: Extract JSON from markdown response
6. **Answer Remapping**: Ensure correct answer maps to target letter
7. **Quota Tracking**: Update production counts

**Answer Remapping Logic**:
```python
def _remap_answer_to_target(exam_item, target_letter):
    if exam_item["answer"] == target_letter:
        return exam_item
    
    # Find correct answer text
    correct_text = exam_item["options"][ord(exam_item["answer"]) - ord('A')]
    
    # Re-shuffle options to put correct answer at target position
    options = exam_item["options"].copy()
    target_idx = ord(target_letter) - ord('A')
    options[target_idx] = correct_text
    
    # Update answer
    return {
        "question": exam_item["question"],
        "options": options,
        "answer": target_letter
    }
```

### 3.5 Progress Monitoring
**Logging**:
- Generation parameters (temperature, top-p, quotas)
- Progress updates every 10 samples
- Error handling and retry logic
- Seed usage audit trail

**Output**: `outputs/exams_raw.jsonl` (raw generated data)

## 🧹 4. POST-PROCESSING PHASE

### 4.1 Schema Validation
**Process**:
1. **Pydantic Validation**: Ensure JSON structure matches schema
2. **Field Validation**: Check required fields and data types
3. **Content Validation**: Verify answer letter validity
4. **Error Logging**: Record validation failures

**EXAMS Schema**:
```python
class ExamItem(BaseModel):
    question: str
    options: List[str] = Field(..., min_items=4, max_items=4)
    answer: str = Field(..., regex="^[ABCD]$")
    
    @validator('options')
    def validate_options(cls, v):
        if len(v) != 4:
            raise ValueError('Must have exactly 4 options')
        return v
```

### 4.2 Length Filtering
**Process**:
1. **Question Length Check**: Filter by word count (12-30 words for EXAMS)
2. **Option Length Check**: Ensure options are concise
3. **Threshold Configuration**: Configurable length limits per task

### 4.3 TTR (Type-Token Ratio) Filtering
**Process**:
1. **Vocabulary Diversity Calculation**: Count unique words vs. total words
2. **Threshold Application**: Remove samples below threshold (default: 0.18)
3. **Quality Improvement**: Ensure linguistic variety

### 4.4 Deduplication
**Process**:
1. **Similarity Calculation**: Use Levenshtein distance for text similarity
2. **Threshold Application**: Remove samples above similarity threshold (default: 0.8)
3. **Batch Processing**: Efficient comparison of large datasets

**Output**: `outputs/exams_clean.jsonl` (cleaned, validated data)

## 📊 5. EVALUATION PHASE

### 5.1 Fidelity Check
**Purpose**: Compare synthetic data characteristics with real data

**Metrics**:
1. **Length Distribution**: Mean, standard deviation comparison
2. **Answer Balance**: Answer letter distribution, L1 distance
3. **Vocabulary Analysis**: TTR, vocabulary size, Jaccard similarity

### 5.2 Utility Check (TSTR)
**Purpose**: Train on synthetic, test on real data

**Process**:
1. **Feature Extraction**: CountVectorizer for text representation
2. **Model Training**: LogisticRegression on synthetic data
3. **Real Data Testing**: Evaluate on real test set
4. **Performance Comparison**: Accuracy and other metrics

### 5.3 Privacy Check
**Purpose**: Assess re-identification risk

**Metrics**:
1. **Token Overlap Analysis**: Similarity to nearest real item
2. **Risk Assessment**: Maximum and mean overlap scores
3. **Threshold Analysis**: Share of samples above risk threshold

## 📤 6. EXPORT PHASE

### 6.1 Format Conversion
**Supported Formats**: JSONL (default), CSV, JSON, Custom formats

### 6.2 Metadata Addition
**Metadata Fields**: Batch ID, timestamp, model parameters, quality metrics

### 6.3 Output Organization
**File Structure**:
```
outputs/
├── exams_raw.jsonl           # Raw generated data
├── exams_clean.jsonl         # Cleaned, validated data
├── exams_real_from_testset.jsonl  # Converted real data
└── quality_report.json       # Evaluation results
```

## 🔄 PIPELINE EXECUTION EXAMPLES

### Complete Pipeline Run
```bash
# 1. Setup
source .venv/bin/activate
export OPENAI_API_KEY="your-key"

# 2. Generate
arabic-synth generate exams \
  --num-samples 200 \
  --model openai:gpt-4o \
  --seed-file data/seeds/exams_seeds_from_testset.jsonl \
  --temperature 0.9 \
  --top-p 0.95

# 3. Clean
arabic-synth clean exams \
  --in-path outputs/exams_raw.jsonl \
  --out-path outputs/exams_clean.jsonl

# 4. Evaluate
arabic-synth evaluate exams \
  --in-path outputs/exams_clean.jsonl

# 5. Export
arabic-synth export exams \
  --in-path outputs/exams_clean.jsonl \
  --out-format csv \
  --meta-batch-id pilot-001
```

## 📈 QUALITY METRICS INTERPRETATION

### Fidelity Targets
- **Length Distribution**: Mean difference < 2 words
- **Answer Balance**: L1 distance < 0.1
- **Vocabulary Diversity**: TTR > 0.3
- **Content Overlap**: Jaccard < 0.1

### Utility Targets
- **TSTR Accuracy**: > 0.6 (baseline performance)
- **Performance Gap**: < 0.2 from real data

### Privacy Targets
- **Max Overlap**: < 0.7
- **Mean Overlap**: < 0.4
- **High Risk Samples**: < 5%

## 🚨 TROUBLESHOOTING

### Common Issues
1. **API Rate Limits**: Implement exponential backoff
2. **JSON Parsing Errors**: Handle markdown formatting
3. **Quality Failures**: Adjust thresholds or regenerate
4. **Distribution Imbalance**: Check quota scheduling logic

### Debug Commands
```bash
# Check seed loading
python -c "from src.arabic_synth.utils.seed_manager import SeedManager; sm = SeedManager(); print(sm.load_seeds_from_testset('data/seeds/exams_seeds_from_testset.jsonl'))"

# Validate schema
python -c "from src.arabic_synth.schemas.exams import ExamItem; import json; data = json.loads(open('outputs/exams_raw.jsonl').readline()); ExamItem(**data)"

# Check quality metrics
arabic-synth evaluate exams --in-path outputs/exams_clean.jsonl
```

## 📚 ADDITIONAL RESOURCES

- **SEED_CONSTRAINTS.md**: Detailed seed constraint documentation
- **README.md**: Project overview and quick start
- **pyproject.toml**: Package configuration and dependencies
- **src/arabic_synth/**: Source code and implementation details

---

This pipeline ensures high-quality, diverse Arabic synthetic data generation while maintaining strict quality standards and preventing data leakage through the seed constraint system. 