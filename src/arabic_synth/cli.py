import json
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

# Auto-load .env from project root when CLI starts
load_dotenv()

from arabic_synth.generators.run import run_generation
from arabic_synth.generators.batch_generation import run_batch_generation, BatchGenerationConfig
from arabic_synth.batch.enhanced_generator import EnhancedBatchGenerationProgram
from arabic_synth.postprocess.clean import run_cleaning
from arabic_synth.evaluate.evaluate_style import run_evaluation, run_evaluate_style
from arabic_synth.utils.io import export_dataset
from arabic_synth.augment.augment import run_augmentation

app = typer.Typer(add_completion=False)


@app.command()
def generate(
    task: str = typer.Argument(..., help="Task: exams|sentiment|grammar|mmlu|madinahqa"),
    num_samples: int = typer.Option(100, help="Number of samples to generate"),
    model: str = typer.Option("mock", help="Model name; use 'openai:MODEL' for OpenAI or 'openrouter:MODEL' for OpenRouter"),
    batch_size: int = typer.Option(50, help="Batch size for generation"),
    persona: Optional[str] = typer.Option(None, help="Override persona role if needed"),
    seed_file: Optional[Path] = typer.Option(None, help="Optional seed examples JSONL"),
    temperature: float = typer.Option(0.7, help="Sampling temperature"),
    top_p: float = typer.Option(0.95, help="Top-p nucleus sampling"),
    output_dir: Path = typer.Option(..., help="Output directory for generated data and intermediate files"),
    subject: Optional[str] = typer.Option(None, help="Optional subject for exams tasks (e.g., 'Islamic Studies', 'Mathematics', 'Physics')"),
    balanced_answers: bool = typer.Option(True, help="Use balanced answer distribution for multiple choice tasks"),
    use_batch: bool = typer.Option(False, help="Use batch processing (supports OpenAI and OpenRouter via llm_batch_helper)"),
    use_diversity: bool = typer.Option(True, help="Enable diversity features: sampling jitter, prompt variation, fast duplicate screening"),
    one_prompt_per_seed: bool = typer.Option(True, help="Use one-prompt-per-seed strategy: each seed generates exactly one prompt, avoiding seed rephrasing"),
):
    # Set up balanced answer distribution for multiple choice tasks
    target_answer_distribution = None
    if balanced_answers and task in ["exams", "mmlu", "madinahqa"]:
        target_answer_distribution = {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}
    
    # Check if batch mode is requested but model is not supported
    if use_batch and not (model.startswith("openai:") or model.startswith("openrouter:")):
        typer.echo("Warning: Batch mode only supports OpenAI and OpenRouter models. Falling back to regular generation.")
        use_batch = False
    
    # Use batch generation if requested
    if use_batch:
        typer.echo(f"Using batch generation mode with llm_batch_helper...")
        batch_config = BatchGenerationConfig(
            batch_size=batch_size,
            temperature=temperature,
            top_p=top_p,
            max_retries=3,
            delay_between_batches=1.0,
            timeout=30.0
        )
        dataset = run_batch_generation(
            task=task,
            num_samples=num_samples,
            model=model,
            batch_config=batch_config,
            persona_override=persona,
            seed_path=seed_file,
            output_dir=output_dir,
            target_answer_distribution=target_answer_distribution,
            subject=subject
        )
    else:
        # Use regular generation
        dataset = run_generation(
            task=task, 
            num_samples=num_samples, 
            model=model, 
            batch_size=batch_size, 
            persona_override=persona, 
            seed_path=seed_file, 
            output_dir=output_dir, 
            temperature=temperature, 
            top_p=top_p, 
            target_answer_distribution=target_answer_distribution,
            subject=subject,
            use_diversity=use_diversity,
            one_prompt_per_seed=one_prompt_per_seed
        )
    
    # Create output file with naming convention: generate_style_{num_samples}.jsonl
    output_file = output_dir / f"generate_style_{subject}_{num_samples}.jsonl"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with output_file.open("w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    typer.echo(f"Wrote raw data to {output_file}")


@app.command()
def generate_mmlu(
    num_samples: int = typer.Option(100, help="Number of samples to generate"),
    model: str = typer.Option("openai:gpt-4o", help="Model name; use 'openai:MODEL' for OpenAI or 'openrouter:MODEL' for OpenRouter"),
    seed_file: Path = typer.Option(..., help="Seed examples JSONL file"),
    output_dir: Path = typer.Option(..., help="Output directory for generated data and intermediate files"),
    subject: Optional[str] = typer.Option(None, help="Subject filter (e.g., 'Computer Science', 'Physics')"),
    temperature: float = typer.Option(0.7, help="Sampling temperature"),
    top_p: float = typer.Option(0.95, help="Top-p nucleus sampling"),
    balanced_answers: bool = typer.Option(True, help="Use balanced answer distribution (A=25%, B=25%, C=25%, D=25%)"),
    use_diversity: bool = typer.Option(True, help="Enable diversity features: sampling jitter, prompt variation, fast duplicate screening"),
    one_prompt_per_seed: bool = typer.Option(True, help="Use one-prompt-per-seed strategy: each seed generates exactly one prompt, avoiding seed rephrasing"),
):
    """Generate MMLU questions using one-prompt-per-seed strategy."""
    
    # Set up balanced answer distribution
    target_answer_distribution = None
    if balanced_answers:
        target_answer_distribution = {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}
    
    # Generate dataset
    dataset = run_generation(
        task="mmlu", 
        num_samples=num_samples, 
        model=model, 
        batch_size=50, 
        persona_override=None, 
        seed_path=seed_file, 
        output_dir=output_dir, 
        temperature=temperature, 
        top_p=top_p, 
        target_answer_distribution=target_answer_distribution,
        subject=subject,
        use_diversity=use_diversity,
        one_prompt_per_seed=one_prompt_per_seed
    )
    
    # Create output file with naming convention: generate_style_{subject}_{num_samples}.jsonl
    output_file = output_dir / f"generate_style_{subject or 'None'}_{num_samples}.jsonl"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with output_file.open("w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    typer.echo(f"Generated {len(dataset)} MMLU questions using one-prompt-per-seed strategy")
    typer.echo(f"Wrote data to {output_file}")
    
    # Print seed usage summary if available
    if dataset and "_seed_index" in dataset[0]:
        used_seeds = set(item["_seed_index"] for item in dataset)
        typer.echo(f"Used {len(used_seeds)} unique seeds out of {num_samples} requested samples")


@app.command()
def generate_enhanced_batch(
    input_file: Path = typer.Option(..., help="Path to Arabic MMLU CSV file"),
    output_dir: Path = typer.Option(..., help="Output directory for results"),
    model: str = typer.Option("openai:gpt-4o", help="LLM model to use"),
    sampling_mode: str = typer.Option("stratified", help="Seed sampling mode: stratified or uniform"),
    seeds_per_batch: int = typer.Option(20, help="Number of seeds per batch"),
    total_batches: int = typer.Option(5, help="Number of batches to run"),
    use_batch_helper: bool = typer.Option(True, help="Use llm-batch-helper for parallel processing"),
    max_concurrent_requests: int = typer.Option(10, help="Maximum concurrent requests for batch processing"),
    prioritize_diversity: bool = typer.Option(False, help="Prioritize full diversity per request over speed (uses sequential processing)"),
):
    """Generate MMLU questions using enhanced batch processing with llm-batch-helper.
    
    This command implements the one-prompt-per-seed strategy with parallel processing:
    - Samples seeds with varied random seeds (no fixed seed=42)
    - Uses llm-batch-helper for concurrent API calls (5-10x faster)
    - Produces clean output with strict A. B. C. D. formatting
    - Separates metadata from main output files
    - Supports multiple providers: OpenAI, OpenRouter, Together.ai, Google Gemini
    """
    
    # Validate input file exists
    if not input_file.exists():
        typer.echo(f"❌ Input file not found: {input_file}")
        raise typer.Exit(1)
    
    # Create and run the enhanced batch generation program
    program = EnhancedBatchGenerationProgram(
        input_file=input_file,
        output_dir=output_dir,
        model=model,
        sampling_mode=sampling_mode,
        seeds_per_batch=seeds_per_batch,
        total_batches=total_batches,
        use_batch_helper=use_batch_helper,
        max_concurrent_requests=max_concurrent_requests,
        prioritize_diversity=prioritize_diversity
    )
    
    try:
        program.run()
        typer.echo(f"\n✅ Enhanced batch generation completed successfully!")
        typer.echo(f"📁 Results saved to: {output_dir}")
        typer.echo(f"📊 Total items generated: {program.generation_stats['total_items_generated']}")
        typer.echo(f"⚡ Processing method: {'Parallel (llm-batch-helper)' if program.use_batch_helper else 'Sequential'}")
    except Exception as e:
        typer.echo(f"❌ Enhanced batch generation failed: {e}")
        raise typer.Exit(1)


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
    task: str = typer.Argument(..., help="Task: exams|sentiment|grammar|mmlu"),
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
def evaluate_style(
    task: str = typer.Argument(..., help="Task: exams|sentiment|grammar|mmlu"),
    in_path: Path = typer.Option(Path("outputs/clean.jsonl"), help="Input JSONL path"),
):
    """Style Guide Pipeline evaluation with enhanced reporting for style consistency."""
    report = run_evaluate_style(task=task, in_path=in_path)
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
def evaluate_persona(
    input_file: Path = typer.Option(Path("outputs/exams_raw.jsonl"), help="Input generated data file"),
    real_data_file: Optional[Path] = typer.Option(None, help="Real data file for comparison (optional)"),
    report_json: Path = typer.Option(Path("outputs/quality_report.json"), help="Quality report output"),
    flag_csv: Path = typer.Option(Path("outputs/flagged_samples.csv"), help="Flagged samples output"),
    arabic_ratio: float = typer.Option(0.90, help="Minimum Arabic character ratio"),
    min_len: int = typer.Option(10, help="Minimum question length"),
    max_len: int = typer.Option(600, help="Maximum question length"),
    include_comparison: bool = typer.Option(False, help="Include comparison with real data"),
):
    """Persona-augmented evaluation with comprehensive quality assessment and real data comparison"""
    from arabic_synth.evaluate.evaluate_persona import main as quality_main
    
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
    task: str = typer.Argument(..., help="Task: exams|mmlu|madinahqa"),
    input_file: Path = typer.Option(Path("data/test-00000-of-00001.arabic.csv"), help="Input CSV file"),
    output_file: Path = typer.Option(Path("outputs/data_sampled.jsonl"), help="Output JSONL file"),
    n: int = typer.Option(10, help="Number of samples to extract"),
    mode: str = typer.Option("uniform", help="Sampling mode: uniform or stratified"),
    stratify_col: Optional[str] = typer.Option(None, help="Column to stratify by - defaults: 'subject' for exams, 'Subject' for mmlu"),
    filter_grade: Optional[str] = typer.Option(None, help="Filter by specific grade(s) - single grade (e.g., '4') or comma-separated list (e.g., '9,10,11,12') - exams only"),
    filter_subject: Optional[str] = typer.Option(None, help="Filter by specific subject(s) - single subject or comma-separated list (e.g., 'Islamic Studies,Mathematics')"),
    filter_language: Optional[str] = typer.Option(None, help="Filter by specific language(s) - single language or comma-separated list (e.g., 'Arabic,English') - exams only"),
    filter_level: Optional[str] = typer.Option(None, help="Filter by specific level(s) - single level or comma-separated list (e.g., 'High School,University') - mmlu/madinahqa only"),
    filter_country: Optional[str] = typer.Option(None, help="Filter by specific country(s) - single country or comma-separated list - mmlu/madinahqa only"),
    seed: Optional[int] = typer.Option(None, help="Random seed for reproducibility"),
):
    """Sample data and convert to JSONL format in one step. Supports exams, MMLU, and MadinahQA datasets."""
    from arabic_synth.data_prep.exam_processor import ExamProcessor
    from arabic_synth.data_prep.mmlu_processor import MMLUProcessor
    from arabic_synth.data_prep.madinah_processor import MadinahQAProcessor

    if mode not in ["uniform", "stratified"]:
        typer.echo("Error: mode must be 'uniform' or 'stratified'", err=True)
        raise typer.Exit(1)
    
    if task not in ["exams", "mmlu", "madinahqa"]:
        typer.echo("Error: task must be 'exams', 'mmlu', or 'madinahqa'", err=True)
        raise typer.Exit(1)
    
    try:
        if task == "exams":
            # Use ExamProcessor for exams dataset
            processor = ExamProcessor(str(input_file))
            
            # Set default stratify column for exams
            if stratify_col is None:
                stratify_col = "subject"
            
            stats = processor.sample_and_convert(
                n=n,
                mode=mode,
                stratify_col=stratify_col,
                output_jsonl=str(output_file),
                seed=seed,
                filter_grade=filter_grade,
                filter_subject=filter_subject,
                filter_language=filter_language
            )
            
        elif task == "mmlu":
            # Use MMLUProcessor for MMLU dataset
            processor = MMLUProcessor(str(input_file))
            
            # Set default stratify column for MMLU
            if stratify_col is None:
                stratify_col = "Subject"
            
            stats = processor.sample_and_convert(
                n=n,
                mode=mode,
                stratify_col=stratify_col,
                output_jsonl=str(output_file),
                seed=seed,
                filter_subject=filter_subject,
                filter_level=filter_level,
                filter_country=filter_country
            )
        elif task == "madinahqa":
            # Use MadinahQAProcessor for MadinahQA dataset
            processor = MadinahQAProcessor(str(input_file))
            
            # Set default stratify column for MMLU
            if stratify_col is None:
                stratify_col = "Subject"
            
            stats = processor.sample_and_convert(
                n=n,
                mode=mode,
                stratify_col=stratify_col,
                output_jsonl=str(output_file),
                seed=seed,
                filter_subject=filter_subject,
                filter_level=filter_level,
                filter_country=filter_country
            )
        
        typer.echo(f"✅ Sample and convert complete:")
        typer.echo(f"  Task: {task}")
        typer.echo(f"  Mode: {stats['sampling_mode']}")
        typer.echo(f"  Requested: {stats['samples_requested']} samples")
        typer.echo(f"  Success: {stats['success']} | Skipped: {stats['skipped']}")
        typer.echo(f"  Output: {stats['output_file']}")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def style_subject_workflow(
    output_dir: Path = typer.Option(Path("outputs/style_subject"), help="Output directory for all workflow results"),
    input_csv: Path = typer.Option(Path("data/test-00000-of-00001.arabic.csv"), help="Input CSV file (test dataset)"),
    model: str = typer.Option("openai:gpt-4o", help="LLM model to use for generation"),
    seed: int = typer.Option(101, help="Random seed for reproducibility"),
    use_batch_processing: bool = typer.Option(True, help="Use llm_batch_helper for efficient batch processing"),
    batch_size: int = typer.Option(10, help="Batch size for processing (when using batch processing)"),
):
    """Complete style-subject workflow: sample seeds per subject → generate synthetic data → clean & evaluate"""
    from arabic_synth.style_subject_workflow import StyleSubjectWorkflow
    
    # Validate input file exists
    if not input_csv.exists():
        typer.echo(f"❌ Error: Input CSV file not found: {input_csv}", err=True)
        raise typer.Exit(1)
    
    # Create and run workflow
    workflow = StyleSubjectWorkflow(
        output_dir=output_dir,
        input_csv=input_csv,
        model=model,
        seed=seed,
        use_batch_processing=use_batch_processing,
        batch_size=batch_size
    )
    
    result = workflow.run_complete_workflow()
    
    if result["success"]:
        typer.echo("🎉 Style-Subject Workflow completed successfully!")
        typer.echo(f"📋 Summary: {result['summary_file']}")
    else:
        typer.echo(f"❌ Workflow failed: {result['error']}", err=True)
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
        
        # Step 4: Build persona-augmented requests using persona pipeline
        typer.echo(f"\n🔄 Step 4: Building persona-augmented requests")
        persona_requests_path = output_dir / "persona_requests.jsonl"
        
        n_requests = build_persona_requests(
            exams_path=str(styled_seeds_path),
            personas_path=str(personas_path),
            output_path=str(persona_requests_path),
            per_item_personas=per_item_personas,
            target_total=len(styled_results) * per_item_personas,
            seed=seed
        )
        typer.echo(f"✅ Persona requests created: {n_requests} requests → {persona_requests_path}")
        
        # Step 5: Send persona requests to generate final responses
        typer.echo(f"\n🚀 Step 5: Sending persona requests to LLM for final generation")
        final_responses_path = output_dir / "final_responses.jsonl"
        error_responses_path = output_dir / "error_responses.jsonl"
        
        from arabic_synth.persona.send_requests import main as send_persona_requests
        
        responses_count = send_persona_requests(
            input_file=str(persona_requests_path),
            output_file=str(final_responses_path),
            error_file=str(error_responses_path),
            model=model.replace("openai:", "") if model.startswith("openai:") else model
        )
        typer.echo(f"✅ Final responses generated: {responses_count} responses → {final_responses_path}")
        
        # Summary
        typer.echo(f"\n🎉 Workflow Complete! Results in {output_dir}:")
        typer.echo(f"  📊 Seeds: {seeds_path} ({stats['success']} samples)")
        typer.echo(f"  🎨 Styled Seeds: {styled_seeds_path} ({len(styled_results)} samples)")
        typer.echo(f"  👥 Personas: {personas_path}")
        typer.echo(f"  🔄 Persona Requests: {persona_requests_path} ({n_requests} requests)")
        typer.echo(f"  🚀 Final Responses: {final_responses_path} ({responses_count} responses)")
        if error_responses_path.exists():
            typer.echo(f"  ⚠️  Error Responses: {error_responses_path}")
        
        # Create summary file
        summary = {
            "workflow": "style-persona-combined-full",
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
                "persona_requests_file": str(persona_requests_path),
                "total_requests": n_requests,
                "final_responses_file": str(final_responses_path),
                "total_responses": responses_count,
                "error_responses_file": str(error_responses_path) if error_responses_path.exists() else None
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