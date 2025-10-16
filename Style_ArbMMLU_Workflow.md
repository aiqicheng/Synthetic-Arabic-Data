# Style MMLU Pipeline Documentation

*Updated: October 8, 2025*

## Overview
This document describes the complete workflow for generating high-quality synthetic Arabic MMLU (Massive Multitask Language Understanding) questions using seed-constrained generation. The pipeline transforms raw MMLU CSV data into diverse, subject-specific synthetic questions while maintaining academic rigor and preventing data leakage.

**Model Support**: The pipeline supports both OpenAI and OpenRouter APIs, including OpenRouter's Auto Router for automatic model selection powered by NotDiamond.

---

## 🎯 Pipeline Architecture

### Key Components
- **MMLUProcessor**: CSV parsing and format conversion
- **SeedManager**: Seed constraint system and style analysis
- **Generator**: LLM-based synthesis with subject generalization
- **Cleaner**: Post-processing and quality assurance
- **Evaluator**: Quality metrics and validation

### Data Flow
```
CSV Data → Seed Selection → Generation → Cleaning → Evaluation → Final Dataset
```

---

## 📋 Phase 1: Data Preparation & Seeding

### 1.1 CSV to JSONL Conversion

**Command:**
```bash
arabic-synth sample-and-convert mmlu \
  --input-file data/arabicmmlu_all.csv \
  --output-file outputs/mmlu_100/mmlu_seeds.jsonl \
  --n 10 \
  --mode uniform
```

**Process:**
1. **Input**: MMLU CSV file with columns:
   - `ID`, `Subject`, `Level`, `Question`, `Answer Key`
   - `Option 1-4`, `Country`, `Group`, `Context`, `is_few_shot`

2. **Processing** (`MMLUProcessor` class):
   - Loads CSV with `MMLURawItem` schema validation
   - Performs stratified sampling by subject
   - Converts via `to_mmlu_item()` → `MMLUItem` validation
   - Outputs JSONL with full metadata

3. **Output**: Seed examples with complete schema:
   ```json
   {
     "question": "طبقة وظيفتها فتح وغلق ومراقبة الجلسة بين المرسل والمستقبل",
     "options": ["الشبكة", "النقل", "الجلسة", "القطعة"],
     "answer": "C",
     "subject": "Computer Science",
     "level": "High",
     "country": "Palestine",
     "group": "STEM",
     "context": null,
     "is_few_shot": false
   }
   ```

### 1.2 Seed Constraint System

**Principles:**
- **Maximum 10 seeds**: Prevents overfitting to test data
- **Stratified sampling**: Ensures subject representation
- **Style extraction**: Analyzes patterns without copying content
- **Audit trail**: Tracks seed usage for reproducibility

**Seed Analysis Features:**
- Subject distribution analysis
- Question length patterns
- Technical terminology extraction
- Option format detection

---

## 🚀 Phase 2: Generation

### 2.1 Model Configuration

**Supported Model Providers:**

The pipeline supports both OpenAI and OpenRouter APIs for generation.

#### OpenAI Models
```bash
--model openai:gpt-4o                    # GPT-4 Optimized (recommended)
--model openai:gpt-4o-mini               # GPT-4 Mini (cost-effective)
--model openai:gpt-3.5-turbo             # GPT-3.5 Turbo (budget option)
```

#### OpenRouter Models
OpenRouter provides access to multiple model providers through a unified API:

**Auto Router (Recommended):**
```bash
--model "openrouter:openrouter/auto"     # Automatically selects best model for your prompt
```

**Specific Models:**
```bash
# OpenAI via OpenRouter
--model "openrouter:openai/gpt-4o"
--model "openrouter:openai/gpt-4o-mini"
--model "openrouter:openai/gpt-3.5-turbo"

# Anthropic Claude
--model "openrouter:anthropic/claude-3.5-sonnet"   # Excellent for complex tasks
--model "openrouter:anthropic/claude-3-haiku"      # Fast and cost-effective

# Google Gemini
--model "openrouter:google/gemini-pro-1.5"         # Strong multilingual support
--model "openrouter:google/gemini-flash-1.5"       # Fast and affordable

# Open Source Alternatives
--model "openrouter:meta-llama/llama-3.1-70b-instruct"
--model "openrouter:qwen/qwen-2.5-72b-instruct"
```

**Environment Setup:**
- **OpenAI**: Set `OPENAI_API_KEY` in your `.env` file
- **OpenRouter**: Set `OPENROUTER_API_KEY` in your `.env` file
  - Optional: `OPENROUTER_SITE_URL` and `OPENROUTER_SITE_NAME` for attribution

**References:**
- [OpenRouter Quickstart](https://openrouter.ai/docs/quickstart)
- [OpenRouter Model Routing](https://openrouter.ai/docs/features/model-routing)

### 2.2 MMLU Generation Command

**Command (OpenAI):**
```bash
arabic-synth generate mmlu \
  --num-samples 100 \
  --model openai:gpt-4o \
  --seed-file outputs/mmlu_100/mmlu_seeds.jsonl \
  --output-dir outputs/mmlu_100
```

**Command (OpenRouter with Auto Router):**
```bash
arabic-synth generate mmlu \
  --num-samples 100 \
  --model "openrouter:openrouter/auto" \
  --seed-file outputs/mmlu_100/mmlu_seeds.jsonl \
  --output-dir outputs/mmlu_100
```

### 2.3 Generation Process

**1. Seed Loading & Analysis:**
- `SeedManager` loads and validates seed examples
- Extracts subject information from seeds
- Generates style guidance without exposing specific content

**2. Prompt Construction:**
- **Subject Detection**: Automatically identifies subject from seeds
- **Dynamic Substitution**: Replaces `{subject}` placeholders
- **Seed Filtering**: Uses only subject-relevant examples
- **Style Integration**: Adds style guidance and seed examples

**3. LLM Generation:**
- Sends subject-specific prompts to LLM
- Generates questions following seed style patterns
- Maintains academic rigor and Arabic technical terminology

**4. Validation & Output:**
- `MMLUItem` schema validates generated content
- Returns only essential fields: `{"question", "options", "answer"}`
- Ensures quality and format consistency

### 2.4 Subject Generalization

**Supported Subjects:**
- Computer Science
- Philosophy  
- Any subject present in MMLU dataset

**Features:**
- **Dynamic Subject Detection**: Automatically extracts subject from seed data
- **Subject-Specific Prompts**: Tailored instructions for each domain
- **Technical Terminology**: Domain-appropriate Arabic vocabulary
- **Academic Style**: Maintains MMLU assessment standards

### 2.5 Prompt Template Structure

```
[Role: Experienced Arabic instructor]
You are given an original MMLU question from {subject}.

**Subject Focus**: Generate questions specifically in: {subject}

**Seed Examples for Reference:**
Example: {"question": "...", "options": [...], "answer": "..."}

**Important**: Generate a NEW question in the same style and subject domain ({subject}) as the examples above, but with completely different content.

Output Format:
{
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "answer": "{target_answer_letter}"
}
```

---

## 🧹 Phase 3: Post-Processing & Cleaning

### 3.1 Data Cleaning Command

**Command:**
```bash
arabic-synth clean mmlu \
  --in-path outputs/mmlu_100/generate_style_None_100.jsonl \
  --out-path outputs/mmlu_100/mmlu_clean.jsonl
```

### 3.2 Cleaning Process

**1. Deduplication:**
- **Exact duplicates**: Removes identical questions
- **Fuzzy matching**: Detects similar content using Levenshtein distance
- **Configurable threshold**: Adjustable similarity cutoff

**2. Validation:**
- Schema validation with `MMLUItem`
- Ensures all required fields present
- Validates answer format (A, B, C, D)

**3. Text Normalization:**
- Arabic Unicode normalization
- Whitespace standardization
- Character encoding consistency

**4. Quality Filtering:**
- Removes malformed questions
- Filters incomplete options
- Eliminates nonsensical content

---

## 📊 Phase 4: Evaluation & Quality Assessment

### 4.1 Style Evaluation Command

**Command:**
```bash
arabic-synth evaluate-style mmlu \
  --in-path outputs/mmlu_100/mmlu_clean.jsonl
```

### 4.2 Evaluation Metrics

**1. Fidelity Metrics:**
- **Style Consistency**: How well generated data matches seed characteristics
- **Subject Alignment**: Appropriateness of content for specified subject
- **Language Quality**: Arabic language fluency and technical accuracy

**2. Diversity Metrics:**
- **Content Variation**: Uniqueness of generated questions
- **Topic Coverage**: Breadth of subject areas covered
- **Answer Distribution**: Balanced A/B/C/D distribution

**3. Quality Metrics:**
- **Technical Accuracy**: Factual correctness of questions and answers
- **Academic Rigor**: Appropriate difficulty level
- **Option Quality**: Plausibility of distractors

---

## 🔄 Complete Workflow Example

### End-to-End Pipeline

**Option 1: Using OpenAI Models**
```bash
# Step 1: Prepare seeds from MMLU dataset
arabic-synth sample-and-convert mmlu \
  --input-file data/arabicmmlu_all.csv \
  --output-file outputs/mmlu_100/mmlu_seeds.jsonl \
  --n 10 --mode uniform

# Step 2: Generate synthetic data
arabic-synth generate mmlu \
  --num-samples 100 \
  --model openai:gpt-4o \
  --seed-file outputs/mmlu_100/mmlu_seeds.jsonl \
  --output-dir outputs/mmlu_100

# Step 3: Clean generated data
arabic-synth clean mmlu \
  --in-path outputs/mmlu_100/generate_style_None_100.jsonl \
  --out-path outputs/mmlu_100/mmlu_final_clean.jsonl

# Step 4: Evaluate quality
arabic-synth evaluate-style mmlu \
  --in-path outputs/mmlu_100/mmlu_final_clean.jsonl
```

**Option 2: Using OpenRouter Auto Router (Recommended)**
```bash
# Step 1: Prepare seeds from MMLU dataset
arabic-synth sample-and-convert mmlu \
  --input-file data/arabicmmlu_all.csv \
  --output-file outputs/mmlu_100/mmlu_seeds.jsonl \
  --n 10 --mode uniform

# Step 2: Generate synthetic data with Auto Router
arabic-synth generate mmlu \
  --num-samples 100 \
  --model "openrouter:openrouter/auto" \
  --seed-file outputs/mmlu_100/mmlu_seeds.jsonl \
  --output-dir outputs/mmlu_100

# Step 3: Clean generated data
arabic-synth clean mmlu \
  --in-path outputs/mmlu_100/generate_style_None_100.jsonl \
  --out-path outputs/mmlu_100/mmlu_final_clean.jsonl

# Step 4: Evaluate quality
arabic-synth evaluate-style mmlu \
  --in-path outputs/mmlu_100/mmlu_final_clean.jsonl
```

**Option 3: Using Specific OpenRouter Model**
```bash
# Example with Claude 3.5 Sonnet for high-quality generation
arabic-synth generate mmlu \
  --num-samples 100 \
  --model "openrouter:anthropic/claude-3.5-sonnet" \
  --seed-file outputs/mmlu_100/mmlu_seeds.jsonl \
  --output-dir outputs/mmlu_100
```

## 📁 Source and Input Files Structure

### Input Data Structure

```
data/
├── arabicmmlu_all.csv              # Main MMLU dataset (306 rows, 2 subjects)
├── arabic_mmlu_compsci.csv                # Computer Science subset
├── DownloadMMLU.ipynb                     # Data download and processing notebook
└── distribution.txt                       # Dataset distribution information
```

### Source Code Structure

```
src/
├── arabic_synth/
│   ├── cli.py                            # Command-line interface with MMLU support
│   ├── data_prep/
│   │   └── mmlu_processor.py             # MMLU CSV processing and conversion
│   ├── generators/
│   │   └── run.py                        # Core generation logic with MMLU support
│   ├── prompts/
│   │   └── templates.py                  # MMLU prompt templates with subject generalization
│   ├── postprocess/
│   │   └── clean.py                      # Data cleaning with MMLU support
│   ├── evaluate/
│   │   └── evaluate_style.py             # Style evaluation with MMLU support
│   └── utils/
│       └── seed_manager.py               # Seed constraint system for MMLU
└── schemas/
    └── mmlu.py                           # MMLU data validation schemas
```

### Key Configuration Files

```
src/arabic_synth/configs/
├── style_subject_config.json             # Default configuration for style-subject workflow
└── small_batch.json                      # Small batch configuration template
```

### Schema Definitions

| Schema | Purpose | Fields | Usage |
|--------|---------|--------|-------|
| `MMLURawItem` | CSV parsing | All CSV columns with aliases | Data ingestion from CSV |
| `MMLUItem` | Validation & processing | Full schema (optional fields) | Both processing & generation validation |
| Final Output | Generation result | `question`, `options`, `answer` | Clean dataset output |

### Data Flow Architecture

```
CSV Data (MMLURawItem) 
    ↓ [MMLUProcessor]
Seed Selection (MMLUItem) 
    ↓ [SeedManager + Generator]
Raw Generation (MMLUItem validation) 
    ↓ [Cleaner]
Cleaned Data (3 fields only) 
    ↓ [Evaluator]
Quality Metrics
```

### Output Structure

```
outputs/
├── mmlu_seeds.jsonl                           # Seed examples (full schema)
├── mmlu_batch/
│   ├── generate_style_Computer Science_500.jsonl  # Raw generation output
│   └── mmlu_Computer Science_seeds_audit.json     # Seed audit information
└── mmlu_final_clean.jsonl                    # Final cleaned dataset (3 fields only)
```

---

## 🔧 Technical Implementation Details

### Schema Design

| Schema | Purpose | Fields | Usage |
|--------|---------|--------|-------|
| `MMLURawItem` | CSV parsing | All CSV columns | Data ingestion |
| `MMLUItem` | Validation & processing | Full schema (optional fields) | Both processing & generation |
| Final Output | Generation output | `question`, `options`, `answer` | Clean dataset |

### Key Features

**1. Subject Generalization:**
- Automatic subject detection from seed data
- Dynamic prompt generation for any MMLU subject
- Subject-specific technical terminology

**2. Seed Constraint System:**
- Maximum 10 seed examples
- Style guidance without content copying
- Audit trail for reproducibility

**3. Quality Assurance:**
- Multi-stage validation (schema, content, format)
- Arabic language normalization
- Academic rigor maintenance

**4. Simplified Output:**
- Only essential 3 fields in final dataset
- Clean, focused format for downstream use
- Full validation with minimal output

---

## 📈 Expected Results

### Sample Output

**Generated Computer Science Question:**
```json
{
  "question": "أي نوع من هياكل البيانات يُستخدم لتنفيذ خوارزمية البحث الثنائي بكفاءة؟",
  "options": ["A. شجرة البحث الثنائية", "B. قائمة مرتبطة", "C. مخطط غير موجه", "D. كومة أولويات"],
  "answer": "A"
}
```

### Quality Characteristics

- **Subject Accuracy**: Questions are technically correct for the specified domain
- **Arabic Language**: Proper technical terminology and academic style
- **Academic Rigor**: Appropriate difficulty level for MMLU assessments
- **Content Diversity**: Varied topics within the subject domain
- **Answer Quality**: Plausible distractors with clear correct answers

---

## 📋 To-Do

### Future Enhancements

**Batch Processing:**
- Implement automated batch processing workflow for MMLU
- Test and validate `style-subject-workflow` integration with MMLU task
- Create MMLU-specific configuration templates

**Custom Configuration:**
- Develop configuration files for specific subjects or sampling strategies
- Implement automated multi-subject generation workflows
- Add support for custom sampling parameters and quality thresholds

---

## 📝 Best Practices

### 1. Seed Selection
- Use stratified sampling to ensure subject representation
- Limit to ≤10 seeds to prevent overfitting
- Include diverse examples within each subject

### 2. Model Selection
- **For production use**: OpenRouter Auto Router (`openrouter:openrouter/auto`) for optimal quality/cost balance
- **For high-quality generation**: Claude 3.5 Sonnet or GPT-4o for complex academic content
- **For cost-effective generation**: GPT-3.5 Turbo or Gemini Flash for large-scale generation
- **For experimentation**: Try different models to find the best fit for your use case

### 3. Generation Parameters
- Use appropriate temperature (0.7-0.8) for balanced creativity/consistency
- Specify subjects explicitly for better control
- Monitor generation quality during large batches
- Set `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env` file before running

### 4. Quality Control
- Always run cleaning step to remove duplicates
- Evaluate a sample of generated data before large-scale use
- Validate technical accuracy for domain-specific questions

### 5. Data Management
- Maintain audit trails of seed usage
- Version control generated datasets
- Document generation parameters for reproducibility

---

## 🔍 Troubleshooting

### Common Issues

**1. Validation Errors:**
- Ensure LLM generates only required 3 fields
- Check for proper JSON formatting
- Verify answer format (A, B, C, D)

**2. Subject Mismatch:**
- Verify seed file contains correct subject examples
- Check subject parameter in generation command
- Ensure seed filtering logic works correctly

**3. Quality Issues:**
- Review seed examples for style consistency
- Adjust generation temperature
- Validate Arabic language quality

### Debug Commands

```bash
# Check seed file content
head -5 outputs/mmlu_seeds.jsonl | jq '.'

# Validate generated data format
head -5 outputs/mmlu_generation/generate_style_*.jsonl | jq '.'

# Check cleaning results
wc -l outputs/mmlu_clean.jsonl
```

---

## 📚 References

- **MMLU Dataset**: Massive Multitask Language Understanding benchmark
- **Seed Constraint System**: Prevents data leakage in synthetic generation
- **Arabic NLP**: Technical terminology and academic style guidelines
- **Quality Metrics**: Fidelity, diversity, and utility assessment methods

---

