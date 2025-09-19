# Arabic Synthetic Dataset Generation Pipeline - Real Implementation

## 🎯 Project Overview

This project implements a comprehensive pipeline for generating high-quality Arabic synthetic datasets using persona-based LLM generation with advanced seed constraints and quality validation.

**Target Datasets:**
- **EXAMS (10,000 items)** → Multi-subject MCQ questions with controlled answer distribution
- **Alghafa Sentiment (10,000 items)** → Sentiment classification (positive:negative:neutral = 4:4:2)
- **Madinah QA Grammar (10,000 items)** → Grammar error correction triplets

---

## 🔹 Overall Strategy

Use **LLMs + persona prompts + seed constraints** to create authentic, diverse Arabic datasets while preventing data leakage through sophisticated constraint systems.

---

## 1. Define Personas & Scenarios

Each dataset uses specific role-playing for authenticity:

- **EXAMS** → *"Arabic high school teacher writing exam questions"*
- **Sentiment** → *"Arabic social media user expressing opinions"*
- **Grammar QA** → *"Arabic language learner making mistakes, teacher correcting"*

Persona prompts lock the **role** and **tone** for consistency across all generations.

---

## 2. Seed Constraint System (Core Innovation)

**Critical Feature**: Uses ≤10 test samples as *style guidance only* to prevent data leakage:

- **Max Seeds**: ≤10 samples per task
- **Style Only**: Seeds provide style guidance, not content replication
- **Diversity Check**: Ensures seed variety across subjects and difficulty levels
- **Similarity Validation**: Prevents generated content from being too similar to seeds
- **Audit Trail**: Full logging of seed usage and constraint application

**Implementation**: `SeedManager` class with configurable constraints:
```python
SeedConstraint(
    max_seeds=10,
    min_seed_diversity=3,
    max_generation_similarity=0.3
)
```

---

## 3. Prompt Templates (Actual Implementation)

### EXAMS (Knowledge Q&A)

```json
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

**Role**: Teacher creates multiple-choice questions covering biology, history, geography, science, and literature.

### Alghafa Sentiment (Sentiment Analysis)

```json
[Role: Arabic social media user]
Generate a short text (20-40 words) expressing a clear sentiment.
The text should be natural and authentic Arabic.
Return ONLY a valid JSON object:
{
  "text": "...",
  "sentiment": "positive|negative|neutral"
}
```

**Role**: Social media user writes authentic posts with explicit sentiment labels.

### Madinah Grammar QA (Error Correction)

```json
[Role: Arabic language teacher]
Create a grammar correction example in Arabic.
Return ONLY a valid JSON object:
{
  "input": "...(incorrect sentence)",
  "correction": "...(corrected sentence)",
  "explanation": "...(explanation of the correction)"
}
```

**Role**: Teacher provides incorrect sentences, corrections, and explanations.

---

## 4. Advanced Generation Features

### Answer Distribution Control
- **Quota Scheduling**: Calculates target distribution for A, B, C, D answers
- **Dynamic Assignment**: Assigns target answer letter for each generation
- **Answer Remapping**: Ensures correct answer maps to target position if LLM doesn't comply

### Sampling Parameters
- **Temperature**: 0.7-0.9 (diversity control)
- **Top-p**: 0.95 (nucleus sampling)
- **Batch Processing**: Configurable batch sizes (default: 50)

### Progress Monitoring
- Real-time quota tracking
- Progress updates every 10 samples
- Comprehensive logging of generation parameters

---

## 5. Data Augmentation & Transformation

### Rule-based Transformations
- **Entity Replacement**: Names, locations, numbers, years
- **Option Shuffling**: Reorder multiple-choice options while maintaining correctness
- **Difficulty Scaling**: Simple → intermediate → advanced complexity

### Quality Enhancement
- **Length Filtering**: Enforce word count constraints per task
- **TTR Filtering**: Remove low-diversity samples (Type-Token Ratio < 0.18)
- **Schema Validation**: Strict Pydantic validation for all data types

---

## 6. Post-processing Pipeline

### 1. Schema Validation
- **Pydantic Models**: Enforce strict JSON structure for each task
- **Field Validation**: Check required fields, data types, and content validity
- **Error Logging**: Record and report validation failures

### 2. Quality Filtering
- **Length Validation**: Task-specific word count requirements
- **TTR Calculation**: Vocabulary diversity assessment
- **Content Quality**: Remove malformed or incomplete samples

### 3. Deduplication
- **Similarity Detection**: Use Levenshtein distance for text similarity
- **Threshold Control**: Configurable similarity threshold (default: 0.8)
- **Batch Processing**: Efficient comparison of large datasets

---

## 7. Quality Validation System

### Fidelity Metrics
- **Length Distribution**: Mean, standard deviation comparison with real data
- **Answer Balance**: L1 distance from target distribution
- **Vocabulary Analysis**: TTR comparison, vocabulary size, Jaccard similarity

### Utility Metrics (TSTR)
- **Train on Synthetic, Test on Real**: Use CountVectorizer + LogisticRegression
- **Performance Comparison**: Accuracy on real test set
- **Baseline Assessment**: Compare with random baseline

### Privacy Metrics
- **Re-identification Risk**: Token overlap analysis with real data
- **Similarity Assessment**: Maximum and mean overlap scores
- **Risk Thresholding**: Share of samples above risk threshold

---

## 8. Implementation Architecture

### Core Components
```
src/arabic_synth/
├── cli.py              # Command-line interface (Typer)
├── generators/run.py   # Core generation logic with quota scheduling
├── postprocess/clean.py # Data cleaning, validation, deduplication
├── evaluate/
│   ├── evaluate_style.py      # Style Guide Pipeline 
│   └── evaluate_persona.py    # Persona-augmented quality assessment and reporting
├── schemas/            # Pydantic validation schemas
├── prompts/templates.py # LLM prompt templates
└── utils/              # Core utilities
    ├── llm.py         # OpenAI API integration
    ├── seed_manager.py # Seed constraint system
    ├── quality_validator.py # Comprehensive quality metrics
    └── anonymizer.py  # Data anonymization
```

### CLI Commands
```bash
# Generate with seed constraints and distribution control
arabic-synth generate exams \
  --num-samples 200 \
  --model openai:gpt-4o \
  --seed-file data/seeds/exams_seeds_from_testset.jsonl \
  --temperature 0.9 \
  --top-p 0.95

# Clean and validate
arabic-synth clean exams \
  --in-path outputs/exams_raw.jsonl \
  --out-path outputs/exams_clean.jsonl

# Evaluate quality
arabic-synth evaluate exams \
  --in-path outputs/exams_clean.jsonl
```

---

## 9. Stepwise Implementation

### 1. Pilot Stage (100-200 samples)
- Generate with seed constraints
- Validate quality metrics
- Refine prompts and parameters
- Test distribution alignment

### 2. Scaling Stage (1K → 5K → 10K)
- Monitor quality metrics
- Adjust generation parameters
- Validate against real data distributions
- Ensure diversity maintenance

### 3. Integration & Validation
- Run comprehensive quality checks
- Compare with real data characteristics
- Validate TSTR performance
- Document final metrics

---

## 10. Dataset Targets & Quality Standards

### EXAMS Dataset
- **Target**: 10,000 multi-subject MCQ questions
- **Quality**: Balanced answer distribution (A:B:C:D ≈ 25% each)
- **Diversity**: TTR > 0.18, length 12-30 words
- **Subjects**: Biology, History, Geography, Science, Literature

### Sentiment Dataset
- **Target**: 10,000 sentiment-labeled texts
- **Distribution**: Positive:Negative:Neutral = 4:4:2
- **Quality**: Natural Arabic expressions, clear sentiment
- **Length**: 20-40 words per text

### Grammar Dataset
- **Target**: 10,000 error-correction triplets
- **Quality**: Authentic grammar mistakes, clear explanations
- **Coverage**: Various error types and difficulty levels

---

## 11. Quality Thresholds

### Fidelity Targets
- **Length Distribution**: Mean difference < 2 words from real data
- **Answer Balance**: L1 distance < 0.1 from target distribution
- **Vocabulary Diversity**: TTR > 0.3 for linguistic variety
- **Content Overlap**: Jaccard similarity < 0.1 with real data

### Utility Targets
- **TSTR Accuracy**: > 0.6 (baseline performance)
- **Performance Gap**: < 0.2 from real data performance

### Privacy Targets
- **Max Overlap**: < 0.7 with real data
- **Mean Overlap**: < 0.4 average similarity
- **High Risk Samples**: < 5% above threshold

---

## 12. Technical Features

### Advanced Controls
- **Temperature & Top-p**: Exposed as CLI options for fine-tuning
- **Answer Distribution**: Target-specific answer letter ratios
- **TTR Filtering**: Configurable diversity thresholds
- **Batch Processing**: Scalable generation with monitoring

### Error Handling
- **API Retries**: Exponential backoff for rate limits
- **JSON Parsing**: Robust handling of markdown-formatted responses
- **Validation Errors**: Comprehensive error reporting and logging
- **Progress Tracking**: Real-time generation monitoring

### Data Management
- **Version Control**: Batch IDs and metadata tracking
- **Audit Trails**: Complete seed usage logging
- **Quality Reports**: Comprehensive evaluation summaries
- **Export Formats**: JSONL, CSV with metadata

---

This pipeline represents a production-ready system for generating high-quality Arabic synthetic data with strict quality controls, advanced constraint systems, and comprehensive validation mechanisms. 