import pandas as pd
import random
import os
import ast

# Fake numpy array converter (handles array([...], dtype=object))
def array(x, dtype=None):
    return list(x)

safe_env = {"array": array}

class ExamSampler:
    def __init__(self, exam_file: str = "test-00000-of-00001.arabic.csv"):
        if not exam_file.endswith(".csv"):
            raise ValueError("This version only supports CSV format exams dataset")
        self.file = exam_file

        # Load CSV (no header, fixed 4 columns)
        df = pd.read_csv(
            exam_file,
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

    def sample_uniform(self, n: int) -> pd.DataFrame:
        """Uniform random sampling"""
        return self.data.sample(n=n, random_state=random.randint(0, 10000))

    def sample_stratified(self, n: int, stratify_col: str = "subject") -> pd.DataFrame:
        """Stratified sampling (default by subject)"""
        if stratify_col not in self.data.columns:
            raise ValueError(f"Column {stratify_col} not in dataset. Available: {list(self.data.columns)}")
        groups = self.data.groupby(stratify_col)
        result = []
        for _, g in groups:
            k = max(1, round(len(g) / len(self.data) * n))
            result.append(g.sample(n=min(k, len(g)), random_state=random.randint(0, 10000)))
        return pd.concat(result).sample(n=n)

    def save(self, df: pd.DataFrame, out_file: str):
        """Save sampled subset in the same CSV format as original dataset"""
        os.makedirs(os.path.dirname(out_file), exist_ok=True)

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

if __name__ == "__main__":
    sampler = ExamSampler("test-00000-of-00001.arabic.csv")

    # Uniform sample: 10 examples
    df1 = sampler.sample_uniform(10)
    sampler.save(df1, "outputs/exams_uniform.csv")

    # Stratified sample: 20 examples by subject
    df2 = sampler.sample_stratified(20, stratify_col="subject")
    sampler.save(df2, "outputs/exams_stratified.csv")
