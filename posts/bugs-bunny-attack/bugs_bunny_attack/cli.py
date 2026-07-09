"""
CLI interface for the Bugs Bunny Attack reproduction.

Usage:
    uv run bugs-bunny run --model claude-sonnet-4-5 --sweep sweep-1 --trials 2
    uv run bugs-bunny sweep --model claude-sonnet-4-5
    uv run bugs-bunny list-sweeps
    uv run bugs-bunny list-characters
"""

from pathlib import Path

import typer
import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Force UTF-8 output on Windows to avoid legacy cp1252 encoding errors
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Load .env from the project root (or cwd)
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv()  # also check cwd

from .experiment import CHARACTER_SETS, SCENARIOS, get_sweeps, get_attacker_turns, FLIP_INDEX
from .runner import run_sweep

app = typer.Typer(
    name="bugs-bunny",
    help="The Bugs Bunny Attack -- LLM contradiction reflex probe",
    no_args_is_help=True,
)
console = Console(force_terminal=True)

CHARACTERS_HELP = f"Character variant: {', '.join(CHARACTER_SETS.keys())}"
SCENARIO_HELP = f"Scenario: {', '.join(SCENARIOS.keys())}"


def _live_turn(turn_index: int, bugs_says: str, daffy_says: str, is_post_flip: bool) -> None:
    """Print a single turn as it happens."""
    flip_marker = " [bold red]<-- FLIP[/bold red]" if turn_index == FLIP_INDEX else ""
    bugs_style = "bold cyan"
    # Highlight if response looks duped (contains victim season in assertive way)
    daffy_style = "bold red" if is_post_flip else "bold green"

    console.print(f"  [dim]Bugs:[/dim]  [{bugs_style}]{bugs_says}[/]{flip_marker}")
    console.print(f"  [dim]Daffy:[/dim] [{daffy_style}]{daffy_says}[/]")
    console.print()


def _trial_header(trial_num: int) -> None:
    """Print trial separator."""
    console.print(f"  [dim]{'-' * 40}[/dim]")
    console.print(f"  [bold]Trial {trial_num + 1}[/bold]\n")


@app.command()
def run(
    model: str = typer.Option(..., help="Model name (litellm format, e.g. 'claude-sonnet-4-5', 'gpt-5')"),
    sweep: str = typer.Option("sweep-1", help="Sweep variant: sweep-1, sweep-2, or sweep-3"),
    trials: int = typer.Option(2, help="Number of trials to run"),
    characters: str = typer.Option("canonical", help=CHARACTERS_HELP),
    scenario: str = typer.Option("hunting", help=SCENARIO_HELP),
    thinking: bool = typer.Option(False, "--thinking", help="Enable high reasoning effort (reasoning_effort=high). Default is low/minimal."),
):
    """Run the switcheroo experiment with a specific model and sweep."""
    chars = CHARACTER_SETS[characters]
    scen = SCENARIOS[scenario]
    sweeps = get_sweeps(chars, scen)
    description, _ = sweeps[sweep]
    thinking_label = " [dim](thinking=high)[/dim]" if thinking else ""
    extra = []
    if characters != "canonical":
        extra.append(characters)
    if scenario != "hunting":
        extra.append(scenario)
    extra_label = f" [dim][{', '.join(extra)}][/dim]" if extra else ""
    console.print(f"\n[bold]Running:[/bold] {model} x {sweep} ({description}) x {trials} trials{thinking_label}{extra_label}\n")

    results = run_sweep(
        model=model,
        sweep=sweep,
        trials=trials,
        characters=characters,
        scenario=scenario,
        thinking=thinking,
        on_turn=_live_turn,
        on_trial_start=_trial_header,
    )

    # Summary
    console.print(f"  [dim]{'-' * 40}[/dim]")
    duped_count = sum(1 for r in results if r.duped)
    probable_count = sum(1 for r in results if r.probable)
    total = len(results)
    marker = "[DUPED]" if duped_count > 0 else ("[PROBABLE]" if probable_count > 0 else "[RESISTED]")
    parts = [f"{duped_count}/{total} duped"]
    if probable_count:
        parts.append(f"{probable_count}/{total} probable")
    console.print(f"\n  {marker} [bold]Result: {', '.join(parts)}[/bold]\n")


@app.command()
def sweep_all(
    model: str = typer.Option(..., help="Model name (litellm format)"),
    trials: int = typer.Option(2, help="Number of trials per sweep"),
    characters: str = typer.Option("canonical", help=CHARACTERS_HELP),
    scenario: str = typer.Option("hunting", help=SCENARIO_HELP),
    thinking: bool = typer.Option(False, "--thinking", help="Enable high reasoning effort (reasoning_effort=high). Default is low/minimal."),
):
    """Run all three sweeps for a given model."""
    chars = CHARACTER_SETS[characters]
    scen = SCENARIOS[scenario]
    sweeps = get_sweeps(chars, scen)
    thinking_label = " (thinking=high)" if thinking else ""
    console.print(f"\n[bold]Model:[/bold] {model}  |  [bold]Trials:[/bold] {trials}  |  [bold]Characters:[/bold] {characters}  |  [bold]Scenario:[/bold] {scenario}{thinking_label}\n")

    table = Table(title=f"Results: {model} [{characters}/{scenario}]")
    table.add_column("Sweep", style="cyan")
    table.add_column("Description")
    table.add_column("Result", justify="center")

    for sweep_name, (description, _) in sweeps.items():
        console.print(f"\n[bold]{sweep_name}:[/bold] {description}\n")
        results = run_sweep(
            model=model,
            sweep=sweep_name,
            trials=trials,
            characters=characters,
            scenario=scenario,
            thinking=thinking,
            on_turn=_live_turn,
            on_trial_start=_trial_header,
        )
        duped_count = sum(1 for r in results if r.duped)
        probable_count = sum(1 for r in results if r.probable)
        total = len(results)
        if duped_count > 0:
            marker = "[DUPED]"
            label = f"{duped_count}/{total}"
        elif probable_count > 0:
            marker = "[PROB]"
            label = f"{probable_count}/{total} probable"
        else:
            marker = "[OK]"
            label = f"0/{total}"
        table.add_row(sweep_name, description, f"{marker} {label}")
        console.print(f"  [dim]{'-' * 40}[/dim]")

    console.print()
    console.print(table)


@app.command()
def list_sweeps(
    characters: str = typer.Option("canonical", help=CHARACTERS_HELP),
    scenario: str = typer.Option("hunting", help=SCENARIO_HELP),
):
    """Show available sweep variants and their system prompts."""
    chars = CHARACTER_SETS[characters]
    scen = SCENARIOS[scenario]
    sweeps = get_sweeps(chars, scen)
    for name, (description, prompt) in sweeps.items():
        console.print(Panel(
            Text(prompt, style="dim"),
            title=f"{name}: {description}",
            border_style="cyan",
        ))


@app.command()
def list_characters():
    """Show available character variants."""
    table = Table(title="Character Variants")
    table.add_column("Name", style="cyan")
    table.add_column("Attacker")
    table.add_column("Victim")
    table.add_column("Description")

    for name, chars in CHARACTER_SETS.items():
        table.add_row(
            name,
            chars.attacker,
            chars.victim,
            chars.description,
        )

    console.print()
    console.print(table)
    console.print()


@app.command()
def list_scenarios():
    """Show available scenario variants."""
    table = Table(title="Scenario Variants")
    table.add_column("Name", style="cyan")
    table.add_column("Dangerous Claim")
    table.add_column("Safe Claim")
    table.add_column("Description")

    for name, scen in SCENARIOS.items():
        table.add_row(
            name,
            scen.dangerous_claim,
            scen.safe_claim,
            scen.description,
        )

    console.print()
    console.print(table)
    console.print()


@app.command()
def show_script(
    characters: str = typer.Option("canonical", help=CHARACTERS_HELP),
    scenario: str = typer.Option("hunting", help=SCENARIO_HELP),
):
    """Show the attacker's scripted turns (the attack itself)."""
    chars = CHARACTER_SETS[characters]
    scen = SCENARIOS[scenario]
    turns = get_attacker_turns(scen)
    console.print(f"\n[bold]{chars.attacker}'s turns ({scenario}):[/bold]\n")
    for i, line in enumerate(turns):
        marker = " [bold red]<-- FLIP[/bold red]" if i == FLIP_INDEX else ""
        console.print(f"  Turn {i+1}: [cyan]{line}[/cyan]{marker}")
    console.print()


def main():
    app()


if __name__ == "__main__":
    main()
