# send_persona_requests.py  (verbose版)
# 依赖：pip install --upgrade openai
import os, json, time, random, sys, argparse
from pathlib import Path

SLEEP_BETWEEN = (0.01, 0.05)
MAX_RETRIES   = 5
BACKOFF_BASE  = 1.5

def read_requests(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line:
                continue
            yield json.loads(line)

def ensure_json_object(text):
    try:
        return json.loads(text)
    except Exception:
        try:
            s = text.find("{")
            e = text.rfind("}")
            if s != -1 and e != -1 and e > s:
                return json.loads(text[s:e+1])
        except Exception:
            pass
    return {"raw_text": text}

def call_openai(prompt, model="gpt-4o", temperature=0.9, top_p=0.95):
    from openai import OpenAI
    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role":"user","content": prompt}],
        temperature=temperature, top_p=top_p,
        response_format={"type":"json_object"}
    )
    return resp.choices[0].message.content

def main(input_file=None, output_file=None, error_file=None, model="gpt-4o"):
    # Use provided arguments or defaults
    in_file = input_file or "outputs/requests_persona_exams.jsonl"
    out_file = output_file or "outputs/exams_raw.jsonl"
    err_file = error_file or "outputs/exams_errors.jsonl"
    
    print("[START] send_persona_requests.py 启动", flush=True)

    if not os.getenv("OPENAI_API_KEY"):
        print("[ERROR] 未检测到 OPENAI_API_KEY 环境变量。", file=sys.stderr, flush=True)
        sys.exit(1)

    if not os.path.exists(in_file):
        print(f"[ERROR] 输入文件不存在: {in_file}", file=sys.stderr, flush=True)
        sys.exit(1)

    # 统计将要处理多少条
    total = sum(1 for _ in open(in_file, "r", encoding="utf-8"))
    print(f"[INFO] 将要处理 {total} 条请求 ← {in_file}", flush=True)

    Path("outputs").mkdir(parents=True, exist_ok=True)
    ok, bad = 0, 0

    with open(out_file, "w", encoding="utf-8") as w_out, \
         open(err_file, "w", encoding="utf-8") as w_err:

        for i, req in enumerate(read_requests(in_file), 1):
            # 兼容两种结构：顶层 or meta
            prompt = req.get("prompt","")
            meta   = req.get("meta") or {}
            persona   = req.get("persona") or meta.get("persona")
            source_id = req.get("source_id") or meta.get("source_id")
            gen_cfg   = req.get("gen_config") or meta.get("gen_config") or {}
            temperature = float(gen_cfg.get("temperature", 0.9))
            top_p       = float(gen_cfg.get("top_p", 0.95))

            if not prompt:
                # 写错误并跳过
                w_err.write(json.dumps({"source_id": source_id, "persona": persona, "error": "empty prompt"}, ensure_ascii=False)+"\n")
                bad += 1
                if i % 50 == 0:
                    print(f"[INFO] 进度 {i}/{total} | ok={ok} bad={bad}", flush=True)
                continue

            # 简单速率控制
            time.sleep(random.uniform(*SLEEP_BETWEEN))

            retry = 0
            while True:
                try:
                    text = call_openai(prompt, model=model, temperature=temperature, top_p=top_p)
                    obj = ensure_json_object(text)
                    rec = {
                        "persona": persona,
                        "source_id": source_id,
                        "model": model,
                        "synthetic": obj
                    }
                    w_out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    ok += 1
                    break
                except Exception as e:
                    retry += 1
                    if retry > MAX_RETRIES:
                        w_err.write(json.dumps({
                            "persona": persona,
                            "source_id": source_id,
                            "error": str(e)
                        }, ensure_ascii=False) + "\n")
                        bad += 1
                        break
                    wait = BACKOFF_BASE ** retry
                    print(f"[WARN] 第{i}条失败，{retry}次重试后等待 {wait:.1f}s：{e}", flush=True)
                    time.sleep(wait)

            if i % 50 == 0 or i == total:
                print(f"[INFO] 进度 {i}/{total} | ok={ok} bad={bad}", flush=True)

    print(f"[DONE] 成功: {ok} | 失败: {bad} → {out_file}", flush=True)
    if bad > 0:
        print(f"[WARN] 失败样本已写入 {err_file}", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send persona-augmented requests to OpenAI API")
    parser.add_argument("--input-file", default="outputs/requests_persona_exams.jsonl", 
                       help="Input requests file")
    parser.add_argument("--output-file", default="outputs/exams_raw.jsonl", 
                       help="Output generated data file")
    parser.add_argument("--error-file", default="outputs/exams_errors.jsonl", 
                       help="Output error log file")
    parser.add_argument("--model", default="gpt-4o", 
                       help="OpenAI model to use")
    args = parser.parse_args()
    
    main(
        input_file=args.input_file,
        output_file=args.output_file,
        error_file=args.error_file,
        model=args.model
    )
