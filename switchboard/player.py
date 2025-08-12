"""Player classes for The Switchboard game."""

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Tuple

from switchboard.adapters.openrouter_adapter import OpenRouterAdapter
from switchboard.prompt_manager import PromptManager
from switchboard.utils.logging import log_ai_call_metadata, format_turn_label

logger = logging.getLogger(__name__)


class Player(ABC):
    """Abstract base class for all players."""

    @abstractmethod
    def get_operator_move(self, board_state: Dict, prompt_file: str) -> Tuple[str, int|str]:
        """Get clue and number from operator."""
        pass

    @abstractmethod
    def get_lineman_moves(
        self, board_state: Dict, clue: str, number: int|str, prompt_file: str
    ) -> List[str]:
        """Get guesses from lineman."""
        pass


class HumanPlayer(Player):
    """Human player implementation."""

    def get_operator_move(self, board_state: Dict, prompt_file: str) -> Tuple[str, int|str]:
        """Human operator input is handled in the game loop."""
        raise NotImplementedError("Human operator input handled in game loop")

    def get_lineman_moves(
        self, board_state: Dict, clue: str, number: int|str, prompt_file: str
    ) -> List[str]:
        """Human lineman input is handled in the game loop."""
        raise NotImplementedError("Human lineman input handled in game loop")


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

    def get_operator_move(self, board_state: Dict, prompt_file: str) -> Tuple[str, int|str]:
        """Get clue and number from AI operator."""
        try:
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
            
            # Load and format prompt
            prompt = self.prompt_manager.load_prompt(
                prompt_file,
                {
                    "board": board_state["board"],
                    "revealed": board_state["revealed"],
                    "team": board_state["current_team"],
                    "red_remaining": red_remaining,
                    "blue_remaining": blue_remaining,
                    "revealed_names": ", ".join(revealed_names) if revealed_names else "None",
                    "red_subscribers": ", ".join(red_subscribers),
                    "blue_subscribers": ", ".join(blue_subscribers),
                    "civilians": ", ".join(civilians),
                    "mole": ", ".join(mole),
                },
            )

            # Call AI model with metadata tracking
            response, metadata = self.adapter.call_model_with_metadata(self.model_name, prompt)

            # Parse response for clue and number
            logger.debug(f"Raw AI response: {response}")
            clue, number = self._parse_operator_response(response)
            
            # Log AI call metadata (we'll need game context passed from caller)
            # For now, store metadata for potential logging at game level
            self._last_call_metadata = metadata
            self._last_call_metadata["call_type"] = "operator"
            self._last_call_metadata["turn_result"] = {
                "clue": clue,
                "clue_number": number if isinstance(number, (int, str)) else str(number)
            }

            logger.info(
                f"AI Operator ({self.model_name}) gave clue: '{clue}' ({number})"
            )
            return clue, number

        except Exception as e:
            logger.error(f"Error in AI operator move: {e}")
            # Fallback
            return "ERROR", 1

    def get_umpire_validation(
        self, clue: str, number: int|str, team: str, board_state: Dict, prompt_file: str
    ) -> Tuple[bool, str]:
        """Get umpire validation of a clue. Returns (is_valid, reasoning)."""
        try:
            # Get team's allied subscribers
            allied_subscribers = [
                name for name, identity in board_state["identities"].items()
                if identity == f"{team}_subscriber"
            ]
            
            # Load and format prompt
            prompt = self.prompt_manager.load_prompt(
                prompt_file,
                {
                    "clue": clue,
                    "number": number,
                    "team": team,
                    "board": board_state["board"],
                    "allied_subscribers": ", ".join(allied_subscribers),
                },
            )

            # Call AI model with metadata tracking
            response, metadata = self.adapter.call_model_with_metadata(self.model_name, prompt)

            # Parse response for validation
            is_valid, reasoning = self._parse_umpire_response(response)
            
            # Store metadata for logging at game level
            self._last_call_metadata = metadata
            self._last_call_metadata["call_type"] = "umpire"
            self._last_call_metadata["turn_result"] = {
                "umpire_result": "valid" if is_valid else "invalid",
                "umpire_reasoning": reasoning
            }

            # Log with full context for debugging if reasoning is generic
            if not is_valid and reasoning in ["Rule violation detected", "Clue approved"]:
                logger.info(
                    f"AI Umpire ({self.model_name}) validation: {'VALID' if is_valid else 'INVALID'} - {reasoning} | Full response: {response[:200]}..."
                )
            else:
                logger.info(
                    f"AI Umpire ({self.model_name}) validation: {'VALID' if is_valid else 'INVALID'} - {reasoning}"
                )
            
            # If invalid, write full prompt+response to logs/umpire/
            if not is_valid:
                self._log_umpire_violation(clue, number, team, prompt, response, reasoning)
            
            return is_valid, reasoning

        except Exception as e:
            logger.error(f"Error in AI umpire validation: {e}")
            # Fallback: allow clue but log the error
            return True, f"Umpire error - allowing clue: {e}"

    def _log_umpire_violation(self, clue: str, number: int|str, team: str, prompt: str, response: str, reasoning: str):
        """Log umpire violation details to logs/umpire/ directory."""
        try:
            # Create logs/umpire directory if it doesn't exist
            umpire_log_dir = "logs/umpire"
            os.makedirs(umpire_log_dir, exist_ok=True)
            
            # Generate filename with timestamp (single file for all violations)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"violations_{timestamp}.log"
            filepath = os.path.join(umpire_log_dir, filename)
            
            # Append violation details (create file if it doesn't exist)
            with open(filepath, 'a') as f:
                f.write(f"=== {team.upper()} TEAM ===\n")
                f.write(f"=== UMPIRE RULE VIOLATION ===\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Team: {team}\n")
                f.write(f"Clue: {clue}\n")
                f.write(f"Number: {number}\n")
                f.write(f"Violation Reason: {reasoning}\n")
                if reasoning in ["Rule violation detected", "Clue approved"]:
                    f.write(f"NOTE: Generic reasoning detected - check full response below\n")
                f.write(f"Umpire Model: {self.model_name}\n\n")
                f.write(f"=== FULL PROMPT ===\n")
                f.write(f"{prompt}\n\n")
                f.write(f"=== UMPIRE RESPONSE ===\n")
                f.write(f"{response}\n\n")
                f.write("="*80 + "\n\n")
                
            logger.info(f"Umpire violation logged to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to log umpire violation: {e}")

    def get_lineman_moves(
        self, board_state: Dict, clue: str, number: int|str, prompt_file: str
    ) -> List[str]:
        """Get guesses from AI lineman."""
        try:
            # Load and format prompt
            # Filter board to only show available (unrevealed) names
            available_names = [
                name for name in board_state["board"] 
                if not board_state["revealed"].get(name, False)
            ]
            
            # Format available names as a simple list
            available_names_formatted = ", ".join(available_names)
            
            prompt = self.prompt_manager.load_prompt(
                prompt_file,
                {
                    "board": self._format_board_for_lineman(board_state),
                    "available_names": available_names_formatted,
                    "clue_history": board_state.get("clue_history", "None (game just started)"),
                    "clue": clue,
                    "number": number,
                    "team": board_state["current_team"],
                },
            )

            # Call AI model with metadata tracking
            response, metadata = self.adapter.call_model_with_metadata(self.model_name, prompt)

            # Parse response for guesses
            guesses = self._parse_lineman_response(response, board_state, number)
            
            # Store metadata for logging at game level
            self._last_call_metadata = metadata
            self._last_call_metadata["call_type"] = "lineman"
            self._last_call_metadata["turn_result"] = {
                "total_guesses": len(guesses),
                "guesses": guesses
            }

            logger.info(f"AI Lineman ({self.model_name}) guesses: {guesses}")
            return guesses

        except Exception as e:
            logger.error(f"Error in AI lineman move: {e}")
            # Fallback
            available = [
                name
                for name in board_state["board"]
                if not board_state["revealed"][name]
            ]
            return available[:1] if available else []

    def _parse_operator_response(self, response: str) -> Tuple[str, int|str]:
        """Parse AI response for operator clue and number."""
        lines = response.strip().split("\n")

        # Look for clue and number patterns
        clue = "UNKNOWN"
        number: int|str = 1

        for line in lines:
            line = line.strip()
            if line.startswith("CLUE:"):
                clue = line.replace("CLUE:", "").strip().strip("\"'")
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
                # Try to parse "clue: number" format
                parts = line.split(":")
                number_str = parts[1].strip().lower()
                if number_str == "unlimited":
                    clue = parts[0].strip().strip("\"'")
                    number = "unlimited"
                elif number_str.isdigit():
                    clue = parts[0].strip().strip("\"'")
                    number = int(number_str)

        # Ensure valid number (allow 0 and unlimited)
        if isinstance(number, int) and number < 0:
            number = 1

        return clue, number

    def _parse_umpire_response(self, response: str) -> Tuple[bool, str]:
        """Parse AI response for umpire validation."""
        lines = response.strip().split("\n")
        
        is_valid = True  # Default to valid (allow clue unless clearly invalid)
        reasoning = "Clue approved"
        
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
                    reasoning = "Clue follows game rules"
                break
            elif line.startswith("INVALID"):
                is_valid = False
                found_verdict = True
                # Look for reasoning on same line
                if ":" in line:
                    reasoning = line.split(":", 1)[1].strip()
                else:
                    # Look for "Violation:" on subsequent lines
                    reasoning = "Rule violation detected"
                    for next_line in lines[i+1:]:
                        next_line = next_line.strip()
                        if next_line.startswith("Violation:"):
                            reasoning = next_line.replace("Violation:", "").strip()
                            break
                        elif next_line.startswith("Reasoning:"):
                            reasoning = next_line.replace("Reasoning:", "").strip()
                            break
                        elif next_line and not next_line.startswith("#") and not next_line.startswith("**"):
                            # Any other non-empty, non-header line might be the reasoning
                            reasoning = next_line
                            break
                break
        
        # Second pass: look for standalone violation lines if no verdict found
        if not found_verdict:
            for line in lines:
                line = line.strip()
                if line.startswith("Violation:"):
                    is_valid = False
                    reasoning = line.replace("Violation:", "").strip()
                    break
                elif line.startswith("Reasoning:"):
                    reasoning = line.replace("Reasoning:", "").strip()
        
        # If no clear reasoning found and clue is invalid, try to extract from full response
        if not is_valid and reasoning == "Rule violation detected":
            # Look for any line that mentions specific violations
            for line in lines:
                line = line.strip().lower()
                if any(keyword in line for keyword in ['multiple words', 'exact match', 'variant', 'letter count', 'position', 'board position']):
                    reasoning = line.title()
                    break
        
        return is_valid, reasoning

    def _format_board_for_lineman(self, board_state: Dict) -> str:
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

    def _parse_lineman_response(
        self, response: str, board_state: Dict, max_number: int|str
    ) -> List[str]:
        """Parse AI response for lineman guesses."""
        available_names = set(
            name for name in board_state["board"] if not board_state["revealed"].get(name, False)
        )
        guesses = []

        # Split response into lines and look for names
        lines = response.strip().split("\n")

        for line in lines:
            line = line.strip()

            # Skip empty lines and obvious non-guess lines
            if not line or line.startswith("#") or line.startswith("//"):
                continue

            # Look for names in the line
            words = line.replace(",", " ").replace(";", " ").split()
            for word in words:
                clean_word = word.strip(".,;:\"'()[]{}").upper()

                # Check if this word is an available name
                for available_name in available_names:
                    if clean_word == available_name.upper():
                        if available_name not in guesses:
                            guesses.append(available_name)
                            # Handle different clue types
                            if max_number == "unlimited" or max_number == 0:
                                # Continue collecting guesses for unlimited/zero clues
                                continue
                            elif isinstance(max_number, int) and len(guesses) >= max_number + 1:  # N+1 rule
                                return guesses

        # If no valid guesses found, return first available name
        if not guesses and available_names:
            guesses = [next(iter(available_names))]

        # Apply limits based on clue type
        if max_number == "unlimited" or max_number == 0:
            return guesses  # No limit for unlimited/zero clues
        elif isinstance(max_number, int):
            return guesses[: max_number + 1]  # Enforce N+1 limit
        else:
            return guesses  # Fallback
