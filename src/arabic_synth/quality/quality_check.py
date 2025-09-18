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
from typing import List, Dict, Any, Tuple, Iterable

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

def main(input_file=None, report_json=None, flag_csv=None, arabic_ratio=0.90, min_len=10, max_len=600, dup_shingle=5, dup_jaccard=0.90, sample_flags=200):
    if input_file:
        # Called programmatically
        class Args:
            def __init__(self):
                self.input = input_file or "outputs/exams_raw.jsonl"
                self.report_json = report_json or "outputs/quality_report.json"
                self.flag_csv = flag_csv or "outputs/flagged_samples.csv"
                self.arabic_ratio = arabic_ratio
                self.min_len = min_len
                self.max_len = max_len
                self.dup_shingle = dup_shingle
                self.dup_jaccard = dup_jaccard
                self.sample_flags = sample_flags
        args = Args()
    else:
        # Called from command line
        ap = argparse.ArgumentParser(description="Run comprehensive quality checks on generated data")
        ap.add_argument("--input-file", default="outputs/exams_raw.jsonl", help="Input generated data file")
        ap.add_argument("--report-json", default="outputs/quality_report.json", help="Quality report output")
        ap.add_argument("--flag-csv", default="outputs/flagged_samples.csv", help="Flagged samples output")
        ap.add_argument("--arabic-ratio", type=float, default=0.90, help="Minimum Arabic character ratio")
        ap.add_argument("--min-len", type=int, default=10, help="Minimum question length")
        ap.add_argument("--max-len", type=int, default=600, help="Maximum question length")
        ap.add_argument("--dup-shingle", type=int, default=5, help="N-gram size for duplicate detection")
        ap.add_argument("--dup-jaccard", type=float, default=0.90, help="Jaccard similarity threshold")
        ap.add_argument("--sample-flags", type=int, default=200, help="Maximum flagged samples to export")
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
