"""Command-line interface for The Playbook AI Game Simulator."""

import logging
import os
import random
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table

from playbook.game import PlaybookGame
from playbook.player import AIPlayer, HumanPlayer, Player
from playbook.prompt_manager import PromptManager
from playbook.utils.logging import setup_logging

app = typer.Typer(help="The Playbook AI Game Simulator")
console = Console()


def _load_model_mappings(mappings_file: Optional[str] = None) -> dict:
    """Load model mappings from YAML configuration file."""
    if mappings_file is None:
        file_path = Path("inputs/model_mappings.yml")
    else:
        file_path = Path(mappings_file)

    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
        return data.get("models", {})
    except FileNotFoundError:
        # Fallback to basic mappings
        return {
            "gpt4": "openai/gpt-4",
            "claude": "anthropic/claude-3.5-sonnet",
            "gemini": "google/gemini-2.5-pro",
        }
    except Exception:
        # Fallback to basic mappings
        return {
            "gpt4": "openai/gpt-4",
            "claude": "anthropic/claude-3.5-sonnet", 
            "gemini": "google/gemini-2.5-pro",
        }


def _validate_api_keys_and_models(red: Optional[str], blue: Optional[str], referee: Optional[str], interactive: bool):
    """Validate that required API keys are present and model names are valid."""
    # Check API keys
    missing_keys = []
    
    if not os.getenv("OPENROUTER_API_KEY"):
        missing_keys.append("OPENROUTER_API_KEY")
    
    if missing_keys:
        console.print(f"[red]Error: Missing required environment variable(s): {', '.join(missing_keys)}[/red]")
        console.print("[yellow]You may need to `source .env` if you are running locally[/yellow]")
        console.print("[yellow]Or set the environment variable directly:[/yellow]")
        for key in missing_keys:
            console.print(f"[yellow]  export {key}='your-key-here'[/yellow]")
        raise typer.Exit(1)
    
    # Check model names
    model_mappings = _load_model_mappings()
    available_models = list(model_mappings.keys())
    invalid_models = []
    
    # Check models that will be used
    models_to_check = []
    if red:
        models_to_check.append(("red", red))
    if blue:
        models_to_check.append(("blue", blue))
    if referee:
        models_to_check.append(("referee", referee))
    
    for team, model in models_to_check:
        if model not in available_models:
            invalid_models.append((team, model))
    
    if invalid_models:
        console.print(f"[red]Error: Invalid model name(s):[/red]")
        for team, model in invalid_models:
            console.print(f"[red]  {team}: '{model}'[/red]")
        console.print(f"\n[yellow]Available models:[/yellow]")
        for model in sorted(available_models):
            console.print(f"[yellow]  {model}[/yellow]")
        console.print(f"\n[yellow]Use 'uv run playbook list-models' for detailed model information[/yellow]")
        raise typer.Exit(1)


def _format_board_for_player_cli(board_state: dict) -> str:
    """Format the field for player display with revealed status."""
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
    referee: Optional[str] = typer.Option("gemini-flash", help="Model for Referee (play validation)"),
    no_referee: bool = typer.Option(False, help="Disable referee validation"),
    interactive: Optional[str] = typer.Option(
        None, help="Interactive mode: referee, red-coach, red-player, blue-coach, blue-player"
    ),
    num_puzzles: int = typer.Option(1, help="Number of games to play"),
    seed: Optional[int] = typer.Option(None, help="Random seed for reproducible games"),
    names_file: str = typer.Option("inputs/names.yaml", help="Path to names YAML file"),
    red_coach_prompt: str = typer.Option(
        "prompts/red_coach.md", help="Red coach prompt file"
    ),
    red_player_prompt: str = typer.Option(
        "prompts/red_player.md", help="Red player prompt file"
    ),
    blue_coach_prompt: str = typer.Option(
        "prompts/blue_coach.md", help="Blue coach prompt file"
    ),
    blue_player_prompt: str = typer.Option(
        "prompts/blue_player.md", help="Blue player prompt file"
    ),
    referee_prompt: str = typer.Option(
        "prompts/referee.md", help="Referee prompt file"
    ),
    log_path: str = typer.Option("logs", help="Directory for log files"),
    verbose: bool = typer.Option(False, help="Enable verbose logging"),
):
    """Run The Playbook game simulation."""

    # Validate API keys and model names first
    _validate_api_keys_and_models(red, blue, referee, interactive)

    # Setup logging
    log_dir = Path(log_path)
    log_dir.mkdir(exist_ok=True)
    setup_logging(log_dir, verbose)

    logger = logging.getLogger(__name__)

    # Set random seed for reproducibility
    if seed is not None:
        random.seed(seed)
        logger.info(f"Random seed set to: {seed}")

    # Validate interactive mode options
    valid_interactive_modes = ["referee", "red-coach", "red-player", "blue-coach", "blue-player"]
    if interactive and interactive not in valid_interactive_modes:
        console.print(
            f"[red]Error: Interactive mode must be one of: {', '.join(valid_interactive_modes)}[/red]"
        )
        raise typer.Exit(1)

    # Validate arguments
    if not interactive and (not red or not blue):
        console.print(
            "[red]Error: Must specify both --red and --blue models, or use --interactive mode[/red]"
        )
        raise typer.Exit(1)

    if interactive and interactive != "referee" and (not red or not blue):
        console.print(
            "[red]Error: Interactive modes other than 'referee' require both --red and --blue models[/red]"
        )
        raise typer.Exit(1)

    # Create players
    try:
        red_player: Player
        blue_player: Player

        if interactive:
            if interactive == "referee":
                # Referee mode: both teams are AI, human is referee
                if not red or not blue:
                    console.print("[red]Error: Referee mode requires both --red and --blue models[/red]")
                    raise typer.Exit(1)
                red_player = AIPlayer(red)
                blue_player = AIPlayer(blue)
            else:
                # Role-specific mode: specific role is human, rest are AI
                red_player = AIPlayer(red)
                blue_player = AIPlayer(blue)
                console.print(f"[green]Interactive mode: Human {interactive}[/green]")
        else:
            if not red or not blue:
                console.print(
                    "[red]Error: Non-interactive mode requires both --red and --blue models[/red]"
                )
                raise typer.Exit(1)
            red_player = AIPlayer(red)
            blue_player = AIPlayer(blue)

        # Create referee player if not disabled
        referee_player = None
        if not no_referee:
            if interactive == "referee":
                referee_player = HumanPlayer()
            elif referee:
                try:
                    referee_player = AIPlayer(referee)
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not create referee player: {e}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error creating players: {e}[/red]")
        raise typer.Exit(1)

    # Run games
    results = []
    for game_num in range(num_puzzles):
        console.print(f"\n[bold]Game {game_num + 1}/{num_puzzles}[/bold]")

        try:
            game = PlaybookGame(
                names_file=names_file,
                red_player=red_player,
                blue_player=blue_player,
                referee_player=referee_player,
                red_coach_prompt=red_coach_prompt,
                red_player_prompt=red_player_prompt,
                blue_coach_prompt=blue_coach_prompt,
                blue_player_prompt=blue_player_prompt,
                referee_prompt=referee_prompt,
                interactive_mode=interactive,
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

        from playbook.adapters.openrouter_adapter import OpenRouterAdapter

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
            "\n💡 Usage: [bold]uv run playbook run --red [model] --blue [model][/bold]"
        )

    except Exception as e:
        console.print(f"[red]Error loading models: {e}[/red]")
        console.print(
            "Make sure the model mappings file exists at inputs/model_mappings.yml"
        )


@app.command()
def prompt(
    role: str = typer.Argument(..., help="Role to test: coach, player, or referee"),
    team: str = typer.Option("red", help="Team color: red or blue"),
    seed: Optional[int] = typer.Option(None, help="Random seed for reproducible board generation"),
    names_file: str = typer.Option("inputs/names.yaml", help="Path to names YAML file"),
    play: str = typer.Option("EXAMPLE", help="Sample play for player/referee prompts"),
    number: str = typer.Option("2", help="Sample number for player/referee prompts (can be 'unlimited' or '0')"),
    red_coach_prompt: str = typer.Option("prompts/red_coach.md", help="Red coach prompt file"),
    red_player_prompt: str = typer.Option("prompts/red_player.md", help="Red player prompt file"),
    blue_coach_prompt: str = typer.Option("prompts/blue_coach.md", help="Blue coach prompt file"),
    blue_player_prompt: str = typer.Option("prompts/blue_player.md", help="Blue player prompt file"),
    referee_prompt: str = typer.Option("prompts/referee.md", help="Referee prompt file"),
    verbose: bool = typer.Option(False, help="Enable verbose logging"),
):
    """Test and display the exact prompt sent to AI agents."""
    
    # Setup logging (but don't create game logs for prompt testing)
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    setup_logging(temp_dir, verbose)
    
    # Validate role
    valid_roles = ["coach", "player", "referee"]
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
        
        game = PlaybookGame(
            names_file=names_file,
            red_player=red_player,
            blue_player=blue_player,
            red_coach_prompt=red_coach_prompt,
            red_player_prompt=red_player_prompt,
            blue_coach_prompt=blue_coach_prompt,
            blue_player_prompt=blue_player_prompt,
            referee_prompt=referee_prompt,
        )
        
        # Setup the board
        game.setup_board()
        
        # Get field state 
        field_state = game.get_field_state(reveal_all=(role == "coach"))
        
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
        if role == "coach":
            prompt_file = red_coach_prompt if team == "red" else blue_coach_prompt
            
            # Calculate remaining targets for coach context
            red_remaining = sum(
                1 for name, identity in field_state["identities"].items()
                if identity == "red_target" and not field_state["revealed"].get(name, False)
            )
            blue_remaining = sum(
                1 for name, identity in field_state["identities"].items()
                if identity == "blue_target" and not field_state["revealed"].get(name, False)
            )
            revealed_names = [name for name, revealed in field_state["revealed"].items() if revealed]
            
            # Categorize identities for cleaner prompt formatting
            red_targets = [name for name, identity in field_state["identities"].items() 
                             if identity == "red_target"]
            blue_targets = [name for name, identity in field_state["identities"].items() 
                              if identity == "blue_target"]
            fake_targets = [name for name, identity in field_state["identities"].items() 
                        if identity == "fake_target"]
            illegal_target = [name for name, identity in field_state["identities"].items() 
                   if identity == "illegal_target"]
            
            prompt = prompt_manager.load_prompt(
                prompt_file,
                {
                    "field": field_state["board"],
                    "revealed": field_state["revealed"],
                    "team": team,
                    "red_remaining": red_remaining,
                    "blue_remaining": blue_remaining,
                    "revealed_names": ", ".join(revealed_names) if revealed_names else "None",
                    "red_targets": ", ".join(red_targets),
                    "blue_targets": ", ".join(blue_targets),
                    "fake_targets": ", ".join(fake_targets),
                    "illegal_target": ", ".join(illegal_target),
                },
            )
            
        elif role == "player":
            prompt_file = red_player_prompt if team == "red" else blue_player_prompt
            
            # Filter field to only show available (unrevealed) names for player
            available_names = [
                name for name in field_state["board"] 
                if not field_state["revealed"].get(name, False)
            ]
            
            # Format available names as a simple list
            available_names_formatted = ", ".join(available_names)
            
            prompt = prompt_manager.load_prompt(
                prompt_file,
                {
                    "field": _format_board_for_player_cli(field_state),
                    "available_names": available_names_formatted,
                    "play_history": field_state.get("play_history", "None (game just started)"),
                    "play": play,
                    "number": parsed_number,
                    "team": team,
                },
            )
            
        elif role == "referee":
            # Get team's allied targets for referee context
            allied_targets = [
                name for name, identity in field_state["identities"].items()
                if identity == f"{team}_target"
            ]
            
            prompt = prompt_manager.load_prompt(
                referee_prompt,
                {
                    "play": play,
                    "number": parsed_number,
                    "team": team,
                    "field": field_state["board"],
                    "allied_targets": ", ".join(allied_targets),
                },
            )
        
        # Display the results
        console.print(f"\n[bold]🎯 {role.title()} Prompt for {team.title()} Team[/bold]")
        console.print(f"[dim]Seed: {seed}, Field: {len(field_state['board'])} names[/dim]")
        
        if role in ["player", "referee"]:
            console.print(f"[dim]Sample play: '{play}' ({parsed_number})[/dim]")
        
        console.print(f"\n[yellow]{'='*80}[/yellow]")
        console.print("[yellow]PROMPT CONTENT:[/yellow]")
        console.print(f"[yellow]{'='*80}[/yellow]\n")
        
        console.print(prompt)
        
        console.print(f"\n[yellow]{'='*80}[/yellow]")
        console.print(f"[green]✅ Prompt generated successfully ({len(prompt)} characters)[/green]")
        
        # Show field state for context
        if role == "coach":
            console.print(f"\n[bold]📋 Field State (Coach View - All Identities Revealed):[/bold]")
            game.display_board(reveal_all=True)
        else:
            console.print(f"\n[bold]📋 Field State (Public View):[/bold]")
            game.display_board(reveal_all=False)
        
    except Exception as e:
        console.print(f"[red]Error generating prompt: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
