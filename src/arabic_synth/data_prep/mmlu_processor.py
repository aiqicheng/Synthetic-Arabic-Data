# -*- coding: utf-8 -*-
"""
MMLU data processing module that handles:
1. CSV parsing and sampling (uniform/stratified)
2. Format conversion (CSV to JSONL)
3. Unified interface for MMLU data operations
"""

import pandas as pd
import random
import os
import argparse
import csv
import json
from typing import Optional, Dict, Any, List
from pathlib import Path

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from schemas.mmlu import MMLUItem, MMLURawItem


class MMLUProcessor:
    """
    Unified MMLU data processor that handles CSV parsing, sampling, and format conversion.
    """
    
    def __init__(self, mmlu_file: str):
        if not mmlu_file.endswith(".csv"):
            raise ValueError("This version only supports CSV format MMLU dataset")
        self.file = mmlu_file
        self.data = None
        self._load_data()

    def _load_data(self):
        """Load and parse CSV data with metadata extraction"""
        # Load CSV with headers
        df = pd.read_csv(self.file, encoding='utf-8')
        
        # Clean column names (remove any extra spaces)
        df.columns = df.columns.str.strip()
        
        # Ensure required columns exist
        required_cols = ['ID', 'Subject', 'Level', 'Question', 'Answer Key', 'Option 1', 'Option 2', 'Option 3', 'Option 4']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Fill NaN values with empty strings for optional columns
        optional_cols = ['Country', 'Group', 'Context', 'Option 5']
        for col in optional_cols:
            if col in df.columns:
                df[col] = df[col].fillna('')
            else:
                df[col] = ''
        
        # Handle is_few_shot column
        if 'is_few_shot' in df.columns:
            df['is_few_shot'] = df['is_few_shot'].fillna(False).astype(bool)
        else:
            df['is_few_shot'] = False
        
        self.data = df

    def sample_uniform(self, n: int, seed: Optional[int] = None, data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Uniform random sampling"""
        if seed is None:
            seed = random.randint(0, 10000)
        data_to_use = data if data is not None else self.data
        return data_to_use.sample(n=n, random_state=seed)

    def sample_stratified(self, n: int, stratify_col: str = "Subject", seed: Optional[int] = None, data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Stratified sampling (default by Subject)"""
        if seed is None:
            seed = random.randint(0, 10000)
        
        data_to_use = data if data is not None else self.data
        
        if stratify_col not in data_to_use.columns:
            raise ValueError(f"Column {stratify_col} not in dataset. Available: {list(data_to_use.columns)}")
        
        groups = data_to_use.groupby(stratify_col)
        result = []
        for _, g in groups:
            k = max(1, round(len(g) / len(data_to_use) * n))
            # Ensure we don't try to sample more than available
            sample_size = min(k, len(g))
            if sample_size > 0:
                result.append(g.sample(n=sample_size, random_state=seed))
        
        if not result:
            return pd.DataFrame()
        
        # If we have fewer samples than requested, return what we have
        combined = pd.concat(result)
        if len(combined) <= n:
            return combined
        else:
            return combined.sample(n=n, random_state=seed)

    def save_csv(self, df: pd.DataFrame, out_file: str):
        """Save sampled subset in the same CSV format as original dataset"""
        out_dir = os.path.dirname(out_file)
        if out_dir:  # Only create directory if there is one
            os.makedirs(out_dir, exist_ok=True)

        # Save with headers
        df.to_csv(out_file, index=False, encoding='utf-8')

    def convert_to_jsonl(self, input_csv: Optional[str] = None, output_jsonl: Optional[str] = None) -> Dict[str, int]:
        """
        Convert CSV format to JSONL format.
        Returns dict with conversion statistics.
        """
        in_csv = input_csv or self.file
        out_jsonl = output_jsonl or "data/mmlu.jsonl"
        
        os.makedirs(os.path.dirname(out_jsonl), exist_ok=True)
        n_in, n_ok, n_skip = 0, 0, 0
        
        with open(in_csv, newline="", encoding="utf-8") as fin, \
             open(out_jsonl, "w", encoding="utf-8") as fout:
            reader = csv.DictReader(fin)
            
            for row in reader:
                n_in += 1
                
                try:
                    # Create raw item and convert to processed item
                    raw_item = MMLURawItem(**row)
                    mmlu_item = raw_item.to_mmlu_item()
                    
                    # Validate the item
                    if not mmlu_item.question or not mmlu_item.options or not mmlu_item.answer:
                        n_skip += 1
                        continue
                    
                    # Write to JSONL
                    item_dict = mmlu_item.model_dump()
                    fout.write(json.dumps(item_dict, ensure_ascii=False, separators=(',', ':')) + "\n")
                    n_ok += 1
                    
                except Exception as e:
                    print(f"Error processing row {n_in}: {e}")
                    n_skip += 1
                    continue

        return {"input_rows": n_in, "success": n_ok, "skipped": n_skip}

    def sample_and_convert(self, n: int, mode: str = "uniform", stratify_col: str = "Subject", 
                          output_jsonl: Optional[str] = None, seed: Optional[int] = None,
                          filter_subject: Optional[str] = None, filter_level: Optional[str] = None, 
                          filter_country: Optional[str] = None) -> Dict[str, Any]:
        """
        Combined operation: sample data and convert to JSONL format.
        Returns conversion statistics.
        """
        # Apply filters first
        filtered_data = self.data.copy()
        
        if filter_subject:
            # Handle multiple subjects (comma-separated)
            if ',' in filter_subject:
                subjects = [s.strip() for s in filter_subject.split(',')]
                filtered_data = filtered_data[filtered_data['Subject'].isin(subjects)]
            else:
                filtered_data = filtered_data[filtered_data['Subject'] == filter_subject]
                
        if filter_level:
            # Handle multiple levels (comma-separated)
            if ',' in filter_level:
                levels = [l.strip() for l in filter_level.split(',')]
                filtered_data = filtered_data[filtered_data['Level'].isin(levels)]
            else:
                filtered_data = filtered_data[filtered_data['Level'] == filter_level]
                
        if filter_country:
            # Handle multiple countries (comma-separated)
            if ',' in filter_country:
                countries = [c.strip() for c in filter_country.split(',')]
                filtered_data = filtered_data[filtered_data['Country'].isin(countries)]
            else:
                filtered_data = filtered_data[filtered_data['Country'] == filter_country]
        
        # Check if we have enough data after filtering
        if len(filtered_data) < n:
            print(f"Warning: Only {len(filtered_data)} samples available after filtering, requested {n}")
            n = min(n, len(filtered_data))
        
        # Sample data
        if mode == "uniform":
            sampled_df = self.sample_uniform(n, seed=seed, data=filtered_data)
        elif mode == "stratified":
            sampled_df = self.sample_stratified(n, stratify_col=stratify_col, seed=seed, data=filtered_data)
        else:
            raise ValueError(f"Unknown sampling mode: {mode}")

        # Save to temporary CSV
        temp_csv = "temp_mmlu_sampled.csv"
        self.save_csv(sampled_df, temp_csv)
        
        # Convert to JSONL
        out_jsonl = output_jsonl or f"outputs/mmlu_{mode}_{n}.jsonl"
        stats = self.convert_to_jsonl(input_csv=temp_csv, output_jsonl=out_jsonl)
        
        # Clean up temporary file
        if os.path.exists(temp_csv):
            os.remove(temp_csv)
        
        stats["sampling_mode"] = mode
        stats["samples_requested"] = n
        stats["output_file"] = out_jsonl
        
        return stats


# Standalone functions for backward compatibility
def sample_uniform_main(input_file=None, output_file=None, n=10, seed=None):
    """Main function for uniform sampling (backward compatibility)"""
    input_file = input_file or "arabic_mmlu_compsci.csv"
    output_file = output_file or "outputs/mmlu_uniform.csv"
    
    processor = MMLUProcessor(input_file)
    df = processor.sample_uniform(n, seed=seed)
    processor.save_csv(df, output_file)
    print(f"[OK] Uniform sampling: {n} samples saved to {output_file}")
    return len(df)


def sample_stratified_main(input_file=None, output_file=None, n=20, stratify_col="Subject", seed=None):
    """Main function for stratified sampling (backward compatibility)"""
    input_file = input_file or "arabic_mmlu_compsci.csv"
    output_file = output_file or "outputs/mmlu_stratified.csv"
    
    processor = MMLUProcessor(input_file)
    df = processor.sample_stratified(n, stratify_col=stratify_col, seed=seed)
    processor.save_csv(df, output_file)
    print(f"[OK] Stratified sampling: {n} samples by '{stratify_col}' saved to {output_file}")
    return len(df)


def convert_csv_main(input_csv=None, output_jsonl=None):
    """Main function for CSV to JSONL conversion (backward compatibility)"""
    in_csv = input_csv or "arabic_mmlu_compsci.csv"
    out_jsonl = output_jsonl or "data/mmlu.jsonl"
    
    processor = MMLUProcessor(in_csv)
    stats = processor.convert_to_jsonl(input_csv=in_csv, output_jsonl=out_jsonl)
    
    print(f"[DONE] Input rows: {stats['input_rows']} | Success: {stats['success']} | Skipped: {stats['skipped']} → {out_jsonl}")
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process MMLU datasets: sample and convert formats")
    parser.add_argument("--operation", choices=["sample", "convert", "sample-convert"], default="sample-convert",
                       help="Operation to perform")
    parser.add_argument("--mode", choices=["uniform", "stratified"], default="uniform",
                       help="Sampling mode (for sample operations)")
    parser.add_argument("--input-file", default="arabic_mmlu_compsci.csv",
                       help="Input CSV file")
    parser.add_argument("--output-csv", 
                       help="Output CSV file (for sampling only)")
    parser.add_argument("--output-jsonl",
                       help="Output JSONL file (for conversion)")
    parser.add_argument("--n", type=int, default=10,
                       help="Number of samples")
    parser.add_argument("--stratify-col", default="Subject",
                       help="Column for stratified sampling")
    parser.add_argument("--seed", type=int,
                       help="Random seed for reproducibility")
    args = parser.parse_args()
    
    processor = MMLUProcessor(args.input_file)
    
    if args.operation == "sample":
        # Sample only, save to CSV
        if args.mode == "uniform":
            output_file = args.output_csv or "outputs/mmlu_uniform.csv"
            sample_uniform_main(
                input_file=args.input_file,
                output_file=output_file,
                n=args.n,
                seed=args.seed
            )
        else:
            output_file = args.output_csv or "outputs/mmlu_stratified.csv"
            sample_stratified_main(
                input_file=args.input_file,
                output_file=output_file,
                n=args.n,
                stratify_col=args.stratify_col,
                seed=args.seed
            )
    
    elif args.operation == "convert":
        # Convert only
        output_jsonl = args.output_jsonl or "data/mmlu.jsonl"
        convert_csv_main(input_csv=args.input_file, output_jsonl=output_jsonl)
    
    elif args.operation == "sample-convert":
        # Sample and convert in one operation
        output_jsonl = args.output_jsonl or f"outputs/mmlu_{args.mode}_{args.n}.jsonl"
        stats = processor.sample_and_convert(
            n=args.n,
            mode=args.mode,
            stratify_col=args.stratify_col,
            output_jsonl=output_jsonl,
            seed=args.seed
        )
        print(f"[DONE] {stats['sampling_mode']} sampling + conversion:")
        print(f"  Requested: {stats['samples_requested']} samples")
        print(f"  Success: {stats['success']} | Skipped: {stats['skipped']}")
        print(f"  Output: {stats['output_file']}")
