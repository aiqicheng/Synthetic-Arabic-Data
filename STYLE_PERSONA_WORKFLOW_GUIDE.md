# Arabic-Synth Style-Persona Workflow Guide

## 🎯 Overview

The `style-persona-workflow` command provides a complete end-to-end pipeline that combines style-guided generation with persona augmentation for Arabic exam question synthesis. This unified workflow implements the methodology described in research papers for creating high-quality, diverse synthetic datasets.

## 🔄 Workflow Steps

The command executes a 4-step pipeline:

```mermaid
graph LR
    A[Original CSV] --> B[Sample & Convert]
    B --> C[Style-Guided Generation]
    C --> D[Persona Augmentation]
    D --> E[Combined Dataset]
    
    B -.-> F[seeds.jsonl]
    C -.-> G[styled_seeds.jsonl]
    D -.-> H[combined_requests.jsonl]
```

### Step 1: Sampling & Conversion 📊
- **Input**: Original CSV exam dataset (`test-00000-of-00001.arabic.csv`)
- **Process**: Scientific sampling (uniform or stratified) + CSV-to-JSONL conversion
- **Output**: `seeds.jsonl` - Small set of seed examples for style guidance
- **Purpose**: Create representative samples while maintaining format compatibility

### Step 2: Style-Guided Generation 🎨
- **Input**: `seeds.jsonl` (for style guidance)
- **Process**: LLM generation using seed-based style constraints via `SeedManager`
- **Output**: `styled_seeds.jsonl` - Questions following established style patterns
- **Purpose**: Generate new questions that match the style, complexity, and format of original data

### Step 3: Persona Integration 👥
- **Input**: Pre-existing persona collection (`selected_200.jsonl`)
- **Process**: Verification and preparation of persona data
- **Purpose**: Ensure diverse perspectives are available for augmentation

### Step 4: Persona Augmentation 🔄
- **Input**: `styled_seeds.jsonl` + `selected_persona.jsonl`
- **Process**: Create persona-augmented prompts for each styled question
- **Output**: `combined_requests.jsonl` - Final dataset ready for LLM processing
- **Purpose**: Apply multiple personas to each question for perspective diversity

## 📋 Command Syntax

```bash
arabic-synth style-persona-workflow [OPTIONS]
```

## 🔧 Parameters

### Required Files
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--input-csv` | `data/test-00000-of-00001.arabic.csv` | Source CSV exam dataset |
| `--personas-path` | `data/personas/selected_200.jsonl` | Pre-selected persona collection |

### Output Configuration
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--output-dir` | `outputs/style_persona` | Directory for all workflow outputs |

### Sampling Configuration
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--n-seeds` | `20` | Number of seed examples to extract |
| `--sampling-mode` | `stratified` | Sampling strategy (`uniform` or `stratified`) |
| `--stratify-col` | `subject` | Column for stratified sampling |

### Generation Configuration
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--n-styled` | `100` | Number of styled questions to generate |
| `--model` | `openai:gpt-4o` | LLM model for generation |

### Persona Configuration
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--per-item-personas` | `5` | Number of personas per styled question |

### Reproducibility
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--seed` | `42` | Random seed for consistent results |

## 🚀 Usage Examples

### Basic Usage (Development)
```bash
# Quick test with mock model
arabic-synth style-persona-workflow \
  --n-seeds 10 \
  --n-styled 50 \
  --model mock \
  --output-dir outputs/dev_test
```

### Production Run (Small Scale)
```bash
# Production run with OpenAI
arabic-synth style-persona-workflow \
  --n-seeds 20 \
  --n-styled 200 \
  --per-item-personas 10 \
  --model openai:gpt-4o \
  --sampling-mode stratified \
  --output-dir outputs/production_small
```

### Large Scale Production
```bash
# Large-scale dataset generation
arabic-synth style-persona-workflow \
  --n-seeds 50 \
  --n-styled 1000 \
  --per-item-personas 15 \
  --model openai:gpt-4o \
  --sampling-mode stratified \
  --stratify-col subject \
  --output-dir outputs/large_scale \
  --seed 123
```

### Custom Configuration
```bash
# Custom input files and uniform sampling
arabic-synth style-persona-workflow \
  --input-csv data/custom_exams.csv \
  --personas-path data/personas/specialized_personas.jsonl \
  --n-seeds 15 \
  --n-styled 300 \
  --sampling-mode uniform \
  --per-item-personas 8 \
  --model openai:gpt-4-turbo \
  --output-dir outputs/custom_workflow
```

## 📁 Output Structure

The workflow creates a comprehensive output directory:

```
outputs/style_persona/
├── seeds.jsonl                    # Step 1: Sampled seed examples
├── styled_seeds.jsonl             # Step 2: Style-guided questions
├── combined_requests.jsonl        # Step 4: Final persona-augmented dataset
├── workflow_summary.json          # Complete workflow metadata
└── exams_seeds_audit.json        # Seed usage audit trail
```

### File Descriptions

#### `seeds.jsonl`
```json
{"id": "28a8e962-7722-11ea-9116-54bef70b159e", "question": "في أي أجزاء البلاستيدة الخضراء تحدث التفاعلات المعتمدة على الضوء في عملية البناء الضوئي؟", "options": ["الستروما ) الحشوة (", "الثيلاكويد", "الغشاء الداخلي", "الغشاء الخارجي"], "answer": "الستروما ) الحشوة (", "explanation": ""}
```

#### `styled_seeds.jsonl`
```json
{"question": "ما هي أكبر قارة في العالم من حيث المساحة؟", "options": ["A. آسيا", "B. أفريقيا", "C. أوروبا", "D. أمريكا الشمالية"], "answer": "A"}
```

#### `combined_requests.jsonl`
```json
{"source_id": 0, "persona": "A civic leader who regularly watches the talk-show host's program and provides feedback on their reporting", "prompt": "أنت مساعد خبير في إنشاء أسئلة امتحانية باللغة العربية...", "gen_config": {"temperature": 0.9, "top_p": 0.95}}
```

#### `workflow_summary.json`
```json
{
  "workflow": "style-persona-combined",
  "input_csv": "data/test-00000-of-00001.arabic.csv",
  "sampling_mode": "stratified",
  "n_seeds": 20,
  "n_styled": 100,
  "per_item_personas": 5,
  "model": "openai:gpt-4o",
  "seed": 42,
  "results": {
    "seeds_file": "outputs/style_persona/seeds.jsonl",
    "seeds_count": 20,
    "styled_seeds_file": "outputs/style_persona/styled_seeds.jsonl",
    "styled_count": 100,
    "personas_file": "data/personas/selected_200.jsonl",
    "combined_requests_file": "outputs/style_persona/combined_requests.jsonl",
    "total_requests": 500
  }
}
```

## 🎛️ Advanced Configuration

### Sampling Strategies

#### Stratified Sampling (Recommended)
```bash
--sampling-mode stratified --stratify-col subject
```
- **Use Case**: Balanced representation across subjects
- **Benefits**: Ensures diverse topic coverage in seeds
- **Best For**: General-purpose datasets

#### Uniform Sampling
```bash
--sampling-mode uniform
```
- **Use Case**: Random sampling without constraints
- **Benefits**: Natural distribution preservation
- **Best For**: Maintaining original data distribution

### Model Selection

#### OpenAI Models
```bash
--model openai:gpt-4o          # Latest, most capable
--model openai:gpt-4-turbo     # Fast, high-quality
--model openai:gpt-3.5-turbo   # Cost-effective
```

#### Mock Model (Development)
```bash
--model mock                   # For testing without API costs
```

### Persona Configuration

#### Conservative (High Quality)
```bash
--per-item-personas 3          # 3 personas per question
```

#### Balanced (Recommended)
```bash
--per-item-personas 5-8        # Good diversity/quality balance
```

#### Aggressive (Maximum Diversity)
```bash
--per-item-personas 10-15      # Maximum perspective variety
```

## 📊 Quality Control Features

### Seed Constraints
- **Maximum Seeds**: Limited to ≤10 by default to prevent test set leakage
- **Diversity Check**: Ensures seed variety with minimum diversity threshold
- **Similarity Validation**: Prevents generated content from being too similar to seeds

### Style Guidance
- **Question Length**: Maintains similar word count as seed examples
- **Subject Coverage**: Balances topics based on seed distribution
- **Format Consistency**: Preserves option format and structure
- **Complexity Matching**: Maintains academic difficulty level

### Audit Trail
- **Seed Usage Tracking**: Complete record of which seeds were used
- **Hash Verification**: Cryptographic hashes for reproducibility
- **Constraint Logging**: Documentation of all applied constraints

## 🔍 Troubleshooting

### Common Issues

#### "Loaded 0 seed examples"
```bash
# Problem: Seeds not loading due to format mismatch
# Solution: Check seed file format, ensure required fields exist
head -2 outputs/style_persona/seeds.jsonl
```

#### Repetitive Generated Content
```bash
# Problem: Mock model generating identical questions
# Solution: Use real OpenAI model or check mock model implementation
--model openai:gpt-4o  # instead of --model mock
```

#### Missing Personas File
```bash
# Problem: Personas file not found
# Solution: Verify personas path or create personas
arabic-synth select-personas --help
```

### Validation Commands

#### Check Seeds Format
```bash
# Verify seeds are properly formatted
jq -r '.question' outputs/style_persona/seeds.jsonl | head -3
```

#### Validate Styled Questions
```bash
# Check styled questions variety
jq -r '.question' outputs/style_persona/styled_seeds.jsonl | sort | uniq -c
```

#### Inspect Persona Requests
```bash
# Sample persona requests
jq -r '.persona' outputs/style_persona/combined_requests.jsonl | head -5
```

## 📈 Performance Optimization

### For Large Datasets
```bash
# Optimize for large-scale generation
arabic-synth style-persona-workflow \
  --n-seeds 30 \                    # More seeds for better style guidance
  --n-styled 2000 \                 # Large styled dataset
  --per-item-personas 10 \          # High persona diversity
  --model openai:gpt-4o \           # Most capable model
  --sampling-mode stratified \      # Balanced sampling
  --seed 42                         # Reproducible results
```

### For Development/Testing
```bash
# Quick testing configuration
arabic-synth style-persona-workflow \
  --n-seeds 5 \                     # Minimal seeds
  --n-styled 20 \                   # Small test set
  --per-item-personas 2 \           # Minimal personas
  --model mock \                    # No API costs
  --output-dir outputs/quick_test
```

## 🔗 Integration with Other Commands

### Pre-workflow Setup
```bash
# 1. Prepare personas (if needed)
arabic-synth select-personas \
  --input-file data/personas/personas_all.jsonl \
  --output-file data/personas/selected_200.jsonl \
  --n 200

# 2. Run style-persona workflow
arabic-synth style-persona-workflow \
  --personas-path data/personas/selected_200.jsonl
```

### Post-workflow Processing
```bash
# 3. Send requests to LLM (if using real model)
arabic-synth send-persona-requests \
  --input-file outputs/style_persona/combined_requests.jsonl \
  --output-file outputs/style_persona/generated_responses.jsonl

# 4. Quality check results
arabic-synth quality-check \
  --input-file outputs/style_persona/generated_responses.jsonl \
  --output-dir outputs/style_persona/quality_reports
```

## 📚 Best Practices

### 🎯 Dataset Design
1. **Start Small**: Begin with `--n-seeds 10 --n-styled 50` for testing
2. **Scale Gradually**: Increase parameters based on quality assessment
3. **Balance Diversity**: Use `--per-item-personas 5-8` for optimal variety
4. **Stratify When Possible**: Use `--sampling-mode stratified` for balanced datasets

### 🔧 Technical Considerations
1. **Reproducibility**: Always set `--seed` for consistent results
2. **Cost Management**: Use `--model mock` for development, real models for production
3. **Quality Control**: Review seed audit files and workflow summaries
4. **Storage Planning**: Large workflows can generate substantial data

### 📊 Quality Assurance
1. **Validate Seeds**: Check that seeds represent desired style and topics
2. **Review Styled Output**: Ensure generated questions show appropriate variety
3. **Inspect Personas**: Verify persona-augmented requests maintain quality
4. **Monitor Constraints**: Check seed constraint compliance in audit files

## 🆘 Support and Documentation

### Related Commands
- `arabic-synth sample-and-convert --help` - Individual sampling and conversion
- `arabic-synth build-persona-requests --help` - Persona request generation
- `arabic-synth quality-check --help` - Quality validation
- `arabic-synth select-personas --help` - Persona curation

### Configuration Files
- `SEED_CONSTRAINTS.md` - Detailed seed constraint documentation
- `StyleGuide_PIPELINE_DETAILED.md` - Style guide methodology
- `Persona_PIPELINE_DETAILED.md` - Persona pipeline details

### Example Workflows
Check the `outputs/` directory for example results from different configurations to understand expected output formats and structures.

---

**Note**: This workflow combines research-backed methodologies for synthetic data generation with practical tools for Arabic language processing. Always validate results with domain experts and consider ethical implications of synthetic data use.
