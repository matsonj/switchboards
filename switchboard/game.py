"""Core game logic for The Switchboard."""

import logging
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from rich.console import Console
from rich.table import Table

from switchboard.player import AIPlayer, HumanPlayer
from switchboard.utils.logging import (
    log_game_start, log_operator_clue, log_lineman_guess, 
    log_game_end, log_box_score, log_turn_end_status, log_umpire_rejection, log_umpire_penalty,
    log_ai_call_metadata, format_turn_label, log_game_setup_metadata
)

console = Console()
logger = logging.getLogger(__name__)


class SwitchboardGame:
    """The main game class that manages a complete Switchboard game."""

    BOARD_SIZE = 25
    STARTING_TEAM_SUBSCRIBERS = 9  # Team that goes first gets 9
    SECOND_TEAM_SUBSCRIBERS = 8    # Team that goes second gets 8
    INNOCENT_CIVILIANS = 7
    MOLES = 1

    def __init__(
        self,
        names_file: str,
        red_player,
        blue_player,
        umpire_player=None,
        red_operator_prompt: str = "",
        red_lineman_prompt: str = "",
        blue_operator_prompt: str = "",
        blue_lineman_prompt: str = "",
        umpire_prompt: str = "",
        interactive_mode: Optional[str] = None,
    ):
        self.names_file = names_file
        self.red_player = red_player
        self.blue_player = blue_player
        self.umpire_player = umpire_player
        self.interactive_mode = interactive_mode
        self.prompt_files = {
            "red_operator": red_operator_prompt,
            "red_lineman": red_lineman_prompt,
            "blue_operator": blue_operator_prompt,
            "blue_lineman": blue_lineman_prompt,
            "umpire": umpire_prompt,
        }

        # Game state
        self.board: List[str] = []
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
        self.clue_history: List[Dict] = []
        
        # Generate unique game ID
        import uuid
        self.game_id = str(uuid.uuid4())[:8]

    def load_names(self) -> List[str]:
        """Load names from YAML file."""
        try:
            with open(self.names_file, "r") as f:
                data = yaml.safe_load(f)
                names = data.get("names", [])
                if len(names) < self.BOARD_SIZE:
                    raise ValueError(
                        f"Need at least {self.BOARD_SIZE} names, got {len(names)}"
                    )
                return names
        except FileNotFoundError:
            logger.error(f"Names file not found: {self.names_file}")
            raise
        except Exception as e:
            logger.error(f"Error loading names: {e}")
            raise

    def setup_board(self):
        """Initialize the game board with random name assignment."""
        all_names = self.load_names()

        # Select 25 random names
        self.board = random.sample(all_names, self.BOARD_SIZE)

        # Assign identities
        positions = list(range(self.BOARD_SIZE))
        random.shuffle(positions)

        # Assign allied subscribers based on who starts first
        if self.starting_team == "red":
            red_count = self.STARTING_TEAM_SUBSCRIBERS
            blue_count = self.SECOND_TEAM_SUBSCRIBERS
        else:
            red_count = self.SECOND_TEAM_SUBSCRIBERS
            blue_count = self.STARTING_TEAM_SUBSCRIBERS
        
        red_positions = positions[:red_count]
        blue_positions = positions[red_count:red_count + blue_count]

        # Assign mole and civilians
        remaining_positions = positions[red_count + blue_count:]
        mole_position = remaining_positions[0]
        civilian_positions = remaining_positions[1 : 1 + self.INNOCENT_CIVILIANS]

        # Create identity mapping
        self.identities = {}
        self.revealed = {}

        for i, name in enumerate(self.board):
            if i in red_positions:
                self.identities[name] = "red_subscriber"
            elif i in blue_positions:
                self.identities[name] = "blue_subscriber"
            elif i == mole_position:
                self.identities[name] = "mole"
            else:
                self.identities[name] = "civilian"

            self.revealed[name] = False

        logger.info(
            f"Board setup complete. Starting team: {self.starting_team.upper()}. Red: {len(red_positions)}, Blue: {len(blue_positions)}, Civilians: {len(civilian_positions)}, Mole: 1"
        )

    def get_board_state(self, reveal_all: bool = False) -> Dict[str, Any]:
        """Get current board state for display."""
        identities: Dict[str, str] = {} if not reveal_all else self.identities.copy()

        # Add revealed identities
        if not reveal_all:
            for name in self.board:
                if self.revealed.get(name, False):
                    identities[name] = self.identities[name]

        state = {
            "board": self.board.copy(),
            "revealed": self.revealed.copy(),
            "identities": identities,
            "current_team": self.current_team,
            "turn_count": self.turn_count,
            "clue_history": self.format_clue_history(),
        }

        return state

    def _format_board_for_lineman_cli(self, board_state: dict) -> str:
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
                name = self.board[idx]
                row_items.append(f"[white]{name}[/white]")
            table.add_row(*row_items)

        console.print(table)
        
        # Show team info
        red_total = sum(1 for identity in self.identities.values() if identity == "red_subscriber")
        blue_total = sum(1 for identity in self.identities.values() if identity == "blue_subscriber")
        civilian_total = sum(1 for identity in self.identities.values() if identity == "civilian")
        
        console.print(f"\n[red]Red Team:[/red] {red_total} subscribers")
        console.print(f"[blue]Blue Team:[/blue] {blue_total} subscribers")
        console.print(f"[dim]Civilians:[/dim] {civilian_total}")
        console.print(f"[black on white]The Mole:[/black on white] 1")
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
                name = self.board[idx]

                # Color coding based on identity (if revealed or reveal_all)
                if name in state["identities"]:
                    identity = state["identities"][name]
                    if identity == "red_subscriber":
                        color = "red"
                    elif identity == "blue_subscriber":
                        color = "blue"
                    elif identity == "mole":
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
            if identity == "red_subscriber" and not self.revealed[name]
        )
        blue_remaining = sum(
            1
            for name, identity in self.identities.items()
            if identity == "blue_subscriber" and not self.revealed[name]
        )

        console.print(
            f"\n[red]Red Team Remaining: {red_remaining}[/red]  [blue]Blue Team Remaining: {blue_remaining}[/blue]"
        )

    def get_operator_turn(self) -> Tuple[Optional[str], Optional[int|str]]:
        """Get clue and number from the current team's operator."""
        player = self.red_player if self.current_team == "red" else self.blue_player
        prompt_key = f"{self.current_team}_operator"

        # Check if this specific role should be human
        is_human_operator = (self.interactive_mode == f"{self.current_team}-operator")
        
        if is_human_operator:
            # Display the operator prompt first
            board_state = self.get_board_state(reveal_all=True)
            from switchboard.prompt_manager import PromptManager
            prompt_manager = PromptManager()
            
            # Calculate remaining subscribers
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
                self.prompt_files[prompt_key],
                {
                    "board": board_state["board"],
                    "revealed": board_state["revealed"],
                    "team": self.current_team,
                    "red_remaining": red_remaining,
                    "blue_remaining": blue_remaining,
                    "revealed_names": ", ".join(revealed_names) if revealed_names else "None",
                    "red_subscribers": ", ".join(red_subscribers),
                    "blue_subscribers": ", ".join(blue_subscribers),
                    "civilians": ", ".join(civilians),
                    "mole": ", ".join(mole),
                },
            )
            
            console.print(f"\n[bold]{self.current_team.title()} Operator Turn (Human)[/bold]")
            console.print(f"[yellow]{'='*80}[/yellow]")
            console.print("[yellow]OPERATOR PROMPT:[/yellow]")
            console.print(f"[yellow]{'='*80}[/yellow]")
            console.print(prompt)
            console.print(f"[yellow]{'='*80}[/yellow]\n")

            clue = console.input("Enter your clue: ").strip()
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

            # Validate clue with umpire if available
            if self.umpire_player:
                board_state = self.get_board_state(reveal_all=True)
                validated_clue, validated_number, is_valid, reasoning = self._validate_clue_with_umpire(clue, number, board_state)
                if not is_valid:
                    # Record invalid clue in history for future reference
                    self.record_clue(self.current_team, clue, number, invalid=True, invalid_reason=reasoning)
                    # Log the rejected clue and end turn
                    log_operator_clue(self.current_team, "human", f"REJECTED: {clue}", number, self.turn_count, self.starting_team)
                    return None, None  # Signal that turn should end
            
            # Log the clue
            log_operator_clue(self.current_team, "human", clue, number, self.turn_count, self.starting_team)
            return clue, number

        else:  # AI Player
            board_state = self.get_board_state(reveal_all=True)
            clue, number = player.get_operator_move(
                board_state, self.prompt_files[prompt_key]
            )
            console.print(
                f'[{self.current_team}]{self.current_team.title()} Operator[/{self.current_team}]: "{clue}" ({number})'
            )
            
            # Log AI call metadata first (before umpire validation) if this is an AI player
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
            
            # Validate clue with umpire if available
            if self.umpire_player:
                validated_clue, validated_number, is_valid, reasoning = self._validate_clue_with_umpire(clue, number, board_state)
                if not is_valid:
                    # Record invalid clue in history for future reference
                    self.record_clue(self.current_team, clue, number, invalid=True, invalid_reason=reasoning)
                    # Log the rejected clue and end turn
                    log_operator_clue(self.current_team, player.model_name, f"REJECTED: {clue}", number, self.turn_count, self.starting_team)
                    return None, None  # Signal that turn should end
            
            # Log the clue
            log_operator_clue(self.current_team, player.model_name, clue, number, self.turn_count, self.starting_team)
            
            return clue, number

    def get_lineman_guesses(self, clue: str, number: int|str) -> List[str]:
        """Get guesses from the current team's lineman."""
        player = self.red_player if self.current_team == "red" else self.blue_player
        prompt_key = f"{self.current_team}_lineman"

        # Check if this specific role should be human
        is_human_lineman = (self.interactive_mode == f"{self.current_team}-lineman")
        
        if is_human_lineman:
            # Display the lineman prompt first
            board_state = self.get_board_state(reveal_all=False)
            from switchboard.prompt_manager import PromptManager
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
                    "board": self._format_board_for_lineman_cli(board_state),
                    "available_names": available_names_formatted,
                    "clue_history": board_state.get("clue_history", "None (game just started)"),
                    "clue": clue,
                    "number": number,
                    "team": self.current_team,
                },
            )
            
            console.print(f"\n[bold]{self.current_team.title()} Lineman Turn (Human)[/bold]")
            console.print(f"[yellow]{'='*80}[/yellow]")
            console.print("[yellow]LINEMAN PROMPT:[/yellow]")
            console.print(f"[yellow]{'='*80}[/yellow]")
            console.print(prompt)
            console.print(f"[yellow]{'='*80}[/yellow]\n")

            guesses: List[str] = []
            
            # Determine max guesses based on clue type
            if number == "unlimited" or number == 0:
                max_guesses = len([name for name in self.board if not self.revealed[name]])  # All available names
                min_guesses = 1 if number == 0 else 0  # Zero clues require at least one guess
            elif isinstance(number, int):
                max_guesses = number + 1  # N+1 rule
                min_guesses = 0
            else:
                max_guesses = 1  # Fallback
                min_guesses = 0

            for i in range(max_guesses):
                available_names = [
                    name for name in self.board if not self.revealed[name]
                ]

                console.print(f"\nAvailable names: {', '.join(available_names)}")
                
                # Show appropriate prompt based on clue type
                if number == "unlimited":
                    prompt = f"Guess {i+1} (or 'done' to stop): "
                elif number == 0:
                    if i == 0:
                        prompt = f"Guess {i+1} (required for zero clue): "
                    else:
                        prompt = f"Guess {i+1} (or 'done' to stop): "
                else:
                    prompt = f"Guess {i+1}/{max_guesses} (or 'done' to stop): "
                
                guess = console.input(prompt).strip()

                if guess.lower() == "done":
                    # Check minimum guess requirement for zero clues
                    if number == 0 and len(guesses) == 0:
                        console.print(f"[red]Zero clues require at least one guess[/red]")
                        continue
                    break

                if guess not in available_names:
                    console.print(f"[red]'{guess}' is not available. Try again.[/red]")
                    continue

                guesses.append(guess)

                # Process guess immediately
                result = self.process_guess(guess)
                if not result:  # Wrong guess ends turn
                    break

            return guesses

        else:  # AI Player
            board_state = self.get_board_state(reveal_all=False)
            guesses = player.get_lineman_moves(
                board_state, clue, number, self.prompt_files[prompt_key]
            )

            # Track guess results for metadata logging
            guess_results = []
            
            # Process guesses one by one
            for guess in guesses:
                console.print(
                    f"[{self.current_team}]{self.current_team.title()} Lineman[/{self.current_team}] guesses: {guess}"
                )
                result = self.process_guess(guess)
                
                # Track result for metadata
                if guess in self.identities:
                    identity = self.identities[guess]
                    if identity == f"{self.current_team}_subscriber":
                        guess_results.append({"guess": guess, "result": "correct"})
                    elif identity == "mole":
                        guess_results.append({"guess": guess, "result": "mole"})
                    elif identity == "civilian":
                        guess_results.append({"guess": guess, "result": "civilian"})
                    else:  # enemy subscriber
                        guess_results.append({"guess": guess, "result": "enemy"})
                
                if not result:  # Wrong guess ends turn
                    break

            # Log AI call metadata if this is an AI player
            if isinstance(player, AIPlayer):
                metadata = player.get_last_call_metadata()
                if metadata:
                    turn_label = format_turn_label(self.turn_count, self.current_team, self.starting_team)
                    
                    # Add detailed results from processing guesses
                    turn_result = metadata.get("turn_result", {})
                    turn_result.update({
                        "correct_guesses": sum(1 for r in guess_results if r["result"] == "correct"),
                        "civilian_hits": sum(1 for r in guess_results if r["result"] == "civilian"),
                        "enemy_hits": sum(1 for r in guess_results if r["result"] == "enemy"),
                        "mole_hits": sum(1 for r in guess_results if r["result"] == "mole"),
                        "guess_details": guess_results
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

            return guesses

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
            "correct": identity == f"{self.current_team}_subscriber",
        }
        self.moves_log.append(move)

        # Record guess outcome for clue history
        correct = identity == f"{self.current_team}_subscriber"
        self.record_guess_outcome(name, identity, correct)

        # Determine result type for logging
        player = self.red_player if self.current_team == "red" else self.blue_player
        model_name = player.model_name if hasattr(player, 'model_name') else "human"

        if identity == "mole":
            console.print(
                f"[black on white]💀 THE MOLE! {self.current_team.title()} team loses![/black on white]"
            )
            log_lineman_guess(self.current_team, model_name, name, "mole", self.turn_count, self.starting_team)
            self.game_over = True
            self.winner = "blue" if self.current_team == "red" else "red"
            return False

        elif identity == f"{self.current_team}_subscriber":
            console.print(f"[green]✓ Correct! {name} is an Allied Subscriber[/green]")
            log_lineman_guess(self.current_team, model_name, name, "correct", self.turn_count, self.starting_team)

            # Check win condition
            remaining = sum(
                1
                for n, i in self.identities.items()
                if i == f"{self.current_team}_subscriber" and not self.revealed[n]
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
                console.print(f"[yellow]✗ {name} is an Innocent Civilian[/yellow]")
                log_lineman_guess(self.current_team, model_name, name, "civilian", self.turn_count, self.starting_team)
            else:
                console.print(f"[red]✗ {name} belongs to the other team[/red]")
                log_lineman_guess(self.current_team, model_name, name, "enemy", self.turn_count, self.starting_team)
            return False

    def get_remaining_subscribers(self):
        """Get remaining subscriber counts for both teams."""
        red_remaining = sum(
            1 for name, identity in self.identities.items()
            if identity == "red_subscriber" and not self.revealed[name]
        )
        blue_remaining = sum(
            1 for name, identity in self.identities.items()
            if identity == "blue_subscriber" and not self.revealed[name]
        )
        return red_remaining, blue_remaining

    def display_game_status(self):
        """Display the current game status showing remaining subscribers."""
        red_remaining, blue_remaining = self.get_remaining_subscribers()
        
        # Always show starting team first
        if self.starting_team == "red":
            console.print(f"[bold]Status:[/bold] [red]Red {red_remaining}[/red], [blue]Blue {blue_remaining}[/blue]")
        else:
            console.print(f"[bold]Status:[/bold] [blue]Blue {blue_remaining}[/blue], [red]Red {red_remaining}[/red]")
        console.print("")

    def record_clue(self, team: str, clue: str, number: int|str, invalid: bool = False, invalid_reason: str = ""):
        """Record a clue for the game history."""
        clue_entry = {
            "turn": self.turn_count,
            "team": team,
            "clue": clue,
            "number": number,
            "guesses": [],
            "invalid": invalid,
            "invalid_reason": invalid_reason
        }
        self.clue_history.append(clue_entry)

    def record_guess_outcome(self, name: str, identity: str, correct: bool):
        """Record the outcome of a guess for the current clue."""
        if self.clue_history:
            current_clue = self.clue_history[-1]
            outcome = "correct" if correct else ("enemy" if identity.endswith("_subscriber") else ("civilian" if identity == "civilian" else "mole"))
            current_clue["guesses"].append({
                "name": name,
                "identity": identity,
                "outcome": outcome
            })

    def format_clue_history(self) -> str:
        """Format the clue history for display to linemen."""
        if not self.clue_history:
            return "None (game just started)"
        
        history_lines = []
        for entry in self.clue_history:
            turn_letter = "a" if entry["team"] == self.starting_team else "b"
            turn_label = f"Turn {entry['turn'] + 1}{turn_letter}"
            
            # Format the clue line
            if entry.get("invalid", False):
                clue_line = f"{turn_label}: {entry['team'].title()} Clue: \"{entry['clue']}\" ({entry['number']}) [INVALID: {entry.get('invalid_reason', 'rule violation')}]"
            else:
                clue_line = f"{turn_label}: {entry['team'].title()} Clue: \"{entry['clue']}\" ({entry['number']})"
            history_lines.append(clue_line)
            
            # Format the outcomes
            if entry.get("invalid", False):
                history_lines.append("  → Turn ended due to invalid clue")
            elif entry["guesses"]:
                outcomes = []
                for guess in entry["guesses"]:
                    if guess["outcome"] == "correct":
                        outcomes.append(f"{guess['name']} ✓")
                    elif guess["outcome"] == "enemy":
                        outcomes.append(f"{guess['name']} ✗ (enemy)")
                    elif guess["outcome"] == "civilian":
                        outcomes.append(f"{guess['name']} ○ (civilian)")
                    # Note: mole outcomes end the game, so we don't need to handle them here
                
                if outcomes:
                    history_lines.append(f"  → {', '.join(outcomes)}")
            else:
                history_lines.append("  → No guesses made")
            
            history_lines.append("")  # Empty line for spacing
        
        return "\n".join(history_lines).strip()

    def _validate_clue_with_umpire(self, clue: str, number: int|str, board_state: Dict) -> Tuple[str, int|str, bool, str]:
        """Validate clue with umpire and handle invalid clues. Returns (clue, number, is_valid, reasoning)."""
        try:
            if self.interactive_mode == "umpire":
                # Human umpire validation
                from switchboard.prompt_manager import PromptManager
                prompt_manager = PromptManager()
                
                # Get team's allied subscribers
                allied_subscribers = [
                    name for name, identity in board_state["identities"].items()
                    if identity == f"{self.current_team}_subscriber"
                ]
                
                prompt = prompt_manager.load_prompt(
                    self.prompt_files["umpire"],
                    {
                        "clue": clue,
                        "number": number,
                        "team": self.current_team,
                        "board": board_state["board"],
                        "allied_subscribers": ", ".join(allied_subscribers),
                    },
                )
                
                console.print(f"\n[bold]Umpire Validation (Human)[/bold]")
                console.print(f"Team: {self.current_team.title()}")
                console.print(f'Clue: "{clue}" ({number})')
                console.print(f"[yellow]{'='*80}[/yellow]")
                console.print("[yellow]UMPIRE PROMPT:[/yellow]")
                console.print(f"[yellow]{'='*80}[/yellow]")
                console.print(prompt)
                console.print(f"[yellow]{'='*80}[/yellow]\n")
                
                while True:
                    decision = console.input("Is this clue valid? (y/n): ").strip().lower()
                    if decision in ['y', 'yes']:
                        reasoning = console.input("Reasoning (optional): ").strip() or "Clue approved by human umpire"
                        is_valid = True
                        break
                    elif decision in ['n', 'no']:
                        reasoning = console.input("Violation reasoning: ").strip() or "Rule violation detected by human umpire"
                        is_valid = False
                        break
                    else:
                        console.print("[red]Please enter 'y' or 'n'[/red]")
            else:
                # AI umpire validation
                is_valid, reasoning = self.umpire_player.get_umpire_validation(
                    clue, number, self.current_team, board_state, self.prompt_files["umpire"]
                )
                
                # If first umpire flags as invalid, do second review with Gemini 2.5 Pro
                if not is_valid and self.umpire_player is not None:
                    console.print(f"[yellow]🔄 First umpire flagged clue as invalid. Getting second opinion from Gemini 2.5 Pro...[/yellow]")
                    
                    # Create a temporary Gemini 2.5 Pro player for second review
                    review_umpire = AIPlayer("gemini-2.5")
                    
                    # Get second opinion with same prompt
                    review_valid, review_reasoning = review_umpire.get_umpire_validation(
                        clue, number, self.current_team, board_state, self.prompt_files["umpire"]
                    )
                    
                    # Log the review umpire metadata
                    review_metadata = review_umpire.get_last_call_metadata()
                    if review_metadata:
                        turn_label = format_turn_label(self.turn_count, self.current_team, self.starting_team)
                        
                        # Update turn result with review umpire validation outcome
                        turn_result = review_metadata.get("turn_result", {})
                        turn_result.update({
                            "evaluated_clue": clue,
                            "evaluated_number": number,
                            "review_umpire": True,
                            "first_umpire_model": self.umpire_player.model_name,
                            "first_umpire_decision": "invalid",
                            "first_umpire_reasoning": reasoning
                        })
                        
                        log_ai_call_metadata(
                            game_id=self.game_id,
                            model_name=review_umpire.model_name,
                            call_type=review_metadata["call_type"],
                            team=f"review_umpire_{self.current_team}",
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
                        # Second umpire says it's valid - override first decision
                        console.print(f"[green]✅ Review umpire (Gemini 2.5 Pro) APPROVED the clue - overriding first decision[/green]")
                        console.print(f"[dim]First umpire ({self.umpire_player.model_name}): {reasoning}[/dim]")
                        console.print(f"[dim]Review umpire: {review_reasoning}[/dim]")
                        is_valid = True
                        reasoning = f"Approved on review by Gemini 2.5 Pro: {review_reasoning}"
                    else:
                        # Both umpires say invalid - reject the clue
                        console.print(f"[red]❌ Review umpire (Gemini 2.5 Pro) also REJECTED the clue - final decision: INVALID[/red]")
                        console.print(f"[dim]First umpire ({self.umpire_player.model_name}): {reasoning}[/dim]")
                        console.print(f"[dim]Review umpire: {review_reasoning}[/dim]")
                        reasoning = f"Rejected by both umpires. First: {reasoning}. Review: {review_reasoning}"
            
            # Log AI call metadata for umpire validation
            if isinstance(self.umpire_player, AIPlayer):
                metadata = self.umpire_player.get_last_call_metadata()
                if metadata:
                    turn_label = format_turn_label(self.turn_count, self.current_team, self.starting_team)
                    
                    # Update turn result with umpire validation outcome
                    turn_result = metadata.get("turn_result", {})
                    turn_result.update({
                        "evaluated_clue": clue,
                        "evaluated_number": number
                    })
                    
                    log_ai_call_metadata(
                        game_id=self.game_id,
                        model_name=self.umpire_player.model_name,
                        call_type=metadata["call_type"],
                        team=f"umpire_{self.current_team}",  # Include which team's clue was evaluated
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
                return clue, number, True, reasoning
            else:
                console.print(f"[red]🔴 Umpire: Clue REJECTED - {reasoning}[/red]")
                console.print(f"[yellow]⚠️  Turn ended due to invalid clue[/yellow]")
                log_umpire_rejection(self.current_team, clue, number, reasoning)
                return clue, number, False, reasoning
                
        except Exception as e:
            logger.error(f"Error in umpire validation: {e}")
            console.print(f"[yellow]⚠️  Umpire error, allowing original clue[/yellow]")
            return clue, number, True, "Umpire error - clue allowed"

    def apply_invalid_clue_penalty(self):
        """Apply penalty for invalid clue: remove one of the opposing team's words."""
        # Get opposing team
        opposing_team = "blue" if self.current_team == "red" else "red"
        
        # Find unrevealed opposing team subscribers
        opposing_subscribers = [
            name for name, identity in self.identities.items()
            if identity == f"{opposing_team}_subscriber" and not self.revealed[name]
        ]
        
        if opposing_subscribers:
            # Randomly select one to remove
            penalty_word = random.choice(opposing_subscribers)
            self.revealed[penalty_word] = True
            
            console.print(f"[yellow]⚖️  PENALTY: {penalty_word} revealed for {opposing_team.upper()} team due to invalid clue[/yellow]")
            
            # Log the penalty action
            log_umpire_penalty(self.current_team, opposing_team, penalty_word)
            
            logger.info(f"Invalid clue penalty applied: revealed {penalty_word} for {opposing_team} team")
            
            return penalty_word
        else:
            console.print(f"[yellow]⚖️  PENALTY: No unrevealed {opposing_team.upper()} subscribers to remove[/yellow]")
            logger.info(f"Invalid clue penalty: no unrevealed {opposing_team} subscribers available")
            return None

    def switch_teams(self):
        """Switch to the other team."""
        # Log status before switching
        red_remaining, blue_remaining = self.get_remaining_subscribers()
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
        log_game_start(self.game_id, red_model, blue_model, self.board, self.identities)
        
        # Log game setup metadata
        log_game_setup_metadata(self.game_id, red_model, blue_model, self.prompt_files, self.board, self.identities)

        console.print("[bold]🎯 The Switchboard Game Starting![/bold]")
        console.print(f"[red]Red Team:[/red] {red_model}")
        console.print(f"  • Operator: {self.prompt_files.get('red_operator', 'default')}")
        console.print(f"  • Lineman: {self.prompt_files.get('red_lineman', 'default')}")
        console.print(f"[blue]Blue Team:[/blue] {blue_model}")
        console.print(f"  • Operator: {self.prompt_files.get('blue_operator', 'default')}")
        console.print(f"  • Lineman: {self.prompt_files.get('blue_lineman', 'default')}")
        if self.umpire_player:
            umpire_model = self.umpire_player.model_name if hasattr(self.umpire_player, 'model_name') else "human"
            console.print(f"[yellow]Umpire:[/yellow] {umpire_model} ({self.prompt_files.get('umpire', 'default')})")
        else:
            console.print("[yellow]Umpire:[/yellow] Disabled")
        console.print(f"[green]Game ID:[/green] {self.game_id}")
        console.print()
        
        # Display the initial board
        self.display_board_start()

        while not self.game_over:
            # Operator phase
            clue, number = self.get_operator_turn()
            
            # Check if clue was rejected by umpire
            if clue is None or number is None:
                # Clue was rejected, apply penalty and end turn immediately
                self.apply_invalid_clue_penalty()
                self.switch_teams()
                continue

            # Record the clue for history tracking
            self.record_clue(self.current_team, clue, number)

            # Lineman phase - clue and number are guaranteed to be non-None at this point
            guesses = self.get_lineman_guesses(clue, number)

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
