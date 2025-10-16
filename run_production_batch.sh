#!/bin/bash

# Production Batch Generation Script
# This script runs 5 production runs with different input files and combines the results

set -e  # Exit on any error

echo "🚀 Starting Production Batch Generation"
echo "========================================"

# Create production directory
mkdir -p outputs/production

# Execute program automatically for 5 runs
echo "📊 Running 5 production runs..."
for i in {1..5}; do
    echo ""
    echo "🔄 Starting Run $i/5..."
    echo "Input file: data/arabicmmlu/arabicmmlu_${i}.csv"
    echo "Output directory: outputs/production/run${i}"
    
    arabic-synth generate-enhanced-batch \
        --input-file "data/arabicmmlu/arabicmmlu_${i}.csv" \
        --output-dir "outputs/production/run${i}" \
        --sampling-mode stratified \
        --total-batches 100 \
        --seeds-per-batch 20 \
        --max-concurrent-requests 100 \
        --model openai:gpt-4o-mini
    
    # Clean up intermediate batch seed files (keep only consolidated files)
    echo "🧹 Cleaning up intermediate files for run ${i}..."
    rm -f outputs/production/run${i}/batch_*_seeds.jsonl
    
    echo "✅ Run $i completed successfully!"
done

echo ""
echo "📁 Combining results from all runs..."

# Combine all generated items
echo "🔗 Combining generated items..."
cat outputs/production/run*/generated_items.jsonl > outputs/production/combine_mcq.jsonl

# Combine all generation summaries
echo "📊 Combining generation summaries..."
cat outputs/production/run*/generation_summary.json > outputs/production/combine_summaries.json

# Get file statistics
total_items=$(wc -l < outputs/production/combine_mcq.jsonl)
echo "📈 Total items generated: $total_items"

echo ""
echo "🧹 Cleaning combined dataset..."

# Clean the combined dataset
arabic-synth clean mmlu \
    --in-path outputs/production/combine_mcq.jsonl \
    --out-path outputs/production/combine_mcq_cleaned.jsonl

# Get cleaned statistics
cleaned_items=$(wc -l < outputs/production/combine_mcq_cleaned.jsonl)
echo "✅ Cleaned items: $cleaned_items"
echo "📊 Cleanup rate: $(( (total_items - cleaned_items) * 100 / total_items ))%"

echo ""
echo "🔍 Evaluating cleaned dataset..."

# Evaluate the cleaned dataset
arabic-synth evaluate mmlu \
    --in-path outputs/production/combine_mcq_cleaned.jsonl

echo ""
echo "🎉 Production batch generation completed!"
echo "========================================"
echo "📁 Final outputs:"
echo "  - outputs/production/combine_mcq.jsonl: $total_items raw items"
echo "  - outputs/production/combine_mcq_cleaned.jsonl: $cleaned_items cleaned items"
echo "  - outputs/production/combine_summaries.json: Combined statistics"
echo ""
echo "📊 Individual run results in outputs/production/run1/ through outputs/production/run5/"
