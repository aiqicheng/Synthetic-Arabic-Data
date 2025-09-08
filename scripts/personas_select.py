# -*- coding: utf-8 -*-
import json, random, re, argparse, os

def _read_personas(path: str):
    arr = []
    if path.endswith(".jsonl"):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    txt = obj.get("persona") or obj.get("text") or obj.get("description") or ""
                except json.JSONDecodeError:
                    txt = line
                if isinstance(txt, dict):
                    txt = txt.get("persona") or txt.get("text") or ""
                if txt:
                    arr.append(str(txt).strip())
    else:
        data = json.load(open(path, "r", encoding="utf-8"))
        if isinstance(data, list):
            for x in data:
                if isinstance(x, dict):
                    txt = x.get("persona") or x.get("text") or x.get("description") or ""
                else:
                    txt = str(x)
                if txt:
                    arr.append(str(txt).strip())
        else:
            txt = str(data)
            if txt:
                arr.append(txt)
    seen, out = set(), []
    for p in arr:
        norm = re.sub(r"\s+", " ", p).lower()
        if norm and norm not in seen:
            seen.add(norm)
            out.append(p)
    return out

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    random.seed(args.seed)

    personas = _read_personas(args.input)
    if len(personas) < args.n:
        raise ValueError(f"personas不足：{len(personas)} < {args.n}")
    selected = random.sample(personas, args.n)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as w:
        for p in selected:
            w.write(json.dumps({"persona": p}, ensure_ascii=False) + "\n")
    print(f"[OK] 写出 {args.n} 条 → {args.output}")

if __name__ == "__main__":
    main()