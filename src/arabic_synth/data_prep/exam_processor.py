# -*- coding: utf-8 -*-
"""
Combined exam data processing module that handles:
1. CSV parsing and sampling (uniform/stratified)
2. Format conversion (CSV to JSONL)
3. Unified interface for exam data operations
"""

import pandas as pd
import random
import os
import ast
import argparse
import csv
import json
import re
from typing import Optional, Dict, Any, List
from pathlib import Path


# Regex for handling numpy array strings
ARRAY_RE = re.compile(r"array\(\s*(\[[\s\S]*?\])\s*(?:,\s*dtype=object)?\s*\)")


def strip_numpy_array(s: str) -> str:
    """Remove numpy array(...) wrappers from string representations"""
    prev = None
    while prev != s:
        prev = s
        s = ARRAY_RE.sub(r"\1", s)
    return s


def safe_parse_py_literal(s: str):
    """
    Parse Python literal strings (dicts/lists) while handling numpy arrays.
    Converts single-quoted Python dict strings to Python objects.
    """
    s = strip_numpy_array(s.strip())
    return ast.literal_eval(s)


# Fake numpy array converter for backward compatibility
def array(x, dtype=None):
    return list(x)


safe_env = {"array": array}


class ExamProcessor:
    """
    Unified exam data processor that handles CSV parsing, sampling, and format conversion.
    """
    
    def __init__(self, exam_file: str = "test-00000-of-00001.arabic.csv"):
        if not exam_file.endswith(".csv"):
            raise ValueError("This version only supports CSV format exams dataset")
        self.file = exam_file
        self.data = None
        self._load_data()

    def _load_data(self):
        """Load and parse CSV data with metadata extraction"""
        # Load CSV (no header, fixed 4 columns)
        df = pd.read_csv(
            self.file,
            header=None,
            names=["id", "qdict", "answer", "meta"]
        )

        # Parse qdict safely (handles array([...]))
        def parse_qdict(x):
            try:
                return eval(str(x), safe_env)
            except Exception:
                return str(x)

        df["qdict"] = df["qdict"].apply(parse_qdict)

        # Parse meta dict safely
        def parse_meta(x):
            try:
                return ast.literal_eval(str(x))
            except Exception:
                return {}
        df["meta"] = df["meta"].apply(parse_meta)

        # Flatten meta fields
        meta_df = pd.json_normalize(df["meta"])
        self.data = pd.concat([df.drop(columns=["meta"]), meta_df], axis=1)

    def sample_uniform(self, n: int, seed: Optional[int] = None) -> pd.DataFrame:
        """Uniform random sampling"""
        if seed is not None:
            random.seed(seed)
        return self.data.sample(n=n, random_state=random.randint(0, 10000))

    def sample_stratified(self, n: int, stratify_col: str = "subject", seed: Optional[int] = None) -> pd.DataFrame:
        """Stratified sampling (default by subject)"""
        if seed is not None:
            random.seed(seed)
        
        if stratify_col not in self.data.columns:
            raise ValueError(f"Column {stratify_col} not in dataset. Available: {list(self.data.columns)}")
        
        groups = self.data.groupby(stratify_col)
        result = []
        for _, g in groups:
            k = max(1, round(len(g) / len(self.data) * n))
            result.append(g.sample(n=min(k, len(g)), random_state=random.randint(0, 10000)))
        return pd.concat(result).sample(n=n)

    def save_csv(self, df: pd.DataFrame, out_file: str):
        """Save sampled subset in the same CSV format as original dataset"""
        out_dir = os.path.dirname(out_file)
        if out_dir:  # Only create directory if there is one
            os.makedirs(out_dir, exist_ok=True)

        out = df[["id", "qdict", "answer", "grade", "subject", "language"]].copy()

        # Convert qdict back to string
        out["qdict"] = out["qdict"].apply(lambda x: str(x))

        # Rebuild meta dict
        meta_cols = ["grade", "subject", "language"]
        out["meta"] = out[meta_cols].to_dict(orient="records")
        out["meta"] = out["meta"].apply(lambda x: str(x))

        out = out.drop(columns=meta_cols)

        # Save without header, same as original
        out.to_csv(out_file, index=False, header=False)

    def convert_to_jsonl(self, input_csv: Optional[str] = None, output_jsonl: Optional[str] = None) -> Dict[str, int]:
        """
        Convert CSV format to JSONL format.
        Returns dict with conversion statistics.
        """
        in_csv = input_csv or self.file
        out_jsonl = output_jsonl or "data/exams.jsonl"
        
        os.makedirs(os.path.dirname(out_jsonl), exist_ok=True)
        n_in, n_ok, n_skip = 0, 0, 0
        
        with open(in_csv, newline="", encoding="utf-8") as fin, \
             open(out_jsonl, "w", encoding="utf-8") as fout:
            reader = csv.reader(fin)
            
            for row in reader:
                n_in += 1
                if not row or len(row) < 3:
                    n_skip += 1
                    continue
                    
                _id = row[0].strip()
                q_blob = row[1].strip()
                ans_label = row[2].strip().strip('"').strip("'")
                meta_blob = row[3].strip() if len(row) > 3 else ""

                if not q_blob:
                    n_skip += 1
                    continue

                try:
                    q_obj = safe_parse_py_literal(q_blob)
                except Exception:
                    n_skip += 1
                    continue

                stem = (q_obj.get("stem") or q_obj.get("question") or "").strip()
                ch = q_obj.get("choices") or {}
                texts = ch.get("text") or []
                labels = ch.get("label") or []

                # Normalize to list[str]
                if not isinstance(texts, list) or not isinstance(labels, list):
                    n_skip += 1
                    continue
                    
                options = [str(x).strip() for x in texts if str(x).strip() != ""]
                labels = [str(x).strip() for x in labels]

                # Map answer letter to option text
                answer_text = None
                if ans_label in labels and labels.index(ans_label) < len(options):
                    answer_text = options[labels.index(ans_label)]
                else:
                    # Handle case differences
                    low = [l.lower() for l in labels]
                    if ans_label.lower() in low:
                        idx = low.index(ans_label.lower())
                        if idx < len(options):
                            answer_text = options[idx]

                # Parse meta for explanation
                explanation = ""
                if meta_blob:
                    try:
                        meta = safe_parse_py_literal(meta_blob)
                        explanation = str(meta.get("explanation") or meta.get("rationale") or "").strip()
                    except Exception:
                        pass

                if not stem or not options or not answer_text:
                    n_skip += 1
                    continue

                rec = {
                    "id": _id,
                    "question": stem,
                    "options": options,
                    "answer": answer_text,
                    "explanation": explanation,
                }
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n_ok += 1

        return {"input_rows": n_in, "success": n_ok, "skipped": n_skip}

    def sample_and_convert(self, n: int, mode: str = "uniform", stratify_col: str = "subject", 
                          output_jsonl: Optional[str] = None, seed: Optional[int] = None) -> Dict[str, Any]:
        """
        Combined operation: sample data and convert to JSONL format.
        Returns conversion statistics.
        """
        # Sample data
        if mode == "uniform":
            sampled_df = self.sample_uniform(n, seed=seed)
        elif mode == "stratified":
            sampled_df = self.sample_stratified(n, stratify_col=stratify_col, seed=seed)
        else:
            raise ValueError(f"Unknown sampling mode: {mode}")

        # Save to temporary CSV
        temp_csv = "temp_sampled.csv"
        self.save_csv(sampled_df, temp_csv)
        
        # Convert to JSONL
        out_jsonl = output_jsonl or f"outputs/exams_{mode}_{n}.jsonl"
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
    input_file = input_file or "test-00000-of-00001.arabic.csv"
    output_file = output_file or "outputs/exams_uniform.csv"
    
    processor = ExamProcessor(input_file)
    df = processor.sample_uniform(n, seed=seed)
    processor.save_csv(df, output_file)
    print(f"[OK] Uniform sampling: {n} samples saved to {output_file}")
    return len(df)


def sample_stratified_main(input_file=None, output_file=None, n=20, stratify_col="subject", seed=None):
    """Main function for stratified sampling (backward compatibility)"""
    input_file = input_file or "test-00000-of-00001.arabic.csv"
    output_file = output_file or "outputs/exams_stratified.csv"
    
    processor = ExamProcessor(input_file)
    df = processor.sample_stratified(n, stratify_col=stratify_col, seed=seed)
    processor.save_csv(df, output_file)
    print(f"[OK] Stratified sampling: {n} samples by '{stratify_col}' saved to {output_file}")
    return len(df)


def convert_csv_main(input_csv=None, output_jsonl=None):
    """Main function for CSV to JSONL conversion (backward compatibility)"""
    in_csv = input_csv or "data/test-00000-of-00001.arabic.csv"
    out_jsonl = output_jsonl or "data/exams.jsonl"
    
    processor = ExamProcessor(in_csv)
    stats = processor.convert_to_jsonl(input_csv=in_csv, output_jsonl=out_jsonl)
    
    print(f"[DONE] Input rows: {stats['input_rows']} | Success: {stats['success']} | Skipped: {stats['skipped']} → {out_jsonl}")
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process exam datasets: sample and convert formats")
    parser.add_argument("--operation", choices=["sample", "convert", "sample-convert"], default="sample-convert",
                       help="Operation to perform")
    parser.add_argument("--mode", choices=["uniform", "stratified"], default="uniform",
                       help="Sampling mode (for sample operations)")
    parser.add_argument("--input-file", default="test-00000-of-00001.arabic.csv",
                       help="Input CSV file")
    parser.add_argument("--output-csv", 
                       help="Output CSV file (for sampling only)")
    parser.add_argument("--output-jsonl",
                       help="Output JSONL file (for conversion)")
    parser.add_argument("--n", type=int, default=10,
                       help="Number of samples")
    parser.add_argument("--stratify-col", default="subject",
                       help="Column for stratified sampling")
    parser.add_argument("--seed", type=int,
                       help="Random seed for reproducibility")
    args = parser.parse_args()
    
    processor = ExamProcessor(args.input_file)
    
    if args.operation == "sample":
        # Sample only, save to CSV
        if args.mode == "uniform":
            output_file = args.output_csv or "outputs/exams_uniform.csv"
            sample_uniform_main(
                input_file=args.input_file,
                output_file=output_file,
                n=args.n,
                seed=args.seed
            )
        else:
            output_file = args.output_csv or "outputs/exams_stratified.csv"
            sample_stratified_main(
                input_file=args.input_file,
                output_file=output_file,
                n=args.n,
                stratify_col=args.stratify_col,
                seed=args.seed
            )
    
    elif args.operation == "convert":
        # Convert only
        output_jsonl = args.output_jsonl or "data/exams.jsonl"
        convert_csv_main(input_csv=args.input_file, output_jsonl=output_jsonl)
    
    elif args.operation == "sample-convert":
        # Sample and convert in one operation
        output_jsonl = args.output_jsonl or f"outputs/exams_{args.mode}_{args.n}.jsonl"
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
