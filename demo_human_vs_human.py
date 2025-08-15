#!/usr/bin/env python3
"""Demo of human vs human gameplay."""

import random

from playbook.game import PlaybookGame
from playbook.player import HumanPlayer


# Create a simple demo that doesn't require API keys
def demo_human_vs_human():
    """Run a demonstration of human vs human gameplay."""
    print("🎯 The Switchboard - Human vs Human Demo")
    print("=" * 50)

    # Set seed for reproducible demo
    random.seed(42)

    # Create human players
    red_player = HumanPlayer()
    blue_player = HumanPlayer()

    # Create game
    game = SwitchboardGame(
        names_file="inputs/names.yaml",
        red_player=red_player,
        blue_player=blue_player,
    )

    print("Setting up board...")
    game.setup_board()

    print("\nBoard created with hidden identities!")
    print("In a real game, only the Operator would see all identities.")
    print("\nHere's the board with all identities revealed (for demo purposes):")

    game.display_board(reveal_all=True)

    print("\nIdentity Summary:")
    red_subs = [
        name
        for name, identity in game.identities.items()
        if identity == "red_subscriber"
    ]
    blue_subs = [
        name
        for name, identity in game.identities.items()
        if identity == "blue_subscriber"
    ]
    civilians = [
        name for name, identity in game.identities.items() if identity == "civilian"
    ]
    mole = [name for name, identity in game.identities.items() if identity == "mole"][0]

    print(f"🔴 Red Subscribers ({len(red_subs)}): {', '.join(red_subs)}")
    print(f"🔵 Blue Subscribers ({len(blue_subs)}): {', '.join(blue_subs)}")
    print(f"😐 Civilians ({len(civilians)}): {', '.join(civilians)}")
    print(f"💀 The Mole: {mole}")

    print("\n" + "=" * 50)
    print("In a real game, the Linemen would only see unrevealed names")
    print("and receive clues from their Operators.")
    print("Demo complete!")


if __name__ == "__main__":
    demo_human_vs_human()
