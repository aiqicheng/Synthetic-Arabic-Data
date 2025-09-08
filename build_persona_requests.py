from src.arabic_synth.generators.persona_augment import iter_requests, write_requests_jsonl

# 新添加的函数 功能是构造 persona-augmented 请求
reqs = iter_requests(
    exams_path="data/exams.jsonl",                # 原始考试题数据集路径
    personas_path="data/personas/selected_200.jsonl",  # 刚才生成的200 persona
    per_item_personas=20,                         # 每道题配3个人设
    target_total=11000,                          # 目标总数 = 10k 但是实际会比10k少 因此设定为11k
    seed=123
)

# 写出到 outputs
out_file = "outputs/requests_persona_exams.jsonl"
n = write_requests_jsonl(out_file, reqs)
print(f"[OK] 已写出 {n} 条请求 → {out_file}")
