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
    log_game_end, log_box_score, log_turn_end_status
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
    ):
        self.names_file = names_file
        self.red_player = red_player
        self.blue_player = blue_player
        self.umpire_player = umpire_player
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

        if isinstance(player, HumanPlayer):
            self.display_board(reveal_all=True)  # Operator sees all identities
            console.print(f"\n[bold]{self.current_team.title()} Operator Turn[/bold]")

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
                validated_clue, validated_number, is_valid = self._validate_clue_with_umpire(clue, number, board_state)
                if not is_valid:
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
            
            # Validate clue with umpire if available
            if self.umpire_player:
                validated_clue, validated_number, is_valid = self._validate_clue_with_umpire(clue, number, board_state)
                if not is_valid:
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

        if isinstance(player, HumanPlayer):
            self.display_board(reveal_all=False)  # Lineman sees only public board
            console.print(f"\n[bold]{self.current_team.title()} Lineman Turn[/bold]")
            console.print(f'Clue: "{clue}" ({number})')

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

            # Process guesses one by one
            for guess in guesses:
                console.print(
                    f"[{self.current_team}]{self.current_team.title()} Lineman[/{self.current_team}] guesses: {guess}"
                )
                result = self.process_guess(guess)
                if not result:  # Wrong guess ends turn
                    break

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

    def record_clue(self, team: str, clue: str, number: int|str):
        """Record a clue for the game history."""
        clue_entry = {
            "turn": self.turn_count,
            "team": team,
            "clue": clue,
            "number": number,
            "guesses": []
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
            clue_line = f"{turn_label}: {entry['team'].title()} Clue: \"{entry['clue']}\" ({entry['number']})"
            history_lines.append(clue_line)
            
            # Format the outcomes
            if entry["guesses"]:
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

    def _validate_clue_with_umpire(self, clue: str, number: int|str, board_state: Dict) -> Tuple[str, int|str, bool]:
        """Validate clue with umpire and handle invalid clues. Returns (clue, number, is_valid)."""
        try:
            is_valid, reasoning = self.umpire_player.get_umpire_validation(
                clue, number, self.current_team, board_state, self.prompt_files["umpire"]
            )
            
            if is_valid:
                console.print(f"[green]🟢 Umpire: Clue APPROVED[/green]")
                return clue, number, True
            else:
                console.print(f"[red]🔴 Umpire: Clue REJECTED - {reasoning}[/red]")
                console.print(f"[yellow]⚠️  Turn ended due to invalid clue[/yellow]")
                return clue, number, False
                
        except Exception as e:
            logger.error(f"Error in umpire validation: {e}")
            console.print(f"[yellow]⚠️  Umpire error, allowing original clue[/yellow]")
            return clue, number, True

    def switch_teams(self):
        """Switch to the other team."""
        # Log status before switching
        red_remaining, blue_remaining = self.get_remaining_subscribers()
        log_turn_end_status(red_remaining, blue_remaining)
        
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

        console.print("[bold]🎯 The Switchboard Game Starting![/bold]")

        while not self.game_over:
            # Operator phase
            clue, number = self.get_operator_turn()
            
            # Check if clue was rejected by umpire
            if clue is None or number is None:
                # Clue was rejected, end turn immediately
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
