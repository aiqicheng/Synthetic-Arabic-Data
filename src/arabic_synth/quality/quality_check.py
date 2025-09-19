# -*- coding: utf-8 -*-
"""
quality_check.py
对 outputs/exams_raw.jsonl 做质量体检并输出报告：
- JSON 结构 & 选项一致性
- 阿语纯度
- 题干长度边界
- 近重复聚类（指纹+Jaccard 复核）
- 多样性指标：distinct-2 / distinct-3
- persona 覆盖分布（均衡度）

用法（PowerShell 单行）：
python quality_check.py --input outputs/exams_raw.jsonl --report_json outputs/quality_report.json --flag_csv outputs/flagged_samples.csv

参数（可选）：
--arabic_ratio 0.9         # 阿语占比阈值
--min_len 10 --max_len 600 # 题干长度边界
--dup_shingle 5            # 指纹的字符 n-gram
--dup_jaccard 0.90         # 重复判定阈值（越高越严格）
--sample_flags 200         # 导出到CSV的问题样本数量上限
"""
import argparse, json, os, re, math, csv, hashlib
from collections import Counter, defaultdict
from typing import List, Dict, Any, Tuple, Iterable, Optional
from statistics import mean, stdev

ARABIC_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\u0660-\u0669\u06F0-\u06F9]"
)  # 字母+扩展+阿拉伯数字

def ar_ratio(s: str) -> float:
    if not s: return 0.0
    total = len(s)
    ar = sum(1 for ch in s if ARABIC_RE.match(ch))
    return ar / total if total else 0.0

def normalize(s: str) -> str:
    return (s or "").strip()

def read_jsonl(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line: 
                continue
            try:
                obj = json.loads(line)
            except Exception:
                yield {"_idx": i, "_parse_error": True}
                continue
            obj["_idx"] = i
            yield obj

def shingles(s: str, n: int = 5) -> set:
    s = " ".join(s.split())
    L = len(s)
    if L < n: 
        return {s} if s else set()
    return {s[i:i+n] for i in range(L - n + 1)}

def jaccard(a: set, b: set) -> float:
    if not a and not b: return 1.0
    if not a or not b:  return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0

def tokenize_words(s: str) -> List[str]:
    # 简单按空白切词（对阿语也够用于 distinct-n 粗指标）
    return [t for t in re.split(r"\s+", s.strip()) if t]

def distinct_n(texts: List[str], n: int = 2) -> float:
    all_ngrams, total = set(), 0
    for t in texts:
        toks = tokenize_words(t)
        if len(toks) < n: 
            continue
        total += (len(toks) - n + 1)
        for i in range(len(toks) - n + 1):
            all_ngrams.add(tuple(toks[i:i+n]))
    return (len(all_ngrams) / total) if total else 0.0

def compare_with_real_data(synthetic_data: List[Dict[str, Any]], real_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare synthetic data with real data distributions"""
    if not real_data:
        return {"error": "No real data provided for comparison"}
    
    return {
        "length_comparison": compare_length_distributions(synthetic_data, real_data),
        "answer_balance_comparison": compare_answer_balance(synthetic_data, real_data),
        "vocabulary_analysis": calculate_vocabulary_overlap(synthetic_data, real_data)
    }

def compare_length_distributions(synthetic: List[Dict], real: List[Dict]) -> Dict:
    """Compare question length distributions between synthetic and real data"""
    syn_lengths = [len(item.get("question", "").split()) for item in synthetic if item.get("question")]
    real_lengths = [len(item.get("question", "").split()) for item in real if item.get("question")]
    
    if not syn_lengths or not real_lengths:
        return {"error": "Insufficient data for length comparison"}
    
    syn_mean = mean(syn_lengths)
    real_mean = mean(real_lengths)
    syn_std = stdev(syn_lengths) if len(syn_lengths) > 1 else 0
    real_std = stdev(real_lengths) if len(real_lengths) > 1 else 0
    
    return {
        "synthetic_mean": round(syn_mean, 2),
        "real_mean": round(real_mean, 2),
        "mean_difference": round(abs(syn_mean - real_mean), 2),
        "synthetic_std": round(syn_std, 2),
        "real_std": round(real_std, 2),
        "std_difference": round(abs(syn_std - real_std), 2)
    }

def compare_answer_balance(synthetic: List[Dict], real: List[Dict]) -> Dict:
    """Compare answer distribution balance between synthetic and real data"""
    syn_answers = Counter(item.get("answer", "").strip() for item in synthetic if item.get("answer"))
    real_answers = Counter(item.get("answer", "").strip() for item in real if item.get("answer"))
    
    # Calculate distributions
    syn_total = sum(syn_answers.values())
    real_total = sum(real_answers.values())
    
    if syn_total == 0 or real_total == 0:
        return {"error": "Insufficient answer data for comparison"}
    
    syn_dist = {k: v/syn_total for k, v in syn_answers.items()}
    real_dist = {k: v/real_total for k, v in real_answers.items()}
    
    # Calculate L1 distance
    all_letters = set(list(syn_dist.keys()) + list(real_dist.keys()))
    l1_distance = sum(abs(syn_dist.get(letter, 0) - real_dist.get(letter, 0)) for letter in all_letters)
    
    return {
        "synthetic_distribution": dict(syn_dist),
        "real_distribution": dict(real_dist),
        "l1_distance": round(l1_distance, 4),
        "balance_quality": "good" if l1_distance < 0.1 else "needs_improvement"
    }

def calculate_vocabulary_overlap(synthetic: List[Dict], real: List[Dict]) -> Dict:
    """Calculate vocabulary overlap between synthetic and real data"""
    syn_words = set()
    real_words = set()
    
    for item in synthetic:
        if item.get("question"):
            syn_words.update(item["question"].split())
    
    for item in real:
        if item.get("question"):
            real_words.update(item["question"].split())
    
    if not syn_words or not real_words:
        return {"error": "Insufficient vocabulary data"}
    
    overlap = len(syn_words.intersection(real_words))
    union = len(syn_words.union(real_words))
    jaccard = overlap / union if union > 0 else 0
    
    return {
        "synthetic_vocab_size": len(syn_words),
        "real_vocab_size": len(real_words),
        "overlap_words": overlap,
        "jaccard_similarity": round(jaccard, 4),
        "vocabulary_diversity": round(len(syn_words) / len(real_words), 4) if real_words else 0
    }

def main(input_file=None, real_data_file=None, report_json=None, flag_csv=None, arabic_ratio=0.90, min_len=10, max_len=600, dup_shingle=5, dup_jaccard=0.90, sample_flags=200, include_comparison=False):
    if input_file:
        # Called programmatically
        class Args:
            def __init__(self):
                self.input = input_file or "outputs/exams_raw.jsonl"
                self.real_data_file = real_data_file
                self.report_json = report_json or "outputs/quality_report.json"
                self.flag_csv = flag_csv or "outputs/flagged_samples.csv"
                self.arabic_ratio = arabic_ratio
                self.min_len = min_len
                self.max_len = max_len
                self.dup_shingle = dup_shingle
                self.dup_jaccard = dup_jaccard
                self.sample_flags = sample_flags
                self.include_comparison = include_comparison
        args = Args()
    else:
        # Called from command line
        ap = argparse.ArgumentParser(description="Run comprehensive quality checks on generated data")
        ap.add_argument("--input-file", default="outputs/exams_raw.jsonl", help="Input generated data file")
        ap.add_argument("--real-data-file", help="Real data file for comparison (optional)")
        ap.add_argument("--report-json", default="outputs/quality_report.json", help="Quality report output")
        ap.add_argument("--flag-csv", default="outputs/flagged_samples.csv", help="Flagged samples output")
        ap.add_argument("--arabic-ratio", type=float, default=0.90, help="Minimum Arabic character ratio")
        ap.add_argument("--min-len", type=int, default=10, help="Minimum question length")
        ap.add_argument("--max-len", type=int, default=600, help="Maximum question length")
        ap.add_argument("--dup-shingle", type=int, default=5, help="N-gram size for duplicate detection")
        ap.add_argument("--dup-jaccard", type=float, default=0.90, help="Jaccard similarity threshold")
        ap.add_argument("--sample-flags", type=int, default=200, help="Maximum flagged samples to export")
        ap.add_argument("--include-comparison", action="store_true", help="Include comparison with real data")
        args = ap.parse_args()
        
        # Convert hyphens to underscores for compatibility
        args.input = args.input_file
        args.report_json = args.report_json
        args.flag_csv = args.flag_csv
        args.arabic_ratio = args.arabic_ratio
        args.min_len = args.min_len
        args.max_len = args.max_len
        args.dup_shingle = args.dup_shingle
        args.dup_jaccard = args.dup_jaccard
        args.sample_flags = args.sample_flags

    if not os.path.exists(args.input):
        print(f"[ERROR] 输入文件不存在：{args.input}")
        return

    total = 0
    bad_schema = 0
    bad_answer = 0
    low_ar = 0
    too_short = 0
    too_long  = 0
    parse_err = 0

    persona_ctr = Counter()
    questions: List[str] = []
    flagged_rows: List[Dict[str, Any]] = []

    # 为重复检测准备
    sig_buckets: Dict[str, List[Tuple[int, set, str]]] = defaultdict(list)

    for rec in read_jsonl(args.input):
        total += 1
        if rec.get("_parse_error"):
            parse_err += 1
            flagged_rows.append({"idx": rec["_idx"], "issue": "json_parse_error", "preview": ""})
            continue

        syn = rec.get("synthetic") or {}
        q = normalize(syn.get("question"))
        ans = normalize(syn.get("answer"))
        opts = syn.get("options")
        persona = rec.get("persona")
        if persona: 
            persona_ctr[persona] += 1

        # 基础结构检查
        schema_ok = True
        if not q or not ans:
            bad_schema += 1
            schema_ok = False
            flagged_rows.append({"idx": rec["_idx"], "issue": "missing_question_or_answer", "preview": q[:120]})
        if opts is not None and not isinstance(opts, list):
            bad_schema += 1
            schema_ok = False
            flagged_rows.append({"idx": rec["_idx"], "issue": "options_not_list", "preview": q[:120]})

        # 答案是否在选项内（仅当有选项时）
        if schema_ok and isinstance(opts, list):
            norm_opts = [normalize(x) for x in opts]
            if normalize(ans) not in norm_opts:
                bad_answer += 1
                flagged_rows.append({"idx": rec["_idx"], "issue": "answer_not_in_options", "preview": q[:120]})

        # 阿语比例
        if q:
            ratio = ar_ratio(q)
            if ratio < args.arabic_ratio:
                low_ar += 1
                flagged_rows.append({"idx": rec["_idx"], "issue": f"low_arabic_ratio({ratio:.2f})", "preview": q[:120]})

        # 长度边界
        qlen = len(q)
        if qlen and qlen < args.min_len:
            too_short += 1
            flagged_rows.append({"idx": rec["_idx"], "issue": f"too_short({qlen})", "preview": q[:120]})
        if qlen and qlen > args.max_len:
            too_long += 1
            flagged_rows.append({"idx": rec["_idx"], "issue": f"too_long({qlen})", "preview": q[:120]})

        # 用于多样性指标
        questions.append(q)

        # 近重复预聚类（粗指纹）
        if q:
            sh = shingles(q, n=args.dup_shingle)
            # 截断部分 shingles 以降内存
            head = "|".join(sorted(list(sh))[:200])
            sig = hashlib.md5(head.encode("utf-8")).hexdigest()
            sig_buckets[sig].append((rec["_idx"], sh, q))

    # 近重复复核：在每个桶内做 pairwise Jaccard，超过阈值的放到同一簇
    dup_clusters: List[List[int]] = []
    visited = set()
    for bucket in sig_buckets.values():
        m = len(bucket)
        if m < 2: 
            continue
        # 简单的贪心聚类
        for i in range(m):
            idx_i = bucket[i][0]
            if idx_i in visited: 
                continue
            cluster = [idx_i]
            visited.add(idx_i)
            for j in range(i+1, m):
                idx_j = bucket[j][0]
                if idx_j in visited: 
                    continue
                jac = jaccard(bucket[i][1], bucket[j][1])
                if jac >= args.dup_jaccard:
                    cluster.append(idx_j)
                    visited.add(idx_j)
            if len(cluster) > 1:
                dup_clusters.append(sorted(cluster))

    # 多样性指标
    d2 = distinct_n(questions, n=2)
    d3 = distinct_n(questions, n=3)

    # persona 覆盖与均衡
    persona_count = len(persona_ctr)
    per_vals = list(persona_ctr.values())
    per_mean = (sum(per_vals)/persona_count) if persona_count else 0.0
    per_std = math.sqrt(sum((x - per_mean)**2 for x in per_vals)/persona_count) if persona_count else 0.0

    # 汇总报告
    report = {
        "total": total,
        "parse_errors": parse_err,
        "bad_schema": bad_schema,
        "answer_not_in_options": bad_answer,
        "low_arabic_ratio(<={})".format(args.arabic_ratio): low_ar,
        "too_short(<={})".format(args.min_len): too_short,
        "too_long(>={})".format(args.max_len): too_long,
        "dup_clusters": len(dup_clusters),
        "dup_cluster_examples": [c[:5] for c in dup_clusters[:5]],  # 只给几个索引示例
        "diversity": {
            "distinct2": round(d2, 4),
            "distinct3": round(d3, 4),
        },
        "persona_stats": {
            "unique_personas": persona_count,
            "mean_per_persona": round(per_mean, 2),
            "std_per_persona": round(per_std, 2),
            "top5_personas": persona_ctr.most_common(5),
        },
        "config": {
            "arabic_ratio": args.arabic_ratio,
            "min_len": args.min_len,
            "max_len": args.max_len,
            "dup_shingle": args.dup_shingle,
            "dup_jaccard": args.dup_jaccard,
        }
    }

    # Add comparison with real data if provided
    if hasattr(args, 'real_data_file') and args.real_data_file and os.path.exists(args.real_data_file):
        try:
            # Load real data
            real_data = []
            with open(args.real_data_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        real_data.append(json.loads(line))
            
            # Load synthetic data (extract from personas structure)
            synthetic_data = []
            for rec in read_jsonl(args.input):
                if rec.get("synthetic"):
                    synthetic_data.append(rec["synthetic"])
                elif rec.get("question"):  # Direct exam format
                    synthetic_data.append(rec)
            
            comparison_results = compare_with_real_data(synthetic_data, real_data)
            report["comparison_with_real"] = comparison_results
            print(f"[INFO] Added comparison with real data from {args.real_data_file}")
        except Exception as e:
            report["comparison_error"] = str(e)
            print(f"[WARN] Failed to compare with real data: {e}")

    os.makedirs(os.path.dirname(args.report_json), exist_ok=True)
    with open(args.report_json, "w", encoding="utf-8") as w:
        json.dump(report, w, ensure_ascii=False, indent=2)

    # 问题样本（去重后留前 N 条）
    seen = set()
    unique_flags = []
    for r in flagged_rows:
        key = (r["idx"], r["issue"])
        if key in seen:
            continue
        seen.add(key)
        unique_flags.append(r)
    unique_flags = unique_flags[:args.sample_flags]

    os.makedirs(os.path.dirname(args.flag_csv), exist_ok=True)
    with open(args.flag_csv, "w", encoding="utf-8", newline="") as fcsv:
        writer = csv.DictWriter(fcsv, fieldnames=["idx", "issue", "preview"])
        writer.writeheader()
        for r in unique_flags:
            writer.writerow(r)

    print(f"[DONE] 质量报告 → {args.report_json}")
    print(f"[DONE] 问题样本（前 {len(unique_flags)} 条）→ {args.flag_csv}")

if __name__ == "__main__":
    main()
