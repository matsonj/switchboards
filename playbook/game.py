"""Core game logic for The Playbook."""

import logging
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from rich.console import Console
from rich.table import Table

from playbook.player import AIPlayer, HumanPlayer
from playbook.utils.logging import (
    log_game_start, log_coach_play, log_player_shot, 
    log_game_end, log_box_score, log_turn_end_status, log_referee_rejection, log_referee_penalty,
    log_ai_call_metadata, format_turn_label, log_game_setup_metadata
)

console = Console()
logger = logging.getLogger(__name__)


class PlaybookGame:
    """The main game class that manages a complete Playbook game."""

    FIELD_SIZE = 25
    STARTING_TEAM_TARGETS = 9  # Team that goes first gets 9
    SECOND_TEAM_TARGETS = 8    # Team that goes second gets 8
    FAKE_TARGETS = 7
    ILLEGAL_TARGETS = 1

    def __init__(
        self,
        names_file: str,
        red_player,
        blue_player,
        referee_player=None,
        red_coach_prompt: str = "",
        red_player_prompt: str = "",
        blue_coach_prompt: str = "",
        blue_player_prompt: str = "",
        referee_prompt: str = "",
        interactive_mode: Optional[str] = None,
    ):
        self.names_file = names_file
        self.red_player = red_player
        self.blue_player = blue_player
        self.referee_player = referee_player
        self.interactive_mode = interactive_mode
        self.prompt_files = {
            "red_coach": red_coach_prompt,
            "red_player": red_player_prompt,
            "blue_coach": blue_coach_prompt,
            "blue_player": blue_player_prompt,
            "referee": referee_prompt,
        }

        # Game state
        self.field: List[str] = []
        self.identities: Dict[str, str] = {}  # name -> identity
        self.revealed: Dict[str, bool] = {}  # name -> revealed status
        # Randomly choose which team starts first
        self.starting_team = random.choice(["red", "blue"])
        self.current_team = self.starting_team
        self.game_over = False
        self.winner: Optional[str] = None
        self.turn_count = 0

        # Track game statistics
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.moves_log: List[Dict] = []
        self.play_history: List[Dict] = []
        
        # Generate unique game ID
        import uuid
        self.game_id = str(uuid.uuid4())[:8]

    def load_names(self) -> List[str]:
        """Load names from YAML file."""
        try:
            with open(self.names_file, "r") as f:
                data = yaml.safe_load(f)
                names = data.get("names", [])
                if len(names) < self.FIELD_SIZE:
                    raise ValueError(
                        f"Need at least {self.FIELD_SIZE} names, got {len(names)}"
                    )
                return names
        except FileNotFoundError:
            logger.error(f"Names file not found: {self.names_file}")
            raise
        except Exception as e:
            logger.error(f"Error loading names: {e}")
            raise

    def setup_field(self):
        """Initialize the game field with random name assignment."""
        all_names = self.load_names()

        # Select 25 random names
        self.field = random.sample(all_names, self.FIELD_SIZE)

        # Assign identities
        positions = list(range(self.FIELD_SIZE))
        random.shuffle(positions)

        # Assign allied targets based on who starts first
        if self.starting_team == "red":
            red_count = self.STARTING_TEAM_TARGETS
            blue_count = self.SECOND_TEAM_TARGETS
        else:
            red_count = self.SECOND_TEAM_TARGETS
            blue_count = self.STARTING_TEAM_TARGETS
        
        red_positions = positions[:red_count]
        blue_positions = positions[red_count:red_count + blue_count]

        # Assign illegal target and fake targets
        remaining_positions = positions[red_count + blue_count:]
        illegal_target_position = remaining_positions[0]
        fake_target_positions = remaining_positions[1 : 1 + self.FAKE_TARGETS]

        # Create identity mapping
        self.identities = {}
        self.revealed = {}

        for i, name in enumerate(self.field):
            if i in red_positions:
                self.identities[name] = "red_target"
            elif i in blue_positions:
                self.identities[name] = "blue_target"
            elif i == illegal_target_position:
                self.identities[name] = "illegal_target"
            else:
                self.identities[name] = "civilian"

            self.revealed[name] = False

        logger.info(
            f"Field setup complete. Starting team: {self.starting_team.upper()}. Red: {len(red_positions)}, Blue: {len(blue_positions)}, Civilians: {len(fake_target_positions)}, Illegal target: 1"
        )

    def get_field_state(self, reveal_all: bool = False) -> Dict[str, Any]:
        """Get current field state for display."""
        identities: Dict[str, str] = {} if not reveal_all else self.identities.copy()

        # Add revealed identities
        if not reveal_all:
            for name in self.field:
                if self.revealed.get(name, False):
                    identities[name] = self.identities[name]

        state = {
            "board": self.field.copy(),
            "revealed": self.revealed.copy(),
            "identities": identities,
            "current_team": self.current_team,
            "turn_count": self.turn_count,
            "play_history": self.format_play_history(),
        }

        return state

    def setup_board(self):
        """Compatibility method - calls setup_field."""
        return self.setup_field()

    def get_board_state(self, reveal_all: bool = False) -> Dict[str, Any]:
        """Compatibility method - calls get_field_state."""
        return self.get_field_state(reveal_all)

    def _format_field_for_player_cli(self, field_state: dict) -> str:
        """Format the field for player display with revealed status."""
        board = field_state["board"]
        revealed = field_state["revealed"]
        
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

    def display_board_start(self):
        """Display the initial board state at game start."""
        console.print(f"\n[bold]Game Board - {self.current_team.title()} Team Goes First[/bold]")
        
        # Create a 5x5 grid
        table = Table(show_header=False, show_lines=True)
        for _ in range(5):
            table.add_column(justify="center", min_width=12)

        for row in range(5):
            row_items = []
            for col in range(5):
                idx = row * 5 + col
                name = self.field[idx]
                row_items.append(f"[white]{name}[/white]")
            table.add_row(*row_items)

        console.print(table)
        
        # Show team info
        red_total = sum(1 for identity in self.identities.values() if identity == "red_target")
        blue_total = sum(1 for identity in self.identities.values() if identity == "blue_target")
        civilian_total = sum(1 for identity in self.identities.values() if identity == "civilian")
        
        console.print(f"\n[red]Red Team:[/red] {red_total} targets")
        console.print(f"[blue]Blue Team:[/blue] {blue_total} targets")
        console.print(f"[dim]Fakes:[/dim] {civilian_total} targets")
        console.print(f"[black on white]Illegal:[/black on white] 1 target")
        console.print("")

    def display_board(self, reveal_all: bool = False):
        """Display the current board state."""
        state = self.get_board_state(reveal_all)

        console.print(
            f"\n[bold]Turn {self.turn_count + 1} - {self.current_team.title()} Team[/bold]"
        )

        # Create a 5x5 grid
        table = Table(show_header=False, show_lines=True)
        for _ in range(5):
            table.add_column()

        for row in range(5):
            row_items = []
            for col in range(5):
                idx = row * 5 + col
                name = state["board"][idx]

                # Color coding based on identity (if revealed or reveal_all)
                if name in state["identities"]:
                    identity = state["identities"][name]
                    if identity == "red_target":
                        color = "red"
                    elif identity == "blue_target":
                        color = "blue"
                    elif identity == "illegal_target":
                        color = "black on white"
                    else:  # civilian
                        color = "dim"
                else:
                    color = "white"

                # Add revealed indicator
                display_name = name
                if self.revealed[name]:
                    display_name = f"[{name}]"

                row_items.append(f"[{color}]{display_name}[/{color}]")

            table.add_row(*row_items)

        console.print(table)

        # Show team counts
        red_remaining = sum(
            1
            for name, identity in self.identities.items()
            if identity == "red_target" and not self.revealed[name]
        )
        blue_remaining = sum(
            1
            for name, identity in self.identities.items()
            if identity == "blue_target" and not self.revealed[name]
        )

        console.print(
            f"\n[red]Red Team Remaining: {red_remaining}[/red]  [blue]Blue Team Remaining: {blue_remaining}[/blue]"
        )

    def get_coach_turn(self) -> Tuple[Optional[str], Optional[int|str]]:
        """Get play and number from the current team's coach."""
        player = self.red_player if self.current_team == "red" else self.blue_player
        prompt_key = f"{self.current_team}_coach"

        # Check if this specific role should be human
        is_human_coach = (self.interactive_mode == f"{self.current_team}-coach")
        
        if is_human_coach:
            # Display the coach prompt first
            board_state = self.get_board_state(reveal_all=True)
            from playbook.prompt_manager import PromptManager
            prompt_manager = PromptManager()
            
            # Calculate remaining targets
            red_remaining = sum(
                1 for name, identity in board_state["identities"].items()
                if identity == "red_target" and not board_state["revealed"].get(name, False)
            )
            blue_remaining = sum(
                1 for name, identity in board_state["identities"].items()
                if identity == "blue_target" and not board_state["revealed"].get(name, False)
            )
            revealed_names = [name for name, revealed in board_state["revealed"].items() if revealed]
            
            # Categorize identities for cleaner prompt formatting
            red_targets = [name for name, identity in board_state["identities"].items() 
                             if identity == "red_target"]
            blue_targets = [name for name, identity in board_state["identities"].items() 
                              if identity == "blue_target"]
            fake_targets = [name for name, identity in board_state["identities"].items() 
                        if identity == "civilian"]
            illegal_target = [name for name, identity in board_state["identities"].items() 
                   if identity == "illegal_target"]
            
            prompt = prompt_manager.load_prompt(
                self.prompt_files[prompt_key],
                {
                    "board": board_state["board"],
                    "revealed": board_state["revealed"],
                    "team": self.current_team,
                    "red_remaining": red_remaining,
                    "blue_remaining": blue_remaining,
                    "revealed_names": ", ".join(revealed_names) if revealed_names else "None",
                    "red_targets": ", ".join(red_targets),
                    "blue_targets": ", ".join(blue_targets),
                    "fake_targets": ", ".join(fake_targets),
                    "illegal_target": ", ".join(illegal_target),
                },
            )
            
            console.print(f"\n[bold]{self.current_team.title()} Coach Turn (Human)[/bold]")
            console.print(f"[yellow]{'='*80}[/yellow]")
            console.print("[yellow]COACH PROMPT:[/yellow]")
            console.print(f"[yellow]{'='*80}[/yellow]")
            console.print(prompt)
            console.print(f"[yellow]{'='*80}[/yellow]\n")

            play = console.input("Enter your play: ").strip()
            number: int|str
            while True:
                try:
                    number_input = console.input("Enter number of related names (or 'unlimited'): ").strip().lower()
                    if number_input == "unlimited":
                        number = "unlimited"
                        break
                    else:
                        number_val = int(number_input)
                        if number_val >= 0:
                            number = number_val
                            break
                        console.print("[red]Number must be 0 or positive[/red]")
                except ValueError:
                    console.print("[red]Please enter a valid number or 'unlimited'[/red]")

            # Validate play with referee if available
            if self.referee_player:
                board_state = self.get_board_state(reveal_all=True)
                validated_play, validated_number, is_valid, reasoning = self._validate_play_with_referee(play, number, board_state)
                if not is_valid:
                    # Record invalid play in history for future reference
                    self.record_play(self.current_team, play, number, invalid=True, invalid_reason=reasoning)
                    # Log the rejected play and end turn
                    log_coach_play(self.current_team, "human", f"REJECTED: {play}", number, self.turn_count, self.starting_team)
                    return None, None  # Signal that turn should end
            
            # Log the play
            log_coach_play(self.current_team, "human", play, number, self.turn_count, self.starting_team)
            return play, number

        else:  # AI Player
            board_state = self.get_board_state(reveal_all=True)
            play, number = player.get_coach_move(
                board_state, self.prompt_files[prompt_key]
            )
            console.print(
                f'[{self.current_team}]{self.current_team.title()} Coach[/{self.current_team}]: "{play}" ({number})'
            )
            
            # Log AI call metadata first (before referee validation) if this is an AI player
            if isinstance(player, AIPlayer):
                metadata = player.get_last_call_metadata()
                if metadata:
                    turn_label = format_turn_label(self.turn_count, self.current_team, self.starting_team)
                    log_ai_call_metadata(
                        game_id=self.game_id,
                        model_name=player.model_name,
                        call_type=metadata["call_type"],
                        team=self.current_team,
                        turn=turn_label,
                        input_tokens=metadata["input_tokens"],
                        output_tokens=metadata["output_tokens"],
                        total_tokens=metadata["total_tokens"],
                        latency_ms=metadata["latency_ms"],
                        openrouter_cost=metadata.get("openrouter_cost", 0.0),
                        upstream_cost=metadata.get("upstream_cost", 0.0),
                        turn_result=metadata.get("turn_result", {}),
                        game_continues=not self.game_over
                    )
            
            # Validate play with referee if available
            if self.referee_player:
                validated_play, validated_number, is_valid, reasoning = self._validate_play_with_referee(play, number, board_state)
                if not is_valid:
                    # Record invalid play in history for future reference
                    self.record_play(self.current_team, play, number, invalid=True, invalid_reason=reasoning)
                    # Log the rejected play and end turn
                    log_coach_play(self.current_team, player.model_name, f"REJECTED: {play}", number, self.turn_count, self.starting_team)
                    return None, None  # Signal that turn should end
            
            # Log the play
            log_coach_play(self.current_team, player.model_name, play, number, self.turn_count, self.starting_team)
            
            return play, number

    def get_player_shots(self, play: str, number: int|str) -> List[str]:
        """Get shots from the current team's player."""
        player = self.red_player if self.current_team == "red" else self.blue_player
        prompt_key = f"{self.current_team}_player"

        # Check if this specific role should be human
        is_human_player = (self.interactive_mode == f"{self.current_team}-player")
        
        if is_human_player:
            # Display the player prompt first
            board_state = self.get_board_state(reveal_all=False)
            from playbook.prompt_manager import PromptManager
            prompt_manager = PromptManager()
            
            # Filter board to only show available (unrevealed) names
            available_names = [
                name for name in board_state["board"] 
                if not board_state["revealed"].get(name, False)
            ]
            
            # Format available names as a simple list
            available_names_formatted = ", ".join(available_names)
            
            prompt = prompt_manager.load_prompt(
                self.prompt_files[prompt_key],
                {
                    "board": board_state,
                    "available_names": available_names_formatted,
                    "play_history": board_state.get("play_history", "None (game just started)"),
                    "play": play,
                    "number": number,
                    "team": self.current_team,
                },
            )
            
            console.print(f"\n[bold]{self.current_team.title()} Player Turn (Human)[/bold]")
            console.print(f"[yellow]{'='*80}[/yellow]")
            console.print("[yellow]PLAYER PROMPT:[/yellow]")
            console.print(f"[yellow]{'='*80}[/yellow]")
            console.print(prompt)
            console.print(f"[yellow]{'='*80}[/yellow]\n")

            shots: List[str] = []
            
            # Determine max shots based on play type
            if number == "unlimited" or number == 0:
                max_shots = len([name for name in self.field if not self.revealed[name]])  # All available names
                min_shots = 1 if number == 0 else 0  # Zero plays require at least one shot
            elif isinstance(number, int):
                max_shots = number + 1  # N+1 rule
                min_shots = 0
            else:
                max_shots = 1  # Fallback
                min_shots = 0

            for i in range(max_shots):
                available_names = [
                    name for name in self.field if not self.revealed[name]
                ]

                console.print(f"\nAvailable names: {', '.join(available_names)}")
                
                # Show appropriate prompt based on clue type
                if number == "unlimited":
                    prompt = f"Shot {i+1} (or 'done' to stop): "
                elif number == 0:
                    if i == 0:
                        prompt = f"Shot {i+1} (required for zero play): "
                    else:
                        prompt = f"Shot {i+1} (or 'done' to stop): "
                else:
                    prompt = f"Shot {i+1}/{max_shots} (or 'done' to stop): "
                
                guess = console.input(prompt).strip()

                if guess.lower() == "done":
                    # Check minimum shot requirement for zero plays
                    if number == 0 and len(shots) == 0:
                        console.print(f"[red]Zero plays require at least one shot[/red]")
                        continue
                    break

                if guess not in available_names:
                    console.print(f"[red]'{guess}' is not available. Try again.[/red]")
                    continue

                shots.append(guess)

                # Process shot immediately
                result = self.process_guess(guess)
                if not result:  # Wrong shot ends turn
                    break

            return shots

        else:  # AI Player
            board_state = self.get_board_state(reveal_all=False)
            shots = player.get_player_moves(
                board_state, play, number, self.prompt_files[prompt_key]
            )

            # Track shot results for metadata logging
            shot_results = []
            
            # Process shots one by one
            for guess in shots:
                console.print(
                    f"[{self.current_team}]{self.current_team.title()} Player[/{self.current_team}] shoots: {guess}"
                )
                result = self.process_guess(guess)
                
                # Track result for metadata
                if guess in self.identities:
                    identity = self.identities[guess]
                    if identity == f"{self.current_team}_target":
                        shot_results.append({"shot": guess, "result": "correct"})
                    elif identity == "illegal_target":
                        shot_results.append({"shot": guess, "result": "illegal_target"})
                    elif identity == "civilian":
                        shot_results.append({"shot": guess, "result": "civilian"})
                    else:  # enemy target
                        shot_results.append({"shot": guess, "result": "enemy"})
                
                if not result:  # Wrong shot ends turn
                    break

            # Log AI call metadata if this is an AI player
            if isinstance(player, AIPlayer):
                metadata = player.get_last_call_metadata()
                if metadata:
                    turn_label = format_turn_label(self.turn_count, self.current_team, self.starting_team)
                    
                    # Add detailed results from processing shots
                    turn_result = metadata.get("turn_result", {})
                    turn_result.update({
                        "correct_shots": sum(1 for r in shot_results if r["result"] == "correct"),
                        "civilian_hits": sum(1 for r in shot_results if r["result"] == "civilian"),
                        "enemy_hits": sum(1 for r in shot_results if r["result"] == "enemy"),
                        "illegal_target_hits": sum(1 for r in shot_results if r["result"] == "illegal_target"),
                        "shot_details": shot_results
                    })
                    
                    log_ai_call_metadata(
                        game_id=self.game_id,
                        model_name=player.model_name,
                        call_type=metadata["call_type"],
                        team=self.current_team,
                        turn=turn_label,
                        input_tokens=metadata["input_tokens"],
                        output_tokens=metadata["output_tokens"],
                        total_tokens=metadata["total_tokens"],
                        latency_ms=metadata["latency_ms"],
                        openrouter_cost=metadata.get("openrouter_cost", 0.0),
                        upstream_cost=metadata.get("upstream_cost", 0.0),
                        turn_result=turn_result,
                        game_continues=not self.game_over
                    )

            return shots

    def process_guess(self, name: str) -> bool:
        """Process a single guess and return True if correct, False if wrong."""
        if name not in self.identities:
            logger.warning(f"Invalid guess: {name}")
            return False

        identity = self.identities[name]
        self.revealed[name] = True

        # Log the move
        move = {
            "team": self.current_team,
            "name": name,
            "identity": identity,
            "correct": identity == f"{self.current_team}_target",
        }
        self.moves_log.append(move)

        # Record guess outcome for clue history
        correct = identity == f"{self.current_team}_target"
        self.record_shot_outcome(name, identity, correct)

        # Determine result type for logging
        player = self.red_player if self.current_team == "red" else self.blue_player
        model_name = player.model_name if hasattr(player, 'model_name') else "human"

        if identity == "illegal_target":
            console.print(
                f"[black on white]💀 THE ILLEGAL TARGET! {self.current_team.title()} team loses![/black on white]"
            )
            log_player_shot(self.current_team, model_name, name, "illegal_target", self.turn_count, self.starting_team)
            self.game_over = True
            self.winner = "blue" if self.current_team == "red" else "red"
            return False

        elif identity == f"{self.current_team}_target":
            console.print(f"[green]✓ Correct! {name} scores 1 goal![/green]")
            log_player_shot(self.current_team, model_name, name, "correct", self.turn_count, self.starting_team)

            # Check win condition
            remaining = sum(
                1
                for n, i in self.identities.items()
                if i == f"{self.current_team}_target" and not self.revealed[n]
            )
            if remaining == 0:
                console.print(
                    f"[green]🎉 {self.current_team.title()} team wins![/green]"
                )
                self.game_over = True
                self.winner = self.current_team

            return True

        else:
            if identity == "civilian":
                console.print(f"[yellow]✗ {name} is a fake.[/yellow]")
                log_player_shot(self.current_team, model_name, name, "civilian", self.turn_count, self.starting_team)
            else:
                console.print(f"[dim]✗ {name} is an own goal.[/dim]")
                log_player_shot(self.current_team, model_name, name, "enemy", self.turn_count, self.starting_team)
                
                # Check if the opposing team just won by having this team hit their target
                opposing_team = "blue" if self.current_team == "red" else "red"
                remaining = sum(
                    1
                    for n, i in self.identities.items()
                    if i == f"{opposing_team}_target" and not self.revealed[n]
                )
                if remaining == 0:
                    console.print(
                        f"[green]🎉 {opposing_team.title()} team wins![/green]"
                    )
                    self.game_over = True
                    self.winner = opposing_team
                    
            return False

    def get_remaining_targets(self):
        """Get remaining target counts for both teams."""
        red_remaining = sum(
            1 for name, identity in self.identities.items()
            if identity == "red_target" and not self.revealed[name]
        )
        blue_remaining = sum(
            1 for name, identity in self.identities.items()
            if identity == "blue_target" and not self.revealed[name]
        )
        return red_remaining, blue_remaining

    def display_game_status(self):
        """Display the current game status showing remaining targets."""
        red_remaining, blue_remaining = self.get_remaining_targets()
        
        # Always show starting team first
        if self.starting_team == "red":
            console.print(f"[bold]Status:[/bold] [red]Red {red_remaining}[/red], [blue]Blue {blue_remaining}[/blue]")
        else:
            console.print(f"[bold]Status:[/bold] [blue]Blue {blue_remaining}[/blue], [red]Red {red_remaining}[/red]")
        console.print("")

    def record_play(self, team: str, play: str, number: int|str, invalid: bool = False, invalid_reason: str = ""):
        """Record a play for the game history."""
        play_entry = {
            "turn": self.turn_count,
            "team": team,
            "play": play,
            "number": number,
            "shots": [],
            "invalid": invalid,
            "invalid_reason": invalid_reason
        }
        self.play_history.append(play_entry)

    def record_shot_outcome(self, name: str, identity: str, correct: bool):
        """Record the outcome of a shot for the current play."""
        if self.play_history:
            current_play = self.play_history[-1]
            outcome = "correct" if correct else ("enemy" if identity.endswith("_target") else ("civilian" if identity == "civilian" else "illegal_target"))
            current_play["shots"].append({
                "name": name,
                "identity": identity,
                "outcome": outcome
            })

    def format_play_history(self) -> str:
        """Format the play history for display to players."""
        if not self.play_history:
            return "None (game just started)"
        
        history_lines = []
        for entry in self.play_history:
            turn_letter = "a" if entry["team"] == self.starting_team else "b"
            turn_label = f"Turn {entry['turn'] + 1}{turn_letter}"
            
            # Format the clue line
            if entry.get("invalid", False):
                play_line = f"{turn_label}: {entry['team'].title()} Play: \"{entry['play']}\" ({entry['number']}) [INVALID: {entry.get('invalid_reason', 'rule violation')}]"
            else:
                play_line = f"{turn_label}: {entry['team'].title()} Play: \"{entry['play']}\" ({entry['number']})"
            history_lines.append(play_line)
            
            # Format the outcomes
            if entry.get("invalid", False):
                history_lines.append("  → Turn ended due to invalid play")
            elif entry["shots"]:
                outcomes = []
                for shot in entry["shots"]:
                    if shot["outcome"] == "correct":
                        outcomes.append(f"{shot['name']} ✓")
                    elif shot["outcome"] == "enemy":
                        outcomes.append(f"{shot['name']} ✗ (enemy)")
                    elif shot["outcome"] == "civilian":
                        outcomes.append(f"{shot['name']} ○ (civilian)")
                    # Note: illegal_target outcomes end the game, so we don't need to handle them here
                
                if outcomes:
                    history_lines.append(f"  → {', '.join(outcomes)}")
            else:
                history_lines.append("  → No shots taken")
            
            history_lines.append("")  # Empty line for spacing
        
        return "\n".join(history_lines).strip()

    def _validate_play_with_referee(self, play: str, number: int|str, board_state: Dict) -> Tuple[str, int|str, bool, str]:
        """Validate play with referee and handle invalid plays. Returns (play, number, is_valid, reasoning)."""
        try:
            if self.interactive_mode == "referee":
                # Human referee validation
                from playbook.prompt_manager import PromptManager
                prompt_manager = PromptManager()
                
                # Get team's allied targets
                allied_targets = [
                    name for name, identity in board_state["identities"].items()
                    if identity == f"{self.current_team}_target"
                ]
                
                prompt = prompt_manager.load_prompt(
                    self.prompt_files["referee"],
                    {
                        "play": play,
                        "number": number,
                        "team": self.current_team,
                        "board": board_state["board"],
                        "allied_targets": ", ".join(allied_targets),
                    },
                )
                
                console.print(f"\n[bold]Referee Validation (Human)[/bold]")
                console.print(f"Team: {self.current_team.title()}")
                console.print(f'Play: "{play}" ({number})')
                console.print(f"[yellow]{'='*80}[/yellow]")
                console.print("[yellow]REFEREE PROMPT:[/yellow]")
                console.print(f"[yellow]{'='*80}[/yellow]")
                console.print(prompt)
                console.print(f"[yellow]{'='*80}[/yellow]\n")
                
                while True:
                    decision = console.input("Is this play valid? (y/n): ").strip().lower()
                    if decision in ['y', 'yes']:
                        reasoning = console.input("Reasoning (optional): ").strip() or "Play approved by human referee"
                        is_valid = True
                        break
                    elif decision in ['n', 'no']:
                        reasoning = console.input("Violation reasoning: ").strip() or "Rule violation detected by human referee"
                        is_valid = False
                        break
                    else:
                        console.print("[red]Please enter 'y' or 'n'[/red]")
            else:
                # AI referee validation
                is_valid, reasoning = self.referee_player.get_referee_validation(
                    play, number, self.current_team, board_state, self.prompt_files["referee"]
                )
                
                # If first referee flags as invalid, do second review with Gemini 2.5 Pro
                if not is_valid and self.referee_player is not None:
                    console.print(f"[yellow]🔄 First referee flagged play as invalid. Getting second opinion from Gemini 2.5 Pro...[/yellow]")
                    
                    # Create a temporary Gemini 2.5 Pro player for second review
                    review_referee = AIPlayer("gemini-2.5")
                    
                    # Get second opinion with same prompt
                    review_valid, review_reasoning = review_referee.get_referee_validation(
                        play, number, self.current_team, board_state, self.prompt_files["referee"]
                    )
                    
                    # Log the review referee metadata
                    review_metadata = review_referee.get_last_call_metadata()
                    if review_metadata:
                        turn_label = format_turn_label(self.turn_count, self.current_team, self.starting_team)
                        
                        # Update turn result with review referee validation outcome
                        turn_result = review_metadata.get("turn_result", {})
                        turn_result.update({
                            "evaluated_play": play,
                            "evaluated_number": number,
                            "review_referee": True,
                            "first_referee_model": self.referee_player.model_name,
                            "first_referee_decision": "invalid",
                            "first_referee_reasoning": reasoning
                        })
                        
                        log_ai_call_metadata(
                            game_id=self.game_id,
                            model_name=review_referee.model_name,
                            call_type=review_metadata["call_type"],
                            team=f"review_referee_{self.current_team}",
                            turn=turn_label,
                            input_tokens=review_metadata["input_tokens"],
                            output_tokens=review_metadata["output_tokens"],
                            total_tokens=review_metadata["total_tokens"],
                            latency_ms=review_metadata["latency_ms"],
                            openrouter_cost=review_metadata.get("openrouter_cost", 0.0),
                            upstream_cost=review_metadata.get("upstream_cost", 0.0),
                            turn_result=turn_result,
                            game_continues=not self.game_over
                        )
                    
                    if review_valid:
                        # Second referee says it's valid - override first decision
                        console.print(f"[green]✅ The ruling is overturned![/green]")
                        console.print(f"[dim]First referee ({self.referee_player.model_name}) - {reasoning}[/dim]")
                        console.print(f"[dim]Review referee: {review_reasoning}[/dim]")
                        is_valid = True
                        reasoning = f"Approved on review by Gemini 2.5 Pro: {review_reasoning}"
                    else:
                        # Both referees say invalid - reject the play
                        console.print(f"[yellow]❌ The ruling on the play stands![/yellow]")
                        console.print(f"[dim]First referee ({self.referee_player.model_name}): {reasoning}[/dim]")
                        console.print(f"[dim]Review referee: {review_reasoning}[/dim]")
                        reasoning = f"Upheld on review. First: {reasoning}. Review: {review_reasoning}"
            
            # Log AI call metadata for referee validation
            if isinstance(self.referee_player, AIPlayer):
                metadata = self.referee_player.get_last_call_metadata()
                if metadata:
                    turn_label = format_turn_label(self.turn_count, self.current_team, self.starting_team)
                    
                    # Update turn result with referee validation outcome
                    turn_result = metadata.get("turn_result", {})
                    turn_result.update({
                        "evaluated_play": play,
                        "evaluated_number": number
                    })
                    
                    log_ai_call_metadata(
                        game_id=self.game_id,
                        model_name=self.referee_player.model_name,
                        call_type=metadata["call_type"],
                        team=f"referee_{self.current_team}",  # Include which team's play was evaluated
                        turn=turn_label,
                        input_tokens=metadata["input_tokens"],
                        output_tokens=metadata["output_tokens"],
                        total_tokens=metadata["total_tokens"],
                        latency_ms=metadata["latency_ms"],
                        openrouter_cost=metadata.get("openrouter_cost", 0.0),
                        upstream_cost=metadata.get("upstream_cost", 0.0),
                        turn_result=turn_result,
                        game_continues=not self.game_over
                    )
            
            if is_valid:
                return play, number, True, reasoning
            else:
                #console.print(f"[red]🔴 Referee: Play REJECTED - {reasoning}[/red]")
                console.print(f"⚠️  Turn ended due to invalid play")
                log_referee_rejection(self.current_team, play, number, reasoning)
                return play, number, False, reasoning
                
        except Exception as e:
            logger.error(f"Error in referee validation: {e}")
            console.print(f"[yellow]⚠️  Referee error, allowing original play[/yellow]")
            return play, number, True, "Referee error - play allowed"

    def apply_invalid_play_penalty(self):
        """Apply penalty for invalid play: remove one of the opposing team's targets."""
        # Get opposing team
        opposing_team = "blue" if self.current_team == "red" else "red"
        
        # Find unrevealed opposing team targets
        opposing_targets = [
            name for name, identity in self.identities.items()
            if identity == f"{opposing_team}_target" and not self.revealed[name]
        ]
        
        if opposing_targets:
            # Randomly select one to remove
            penalty_target = random.choice(opposing_targets)
            self.revealed[penalty_target] = True
            
            console.print(f"[dim]⚖️  PENALTY: {penalty_target} revealed for {opposing_team.upper()} team due to invalid play[/dim]")
            
            # Log the penalty action
            log_referee_penalty(self.current_team, opposing_team, penalty_target)
            
            logger.info(f"Invalid play penalty applied: revealed {penalty_target} for {opposing_team} team")
            
            return penalty_target
        else:
            console.print(f"[yellow]⚖️  PENALTY: No unrevealed {opposing_team.upper()} targets to remove[/yellow]")
            logger.info(f"Invalid play penalty: no unrevealed {opposing_team} targets available")
            return None

    def switch_teams(self):
        """Switch to the other team."""
        # Log status before switching
        red_remaining, blue_remaining = self.get_remaining_targets()
        log_turn_end_status(red_remaining, blue_remaining)
        
        # Display game status to terminal
        self.display_game_status()
        
        self.current_team = "blue" if self.current_team == "red" else "red"
        self.turn_count += 1

    def play(self) -> Dict:
        """Play a complete game and return results."""
        self.start_time = time.time()

        logger.info("Starting new Switchboard game")
        self.setup_board()
        
        # Log game start
        red_model = self.red_player.model_name if hasattr(self.red_player, 'model_name') else "human"
        blue_model = self.blue_player.model_name if hasattr(self.blue_player, 'model_name') else "human"
        log_game_start(self.game_id, red_model, blue_model, self.field, self.identities)
        
        # Log game setup metadata
        log_game_setup_metadata(self.game_id, red_model, blue_model, self.prompt_files, self.field, self.identities)

        console.print("[bold]🎯 The Playbook Game Starting![/bold]")
        console.print(f"[red]Red Team:[/red] {red_model}")
        console.print(f"  • Coach: {self.prompt_files.get('red_coach', 'default')}")
        console.print(f"  • Player: {self.prompt_files.get('red_player', 'default')}")
        console.print(f"[blue]Blue Team:[/blue] {blue_model}")
        console.print(f"  • Coach: {self.prompt_files.get('blue_coach', 'default')}")
        console.print(f"  • Player: {self.prompt_files.get('blue_player', 'default')}")
        if self.referee_player:
            referee_model = self.referee_player.model_name if hasattr(self.referee_player, 'model_name') else "human"
            console.print(f"[yellow]Referee:[/yellow] {referee_model} ({self.prompt_files.get('referee', 'default')})")
        else:
            console.print("[yellow]Referee:[/yellow] Disabled")
        console.print(f"[green]Game ID:[/green] {self.game_id}")
        console.print()
        
        # Display the initial board
        self.display_board_start()

        while not self.game_over:
            # Coach phase
            play, number = self.get_coach_turn()
            
            # Check if play was rejected by referee
            if play is None or number is None:
                # Play was rejected, apply penalty and end turn immediately
                self.apply_invalid_play_penalty()
                self.switch_teams()
                continue

            # Record the play for history tracking
            self.record_play(self.current_team, play, number)

            # Player phase - play and number are guaranteed to be non-None at this point
            shots = self.get_player_shots(play, number)

            if not self.game_over:
                self.switch_teams()

        self.end_time = time.time()
        duration = self.end_time - self.start_time

        # Compile results
        result = {
            "winner": self.winner,
            "turns": self.turn_count,
            "duration": duration,
            "moves": self.moves_log,
            "final_board": self.get_board_state(reveal_all=True),
        }

        # Log game end and box score
        log_game_end(self.winner or "draw", self.turn_count, duration)
        log_box_score(self.game_id, red_model, blue_model, result)

        logger.info(f"Game completed. Winner: {self.winner}, Turns: {self.turn_count}")
        return result
