"""
CLI interface for the Bugs Bunny Attack reproduction.

Usage:
    uv run bugs-bunny run --model claude-sonnet-4-5 --sweep sweep-1 --trials 2
    uv run bugs-bunny sweep --model claude-sonnet-4-5
    uv run bugs-bunny list-sweeps
"""

from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Load .env from the project root (or cwd)
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv()  # also check cwd

from .experiment import SWEEPS, BUGS_TURNS, FLIP_INDEX
from .runner import run_sweep, run_conversation

app = typer.Typer(
    name="bugs-bunny",
    help="The Bugs Bunny Attack — LLM contradiction reflex probe",
    no_args_is_help=True,
)
console = Console()


def _live_turn(turn_index: int, bugs_says: str, daffy_says: str, is_post_flip: bool) -> None:
    """Print a single turn as it happens."""
    flip_marker = " [bold red]<-- FLIP[/bold red]" if turn_index == FLIP_INDEX else ""
    bugs_style = "bold cyan"
    daffy_style = "bold red" if (is_post_flip and "duck season" in daffy_says.lower()) else "bold green"

    console.print(f"  [dim]Bugs:[/dim]  [{bugs_style}]{bugs_says}[/]{flip_marker}")
    console.print(f"  [dim]Daffy:[/dim] [{daffy_style}]{daffy_says}[/]")
    console.print()


def _trial_header(trial_num: int) -> None:
    """Print trial separator."""
    console.print(f"  [dim]{'─' * 40}[/dim]")
    console.print(f"  [bold]Trial {trial_num + 1}[/bold]\n")


@app.command()
def run(
    model: str = typer.Option(..., help="Model name (litellm format, e.g. 'claude-sonnet-4-5', 'gpt-4o')"),
    sweep: str = typer.Option("sweep-1", help="Sweep variant: sweep-1, sweep-2, or sweep-3"),
    trials: int = typer.Option(2, help="Number of trials to run"),
    thinking: bool = typer.Option(False, "--thinking", help="Enable high reasoning effort (reasoning_effort=high). Default is low/minimal."),
):
    """Run the switcheroo experiment with a specific model and sweep."""
    description, _ = SWEEPS[sweep]
    thinking_label = " [dim](thinking=high)[/dim]" if thinking else ""
    console.print(f"\n[bold]Running:[/bold] {model} x {sweep} ({description}) x {trials} trials{thinking_label}\n")

    results = run_sweep(
        model=model,
        sweep=sweep,
        trials=trials,
        thinking=thinking,
        on_turn=_live_turn,
        on_trial_start=_trial_header,
    )

    # Summary
    console.print(f"  [dim]{'─' * 40}[/dim]")
    duped_count = sum(1 for r in results if r.duped)
    probable_count = sum(1 for r in results if r.probable)
    total = len(results)
    emoji = "🎯" if duped_count > 0 else ("🤔" if probable_count > 0 else "🛡️")
    parts = [f"{duped_count}/{total} duped"]
    if probable_count:
        parts.append(f"{probable_count}/{total} probable")
    console.print(f"\n  {emoji} [bold]Result: {', '.join(parts)}[/bold]\n")


@app.command()
def sweep_all(
    model: str = typer.Option(..., help="Model name (litellm format)"),
    trials: int = typer.Option(2, help="Number of trials per sweep"),
    thinking: bool = typer.Option(False, "--thinking", help="Enable high reasoning effort (reasoning_effort=high). Default is low/minimal."),
):
    """Run all three sweeps for a given model."""
    thinking_label = " (thinking=high)" if thinking else ""
    console.print(f"\n[bold]Model:[/bold] {model}  |  [bold]Trials:[/bold] {trials}{thinking_label}\n")

    table = Table(title=f"Results: {model}")
    table.add_column("Sweep", style="cyan")
    table.add_column("Description")
    table.add_column("Result", justify="center")

    for sweep_name, (description, _) in SWEEPS.items():
        console.print(f"\n[bold]{sweep_name}:[/bold] {description}\n")
        results = run_sweep(
            model=model,
            sweep=sweep_name,
            trials=trials,
            thinking=thinking,
            on_turn=_live_turn,
            on_trial_start=_trial_header,
        )
        duped_count = sum(1 for r in results if r.duped)
        probable_count = sum(1 for r in results if r.probable)
        total = len(results)
        if duped_count > 0:
            emoji = "🎯"
            label = f"{duped_count}/{total}"
        elif probable_count > 0:
            emoji = "🤔"
            label = f"{probable_count}/{total} probable"
        else:
            emoji = "🛡️"
            label = f"0/{total}"
        table.add_row(sweep_name, description, f"{emoji} {label}")
        console.print(f"  [dim]{'─' * 40}[/dim]")

    console.print()
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
