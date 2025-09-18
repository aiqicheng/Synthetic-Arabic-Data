import json
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

# Auto-load .env from project root when CLI starts
load_dotenv()

from arabic_synth.generators.run import run_generation
from arabic_synth.postprocess.clean import run_cleaning
from arabic_synth.evaluate.evaluate import run_evaluation
from arabic_synth.utils.io import export_dataset
from arabic_synth.augment.augment import run_augmentation

app = typer.Typer(add_completion=False)


@app.command()
def generate(
    task: str = typer.Argument(..., help="Task: exams|sentiment|grammar"),
    num_samples: int = typer.Option(100, help="Number of samples to generate"),
    model: str = typer.Option("mock", help="Model name; use 'openai:MODEL' to call OpenAI"),
    batch_size: int = typer.Option(50, help="Batch size for generation"),
    persona: Optional[str] = typer.Option(None, help="Override persona role if needed"),
    seed_file: Optional[Path] = typer.Option(None, help="Optional seed examples JSONL"),
    temperature: float = typer.Option(0.7, help="Sampling temperature"),
    top_p: float = typer.Option(0.95, help="Top-p nucleus sampling"),
):
    dataset = run_generation(task=task, num_samples=num_samples, model=model, batch_size=batch_size, persona_override=persona, seed_path=seed_file, temperature=temperature, top_p=top_p)
    out_dir = Path("outputs")
    out_path = out_dir / f"{task}_raw.jsonl"
    out_dir.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    typer.echo(f"Wrote raw data to {out_path}")


@app.command()
def augment(
    task: str = typer.Argument(..., help="Task: exams|sentiment|grammar"),
    in_path: Path = typer.Option(Path("outputs/raw.jsonl"), help="Input JSONL path"),
    out_path: Path = typer.Option(Path("outputs/augmented.jsonl"), help="Output augmented JSONL path"),
    num_variants: int = typer.Option(2, help="Number of variants per item"),
):
    augmented = run_augmentation(task=task, in_path=in_path, num_variants=num_variants)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for item in augmented:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    typer.echo(f"Wrote augmented data to {out_path}")


@app.command()
def clean(
    task: str = typer.Argument(..., help="Task: exams|sentiment|grammar"),
    in_path: Path = typer.Option(Path("outputs/raw.jsonl"), help="Input JSONL path"),
    out_path: Path = typer.Option(Path("outputs/clean.jsonl"), help="Output cleaned JSONL path"),
):
    cleaned = run_cleaning(task=task, in_path=in_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for item in cleaned:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    typer.echo(f"Wrote cleaned data to {out_path}")


@app.command()
def evaluate(
    task: str = typer.Argument(..., help="Task: exams|sentiment|grammar"),
    in_path: Path = typer.Option(Path("outputs/clean.jsonl"), help="Input JSONL path"),
):
    report = run_evaluation(task=task, in_path=in_path)
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2))


@app.command()
def export(
    task: str = typer.Argument(..., help="Task: exams|sentiment|grammar"),
    in_path: Path = typer.Option(Path("outputs/clean.jsonl"), help="Input JSONL path"),
    out_format: str = typer.Option("jsonl", help="jsonl|csv"),
    meta_task_name: Optional[str] = typer.Option(None),
    meta_persona: Optional[str] = typer.Option(None),
    meta_batch_id: Optional[str] = typer.Option(None),
    out_dir: Path = typer.Option(Path("outputs")),
):
    export_dataset(task=task, in_path=in_path, out_format=out_format, out_dir=out_dir, meta_task_name=meta_task_name or task, meta_persona=meta_persona, meta_batch_id=meta_batch_id)


@app.command()
def convert_csv(
    input_file: Path = typer.Option(Path("data/test-00000-of-00001.arabic.csv"), help="Input CSV file path"),
    output_file: Path = typer.Option(Path("data/exams.jsonl"), help="Output JSONL file path"),
):
    """Convert CSV exam data to JSONL format"""
    from arabic_synth.data_prep.convert_csv import main as convert_main
    
    convert_main(input_csv=str(input_file), output_jsonl=str(output_file))
    typer.echo(f"Converted CSV data from {input_file} to {output_file}")


@app.command()
def build_persona_requests(
    exams_path: Path = typer.Option(Path("data/exams.jsonl"), help="Path to exam data JSONL"),
    personas_path: Path = typer.Option(Path("data/personas/selected_200.jsonl"), help="Path to personas JSONL"),
    output_path: Path = typer.Option(Path("outputs/requests_persona_exams.jsonl"), help="Output requests path"),
    per_item_personas: int = typer.Option(20, help="Number of personas per exam item"),
    target_total: int = typer.Option(11000, help="Target total requests"),
    seed: int = typer.Option(123, help="Random seed"),
):
    """Build persona-augmented requests for LLM generation"""
    from arabic_synth.persona.build_requests import main as build_requests
    
    n = build_requests(
        exams_path=str(exams_path),
        personas_path=str(personas_path),
        output_path=str(output_path),
        per_item_personas=per_item_personas,
        target_total=target_total,
        seed=seed
    )
    typer.echo(f"Built {n} persona-augmented requests → {output_path}")


@app.command()
def send_persona_requests(
    input_file: Path = typer.Option(Path("outputs/requests_persona_exams.jsonl"), help="Input requests file"),
    output_file: Path = typer.Option(Path("outputs/exams_raw.jsonl"), help="Output generated data file"),
    error_file: Path = typer.Option(Path("outputs/exams_errors.jsonl"), help="Output error log file"),
    model: str = typer.Option("gpt-4o", help="OpenAI model to use"),
):
    """Send persona-augmented requests to OpenAI API"""
    from arabic_synth.persona.send_requests import main as send_requests
    
    send_requests(
        input_file=str(input_file),
        output_file=str(output_file),
        error_file=str(error_file),
        model=model
    )
    typer.echo(f"Sent requests and saved results to {output_file}")


@app.command()
def quality_check(
    input_file: Path = typer.Option(Path("outputs/exams_raw.jsonl"), help="Input generated data file"),
    report_json: Path = typer.Option(Path("outputs/quality_report.json"), help="Quality report output"),
    flag_csv: Path = typer.Option(Path("outputs/flagged_samples.csv"), help="Flagged samples output"),
    arabic_ratio: float = typer.Option(0.90, help="Minimum Arabic character ratio"),
    min_len: int = typer.Option(10, help="Minimum question length"),
    max_len: int = typer.Option(600, help="Maximum question length"),
):
    """Run comprehensive quality checks on generated data"""
    from arabic_synth.quality.quality_check import main as quality_main
    
    quality_main(
        input_file=str(input_file),
        report_json=str(report_json),
        flag_csv=str(flag_csv),
        arabic_ratio=arabic_ratio,
        min_len=min_len,
        max_len=max_len
    )
    typer.echo(f"Quality check complete. Report: {report_json}, Flags: {flag_csv}")


@app.command()
def select_personas(
    input_file: Path = typer.Option(Path("data/personas/personas_all.jsonl"), help="Input personas file"),
    output_file: Path = typer.Option(Path("data/personas/selected_200.jsonl"), help="Output selected personas"),
    n: int = typer.Option(200, help="Number of personas to select"),
    seed: int = typer.Option(42, help="Random seed"),
):
    """Select and filter personas from a larger collection"""
    from arabic_synth.data_prep.personas_select import main as personas_select
    
    personas_select(
        input_file=str(input_file),
        output_file=str(output_file),
        n=n,
        seed=seed
    )
    typer.echo(f"Selected {n} personas from {input_file} → {output_file}")


if __name__ == "__main__":
    app() 