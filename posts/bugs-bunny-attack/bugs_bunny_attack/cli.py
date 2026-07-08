"""
CLI interface for the Bugs Bunny Attack reproduction.

Usage:
    uv run bugs-bunny run --model claude-sonnet-4-5 --sweep sweep-1 --trials 2
    uv run bugs-bunny sweep --model claude-sonnet-4-5
    uv run bugs-bunny list-sweeps
"""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .experiment import SWEEPS, BUGS_TURNS, FLIP_INDEX
from .runner import run_sweep

app = typer.Typer(
    name="bugs-bunny",
    help="The Bugs Bunny Attack — LLM contradiction reflex probe",
    no_args_is_help=True,
)
console = Console()


def _format_transcript(turns, duped: bool) -> None:
    """Print a formatted transcript of the conversation."""
    for i, turn in enumerate(turns):
        flip_marker = "  ← FLIP" if i == FLIP_INDEX else ""
        bugs_style = "bold cyan"
        daffy_style = "bold red" if (turn.is_post_flip and "duck season" in turn.daffy_says.lower()) else "bold green"

        console.print(f"  [dim]Bugs:[/dim]  [{bugs_style}]{turn.bugs_says}[/]")
        console.print(f"  [dim]Daffy:[/dim] [{daffy_style}]{turn.daffy_says}[/]{flip_marker}")
        console.print()


@app.command()
def run(
    model: str = typer.Option(..., help="Model name (litellm format, e.g. 'claude-sonnet-4-5', 'gpt-4o')"),
    sweep: str = typer.Option("sweep-1", help="Sweep variant: sweep-1, sweep-2, or sweep-3"),
    trials: int = typer.Option(2, help="Number of trials to run"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full transcripts"),
):
    """Run the switcheroo experiment with a specific model and sweep."""
    description, _ = SWEEPS[sweep]
    console.print(f"\n[bold]Running:[/bold] {model} × {sweep} ({description}) × {trials} trials\n")

    results = run_sweep(model=model, sweep=sweep, trials=trials)

    duped_count = sum(1 for r in results if r.duped)
    total = len(results)
    emoji = "🎯" if duped_count > 0 else "🛡️"

    console.print(f"{emoji} [bold]{duped_count}/{total} duped[/bold]\n")

    if verbose:
        for i, result in enumerate(results):
            label = "🎯 DUPED" if result.duped else "🛡️ HELD"
            console.print(Panel(f"Trial {i+1} — {label}", style="dim"))
            _format_transcript(result.turns, result.duped)


@app.command()
def sweep_all(
    model: str = typer.Option(..., help="Model name (litellm format)"),
    trials: int = typer.Option(2, help="Number of trials per sweep"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full transcripts"),
):
    """Run all three sweeps for a given model."""
    console.print(f"\n[bold]Model:[/bold] {model}  |  [bold]Trials:[/bold] {trials}\n")

    table = Table(title=f"Results: {model}")
    table.add_column("Sweep", style="cyan")
    table.add_column("Description")
    table.add_column("Result", justify="center")

    for sweep_name, (description, _) in SWEEPS.items():
        results = run_sweep(model=model, sweep=sweep_name, trials=trials)
        duped_count = sum(1 for r in results if r.duped)
        total = len(results)
        emoji = "🎯" if duped_count > 0 else "🛡️"
        table.add_row(sweep_name, description, f"{emoji} {duped_count}/{total}")

        if verbose:
            for i, result in enumerate(results):
                label = "🎯 DUPED" if result.duped else "🛡️ HELD"
                console.print(f"\n  [dim]{sweep_name} trial {i+1} — {label}[/dim]")
                _format_transcript(result.turns, result.duped)

    console.print(table)


@app.command()
def list_sweeps():
    """Show available sweep variants and their system prompts."""
    for name, (description, prompt) in SWEEPS.items():
        console.print(Panel(
            Text(prompt, style="dim"),
            title=f"{name}: {description}",
            border_style="cyan",
        ))


@app.command()
def show_script():
    """Show Bugs Bunny's scripted turns (the attack itself)."""
    console.print("\n[bold]Bugs Bunny's turns:[/bold]\n")
    for i, line in enumerate(BUGS_TURNS):
        marker = " [bold red]<-- FLIP[/bold red]" if i == FLIP_INDEX else ""
        console.print(f"  Turn {i+1}: [cyan]{line}[/cyan]{marker}")
    console.print()


def main():
    app()


if __name__ == "__main__":
    main()
