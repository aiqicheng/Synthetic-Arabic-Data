import json
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

# Auto-load .env from project root when CLI starts
load_dotenv()

from arabic_synth.generators.run import run_generation
from arabic_synth.postprocess.clean import run_cleaning
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


# Note: evaluate functionality has been merged into quality_check command
# Use: arabic-synth quality-check --real-data-file path/to/real/data.jsonl --include-comparison


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
    from arabic_synth.data_prep.exam_processor import convert_csv_main as convert_main
    
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
    real_data_file: Optional[Path] = typer.Option(None, help="Real data file for comparison (optional)"),
    report_json: Path = typer.Option(Path("outputs/quality_report.json"), help="Quality report output"),
    flag_csv: Path = typer.Option(Path("outputs/flagged_samples.csv"), help="Flagged samples output"),
    arabic_ratio: float = typer.Option(0.90, help="Minimum Arabic character ratio"),
    min_len: int = typer.Option(10, help="Minimum question length"),
    max_len: int = typer.Option(600, help="Maximum question length"),
    include_comparison: bool = typer.Option(False, help="Include comparison with real data"),
):
    """Run comprehensive quality checks with optional real data comparison"""
    from arabic_synth.quality.quality_check import main as quality_main
    
    quality_main(
        input_file=str(input_file),
        real_data_file=str(real_data_file) if real_data_file else None,
        report_json=str(report_json),
        flag_csv=str(flag_csv),
        arabic_ratio=arabic_ratio,
        min_len=min_len,
        max_len=max_len,
        include_comparison=include_comparison
    )
    
    comparison_msg = f" with real data comparison" if real_data_file else ""
    typer.echo(f"Quality check complete{comparison_msg}. Report: {report_json}, Flags: {flag_csv}")


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


@app.command()
def sample_uniform(
    input_file: Path = typer.Option(Path("data/test-00000-of-00001.arabic.csv"), help="Input CSV exam file"),
    output_file: Path = typer.Option(Path("outputs/exams_uniform.csv"), help="Output CSV file"),
    n: int = typer.Option(10, help="Number of samples to extract"),
    seed: Optional[int] = typer.Option(None, help="Random seed for reproducibility"),
):
    """Sample exam data uniformly (random sampling)"""
    from arabic_synth.data_prep.exam_processor import sample_uniform_main
    
    count = sample_uniform_main(
        input_file=str(input_file),
        output_file=str(output_file),
        n=n,
        seed=seed
    )
    typer.echo(f"Uniform sampling complete: {count} samples → {output_file}")


@app.command()
def sample_stratified(
    input_file: Path = typer.Option(Path("data/test-00000-of-00001.arabic.csv"), help="Input CSV exam file"),
    output_file: Path = typer.Option(Path("outputs/exams_stratified.csv"), help="Output CSV file"),
    n: int = typer.Option(20, help="Number of samples to extract"),
    stratify_col: str = typer.Option("subject", help="Column to stratify by (subject, grade, language)"),
    seed: Optional[int] = typer.Option(None, help="Random seed for reproducibility"),
):
    """Sample exam data with stratification (balanced by category)"""
    from arabic_synth.data_prep.exam_processor import sample_stratified_main
    
    count = sample_stratified_main(
        input_file=str(input_file),
        output_file=str(output_file),
        n=n,
        stratify_col=stratify_col,
        seed=seed
    )
    typer.echo(f"Stratified sampling complete: {count} samples by '{stratify_col}' → {output_file}")


@app.command()
def sample_and_convert(
    input_file: Path = typer.Option(Path("data/test-00000-of-00001.arabic.csv"), help="Input CSV exam file"),
    output_file: Path = typer.Option(Path("outputs/exams_sampled.jsonl"), help="Output JSONL file"),
    n: int = typer.Option(10, help="Number of samples to extract"),
    mode: str = typer.Option("uniform", help="Sampling mode: uniform or stratified"),
    stratify_col: str = typer.Option("subject", help="Column to stratify by (subject, grade, language) - only for stratified mode"),
    seed: Optional[int] = typer.Option(None, help="Random seed for reproducibility"),
):
    """Sample exam data and convert to JSONL format in one step"""
    from arabic_synth.data_prep.exam_processor import ExamProcessor
    
    if mode not in ["uniform", "stratified"]:
        typer.echo("Error: mode must be 'uniform' or 'stratified'", err=True)
        raise typer.Exit(1)
    
    try:
        processor = ExamProcessor(str(input_file))
        stats = processor.sample_and_convert(
            n=n,
            mode=mode,
            stratify_col=stratify_col,
            output_jsonl=str(output_file),
            seed=seed
        )
        
        typer.echo(f"✅ Sample and convert complete:")
        typer.echo(f"  Mode: {stats['sampling_mode']}")
        typer.echo(f"  Requested: {stats['samples_requested']} samples")
        typer.echo(f"  Success: {stats['success']} | Skipped: {stats['skipped']}")
        typer.echo(f"  Output: {stats['output_file']}")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def style_persona_workflow(
    input_csv: Path = typer.Option(Path("data/test-00000-of-00001.arabic.csv"), help="Input CSV exam file"),
    personas_path: Path = typer.Option(Path("data/personas/selected_200.jsonl"), help="Path to personas JSONL"),
    output_dir: Path = typer.Option(Path("outputs/style_persona"), help="Output directory for workflow results"),
    n_seeds: int = typer.Option(20, help="Number of seed samples to extract"),
    n_styled: int = typer.Option(100, help="Number of styled questions to generate"),
    sampling_mode: str = typer.Option("stratified", help="Sampling mode: uniform or stratified"),
    stratify_col: str = typer.Option("subject", help="Column to stratify by"),
    per_item_personas: int = typer.Option(5, help="Number of personas per styled item"),
    model: str = typer.Option("openai:gpt-4o", help="Model for generation"),
    seed: Optional[int] = typer.Option(42, help="Random seed for reproducibility"),
):
    """Complete style-guide + persona workflow: sample → style → personas → combine"""
    from arabic_synth.data_prep.exam_processor import ExamProcessor
    from arabic_synth.generators.run import run_generation
    from arabic_synth.persona.build_requests import main as build_persona_requests
    from pathlib import Path
    import json
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    typer.echo("🚀 Starting Combined Style-Persona Workflow...")
    
    try:
        # Step 1: Sample from original CSV → seeds.jsonl
        typer.echo(f"\n📊 Step 1: Sampling {n_seeds} seeds from {input_csv}")
        processor = ExamProcessor(str(input_csv))
        seeds_path = output_dir / "seeds.jsonl"
        
        stats = processor.sample_and_convert(
            n=n_seeds,
            mode=sampling_mode,
            stratify_col=stratify_col,
            output_jsonl=str(seeds_path),
            seed=seed
        )
        typer.echo(f"✅ Seeds created: {stats['success']} samples → {seeds_path}")
        
        # Step 2: Generate styled seeds using style guide
        typer.echo(f"\n🎨 Step 2: Generating {n_styled} styled questions using seeds as style guide")
        styled_seeds_path = output_dir / "styled_seeds.jsonl"
        
        styled_results = run_generation(
            task="exams",
            num_samples=n_styled,
            model=model,
            batch_size=50,
            persona_override=None,
            seed_path=seeds_path,  # Use seeds as style guidance
            temperature=0.7,
            top_p=0.95
        )
        
        # Save styled results
        with styled_seeds_path.open("w", encoding="utf-8") as f:
            for item in styled_results:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        typer.echo(f"✅ Styled seeds created: {len(styled_results)} samples → {styled_seeds_path}")
        
        # Step 3: Verify personas exist
        typer.echo(f"\n👥 Step 3: Verifying personas at {personas_path}")
        if not personas_path.exists():
            typer.echo(f"❌ Error: Personas file not found at {personas_path}", err=True)
            raise typer.Exit(1)
        typer.echo(f"✅ Personas file found: {personas_path}")
        
        # Step 4: Combine personas with styled seeds
        typer.echo(f"\n🔄 Step 4: Combining personas with styled seeds")
        combined_requests_path = output_dir / "combined_requests.jsonl"
        
        n_requests = build_persona_requests(
            exams_path=str(styled_seeds_path),
            personas_path=str(personas_path),
            output_path=str(combined_requests_path),
            per_item_personas=per_item_personas,
            target_total=len(styled_results) * per_item_personas,
            seed=seed
        )
        typer.echo(f"✅ Combined requests created: {n_requests} requests → {combined_requests_path}")
        
        # Summary
        typer.echo(f"\n🎉 Workflow Complete! Results in {output_dir}:")
        typer.echo(f"  📊 Seeds: {seeds_path} ({stats['success']} samples)")
        typer.echo(f"  🎨 Styled Seeds: {styled_seeds_path} ({len(styled_results)} samples)")
        typer.echo(f"  👥 Personas: {personas_path}")
        typer.echo(f"  🔄 Combined Requests: {combined_requests_path} ({n_requests} requests)")
        
        # Create summary file
        summary = {
            "workflow": "style-persona-combined",
            "input_csv": str(input_csv),
            "sampling_mode": sampling_mode,
            "n_seeds": n_seeds,
            "n_styled": n_styled,
            "per_item_personas": per_item_personas,
            "model": model,
            "seed": seed,
            "results": {
                "seeds_file": str(seeds_path),
                "seeds_count": stats['success'],
                "styled_seeds_file": str(styled_seeds_path),
                "styled_count": len(styled_results),
                "personas_file": str(personas_path),
                "combined_requests_file": str(combined_requests_path),
                "total_requests": n_requests
            }
        }
        
        summary_path = output_dir / "workflow_summary.json"
        with summary_path.open("w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        typer.echo(f"  📋 Summary: {summary_path}")
        
    except Exception as e:
        typer.echo(f"❌ Error in workflow: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app() 