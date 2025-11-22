#!/bin/bash

# MadinahQA Production Batch Generation Script
# This script runs a production batch generation for the MadinahQA dataset.

set -e # Exit on any error

echo "========================================"
echo "🚀 Starting MadinahQA Production Batch Generation"
echo "========================================"

INPUT_FILE="data/MadinahQA/merged_madinah_qa.csv"
OUTPUT_DIR="outputs/production_madinahqa"
TARGET_COUNT=2617

# Create production directory
mkdir -p "$OUTPUT_DIR"

echo "Input file: ${INPUT_FILE}"
echo "Output directory: ${OUTPUT_DIR}"
echo "Target items: ${TARGET_COUNT}"

# The `generate` command is used here with `--use-batch` for batch processing.
# We will generate seeds first, then use them for generation.

SEED_FILE="${OUTPUT_DIR}/madinahqa_seeds.jsonl"
NUM_SEEDS=100

echo ""
echo "1. Sampling ${NUM_SEEDS} seeds for generation..."
arabic-synth sample-and-convert madinahqa \
    --input-file "$INPUT_FILE" \
    --output-file "$SEED_FILE" \
    --n ${NUM_SEEDS} \
    --mode stratified \
    --stratify-col "Subject"

echo "✅ Seeds created at ${SEED_FILE}"

echo ""
echo "2. Starting batch generation for MadinahQA..."

GENERATED_FILE="${OUTPUT_DIR}/generated_items.jsonl"

arabic-synth generate madinahqa \
    --num-samples ${TARGET_COUNT} \
    --model "openrouter:google/gemini-2.5-flash" \
    --seed-file "$SEED_FILE" \
    --output-dir "$OUTPUT_DIR" \
    --batch-size 20

# Rename the output to a consistent name
mv "${OUTPUT_DIR}/generate_style_None_${TARGET_COUNT}.jsonl" "$GENERATED_FILE"

total_items=$(wc -l < "$GENERATED_FILE")
echo "📈 Total items generated: $total_items"

echo ""
echo "3. Cleaning combined dataset..."

CLEANED_FILE="${OUTPUT_DIR}/generated_items_cleaned.jsonl"
arabic-synth clean madinahqa \
    --in-path "$GENERATED_FILE" \
    --out-path "$CLEANED_FILE"

cleaned_items=$(wc -l < "$CLEANED_FILE")
echo "✅ Cleaned items: $cleaned_items"

echo ""
echo "🎉 MadinahQA Production batch generation completed!"
echo "========================================"
echo "📁 Final outputs:"
echo "  - ${GENERATED_FILE}: ${total_items} raw items"
echo "  - ${CLEANED_FILE}: ${cleaned_items} cleaned items"
echo ""
