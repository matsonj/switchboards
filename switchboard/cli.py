"""Command-line interface for The Switchboard AI Game Simulator."""

import logging
import random
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from switchboard.game import SwitchboardGame
from switchboard.player import AIPlayer, HumanPlayer, Player
from switchboard.utils.logging import setup_logging

app = typer.Typer(help="The Switchboard AI Game Simulator")
console = Console()


@app.command()
def run(
    red: Optional[str] = typer.Option(None, help="Model for Red Team"),
    blue: Optional[str] = typer.Option(None, help="Model for Blue Team"),
    interactive: bool = typer.Option(
        False, help="Enable interactive mode for human player"
    ),
    num_puzzles: int = typer.Option(1, help="Number of games to play"),
    seed: Optional[int] = typer.Option(None, help="Random seed for reproducible games"),
    names_file: str = typer.Option("inputs/names.yaml", help="Path to names YAML file"),
    red_operator_prompt: str = typer.Option(
        "prompts/red_operator.md", help="Red operator prompt file"
    ),
    red_lineman_prompt: str = typer.Option(
        "prompts/red_lineman.md", help="Red lineman prompt file"
    ),
    blue_operator_prompt: str = typer.Option(
        "prompts/blue_operator.md", help="Blue operator prompt file"
    ),
    blue_lineman_prompt: str = typer.Option(
        "prompts/blue_lineman.md", help="Blue lineman prompt file"
    ),
    log_path: str = typer.Option("logs", help="Directory for log files"),
    verbose: bool = typer.Option(False, help="Enable verbose logging"),
):
    """Run The Switchboard game simulation."""

    # Setup logging
    log_dir = Path(log_path)
    log_dir.mkdir(exist_ok=True)
    setup_logging(log_dir, verbose)

    logger = logging.getLogger(__name__)

    # Set random seed for reproducibility
    if seed is not None:
        random.seed(seed)
        logger.info(f"Random seed set to: {seed}")

    # Validate arguments
    if not interactive and (not red or not blue):
        console.print(
            "[red]Error: Must specify both --red and --blue models, or use --interactive mode[/red]"
        )
        raise typer.Exit(1)

    if interactive and (red and blue):
        console.print(
            "[yellow]Warning: In interactive mode, only one AI team is needed. Using red team model.[/yellow]"
        )

    # Create players
    try:
        red_player: Player
        blue_player: Player

        if interactive:
            human_player = HumanPlayer()

            # If both models specified, use the first for AI team
            if red and blue:
                console.print(
                    "[yellow]In interactive mode, only one AI team is needed. Using red team for AI.[/yellow]"
                )
                ai_player = AIPlayer(red)
                red_player = ai_player
                blue_player = human_player
                console.print(
                    "[green]Interactive mode: Human playing as Blue team[/green]"
                )
            elif red:
                ai_player = AIPlayer(red)
                red_player = ai_player
                blue_player = human_player
                console.print(
                    "[green]Interactive mode: Human playing as Blue team[/green]"
                )
            elif blue:
                ai_player = AIPlayer(blue)
                red_player = human_player
                blue_player = ai_player
                console.print(
                    "[green]Interactive mode: Human playing as Red team[/green]"
                )
            else:
                console.print(
                    "[red]Error: Interactive mode requires at least one AI model (--red or --blue)[/red]"
                )
                raise typer.Exit(1)
        else:
            if not red or not blue:
                console.print(
                    "[red]Error: Non-interactive mode requires both --red and --blue models[/red]"
                )
                raise typer.Exit(1)
            red_player = AIPlayer(red)
            blue_player = AIPlayer(blue)

    except Exception as e:
        console.print(f"[red]Error creating players: {e}[/red]")
        raise typer.Exit(1)

    # Run games
    results = []
    for game_num in range(num_puzzles):
        console.print(f"\n[bold]Game {game_num + 1}/{num_puzzles}[/bold]")

        try:
            game = SwitchboardGame(
                names_file=names_file,
                red_player=red_player,
                blue_player=blue_player,
                red_operator_prompt=red_operator_prompt,
                red_lineman_prompt=red_lineman_prompt,
                blue_operator_prompt=blue_operator_prompt,
                blue_lineman_prompt=blue_lineman_prompt,
            )

            result = game.play()
            results.append(result)

            # Display game result
            console.print(f"[bold]Game {game_num + 1} Result:[/bold]")
            if result["winner"]:
                console.print(f"[green]Winner: {result['winner'].title()} Team[/green]")
            else:
                console.print("[yellow]Game ended in a draw[/yellow]")

        except Exception as e:
            logger.error(f"Error in game {game_num + 1}: {e}")
            console.print(f"[red]Error in game {game_num + 1}: {e}[/red]")

    # Display summary
    if len(results) > 1:
        display_summary(results)


def display_summary(results: list):
    """Display summary statistics for multiple games."""
    total_games = len(results)
    red_wins = sum(1 for r in results if r.get("winner") == "red")
    blue_wins = sum(1 for r in results if r.get("winner") == "blue")
    draws = total_games - red_wins - blue_wins

    table = Table(title="Game Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Total Games", str(total_games))
    table.add_row("Red Team Wins", str(red_wins))
    table.add_row("Blue Team Wins", str(blue_wins))
    table.add_row("Draws", str(draws))
    table.add_row("Red Win Rate", f"{red_wins/total_games*100:.1f}%")
    table.add_row("Blue Win Rate", f"{blue_wins/total_games*100:.1f}%")

    console.print(table)


@app.command()
def list_models():
    """List available AI models."""
    try:
        # Create adapter to load model mappings (without requiring API key for listing)
        import os

        from switchboard.adapters.openrouter_adapter import OpenRouterAdapter

        original_key = os.environ.get("OPENROUTER_API_KEY")
        os.environ["OPENROUTER_API_KEY"] = "dummy"  # Temporary dummy key for loading

        try:
            adapter = OpenRouterAdapter()
            models = adapter.get_available_models()
        finally:
            # Restore original key
            if original_key:
                os.environ["OPENROUTER_API_KEY"] = original_key
            else:
                os.environ.pop("OPENROUTER_API_KEY", None)

        # Create a nice table
        table = Table(title="Available AI Models")
        table.add_column("CLI Name", style="cyan", min_width=15)
        table.add_column("OpenRouter Model ID", style="magenta", min_width=30)
        table.add_column("Provider", style="green", min_width=12)

        # Sort models by provider then name
        sorted_models = sorted(models)

        for model_name in sorted_models:
            model_id = adapter.model_mappings[model_name]
            provider = model_id.split("/")[0] if "/" in model_id else "Unknown"
            table.add_row(model_name, model_id, provider)

        console.print(table)
        console.print(f"\n✨ Total: {len(models)} models available")
        console.print(
            "\n💡 Usage: [bold]uv run switchboard run --red [model] --blue [model][/bold]"
        )

    except Exception as e:
        console.print(f"[red]Error loading models: {e}[/red]")
        console.print(
            "Make sure the model mappings file exists at inputs/model_mappings.yml"
        )


if __name__ == "__main__":
    app()
