"""Player classes for The Switchboard game."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

from switchboard.adapters.openrouter_adapter import OpenRouterAdapter
from switchboard.prompt_manager import PromptManager

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

        logger.info(f"Created AI player with model: {model_name}")

    @property
    def adapter(self):
        """Lazy initialization of OpenRouter adapter."""
        if self._adapter is None:
            self._adapter = OpenRouterAdapter()
        return self._adapter

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

            # Call AI model
            response = self.adapter.call_model(self.model_name, prompt)

            # Parse response for clue and number
            logger.debug(f"Raw AI response: {response}")
            clue, number = self._parse_operator_response(response)

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

            # Call AI model
            response = self.adapter.call_model(self.model_name, prompt)

            # Parse response for validation
            is_valid, reasoning = self._parse_umpire_response(response)

            logger.info(
                f"AI Umpire ({self.model_name}) validation: {'VALID' if is_valid else 'INVALID'} - {reasoning}"
            )
            return is_valid, reasoning

        except Exception as e:
            logger.error(f"Error in AI umpire validation: {e}")
            # Fallback: allow clue but log the error
            return True, f"Umpire error - allowing clue: {e}"

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
            
            prompt = self.prompt_manager.load_prompt(
                prompt_file,
                {
                    "board": available_names,
                    "clue_history": board_state.get("clue_history", "None (game just started)"),
                    "clue": clue,
                    "number": number,
                    "team": board_state["current_team"],
                },
            )

            # Call AI model
            response = self.adapter.call_model(self.model_name, prompt)

            # Parse response for guesses
            guesses = self._parse_lineman_response(response, board_state, number)

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
        
        for line in lines:
            line = line.strip()
            if line.startswith("VALID"):
                is_valid = True
                # Look for reasoning on same line or next lines
                if ":" in line:
                    reasoning = line.split(":", 1)[1].strip()
                else:
                    reasoning = "Clue follows game rules"
                break
            elif line.startswith("INVALID"):
                is_valid = False
                # Look for violation/reasoning on same line or next lines
                if ":" in line:
                    reasoning = line.split(":", 1)[1].strip()
                else:
                    reasoning = "Rule violation detected"
                break
            elif line.startswith("Violation:"):
                is_valid = False
                reasoning = line.replace("Violation:", "").strip()
            elif line.startswith("Reasoning:") and not is_valid:
                # Only use reasoning line for invalid clues
                reasoning = line.replace("Reasoning:", "").strip()
        
        # If no clear VALID/INVALID found, default to valid to avoid false rejections
        return is_valid, reasoning

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
