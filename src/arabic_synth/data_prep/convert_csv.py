# -*- coding: utf-8 -*-
# 用途：把你的 CSV 行（含 python 字典字符串 + numpy array 字样）转换为 JSONL
# 输出字段：question, options, answer, explanation（如果没有解析则为空字符串）

import csv, json, re, ast, sys, os, argparse

# 将 "array([...], dtype=object)" → "[...]"；支持跨行/有换行空格
ARRAY_RE = re.compile(r"array\(\s*(\[[\s\S]*?\])\s*(?:,\s*dtype=object)?\s*\)")

def strip_numpy_array(s: str) -> str:
    # 多次替换直到没有 array(...) 为止（嵌套时也能处理）
    prev = None
    while prev != s:
        prev = s
        s = ARRAY_RE.sub(r"\1", s)
    return s

def safe_parse_py_literal(s: str):
    """
    将单引号的 Python 字典字符串 -> Python 对象。
    在此之前会先把 numpy 风格的 array(...) 抹掉。
    """
    s = strip_numpy_array(s.strip())
    # ast.literal_eval 只能识别标准 Python 字面量（dict/list/str/num/...）
    return ast.literal_eval(s)

def main(input_csv=None, output_jsonl=None):
    # Use command line arguments or defaults
    in_csv = input_csv or "data/test-00000-of-00001.arabic.csv"
    out_jsonl = output_jsonl or "data/exams.jsonl"
    
    os.makedirs(os.path.dirname(out_jsonl), exist_ok=True)
    n_in, n_ok, n_skip = 0, 0, 0
    with open(in_csv, newline="", encoding="utf-8") as fin, \
         open(out_jsonl, "w", encoding="utf-8") as fout:
        reader = csv.reader(fin)
        # 如果有表头可改用 DictReader；此处按你示例的 4 列处理：
        # 0:id, 1:question_blob, 2:answer_label, 3:meta_blob
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
                q_obj = safe_parse_py_literal(q_blob)  # {'stem': '…', 'choices': {'text': [...], 'label': [...]} }
            except Exception as e:
                # 解析失败就跳过该行
                n_skip += 1
                continue

            stem = (q_obj.get("stem") or q_obj.get("question") or "").strip()
            ch = q_obj.get("choices") or {}
            texts = ch.get("text") or []
            labels = ch.get("label") or []

            # 规范化成 list[str]
            if not isinstance(texts, list) or not isinstance(labels, list):
                n_skip += 1
                continue
            # 去除空串
            options = [str(x).strip() for x in texts if str(x).strip() != ""]
            labels = [str(x).strip() for x in labels]

            # 映射字母答案 → 选项文本
            answer_text = None
            if ans_label in labels and labels.index(ans_label) < len(options):
                answer_text = options[labels.index(ans_label)]
            else:
                # 容忍大小写差异
                low = [l.lower() for l in labels]
                if ans_label.lower() in low:
                    idx = low.index(ans_label.lower())
                    if idx < len(options):
                        answer_text = options[idx]

            # 解析 meta（可选）
            explanation = ""
            if meta_blob:
                try:
                    meta = safe_parse_py_literal(meta_blob)
                    # 如果原始里有解释字段，可以按需获取
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

    print(f"[DONE] 输入行: {n_in} | 成功: {n_ok} | 跳过: {n_skip} → {out_jsonl}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert CSV exam data to JSONL format")
    parser.add_argument("--input-csv", default="data/test-00000-of-00001.arabic.csv", 
                       help="Input CSV file path")
    parser.add_argument("--output-jsonl", default="data/exams.jsonl", 
                       help="Output JSONL file path")
    args = parser.parse_args()
    
    main(input_csv=args.input_csv, output_jsonl=args.output_jsonl)
