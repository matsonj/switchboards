"""Tests for prompt template variable hydration."""

import random
import tempfile
from pathlib import Path

import pytest

from playbook.game import PlaybookGame
from playbook.player import HumanPlayer
from playbook.prompt_manager import PromptManager


class TestPromptHydration:
    """Test cases for prompt template variable replacement."""

    def setup_method(self):
        """Setup for each test."""
        # Set up a consistent game state for testing
        random.seed(42)
        
        # Create dummy players
        self.red_player = HumanPlayer()
        self.blue_player = HumanPlayer()
        
        # Initialize game
        self.game = PlaybookGame(
            names_file="inputs/names.yaml",
            red_player=self.red_player,
            blue_player=self.blue_player,
        )
        
        # Setup board with consistent seed
        self.game.setup_board()
        
        # Get field state
        self.field_state = self.game.get_field_state(reveal_all=True)
        
        # Initialize prompt manager
        self.prompt_manager = PromptManager()

    def test_coach_prompt_hydration_red(self):
        """Test that red coach prompt variables are properly hydrated."""
        # Calculate context variables similar to CLI
        red_remaining = sum(
            1 for name, identity in self.field_state["identities"].items()
            if identity == "red_target" and not self.field_state["revealed"].get(name, False)
        )
        blue_remaining = sum(
            1 for name, identity in self.field_state["identities"].items()
            if identity == "blue_target" and not self.field_state["revealed"].get(name, False)
        )
        revealed_names = [name for name, revealed in self.field_state["revealed"].items() if revealed]
        
        # Categorize identities
        red_targets = [name for name, identity in self.field_state["identities"].items() 
                         if identity == "red_target"]
        blue_targets = [name for name, identity in self.field_state["identities"].items() 
                          if identity == "blue_target"]
        fake_targets = [name for name, identity in self.field_state["identities"].items() 
                       if identity == "civilian"]
        illegal_target = [name for name, identity in self.field_state["identities"].items() 
                         if identity == "illegal_target"]
        
        # Load and format prompt
        context = {
            "field": self.field_state["board"],
            "revealed": self.field_state["revealed"],
            "team": "red",
            "red_remaining": red_remaining,
            "blue_remaining": blue_remaining,
            "revealed_names": ", ".join(revealed_names) if revealed_names else "None",
            "red_subscribers": ", ".join(red_targets),
            "blue_subscribers": ", ".join(blue_targets),
            "civilians": ", ".join(fake_targets),
            "mole": ", ".join(illegal_target),
            "clue_history": "No previous plays yet",
        }
        
        prompt = self.prompt_manager.load_prompt("prompts/red_coach.md", context)
        
        # Verify key variables are replaced (should not contain {{}} patterns)
        assert "{{RED_SUBSCRIBERS}}" not in prompt, "RED_SUBSCRIBERS variable not replaced"
        assert "{{BLUE_SUBSCRIBERS}}" not in prompt, "BLUE_SUBSCRIBERS variable not replaced"
        assert "{{CIVILIANS}}" not in prompt, "CIVILIANS variable not replaced"
        assert "{{MOLE}}" not in prompt, "MOLE variable not replaced"
        assert "{{CLUE_HISTORY}}" not in prompt, "CLUE_HISTORY variable not replaced"
        
        # Verify actual content is present
        if red_targets:
            assert red_targets[0] in prompt, f"Red target {red_targets[0]} should be in prompt"
        if blue_targets:
            assert blue_targets[0] in prompt, f"Blue target {blue_targets[0]} should be in prompt"
        if fake_targets:
            assert fake_targets[0] in prompt, f"Civilian target {fake_targets[0]} should be in prompt"
        if illegal_target:
            assert illegal_target[0] in prompt, f"Illegal target {illegal_target[0]} should be in prompt"
        
        assert "No previous plays yet" in prompt, "Clue history should be present"

    def test_coach_prompt_hydration_blue(self):
        """Test that blue coach prompt variables are properly hydrated."""
        # Get blue targets
        blue_targets = [name for name, identity in self.field_state["identities"].items() 
                       if identity == "blue_target"]
        red_targets = [name for name, identity in self.field_state["identities"].items() 
                      if identity == "red_target"]
        
        context = {
            "team": "blue",
            "red_subscribers": ", ".join(red_targets),
            "blue_subscribers": ", ".join(blue_targets),
            "civilians": "TEST_CIVILIAN",
            "mole": "TEST_ILLEGAL",
            "clue_history": "Test history",
            "red_remaining": 8,
            "blue_remaining": 9,
            "revealed_names": "None",
        }
        
        prompt = self.prompt_manager.load_prompt("prompts/blue_coach.md", context)
        
        # Verify no unreplaced variables
        assert "{{RED_SUBSCRIBERS}}" not in prompt
        assert "{{BLUE_SUBSCRIBERS}}" not in prompt
        assert "{{CIVILIANS}}" not in prompt
        assert "{{MOLE}}" not in prompt
        assert "{{CLUE_HISTORY}}" not in prompt
        
        # Verify blue-specific content
        if blue_targets:
            assert blue_targets[0] in prompt, "Blue team targets should be in blue coach prompt"

    def test_player_prompt_hydration_red(self):
        """Test that red player prompt variables are properly hydrated."""
        available_names = [
            name for name in self.field_state["board"] 
            if not self.field_state["revealed"].get(name, False)
        ]
        
        def _format_board_for_player_cli(field_state):
            """Helper function to format board like CLI does."""
            board = field_state["board"]
            if len(board) != 25:
                return ", ".join(board)
            
            lines = []
            for row in range(5):
                row_items = board[row * 5 : (row + 1) * 5]
                lines.append(" | ".join(f"{item:>12}" for item in row_items))
            return "\n".join(lines)
        
        context = {
            "board": _format_board_for_player_cli(self.field_state),
            "available_names": ", ".join(available_names),
            "clue_history": "None (game just started)",
            "clue": "ANIMALS",
            "number": 2,
            "team": "red",
        }
        
        prompt = self.prompt_manager.load_prompt("prompts/red_player.md", context)
        
        # Verify key variables are replaced
        assert "{{BOARD}}" not in prompt, "BOARD variable not replaced"
        assert "{{AVAILABLE_NAMES}}" not in prompt, "AVAILABLE_NAMES variable not replaced"
        assert "{{CLUE_HISTORY}}" not in prompt, "CLUE_HISTORY variable not replaced"
        assert "{{CLUE}}" not in prompt, "CLUE variable not replaced"
        assert "{{NUMBER}}" not in prompt, "NUMBER variable not replaced"
        
        # Verify actual content is present
        assert "ANIMALS" in prompt, "Clue should be in prompt"
        assert "2" in prompt, "Number should be in prompt"
        assert "None (game just started)" in prompt, "Clue history should be in prompt"
        if available_names:
            assert available_names[0] in prompt, f"Available name {available_names[0]} should be in prompt"

    def test_player_prompt_hydration_blue(self):
        """Test that blue player prompt variables are properly hydrated."""
        context = {
            "board": "TEST_BOARD",
            "available_names": "NAME1, NAME2, NAME3",
            "clue_history": "Previous play: TOOLS (2)",
            "clue": "WEAPONS",
            "number": 3,
            "team": "blue",
        }
        
        prompt = self.prompt_manager.load_prompt("prompts/blue_player.md", context)
        
        # Verify no unreplaced variables
        assert "{{BOARD}}" not in prompt
        assert "{{AVAILABLE_NAMES}}" not in prompt
        assert "{{CLUE_HISTORY}}" not in prompt
        assert "{{CLUE}}" not in prompt
        assert "{{NUMBER}}" not in prompt
        
        # Verify content
        assert "WEAPONS" in prompt, "Clue should be in prompt"
        assert "3" in prompt, "Number should be in prompt"
        assert "Previous play: TOOLS (2)" in prompt, "Clue history should be in prompt"
        assert "NAME1, NAME2, NAME3" in prompt, "Available names should be in prompt"

    def test_player_prompt_special_numbers(self):
        """Test that player prompts handle special number values (0, unlimited)."""
        # Test with 0
        context = {
            "board": "TEST_BOARD",
            "available_names": "NAME1, NAME2",
            "clue_history": "No history",
            "clue": "ZERO_TEST",
            "number": 0,
            "team": "red",
        }
        
        prompt = self.prompt_manager.load_prompt("prompts/red_player.md", context)
        assert "0" in prompt, "Zero should be displayed in prompt"
        assert "ZERO_TEST" in prompt, "Clue should be in prompt"
        
        # Test with unlimited
        context["number"] = "unlimited"
        context["clue"] = "UNLIMITED_TEST"
        
        prompt = self.prompt_manager.load_prompt("prompts/red_player.md", context)
        assert "unlimited" in prompt, "Unlimited should be displayed in prompt"
        assert "UNLIMITED_TEST" in prompt, "Clue should be in prompt"

    def test_referee_prompt_hydration(self):
        """Test that referee prompt variables are properly hydrated."""
        # Get team targets
        allied_targets = [
            name for name, identity in self.field_state["identities"].items()
            if identity == "red_target"
        ]
        
        context = {
            "clue": "EXAMPLE",
            "number": 2,
            "team": "red",
            "board": ", ".join(self.field_state["board"]),
            "allied_subscribers": ", ".join(allied_targets),
        }
        
        prompt = self.prompt_manager.load_prompt("prompts/referee.md", context)
        
        # Verify key variables are replaced
        assert "{{CLUE}}" not in prompt, "CLUE variable not replaced"
        assert "{{NUMBER}}" not in prompt, "NUMBER variable not replaced"
        assert "{{TEAM}}" not in prompt, "TEAM variable not replaced"
        assert "{{BOARD}}" not in prompt, "BOARD variable not replaced"
        assert "{{ALLIED_SUBSCRIBERS}}" not in prompt, "ALLIED_SUBSCRIBERS variable not replaced"
        
        # Verify actual content is present
        assert "EXAMPLE" in prompt, "Clue should be in prompt"
        assert "2" in prompt, "Number should be in prompt"
        assert "red" in prompt, "Team should be in prompt"
        
        # Verify board names are present
        if self.field_state["board"]:
            assert self.field_state["board"][0] in prompt, "Board names should be in prompt"
        
        # Verify allied targets are present
        if allied_targets:
            assert allied_targets[0] in prompt, "Allied targets should be in prompt"

    def test_referee_prompt_special_cases(self):
        """Test referee prompt with special number values and edge cases."""
        context = {
            "clue": "SPECIAL_CASE",
            "number": "unlimited",
            "team": "blue",
            "board": "NAME1, NAME2, NAME3",
            "allied_subscribers": "TARGET1, TARGET2",
        }
        
        prompt = self.prompt_manager.load_prompt("prompts/referee.md", context)
        
        # Verify special values are handled
        assert "unlimited" in prompt, "Unlimited should be in prompt"
        assert "SPECIAL_CASE" in prompt, "Special case clue should be in prompt"
        assert "blue" in prompt, "Blue team should be in prompt"

    def test_prompt_includes_work(self):
        """Test that {{include}} directives are processed correctly."""
        # All our prompts include shared/game_rules.md
        context = {"test": "value"}
        
        coach_prompt = self.prompt_manager.load_prompt("prompts/red_coach.md", context)
        player_prompt = self.prompt_manager.load_prompt("prompts/red_player.md", context)
        referee_prompt = self.prompt_manager.load_prompt("prompts/referee.md", context)
        
        # Check that game rules content appears in all prompts
        game_rules_content = "Playbook is a strategic deduction game"
        
        assert game_rules_content in coach_prompt, "Game rules should be included in coach prompt"
        assert game_rules_content in player_prompt, "Game rules should be included in player prompt"
        assert game_rules_content in referee_prompt, "Game rules should be included in referee prompt"
        
        # Verify {{include}} directive is removed
        assert "{{include:" not in coach_prompt, "Include directive should be processed"
        assert "{{include:" not in player_prompt, "Include directive should be processed"
        assert "{{include:" not in referee_prompt, "Include directive should be processed"

    def test_missing_variables_handled_gracefully(self):
        """Test that missing context variables don't break prompt generation."""
        # Minimal context (missing some expected variables)
        context = {
            "team": "red",
            "clue": "TEST",
        }
        
        # Should not raise exceptions even with missing variables
        coach_prompt = self.prompt_manager.load_prompt("prompts/red_coach.md", context)
        player_prompt = self.prompt_manager.load_prompt("prompts/red_player.md", context)
        referee_prompt = self.prompt_manager.load_prompt("prompts/referee.md", context)
        
        # Should still contain basic content
        assert "Red Team Coach" in coach_prompt
        assert "Red Team Players" in player_prompt
        assert "Referee" in referee_prompt
        
        # Missing variables should remain as placeholders
        assert "{{RED_SUBSCRIBERS}}" in coach_prompt  # Missing variable
        assert "{{BOARD}}" in player_prompt  # Missing variable
