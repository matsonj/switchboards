#!/usr/bin/env python3
"""Basic test of game setup without AI calls."""

import random

from switchboard.game import SwitchboardGame
from switchboard.player import HumanPlayer


# Mock human player for testing
class MockHumanPlayer(HumanPlayer):
    def __init__(self, moves=None):
        self.moves = moves or []
        self.move_index = 0

    def get_next_move(self):
        if self.move_index < len(self.moves):
            move = self.moves[self.move_index]
            self.move_index += 1
            return move
        return "ALPHA"  # Default fallback


def test_game_setup():
    """Test basic game setup and board generation."""
    print("Testing game setup...")

    # Set seed for reproducible test
    random.seed(42)

    # Create mock players
    red_player = MockHumanPlayer()
    blue_player = MockHumanPlayer()

    # Create game
    game = SwitchboardGame(
        names_file="inputs/names.yaml",
        red_player=red_player,
        blue_player=blue_player,
    )

    # Test board setup
    game.setup_board()

    print(f"Board size: {len(game.board)}")
    print(f"Board: {game.board[:10]}...")  # Show first 10 names

    # Count identities
    red_count = sum(
        1 for identity in game.identities.values() if identity == "red_subscriber"
    )
    blue_count = sum(
        1 for identity in game.identities.values() if identity == "blue_subscriber"
    )
    civilian_count = sum(
        1 for identity in game.identities.values() if identity == "civilian"
    )
    mole_count = sum(1 for identity in game.identities.values() if identity == "mole")

    print(f"Red subscribers: {red_count}")
    print(f"Blue subscribers: {blue_count}")
    print(f"Civilians: {civilian_count}")
    print(f"Moles: {mole_count}")

    # Verify counts
    assert len(game.board) == 25, f"Expected 25 names, got {len(game.board)}"
    assert red_count == 9, f"Expected 9 red subscribers, got {red_count}"
    assert blue_count == 8, f"Expected 8 blue subscribers, got {blue_count}"
    assert civilian_count == 7, f"Expected 7 civilians, got {civilian_count}"
    assert mole_count == 1, f"Expected 1 mole, got {mole_count}"

    print("✓ Game setup test passed!")

    # Test board display
    print("\nTesting board display...")
    game.display_board(reveal_all=True)

    print("✓ Board display test passed!")


if __name__ == "__main__":
    test_game_setup()
