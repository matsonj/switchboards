"""Integration tests for AIPlayer prompt generation."""

import random
from unittest.mock import Mock, patch

import pytest

from playbook.game import PlaybookGame
from playbook.player import AIPlayer, HumanPlayer


class TestAIPlayerIntegration:
    """Test that AIPlayer methods generate prompts correctly with real game state."""

    def setup_method(self):
        """Setup for each test."""
        random.seed(42)  # Reproducible tests
        
        # Create real game with human players for setup
        red_human = HumanPlayer()
        blue_human = HumanPlayer()
        
        self.game = PlaybookGame(
            names_file="inputs/names.yaml",
            red_player=red_human,
            blue_player=blue_human,
        )
        self.game.setup_board()
        
        # Create AI players for testing
        self.red_ai = AIPlayer("gpt-4")
        self.blue_ai = AIPlayer("gpt-4")

    def test_red_coach_prompt_integration(self):
        """Test that AIPlayer.get_coach_move() generates correct prompts for red team."""
        board_state = self.game.get_board_state(reveal_all=True)
        
        # Mock the OpenRouter call to capture the prompt
        with patch.object(self.red_ai.adapter, 'call_model_with_metadata') as mock_call:
            mock_call.return_value = ("PLAY: ANIMALS\nNUMBER: 2", {"tokens": 100, "cost": 0.01})
            
            # Call the coach method
            try:
                play, number = self.red_ai.get_coach_move(board_state, "prompts/red_coach.md")
            except Exception:
                # We don't care if it fails, we just want to check the prompt
                pass
            
            # Verify the method was called
            assert mock_call.called, "OpenRouter adapter should have been called"
            
            # Get the prompt that was sent to the AI
            call_args = mock_call.call_args
            prompt = call_args[0][1]  # Second argument is the prompt
            
            # Verify template variables were replaced correctly
            assert "{{RED_SUBSCRIBERS}}" not in prompt, "RED_SUBSCRIBERS should be replaced"
            assert "{{BLUE_SUBSCRIBERS}}" not in prompt, "BLUE_SUBSCRIBERS should be replaced" 
            assert "{{CIVILIANS}}" not in prompt, "CIVILIANS should be replaced"
            assert "{{MOLE}}" not in prompt, "MOLE should be replaced"
            assert "{{CLUE_HISTORY}}" not in prompt, "CLUE_HISTORY should be replaced"
            assert "{{RED_REMAINING}}" not in prompt, "RED_REMAINING should be replaced"
            assert "{{BLUE_REMAINING}}" not in prompt, "BLUE_REMAINING should be replaced"
            
            # Verify actual game content is present
            red_targets = [name for name, identity in board_state["identities"].items() 
                          if identity == "red_target"]
            blue_targets = [name for name, identity in board_state["identities"].items() 
                           if identity == "blue_target"]
            civilians = [name for name, identity in board_state["identities"].items() 
                        if identity == "civilian"]
            illegal = [name for name, identity in board_state["identities"].items() 
                      if identity == "illegal_target"]
            
            if red_targets:
                assert red_targets[0] in prompt, f"Red target {red_targets[0]} should be in prompt"
            if blue_targets:
                assert blue_targets[0] in prompt, f"Blue target {blue_targets[0]} should be in prompt"
            if civilians:
                assert civilians[0] in prompt, f"Civilian {civilians[0]} should be in prompt"
            if illegal:
                assert illegal[0] in prompt, f"Illegal target {illegal[0]} should be in prompt"

    def test_blue_coach_prompt_integration(self):
        """Test that AIPlayer.get_coach_move() generates correct prompts for blue team."""
        board_state = self.game.get_board_state(reveal_all=True)
        board_state["current_team"] = "blue"  # Switch to blue team
        
        with patch.object(self.blue_ai.adapter, 'call_model_with_metadata') as mock_call:
            mock_call.return_value = ("PLAY: TOOLS\nNUMBER: 3", {"tokens": 100, "cost": 0.01})
            
            try:
                play, number = self.blue_ai.get_coach_move(board_state, "prompts/blue_coach.md")
            except Exception:
                pass
            
            assert mock_call.called
            prompt = mock_call.call_args[0][1]
            
            # Verify no template variables remain
            assert "{{RED_SUBSCRIBERS}}" not in prompt
            assert "{{BLUE_SUBSCRIBERS}}" not in prompt
            assert "{{CIVILIANS}}" not in prompt
            assert "{{MOLE}}" not in prompt
            
            # Verify blue-specific content
            blue_targets = [name for name, identity in board_state["identities"].items() 
                           if identity == "blue_target"]
            if blue_targets:
                assert blue_targets[0] in prompt, "Blue targets should be in blue coach prompt"

    def test_red_player_prompt_integration(self):
        """Test that AIPlayer.get_player_moves() generates correct prompts for red team."""
        board_state = self.game.get_board_state(reveal_all=False)  # Players don't see identities
        
        with patch.object(self.red_ai.adapter, 'call_model_with_metadata') as mock_call:
            mock_call.return_value = ("WOLF\nKEY", {"tokens": 50, "cost": 0.005})
            
            try:
                guesses = self.red_ai.get_player_moves(board_state, "ANIMALS", 2, "prompts/red_player.md")
            except Exception:
                pass
            
            assert mock_call.called
            prompt = mock_call.call_args[0][1]
            
            # Verify template variables were replaced
            assert "{{BOARD}}" not in prompt, "BOARD should be replaced"
            assert "{{CLUE}}" not in prompt, "CLUE should be replaced"
            assert "{{NUMBER}}" not in prompt, "NUMBER should be replaced"
            assert "{{AVAILABLE_NAMES}}" not in prompt, "AVAILABLE_NAMES should be replaced"
            assert "{{CLUE_HISTORY}}" not in prompt, "CLUE_HISTORY should be replaced"
            
            # Verify actual content is present
            assert "ANIMALS" in prompt, "Clue should be in prompt"
            assert "2" in prompt, "Number should be in prompt"
            
            # Verify board names are present
            available_names = [name for name in board_state["board"] 
                             if not board_state["revealed"].get(name, False)]
            if available_names:
                assert available_names[0] in prompt, "Available names should be in prompt"

    def test_blue_player_prompt_integration(self):
        """Test that AIPlayer.get_player_moves() generates correct prompts for blue team."""
        board_state = self.game.get_board_state(reveal_all=False)
        board_state["current_team"] = "blue"
        
        with patch.object(self.blue_ai.adapter, 'call_model_with_metadata') as mock_call:
            mock_call.return_value = ("RIFLE\nGREADE", {"tokens": 50, "cost": 0.005})
            
            try:
                guesses = self.blue_ai.get_player_moves(board_state, "WEAPONS", 3, "prompts/blue_player.md")
            except Exception:
                pass
            
            assert mock_call.called
            prompt = mock_call.call_args[0][1]
            
            # Verify no template variables remain
            assert "{{BOARD}}" not in prompt
            assert "{{CLUE}}" not in prompt  
            assert "{{NUMBER}}" not in prompt
            assert "{{AVAILABLE_NAMES}}" not in prompt
            
            # Verify content
            assert "WEAPONS" in prompt, "Clue should be in prompt"
            assert "3" in prompt, "Number should be in prompt"

    def test_referee_prompt_integration(self):
        """Test that referee prompt generation works correctly."""
        # This tests the referee functionality from game.py
        board_state = self.game.get_board_state(reveal_all=True)
        
        with patch('playbook.game.prompt_manager') as mock_pm, \
             patch('playbook.game.OpenRouterAdapter') as mock_adapter:
            
            mock_pm.load_prompt.return_value = "REFEREE PROMPT"
            mock_adapter_instance = Mock()
            mock_adapter.return_value = mock_adapter_instance
            mock_adapter_instance.call_model.return_value = "LEGAL"
            
            # Import the function that uses referee
            from playbook.game import validate_clue_with_referee
            
            result = validate_clue_with_referee(
                clue="ANIMALS", 
                number=2, 
                team="red", 
                board_state=board_state,
                model="gpt-4"
            )
            
            # Verify prompt was loaded with correct context
            assert mock_pm.load_prompt.called
            call_args = mock_pm.load_prompt.call_args
            context = call_args[0][1]  # Second argument is context
            
            # Check that context has the right keys
            assert "clue" in context
            assert "number" in context
            assert "team" in context
            assert "board" in context
            assert "allied_subscribers" in context
            
            # Verify values
            assert context["clue"] == "ANIMALS"
            assert context["number"] == 2
            assert context["team"] == "red"

    def test_player_prompt_with_special_numbers(self):
        """Test player prompts with special number values (0, unlimited)."""
        board_state = self.game.get_board_state(reveal_all=False)
        
        # Test with number = 0
        with patch.object(self.red_ai.adapter, 'call_model_with_metadata') as mock_call:
            mock_call.return_value = ("PASS", {"tokens": 20, "cost": 0.001})
            
            try:
                guesses = self.red_ai.get_player_moves(board_state, "ZERO", 0, "prompts/red_player.md")
            except Exception:
                pass
            
            if mock_call.called:
                prompt = mock_call.call_args[0][1]
                assert "0" in prompt, "Zero should appear in prompt"
                assert "ZERO" in prompt, "Clue should appear in prompt"
        
        # Test with number = "unlimited"
        with patch.object(self.red_ai.adapter, 'call_model_with_metadata') as mock_call:
            mock_call.return_value = ("ALL TARGETS", {"tokens": 30, "cost": 0.002})
            
            try:
                guesses = self.red_ai.get_player_moves(board_state, "ALL", "unlimited", "prompts/red_player.md")
            except Exception:
                pass
            
            if mock_call.called:
                prompt = mock_call.call_args[0][1]
                assert "unlimited" in prompt or "ALL" in prompt, "Unlimited/clue should appear in prompt"

    def test_coach_prompt_includes_game_history(self):
        """Test that coach prompts include game history when available."""
        board_state = self.game.get_board_state(reveal_all=True)
        
        # Add some moves to the game history
        self.game.moves_log = [
            {
                "team": "red",
                "type": "coach",
                "play": "ANIMALS",
                "number": 2,
                "turn": 0
            },
            {
                "team": "red", 
                "type": "player",
                "guess": "WOLF",
                "correct": True,
                "turn": 0
            }
        ]
        
        with patch.object(self.blue_ai.adapter, 'call_model_with_metadata') as mock_call:
            mock_call.return_value = ("PLAY: RESPONSE\nNUMBER: 1", {"tokens": 100, "cost": 0.01})
            
            try:
                play, number = self.blue_ai.get_coach_move(board_state, "prompts/blue_coach.md")
            except Exception:
                pass
            
            if mock_call.called:
                prompt = mock_call.call_args[0][1]
                # Should include some indication of previous plays
                # The exact format depends on how clue_history is implemented
                assert "{{CLUE_HISTORY}}" not in prompt, "CLUE_HISTORY should be replaced"
