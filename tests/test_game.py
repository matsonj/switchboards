"""Tests for the core game logic."""

import random

import pytest

from switchboard.game import SwitchboardGame
from switchboard.player import HumanPlayer


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


class TestSwitchboardGame:
    """Test cases for SwitchboardGame."""

    def setup_method(self):
        """Setup for each test."""
        random.seed(42)  # Reproducible tests
        self.red_player = MockHumanPlayer()
        self.blue_player = MockHumanPlayer()
        self.game = SwitchboardGame(
            names_file="inputs/names.yaml",
            red_player=self.red_player,
            blue_player=self.blue_player,
        )

    def test_board_setup(self):
        """Test board initialization."""
        self.game.setup_board()

        # Check board size
        assert len(self.game.board) == 25

        # Check identity counts
        red_count = sum(
            1
            for identity in self.game.identities.values()
            if identity == "red_subscriber"
        )
        blue_count = sum(
            1
            for identity in self.game.identities.values()
            if identity == "blue_subscriber"
        )
        civilian_count = sum(
            1 for identity in self.game.identities.values() if identity == "civilian"
        )
        mole_count = sum(
            1 for identity in self.game.identities.values() if identity == "mole"
        )

        assert red_count == 9
        assert blue_count == 8
        assert civilian_count == 7
        assert mole_count == 1

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

    def test_process_guess_correct(self):
        """Test processing a correct guess."""
        self.game.setup_board()

        # Find a red subscriber to guess
        red_subscriber = None
        for name, identity in self.game.identities.items():
            if identity == "red_subscriber":
                red_subscriber = name
                break

        assert red_subscriber is not None

        # Process the guess
        result = self.game.process_guess(red_subscriber)

        assert result is True
        assert self.game.revealed[red_subscriber] is True
        assert len(self.game.moves_log) == 1
        assert self.game.moves_log[0]["correct"] is True

    def test_process_guess_civilian(self):
        """Test processing a civilian guess."""
        self.game.setup_board()

        # Find a civilian to guess
        civilian = None
        for name, identity in self.game.identities.items():
            if identity == "civilian":
                civilian = name
                break

        assert civilian is not None

        # Process the guess
        result = self.game.process_guess(civilian)

        assert result is False
        assert self.game.revealed[civilian] is True
        assert len(self.game.moves_log) == 1
        assert self.game.moves_log[0]["correct"] is False

    def test_process_guess_mole(self):
        """Test processing a mole guess (instant loss)."""
        self.game.setup_board()

        # Find the mole
        mole = None
        for name, identity in self.game.identities.items():
            if identity == "mole":
                mole = name
                break

        assert mole is not None

        # Process the guess
        result = self.game.process_guess(mole)

        assert result is False
        assert self.game.game_over is True
        assert self.game.winner == "blue"  # Red team loses
        assert self.game.revealed[mole] is True

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

        # Reveal all red subscribers except one
        red_subscribers = [
            name
            for name, identity in self.game.identities.items()
            if identity == "red_subscriber"
        ]

        # Reveal all but the last one
        for name in red_subscribers[:-1]:
            self.game.revealed[name] = True

        # Process the last red subscriber
        result = self.game.process_guess(red_subscribers[-1])

        assert result is True
        assert self.game.game_over is True
        assert self.game.winner == "red"
