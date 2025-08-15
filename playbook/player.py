"""Player classes for The Playbook game."""

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Tuple

from playbook.adapters.openrouter_adapter import OpenRouterAdapter
from playbook.prompt_manager import PromptManager
from playbook.utils.logging import log_ai_call_metadata, format_turn_label

logger = logging.getLogger(__name__)


class Player(ABC):
    """Abstract base class for all players."""

    @abstractmethod
    def get_coach_move(self, board_state: Dict, prompt_file: str) -> Tuple[str, int|str]:
        """Get play and number from coach."""
        pass

    @abstractmethod
    def get_player_moves(
        self, board_state: Dict, play: str, number: int|str, prompt_file: str
    ) -> List[str]:
        """Get shots from player."""
        pass


class HumanPlayer(Player):
    """Human player implementation."""

    def get_coach_move(self, board_state: Dict, prompt_file: str) -> Tuple[str, int|str]:
        """Human coach input is handled in the game loop."""
        raise NotImplementedError("Human coach input handled in game loop")

    def get_player_moves(
        self, board_state: Dict, play: str, number: int|str, prompt_file: str
    ) -> List[str]:
        """Human player input is handled in the game loop."""
        raise NotImplementedError("Human player input handled in game loop")


class AIPlayer(Player):
    """AI player using OpenRouter models."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._adapter = None
        self.prompt_manager = PromptManager()
        self._last_call_metadata = None

        logger.info(f"Created AI player with model: {model_name}")

    @property
    def adapter(self):
        """Lazy initialization of OpenRouter adapter."""
        if self._adapter is None:
            self._adapter = OpenRouterAdapter()
        return self._adapter

    def get_last_call_metadata(self):
        """Get metadata from the last AI call."""
        return self._last_call_metadata

    def get_coach_move(self, board_state: Dict, prompt_file: str) -> Tuple[str, int|str]:
        """Get play and number from AI coach."""
        try:
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
            
            # Load and format prompt
            prompt = self.prompt_manager.load_prompt(
                prompt_file,
                {
                    "field": board_state["board"],
                    "revealed": board_state["revealed"],
                    "team": board_state["current_team"],
                    "red_remaining": red_remaining,
                    "blue_remaining": blue_remaining,
                    "revealed_names": ", ".join(revealed_names) if revealed_names else "None",
                    "red_subscribers": ", ".join(red_targets),
                    "blue_subscribers": ", ".join(blue_targets),
                    "civilians": ", ".join(fake_targets),
                    "mole": ", ".join(illegal_target),
                    "clue_history": "Previous plays will be shown here",  # TODO: Add actual history
                },
            )

            # Call AI model with metadata tracking
            response, metadata = self.adapter.call_model_with_metadata(self.model_name, prompt)

            # Parse response for play and number
            logger.debug(f"Raw AI response: {response}")
            play, number = self._parse_coach_response(response)
            
            # Log AI call metadata (we'll need game context passed from caller)
            # For now, store metadata for potential logging at game level
            self._last_call_metadata = metadata
            self._last_call_metadata["call_type"] = "coach"
            self._last_call_metadata["turn_result"] = {
                "play": play,
                "play_number": number if isinstance(number, (int, str)) else str(number)
            }

            logger.info(
                f"AI Coach ({self.model_name}) gave play: '{play}' ({number})"
            )
            return play, number

        except Exception as e:
            logger.error(f"Error in AI coach move: {e}")
            # Fallback
            return "ERROR", 1

    def get_referee_validation(
        self, play: str, number: int|str, team: str, board_state: Dict, prompt_file: str
    ) -> Tuple[bool, str]:
        """Get referee validation of a play. Returns (is_valid, reasoning)."""
        try:
            # Get team's allied targets
            allied_targets = [
                name for name, identity in board_state["identities"].items()
                if identity == f"{team}_target"
            ]
            
            # Load and format prompt
            prompt = self.prompt_manager.load_prompt(
                prompt_file,
                {
                    "clue": play,
                    "number": number,
                    "team": team,
                    "board": ", ".join(board_state["board"]),
                    "allied_subscribers": ", ".join(allied_targets),
                },
            )

            # Call AI model with metadata tracking
            response, metadata = self.adapter.call_model_with_metadata(self.model_name, prompt)

            # Parse response for validation
            is_valid, reasoning = self._parse_referee_response(response)
            
            # Store metadata for logging at game level
            self._last_call_metadata = metadata
            self._last_call_metadata["call_type"] = "referee"
            self._last_call_metadata["turn_result"] = {
                "referee_result": "valid" if is_valid else "invalid",
                "referee_reasoning": reasoning
            }

            # Log with full context for debugging if reasoning is generic
            if not is_valid and reasoning in ["Rule violation detected", "Play approved"]:
                logger.info(
                    f"AI Referee ({self.model_name}) validation: {'VALID' if is_valid else 'INVALID'} - {reasoning} | Full response: {response[:200]}..."
                )
            else:
                logger.info(
                    f"AI Referee ({self.model_name}) validation: {'VALID' if is_valid else 'INVALID'} - {reasoning}"
                )
            
            # If invalid, write full prompt+response to logs/referee/
            if not is_valid:
                self._log_referee_foul(play, number, team, prompt, response, reasoning)
            
            return is_valid, reasoning

        except Exception as e:
            logger.error(f"Error in AI referee validation: {e}")
            # Fallback: allow play but log the error
            return True, f"Referee error - allowing play: {e}"

    def _log_referee_foul(self, play: str, number: int|str, team: str, prompt: str, response: str, reasoning: str):
        """Log referee foul details to logs/referee/ directory."""
        try:
            # Create logs/referee directory if it doesn't exist
            referee_log_dir = "logs/referee"
            os.makedirs(referee_log_dir, exist_ok=True)
            
            # Generate filename with timestamp (single file for all fouls)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fouls_{timestamp}.log"
            filepath = os.path.join(referee_log_dir, filename)
            
            # Append foul details (create file if it doesn't exist)
            with open(filepath, 'a') as f:
                f.write(f"=== {team.upper()} TEAM ===\n")
                f.write(f"=== REFEREE FOUL ===\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Team: {team}\n")
                f.write(f"Play: {play}\n")
                f.write(f"Number: {number}\n")
                f.write(f"Foul Reason: {reasoning}\n")
                if reasoning in ["Rule violation detected", "Play approved"]:
                    f.write(f"NOTE: Generic reasoning detected - check full response below\n")
                f.write(f"Referee Model: {self.model_name}\n\n")
                f.write(f"=== FULL PROMPT ===\n")
                f.write(f"{prompt}\n\n")
                f.write(f"=== REFEREE RESPONSE ===\n")
                f.write(f"{response}\n\n")
                f.write("="*80 + "\n\n")
                
            logger.info(f"Referee foul logged to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to log referee foul: {e}")

    def get_player_moves(
        self, board_state: Dict, play: str, number: int|str, prompt_file: str
    ) -> List[str]:
        """Get shots from AI player."""
        try:
            # Load and format prompt
            # Filter field to only show available (unrevealed) names
            available_names = [
                name for name in board_state["board"] 
                if not board_state["revealed"].get(name, False)
            ]
            
            # Format available names as a simple list
            available_names_formatted = ", ".join(available_names)
            
            prompt = self.prompt_manager.load_prompt(
                prompt_file,
                {
                    "board": self._format_field_for_player(board_state),
                    "available_names": available_names_formatted,
                    "clue_history": board_state.get("play_history", "None (game just started)"),
                    "clue": play,
                    "number": number,
                    "team": board_state["current_team"],
                },
            )

            # Call AI model with metadata tracking
            response, metadata = self.adapter.call_model_with_metadata(self.model_name, prompt)

            # Parse response for shots
            shots = self._parse_player_response(response, board_state, number)
            
            # Store metadata for logging at game level
            self._last_call_metadata = metadata
            self._last_call_metadata["call_type"] = "player"
            self._last_call_metadata["turn_result"] = {
                "total_shots": len(shots),
                "shots": shots
            }

            logger.info(f"AI Player ({self.model_name}) shots: {shots}")
            return shots

        except Exception as e:
            logger.error(f"Error in AI player move: {e}")
            # Fallback
            available = [
                name
                for name in board_state["board"]
                if not board_state["revealed"][name]
            ]
            return available[:1] if available else []

    def _parse_coach_response(self, response: str) -> Tuple[str, int|str]:
        """Parse AI response for coach play and number."""
        lines = response.strip().split("\n")

        # Look for play and number patterns
        play = "UNKNOWN"
        number: int|str = 1

        for line in lines:
            line = line.strip()
            if line.startswith("PLAY:"):
                play = line.replace("PLAY:", "").strip().strip("\"'")
            elif line.startswith("NUMBER:"):
                number_str = line.replace("NUMBER:", "").strip().lower()
                if number_str == "unlimited":
                    number = "unlimited"
                else:
                    try:
                        number = int(number_str)
                    except ValueError:
                        number = 1
            elif ":" in line and len(line.split(":")) == 2:
                # Try to parse "play: number" format
                parts = line.split(":")
                number_str = parts[1].strip().lower()
                if number_str == "unlimited":
                    play = parts[0].strip().strip("\"'")
                    number = "unlimited"
                elif number_str.isdigit():
                    play = parts[0].strip().strip("\"'")
                    number = int(number_str)

        # Ensure valid number (allow 0 and unlimited)
        if isinstance(number, int) and number < 0:
            number = 1

        return play, number

    def _parse_referee_response(self, response: str) -> Tuple[bool, str]:
        """Parse AI response for referee validation."""
        lines = response.strip().split("\n")
        
        is_valid = True  # Default to valid (allow play unless clearly invalid)
        reasoning = "Play approved"
        
        # First pass: look for VALID/INVALID
        found_verdict = False
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("VALID"):
                is_valid = True
                found_verdict = True
                # Look for reasoning on same line
                if ":" in line:
                    reasoning = line.split(":", 1)[1].strip()
                else:
                    reasoning = "Play follows game rules"
                break
            elif line.startswith("INVALID"):
                is_valid = False
                found_verdict = True
                # Look for reasoning on same line
                if ":" in line:
                    reasoning = line.split(":", 1)[1].strip()
                else:
                    # Look for "Foul:" on subsequent lines
                    reasoning = "Rule violation detected"
                    for next_line in lines[i+1:]:
                        next_line = next_line.strip()
                        if next_line.startswith("Foul:"):
                            reasoning = next_line.replace("Foul:", "").strip()
                            break
                        elif next_line.startswith("Reasoning:"):
                            reasoning = next_line.replace("Reasoning:", "").strip()
                            break
                        elif next_line and not next_line.startswith("#") and not next_line.startswith("**"):
                            # Any other non-empty, non-header line might be the reasoning
                            reasoning = next_line
                            break
                break
        
        # Second pass: look for standalone foul lines if no verdict found
        if not found_verdict:
            for line in lines:
                line = line.strip()
                if line.startswith("Foul:"):
                    is_valid = False
                    reasoning = line.replace("Foul:", "").strip()
                    break
                elif line.startswith("Reasoning:"):
                    reasoning = line.replace("Reasoning:", "").strip()
        
        # If no clear reasoning found and play is invalid, try to extract from full response
        if not is_valid and reasoning == "Rule violation detected":
            # Look for any line that mentions specific violations
            for line in lines:
                line = line.strip().lower()
                if any(keyword in line for keyword in ['multiple words', 'exact match', 'variant', 'letter count', 'position', 'field position']):
                    reasoning = line.title()
                    break
        
        return is_valid, reasoning

    def _format_field_for_player(self, board_state: Dict) -> str:
        """Format the field for player display with revealed status."""
        field = board_state["board"]
        revealed = board_state["revealed"]
        
        # Create a 5x5 grid display
        lines = []
        for row in range(5):
            row_items = []
            for col in range(5):
                idx = row * 5 + col
                name = field[idx]
                
                # Mark revealed names with brackets
                if revealed.get(name, False):
                    display_name = f"[{name}]"
                else:
                    display_name = name
                
                row_items.append(f"{display_name:>12}")
            
            lines.append(" |".join(row_items))
        
        return "\n".join(lines)

    def _parse_player_response(
        self, response: str, board_state: Dict, max_number: int|str
    ) -> List[str]:
        """Parse AI response for player shots."""
        available_names = set(
            name for name in board_state["board"] if not board_state["revealed"].get(name, False)
        )
        shots = []

        # Split response into lines and look for names
        lines = response.strip().split("\n")

        for line in lines:
            line = line.strip()

            # Skip empty lines and obvious non-shot lines
            if not line or line.startswith("#") or line.startswith("//"):
                continue

            # Look for names in the line
            words = line.replace(",", " ").replace(";", " ").split()
            for word in words:
                clean_word = word.strip(".,;:\"'()[]{}").upper()

                # Check if this word is an available name
                for available_name in available_names:
                    if clean_word == available_name.upper():
                        if available_name not in shots:
                            shots.append(available_name)
                            # Handle different play types
                            if max_number == "unlimited" or max_number == 0:
                                # Continue collecting shots for unlimited/zero plays
                                continue
                            elif isinstance(max_number, int) and len(shots) >= max_number + 1:  # N+1 rule
                                return shots

        # If no valid shots found, return first available name
        if not shots and available_names:
            shots = [next(iter(available_names))]

        # Apply limits based on play type
        if max_number == "unlimited" or max_number == 0:
            return shots  # No limit for unlimited/zero plays
        elif isinstance(max_number, int):
            return shots[: max_number + 1]  # Enforce N+1 limit
        else:
            return shots  # Fallback
