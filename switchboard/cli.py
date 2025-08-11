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
from switchboard.prompt_manager import PromptManager
from switchboard.utils.logging import setup_logging

app = typer.Typer(help="The Switchboard AI Game Simulator")
console = Console()


def _format_board_for_lineman_cli(board_state: dict) -> str:
    """Format the board for lineman display with revealed status."""
    board = board_state["board"]
    revealed = board_state["revealed"]
    
    # Create a 5x5 grid display
    lines = []
    for row in range(5):
        row_items = []
        for col in range(5):
            idx = row * 5 + col
            name = board[idx]
            
            # Mark revealed names with brackets
            if revealed.get(name, False):
                display_name = f"[{name}]"
            else:
                display_name = name
            
            row_items.append(f"{display_name:>12}")
        
        lines.append(" |".join(row_items))
    
    return "\n".join(lines)


@app.command()
def run(
    red: Optional[str] = typer.Option(None, help="Model for Red Team"),
    blue: Optional[str] = typer.Option(None, help="Model for Blue Team"),
    umpire: Optional[str] = typer.Option("gemini-flash", help="Model for Umpire (clue validation)"),
    no_umpire: bool = typer.Option(False, help="Disable umpire validation"),
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
    umpire_prompt: str = typer.Option(
        "prompts/umpire.md", help="Umpire prompt file"
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

        # Create umpire player if not disabled
        umpire_player = None
        if not no_umpire and umpire:
            try:
                umpire_player = AIPlayer(umpire)
                console.print(f"[green]Umpire enabled: {umpire}[/green]")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not create umpire player: {e}[/yellow]")
        elif no_umpire:
            console.print("[yellow]Umpire validation disabled[/yellow]")

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
                umpire_player=umpire_player,
                red_operator_prompt=red_operator_prompt,
                red_lineman_prompt=red_lineman_prompt,
                blue_operator_prompt=blue_operator_prompt,
                blue_lineman_prompt=blue_lineman_prompt,
                umpire_prompt=umpire_prompt,
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


@app.command()
def prompt(
    role: str = typer.Argument(..., help="Role to test: operator, lineman, or umpire"),
    team: str = typer.Option("red", help="Team color: red or blue"),
    seed: Optional[int] = typer.Option(None, help="Random seed for reproducible board generation"),
    names_file: str = typer.Option("inputs/names.yaml", help="Path to names YAML file"),
    clue: str = typer.Option("EXAMPLE", help="Sample clue for lineman/umpire prompts"),
    number: str = typer.Option("2", help="Sample number for lineman/umpire prompts (can be 'unlimited' or '0')"),
    red_operator_prompt: str = typer.Option("prompts/red_operator.md", help="Red operator prompt file"),
    red_lineman_prompt: str = typer.Option("prompts/red_lineman.md", help="Red lineman prompt file"),
    blue_operator_prompt: str = typer.Option("prompts/blue_operator.md", help="Blue operator prompt file"),
    blue_lineman_prompt: str = typer.Option("prompts/blue_lineman.md", help="Blue lineman prompt file"),
    umpire_prompt: str = typer.Option("prompts/umpire.md", help="Umpire prompt file"),
):
    """Test and display the exact prompt sent to AI agents."""
    
    # Validate role
    valid_roles = ["operator", "lineman", "umpire"]
    if role not in valid_roles:
        console.print(f"[red]Error: Role must be one of: {', '.join(valid_roles)}[/red]")
        raise typer.Exit(1)
    
    # Validate team
    if team not in ["red", "blue"]:
        console.print(f"[red]Error: Team must be 'red' or 'blue'[/red]")
        raise typer.Exit(1)
    
    # Set random seed if provided
    if seed is not None:
        random.seed(seed)
        console.print(f"[dim]Using seed: {seed}[/dim]")
    
    try:
        # Create a game to generate realistic board state
        red_player = HumanPlayer()  # Dummy players
        blue_player = HumanPlayer()
        
        game = SwitchboardGame(
            names_file=names_file,
            red_player=red_player,
            blue_player=blue_player,
            red_operator_prompt=red_operator_prompt,
            red_lineman_prompt=red_lineman_prompt,
            blue_operator_prompt=blue_operator_prompt,
            blue_lineman_prompt=blue_lineman_prompt,
            umpire_prompt=umpire_prompt,
        )
        
        # Setup the board
        game.setup_board()
        
        # Get board state 
        board_state = game.get_board_state(reveal_all=(role == "operator"))
        
        # Initialize prompt manager
        prompt_manager = PromptManager()
        
        # Parse number parameter (handle unlimited and 0)
        parsed_number: int|str
        if number.lower() == "unlimited":
            parsed_number = "unlimited"
        elif number == "0":
            parsed_number = 0
        else:
            try:
                parsed_number = int(number)
            except ValueError:
                console.print(f"[red]Error: Number must be an integer, 'unlimited', or '0'[/red]")
                raise typer.Exit(1)
        
        # Generate the appropriate prompt
        if role == "operator":
            prompt_file = red_operator_prompt if team == "red" else blue_operator_prompt
            
            # Calculate remaining subscribers for operator context
            red_remaining = sum(
                1 for name, identity in board_state["identities"].items()
                if identity == "red_subscriber" and not board_state["revealed"].get(name, False)
            )
            blue_remaining = sum(
                1 for name, identity in board_state["identities"].items()
                if identity == "blue_subscriber" and not board_state["revealed"].get(name, False)
            )
            revealed_names = [name for name, revealed in board_state["revealed"].items() if revealed]
            
            # Categorize identities for cleaner prompt formatting
            red_subscribers = [name for name, identity in board_state["identities"].items() 
                             if identity == "red_subscriber"]
            blue_subscribers = [name for name, identity in board_state["identities"].items() 
                              if identity == "blue_subscriber"]
            civilians = [name for name, identity in board_state["identities"].items() 
                        if identity == "civilian"]
            mole = [name for name, identity in board_state["identities"].items() 
                   if identity == "mole"]
            
            prompt = prompt_manager.load_prompt(
                prompt_file,
                {
                    "board": board_state["board"],
                    "revealed": board_state["revealed"],
                    "team": team,
                    "red_remaining": red_remaining,
                    "blue_remaining": blue_remaining,
                    "revealed_names": ", ".join(revealed_names) if revealed_names else "None",
                    "red_subscribers": ", ".join(red_subscribers),
                    "blue_subscribers": ", ".join(blue_subscribers),
                    "civilians": ", ".join(civilians),
                    "mole": ", ".join(mole),
                },
            )
            
        elif role == "lineman":
            prompt_file = red_lineman_prompt if team == "red" else blue_lineman_prompt
            
            # Filter board to only show available (unrevealed) names for lineman
            available_names = [
                name for name in board_state["board"] 
                if not board_state["revealed"].get(name, False)
            ]
            
            # Format available names as a simple list
            available_names_formatted = ", ".join(available_names)
            
            prompt = prompt_manager.load_prompt(
                prompt_file,
                {
                    "board": _format_board_for_lineman_cli(board_state),
                    "available_names": available_names_formatted,
                    "clue_history": board_state.get("clue_history", "None (game just started)"),
                    "clue": clue,
                    "number": parsed_number,
                    "team": team,
                },
            )
            
        elif role == "umpire":
            # Get team's allied subscribers for umpire context
            allied_subscribers = [
                name for name, identity in board_state["identities"].items()
                if identity == f"{team}_subscriber"
            ]
            
            prompt = prompt_manager.load_prompt(
                umpire_prompt,
                {
                    "clue": clue,
                    "number": parsed_number,
                    "team": team,
                    "board": board_state["board"],
                    "allied_subscribers": ", ".join(allied_subscribers),
                },
            )
        
        # Display the results
        console.print(f"\n[bold]🎯 {role.title()} Prompt for {team.title()} Team[/bold]")
        console.print(f"[dim]Seed: {seed}, Board: {len(board_state['board'])} names[/dim]")
        
        if role in ["lineman", "umpire"]:
            console.print(f"[dim]Sample clue: '{clue}' ({parsed_number})[/dim]")
        
        console.print(f"\n[yellow]{'='*80}[/yellow]")
        console.print("[yellow]PROMPT CONTENT:[/yellow]")
        console.print(f"[yellow]{'='*80}[/yellow]\n")
        
        console.print(prompt)
        
        console.print(f"\n[yellow]{'='*80}[/yellow]")
        console.print(f"[green]✅ Prompt generated successfully ({len(prompt)} characters)[/green]")
        
        # Show board state for context
        if role == "operator":
            console.print(f"\n[bold]📋 Board State (Operator View - All Identities Revealed):[/bold]")
            game.display_board(reveal_all=True)
        else:
            console.print(f"\n[bold]📋 Board State (Public View):[/bold]")
            game.display_board(reveal_all=False)
        
    except Exception as e:
        console.print(f"[red]Error generating prompt: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
