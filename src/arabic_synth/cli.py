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
from arabic_synth.utils.llm import clear_chat_history, get_chat_history_stats

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
def clear_chat_histories(
    session_id: Optional[str] = typer.Option(None, help="Clear specific session ID (if not provided, clears all)"),
    older_than_hours: Optional[int] = typer.Option(None, help="Only clear histories older than N hours"),
):
    """Clear chat histories to improve performance."""
    cleared_count = clear_chat_history(session_id=session_id, older_than_hours=older_than_hours)
    
    if session_id:
        typer.echo(f"Cleared {cleared_count} messages from session '{session_id}'")
    else:
        typer.echo(f"Cleared {cleared_count} messages from all sessions")


@app.command()
def chat_stats():
    """Show chat history statistics."""
    stats = get_chat_history_stats()
    typer.echo(f"Chat History Statistics:")
    typer.echo(f"  Total sessions: {stats['total_sessions']}")
    typer.echo(f"  Total messages: {stats['total_messages']}")
    
    if stats['sessions']:
        typer.echo(f"  Messages per session:")
        for sid, count in stats['sessions'].items():
            typer.echo(f"    {sid}: {count} messages")


if __name__ == "__main__":
    app() 