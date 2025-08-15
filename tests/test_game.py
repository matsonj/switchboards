"""Tests for the core game logic."""

import random

import pytest

from playbook.game import PlaybookGame
from playbook.player import HumanPlayer


class MockHumanPlayer(HumanPlayer):
    """Mock human player for testing."""

    def __init__(self, moves=None):
        self.moves = moves or []
        self.move_index = 0

    def get_next_move(self):
        if self.move_index < len(self.moves):
            move = self.moves[self.move_index]
            self.move_index += 1
            return move
        return "ALPHA"  # Default fallback


class TestPlaybookGame:
    """Test cases for PlaybookGame."""

    def setup_method(self):
        """Setup for each test."""
        random.seed(42)  # Reproducible tests
        self.red_player = MockHumanPlayer()
        self.blue_player = MockHumanPlayer()
        self.game = PlaybookGame(
            names_file="inputs/names.yaml",
            red_player=self.red_player,
            blue_player=self.blue_player,
        )

    def test_board_setup(self):
        """Test board initialization."""
        self.game.setup_board()

        # Check board size
        assert len(self.game.field) == 25

        # Check identity counts
        red_count = sum(
            1
            for identity in self.game.identities.values()
            if identity == "red_target"
        )
        blue_count = sum(
            1
            for identity in self.game.identities.values()
            if identity == "blue_target"
        )
        civilian_count = sum(
            1 for identity in self.game.identities.values() if identity == "civilian"
        )
        illegal_target_count = sum(
            1 for identity in self.game.identities.values() if identity == "illegal_target"
        )

        assert red_count == 9
        assert blue_count == 8
        assert civilian_count == 7
        assert illegal_target_count == 1

        # Check all names are initially unrevealed
        assert all(not revealed for revealed in self.game.revealed.values())

    def test_board_state(self):
        """Test board state retrieval."""
        self.game.setup_board()

        # Test public board state
        public_state = self.game.get_board_state(reveal_all=False)
        assert len(public_state["board"]) == 25
        assert public_state["current_team"] == "red"
        assert public_state["turn_count"] == 0
        assert len(public_state["identities"]) == 0  # Nothing revealed yet

        # Test revealed board state
        full_state = self.game.get_board_state(reveal_all=True)
        assert len(full_state["identities"]) == 25  # All identities shown

    def test_process_shot_correct(self):
        """Test processing a correct shot."""
        self.game.setup_board()

        # Find a target of the current team to shoot
        current_team_target = None
        for name, identity in self.game.identities.items():
            if identity == f"{self.game.current_team}_target":
                current_team_target = name
                break

        assert current_team_target is not None

        # Process the shot
        result = self.game.process_guess(current_team_target)

        assert result is True
        assert self.game.revealed[current_team_target] is True
        assert len(self.game.moves_log) == 1
        assert self.game.moves_log[0]["correct"] is True

    def test_process_shot_civilian(self):
        """Test processing a civilian shot."""
        self.game.setup_board()

        # Find a civilian to shoot
        civilian = None
        for name, identity in self.game.identities.items():
            if identity == "civilian":
                civilian = name
                break

        assert civilian is not None

        # Process the shot
        result = self.game.process_guess(civilian)

        assert result is False
        assert self.game.revealed[civilian] is True
        assert len(self.game.moves_log) == 1
        assert self.game.moves_log[0]["correct"] is False

    def test_process_shot_illegal_target(self):
        """Test processing an illegal target shot (instant loss)."""
        self.game.setup_board()

        # Find the illegal target
        illegal_target = None
        for name, identity in self.game.identities.items():
            if identity == "illegal_target":
                illegal_target = name
                break

        assert illegal_target is not None

        # Process the shot
        result = self.game.process_guess(illegal_target)

        assert result is False
        assert self.game.game_over is True
        assert self.game.winner == "blue"  # Red team loses
        assert self.game.revealed[illegal_target] is True

    def test_switch_teams(self):
        """Test team switching."""
        assert self.game.current_team == "red"
        assert self.game.turn_count == 0

        self.game.switch_teams()

        assert self.game.current_team == "blue"
        assert self.game.turn_count == 1

        self.game.switch_teams()

        assert self.game.current_team == "red"
        assert self.game.turn_count == 2

    def test_win_condition(self):
        """Test win condition detection."""
        self.game.setup_board()

        # Reveal all red targets except one
        red_targets = [
            name
            for name, identity in self.game.identities.items()
            if identity == "red_target"
        ]

        # Reveal all but the last one
        for name in red_targets[:-1]:
            self.game.revealed[name] = True

        # Process the last red target
        result = self.game.process_guess(red_targets[-1])

        assert result is True
        assert self.game.game_over is True
        assert self.game.winner == "red"
