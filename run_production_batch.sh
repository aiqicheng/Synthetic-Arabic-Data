#!/bin/bash

# Production Batch Generation Script
# This script runs 5 production runs with different input files and combines the results

set -e  # Exit on any error

# Setup environment
# source ./setup_env.sh
# echo "! Environment setup complete. !"

echo "========================================"
echo "🚀 Starting Production Batch Generation"
echo "========================================"

DATA_DIR="data/arabicmmlu/by_subject"
OUTPUT_DIR="outputs/production/by_subject"

# Define target generation counts per subject using an associative array
declare -A TARGET_COUNTS=(
    ["Islamic Studies"]=2222
    ["Biology"]=1412
    ["Geography"]=1376
    ["Driving Test"]=1214
    ["General Knowledge"]=1207
    ["History"]=1074
    ["Social Science"]=952
    ["Arabic Language"]=678
    ["Arabic Language (General)"]=615
    ["Economics"]=593
    ["Natural Science"]=584
    ["Computer Science"]=554
    ["Math"]=412
    ["Arabic Language (Grammar)"]=368
    ["Civics"]=329
    ["Law"]=317
    ["Physics"]=258
    ["Political Science"]=213
    ["Management"]=78
    ["Accounting"]=77
    ["Philosophy"]=42
)

# Create production directory
mkdir -p "$OUTPUT_DIR"

# Execute program for each subject
echo "📊 Running generation for each subject in $DATA_DIR..."
for csv_file in "$DATA_DIR"/arabicmmlu_*.csv; do
    subject=$(basename "$csv_file" .csv | sed 's/arabicmmlu_//')
    subject_key="${subject//_/ }" # Replace underscores with spaces for array lookup
    run_output_dir="${OUTPUT_DIR}/run${subject}"

    echo ""
    echo "🔄 Starting generation for subject: ${subject}"

    target_count=${TARGET_COUNTS[$subject_key]}

    if [ -z "$target_count" ]; then
        echo "⚠️ Warning: No target count defined for subject '${subject_key}'. Skipping."
        continue
    fi

    total_batches=$(( (target_count + 39) / 20 )) # Ceiling division
    echo "Input file: ${csv_file}"
    echo "Output directory: ${run_output_dir}"
    echo "Target items: ${target_count}, Total batches: ${total_batches}"

    arabic-synth generate-enhanced-batch \
        --input-file "$csv_file" \
        --output-dir "$run_output_dir" \
        --sampling-mode stratified \
        --total-batches "${total_batches}" \
        --seeds-per-batch 20 \
        --max-concurrent-requests 100 \
        --model "openrouter:google/gemini-2.5-flash"

    # Clean up intermediate batch seed files (keep only consolidated files)
    echo "🧹 Cleaning up intermediate files for subject ${subject}..."
    rm -f "${run_output_dir}"/batch_*_seeds.jsonl

    echo "✅ Generation for ${subject} completed successfully!"
done

echo ""
echo "📁 Combining results from all runs..."

# Combine all generated items
echo "🔗 Combining generated items..."
cat "${OUTPUT_DIR}"/run*/generated_items.jsonl > "${OUTPUT_DIR}/combine_mcq.jsonl"

# Combine all generation summaries
echo "📊 Combining generation summaries..."
cat "${OUTPUT_DIR}"/run*/generation_summary.json > "${OUTPUT_DIR}/combine_summaries.json"

# Get file statistics
total_items=$(wc -l < "${OUTPUT_DIR}/combine_mcq.jsonl")
echo "📈 Total items generated: $total_items"

echo ""
echo "🧹 Cleaning combined dataset..."

# Clean the combined dataset
arabic-synth clean mmlu \
    --in-path "${OUTPUT_DIR}/combine_mcq.jsonl" \
    --out-path "${OUTPUT_DIR}/combine_mcq_cleaned.jsonl"

# Get cleaned statistics
cleaned_items=$(wc -l < "${OUTPUT_DIR}/combine_mcq_cleaned.jsonl")
echo "✅ Cleaned items: $cleaned_items"
echo "📊 Cleanup rate: $(( (total_items - cleaned_items) * 100 / total_items ))%"

echo ""
echo "🔍 Evaluating cleaned dataset..."

# Evaluate the cleaned dataset
arabic-synth evaluate mmlu \
    --in-path "${OUTPUT_DIR}/combine_mcq_cleaned.jsonl"

echo ""
echo "🎉 Production batch generation completed!"
echo "========================================"
echo "📁 Final outputs:"
echo "  - outputs/production/combine_mcq.jsonl: $total_items raw items"
echo "  - outputs/production/combine_mcq_cleaned.jsonl: $cleaned_items cleaned items"
echo "  - ${OUTPUT_DIR}/combine_summaries.json: Combined statistics"
echo ""
echo "📊 Individual run results in ${OUTPUT_DIR}/"
