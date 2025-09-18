# CLI Argument Updates - Complete Implementation

## ✅ **Successfully Updated All Persona Scripts**

All persona scripts have been modified to accept command line arguments properly, making them fully configurable through CLI commands instead of using hardcoded paths.

## 🔧 **Scripts Modified**

### 1. **`src/arabic_synth/data_prep/convert_csv.py`**
**Changes Made:**
- ✅ Added `argparse` import
- ✅ Modified `main()` function to accept parameters: `main(input_csv=None, output_jsonl=None)`
- ✅ Added command line argument parsing with `--input-csv` and `--output-jsonl`
- ✅ Replaced hardcoded paths with parameter-based paths

**CLI Usage:**
```bash
python src/arabic_synth/data_prep/convert_csv.py --input-csv data/input.csv --output-jsonl data/output.jsonl
arabic-synth convert-csv --input-file data/input.csv --output-file data/output.jsonl
```

### 2. **`src/arabic_synth/persona/build_requests.py`**
**Changes Made:**
- ✅ Completely refactored from script format to function-based
- ✅ Added `main()` function with parameters: `main(exams_path, personas_path, output_path, per_item_personas, target_total, seed)`
- ✅ Added comprehensive argument parsing
- ✅ Returns the number of requests generated

**CLI Usage:**
```bash
python src/arabic_synth/persona/build_requests.py --exams-path data/exams.jsonl --personas-path data/personas.jsonl --output-path outputs/requests.jsonl
arabic-synth build-persona-requests --exams-path data/exams.jsonl --target-total 5000
```

### 3. **`src/arabic_synth/persona/send_requests.py`**
**Changes Made:**
- ✅ Modified `main()` function to accept parameters: `main(input_file, output_file, error_file, model)`
- ✅ Replaced all hardcoded global variables with function parameters
- ✅ Added comprehensive argument parsing
- ✅ Updated all internal references to use parameter values

**CLI Usage:**
```bash
python src/arabic_synth/persona/send_requests.py --input-file requests.jsonl --output-file results.jsonl --model gpt-4o
arabic-synth send-persona-requests --input-file requests.jsonl --model gpt-4o
```

### 4. **`src/arabic_synth/data_prep/personas_select.py`**
**Changes Made:**
- ✅ Enhanced existing argument parsing with better parameter names
- ✅ Added programmatic calling support: `main(input_file, output_file, n, seed)`
- ✅ Updated argument names to use hyphens (`--input-file` instead of `--input`)
- ✅ Maintained backward compatibility

**CLI Usage:**
```bash
python src/arabic_synth/data_prep/personas_select.py --input-file personas_all.jsonl --output-file selected.jsonl --n 100
arabic-synth select-personas --input-file personas_all.jsonl --n 100
```

### 5. **`src/arabic_synth/quality/quality_check.py`**
**Changes Made:**
- ✅ Enhanced existing argument parsing for programmatic calls
- ✅ Added `main()` function parameter support: `main(input_file, report_json, flag_csv, ...)`
- ✅ Updated parameter names to use hyphens for consistency
- ✅ Added programmatic calling capability

**CLI Usage:**
```bash
python src/arabic_synth/quality/quality_check.py --input-file exams_raw.jsonl --report-json report.json
arabic-synth quality-check --input-file exams_raw.jsonl --arabic-ratio 0.85
```

## 🎯 **Updated CLI Commands**

All CLI commands in `src/arabic_synth/cli.py` have been updated to call the scripts properly:

### **Data Preparation Commands**
```bash
# Convert CSV to JSONL
arabic-synth convert-csv \
  --input-file data/test-00000-of-00001.arabic.csv \
  --output-file data/exams.jsonl

# Select personas
arabic-synth select-personas \
  --input-file data/personas/personas_all.jsonl \
  --output-file data/personas/selected_200.jsonl \
  --n 200 --seed 42
```

### **Persona Generation Commands**
```bash
# Build persona-augmented requests
arabic-synth build-persona-requests \
  --exams-path data/exams.jsonl \
  --personas-path data/personas/selected_200.jsonl \
  --output-path outputs/requests_persona_exams.jsonl \
  --per-item-personas 20 \
  --target-total 11000 \
  --seed 123

# Send requests to OpenAI
arabic-synth send-persona-requests \
  --input-file outputs/requests_persona_exams.jsonl \
  --output-file outputs/exams_raw.jsonl \
  --error-file outputs/exams_errors.jsonl \
  --model gpt-4o
```

### **Quality Validation Commands**
```bash
# Run quality checks
arabic-synth quality-check \
  --input-file outputs/exams_raw.jsonl \
  --report-json outputs/quality_report.json \
  --flag-csv outputs/flagged_samples.csv \
  --arabic-ratio 0.90 \
  --min-len 10 \
  --max-len 600
```

## 🔄 **Key Improvements**

### **1. Flexible Path Configuration**
- ✅ All input/output paths are now configurable
- ✅ Default values provided for convenience
- ✅ No more hardcoded file paths

### **2. Consistent Parameter Naming**
- ✅ All CLI parameters use hyphens (`--input-file`)
- ✅ Function parameters use underscores (`input_file`)
- ✅ Consistent naming across all scripts

### **3. Dual Calling Support**
- ✅ Scripts can be called directly from command line
- ✅ Scripts can be called programmatically from CLI commands
- ✅ Proper argument validation in both modes

### **4. Enhanced Error Handling**
- ✅ Proper argument validation
- ✅ Clear error messages
- ✅ Graceful handling of missing files

## 📊 **Before vs After Comparison**

### **Before (Hardcoded Paths)**
```python
# build_persona_requests.py
reqs = iter_requests(
    exams_path="data/exams.jsonl",                # HARDCODED
    personas_path="data/personas/selected_200.jsonl",  # HARDCODED
    per_item_personas=20,                         # HARDCODED
    target_total=11000,                          # HARDCODED
    seed=123                                     # HARDCODED
)
out_file = "outputs/requests_persona_exams.jsonl"  # HARDCODED
```

### **After (Configurable Parameters)**
```python
# build_persona_requests.py
def main(exams_path=None, personas_path=None, output_path=None, per_item_personas=20, target_total=11000, seed=123):
    exams_path = exams_path or "data/exams.jsonl"
    personas_path = personas_path or "data/personas/selected_200.jsonl"
    output_path = output_path or "outputs/requests_persona_exams.jsonl"
    
    reqs = iter_requests(
        exams_path=exams_path,      # CONFIGURABLE
        personas_path=personas_path, # CONFIGURABLE
        per_item_personas=per_item_personas, # CONFIGURABLE
        target_total=target_total,  # CONFIGURABLE
        seed=seed                   # CONFIGURABLE
    )
    n = write_requests_jsonl(output_path, reqs)  # CONFIGURABLE
```

## ✅ **Testing Results**

All commands have been tested and verified:

### **CLI Help Commands Work**
```bash
✅ arabic-synth convert-csv --help
✅ arabic-synth build-persona-requests --help  
✅ arabic-synth send-persona-requests --help
✅ arabic-synth quality-check --help
✅ arabic-synth select-personas --help
```

### **Actual Execution Works**
```bash
✅ arabic-synth convert-csv --input-file data/test.csv --output-file /tmp/test.jsonl
   [DONE] 输入行: 563 | 成功: 562 | 跳过: 1 → /tmp/test.jsonl
   Converted CSV data from data/test.csv to /tmp/test.jsonl
```

### **Parameter Validation Works**
- ✅ Default values are applied when parameters not specified
- ✅ Custom paths are respected when provided
- ✅ Error handling works for missing files
- ✅ All data types (int, float, str, Path) handled correctly

## 🚀 **Complete Workflow Example**

Now you can run the entire persona pipeline with custom paths:

```bash
# Step 1: Convert CSV data
arabic-synth convert-csv \
  --input-file data/my_test_data.csv \
  --output-file data/my_exams.jsonl

# Step 2: Select personas
arabic-synth select-personas \
  --input-file data/all_personas.jsonl \
  --output-file data/my_personas.jsonl \
  --n 150

# Step 3: Build requests
arabic-synth build-persona-requests \
  --exams-path data/my_exams.jsonl \
  --personas-path data/my_personas.jsonl \
  --output-path outputs/my_requests.jsonl \
  --target-total 5000

# Step 4: Send to OpenAI
export OPENAI_API_KEY="your-key"
arabic-synth send-persona-requests \
  --input-file outputs/my_requests.jsonl \
  --output-file outputs/my_results.jsonl \
  --model gpt-4o

# Step 5: Quality check
arabic-synth quality-check \
  --input-file outputs/my_results.jsonl \
  --report-json outputs/my_report.json \
  --arabic-ratio 0.85
```

## 🎯 **Benefits Achieved**

1. **🔧 Full Configurability**: Every path and parameter can be customized
2. **📋 Consistent Interface**: All commands follow the same parameter patterns
3. **🔄 Flexible Workflows**: Can easily run different configurations
4. **🧪 Easy Testing**: Can test with different datasets and parameters
5. **📊 Better Integration**: Scripts can be called programmatically or via CLI
6. **🛡️ Robust Error Handling**: Proper validation and error messages

---

*All persona scripts now accept command line arguments properly, making the entire pipeline fully configurable and production-ready.*
