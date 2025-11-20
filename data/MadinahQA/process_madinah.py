# -*- coding: utf-8 -*-
"""
This script merges multiple CSV files from the MadinahQA dataset into a single file.

The script performs the following actions:
1. Recursively finds all `dev.csv` and `test.csv` files within the './MadinahQA' directory.
2. For each file, it reads the data using pandas.
3. It concatenates the 'Context' column with the 'Question' column to form a new 'Question'.
   - A newline character is placed between the context and the question for clarity.
   - If a row has no context, the question remains unchanged.
4. The 'Context' column is then cleared (set to an empty string).
5. All processed data is merged into a single CSV file named 'merged_madinah_qa.csv'.

This script is designed to handle Arabic text by using UTF-8 encoding for all file operations.
"""

import pandas as pd
from pathlib import Path
import os

def merge_madinah_qa_csvs(base_dir: str, output_file: str):
    """
    Merges MadinahQA CSV files, combining 'Context' and 'Question' columns.

    Args:
        base_dir (str): The directory containing the subject folders (e.g., './MadinahQA').
        output_file (str): The path for the output merged CSV file.
    """
    base_path = Path(base_dir)
    csv_files = list(base_path.rglob("*.csv"))

    if not csv_files:
        print(f"No CSV files found in '{base_dir}'. Please check the path.")
        return

    print(f"Found {len(csv_files)} files to merge: {[str(f) for f in csv_files]}")

    all_dfs = []
    for file_path in csv_files:
        df = pd.read_csv(file_path, encoding='utf-8')
        
        # Fill NaN in 'Context' to avoid errors during string operations
        df['Context'] = df['Context'].fillna('')
        
        # Concatenate 'Context' with 'Question'
        df['Question'] = df.apply(
            lambda row: f"{row['Context']}\n{row['Question']}" if row['Context'] else row['Question'],
            axis=1
        )
        df['Context'] = ''  # Clear the context column
        all_dfs.append(df)

    merged_df = pd.concat(all_dfs, ignore_index=True)
    merged_df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n[SUCCESS] Merged {len(csv_files)} files into '{output_file}' with {len(merged_df)} rows.")

if __name__ == "__main__":
    # Assuming the script is in data/MadinahQA and the subject folders are in the same directory
    current_dir = Path(__file__).parent
    merge_madinah_qa_csvs(str(current_dir), str(current_dir / "merged_madinah_qa.csv"))
