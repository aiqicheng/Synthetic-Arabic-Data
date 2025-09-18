import argparse
from arabic_synth.generators.persona_augment import iter_requests, write_requests_jsonl

def main(exams_path=None, personas_path=None, output_path=None, per_item_personas=20, target_total=11000, seed=123):
    # Use provided arguments or defaults
    exams_path = exams_path or "data/exams.jsonl"
    personas_path = personas_path or "data/personas/selected_200.jsonl"
    output_path = output_path or "outputs/requests_persona_exams.jsonl"
    
    # Generate persona-augmented requests
    reqs = iter_requests(
        exams_path=exams_path,
        personas_path=personas_path,
        per_item_personas=per_item_personas,
        target_total=target_total,
        seed=seed
    )
    
    # Write requests to output file
    n = write_requests_jsonl(output_path, reqs)
    print(f"[OK] 已写出 {n} 条请求 → {output_path}")
    return n

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build persona-augmented requests for LLM generation")
    parser.add_argument("--exams-path", default="data/exams.jsonl", 
                       help="Path to exam data JSONL")
    parser.add_argument("--personas-path", default="data/personas/selected_200.jsonl", 
                       help="Path to personas JSONL")
    parser.add_argument("--output-path", default="outputs/requests_persona_exams.jsonl", 
                       help="Output requests path")
    parser.add_argument("--per-item-personas", type=int, default=20, 
                       help="Number of personas per exam item")
    parser.add_argument("--target-total", type=int, default=11000, 
                       help="Target total requests")
    parser.add_argument("--seed", type=int, default=123, 
                       help="Random seed")
    args = parser.parse_args()
    
    main(
        exams_path=args.exams_path,
        personas_path=args.personas_path,
        output_path=args.output_path,
        per_item_personas=args.per_item_personas,
        target_total=args.target_total,
        seed=args.seed
    )
