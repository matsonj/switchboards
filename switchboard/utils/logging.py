"""Logging utilities for The Switchboard."""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict


def setup_logging(log_dir: Path, verbose: bool = False):
    """Setup logging configuration."""
    log_dir.mkdir(exist_ok=True)

    # Configure root logger
    level = logging.DEBUG if verbose else logging.INFO

    # Create formatters
    console_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )

    file_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)

    # File handler
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"switchboard_{timestamp}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # JSONL logger for structured data
    jsonl_file = log_dir / f"switchboard_{timestamp}.jsonl"
    setup_jsonl_logger(jsonl_file)
    
    # Play-by-play logger for clean game events
    play_by_play_file = log_dir / f"play_by_play_{timestamp}.log"
    setup_play_by_play_logger(play_by_play_file)
    
    # Box score logger for team summaries
    box_score_file = log_dir / f"box_scores_{timestamp}.jsonl"
    setup_box_score_logger(box_score_file)

    logging.info(f"Logging initialized. Log file: {log_file}")
    logging.info(f"JSONL log file: {jsonl_file}")
    logging.info(f"Play-by-play log: {play_by_play_file}")
    logging.info(f"Box score log: {box_score_file}")


def setup_jsonl_logger(jsonl_file: Path):
    """Setup JSONL logger for structured game data."""
    jsonl_logger = logging.getLogger("switchboard.jsonl")
    jsonl_logger.setLevel(logging.INFO)
    jsonl_logger.propagate = False

    # Create JSONL handler
    jsonl_handler = logging.FileHandler(jsonl_file)
    jsonl_handler.setLevel(logging.INFO)

    # Simple formatter for JSONL (just the message)
    jsonl_formatter = logging.Formatter("%(message)s")
    jsonl_handler.setFormatter(jsonl_formatter)

    jsonl_logger.addHandler(jsonl_handler)


def log_game_event(event_type: str, data: Dict[str, Any]):
    """Log a game event in JSONL format."""
    jsonl_logger = logging.getLogger("switchboard.jsonl")

    event = {"timestamp": time.time(), "event_type": event_type, "data": data}

    jsonl_logger.info(json.dumps(event))


def log_ai_exchange(
    team: str, role: str, model: str, prompt: str, response: str, duration: float
):
    """Log an AI model exchange."""
    log_game_event(
        "ai_exchange",
        {
            "team": team,
            "role": role,
            "model": model,
            "prompt_length": len(prompt),
            "response_length": len(response),
            "duration": duration,
            "prompt": prompt,
            "response": response,
        },
    )


def setup_play_by_play_logger(play_by_play_file: Path):
    """Setup play-by-play logger for clean game events."""
    pbp_logger = logging.getLogger("switchboard.play_by_play")
    pbp_logger.setLevel(logging.INFO)
    pbp_logger.propagate = False

    # Create play-by-play handler
    pbp_handler = logging.FileHandler(play_by_play_file)
    pbp_handler.setLevel(logging.INFO)

    # Simple formatter for clean reading
    pbp_formatter = logging.Formatter("%(message)s")
    pbp_handler.setFormatter(pbp_formatter)

    pbp_logger.addHandler(pbp_handler)


def setup_box_score_logger(box_score_file: Path):
    """Setup box score logger for team performance summaries."""
    box_logger = logging.getLogger("switchboard.box_score")
    box_logger.setLevel(logging.INFO)
    box_logger.propagate = False

    # Create box score handler
    box_handler = logging.FileHandler(box_score_file)
    box_handler.setLevel(logging.INFO)

    # Simple formatter for JSONL (just the message)
    box_formatter = logging.Formatter("%(message)s")
    box_handler.setFormatter(box_formatter)

    box_logger.addHandler(box_handler)


def log_game_start(game_id: str, red_model: str, blue_model: str, board: list, identities: dict):
    """Log game start with initial state."""
    pbp_logger = logging.getLogger("switchboard.play_by_play")
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Count identities
    red_subs = [name for name, identity in identities.items() if identity == "red_subscriber"]
    blue_subs = [name for name, identity in identities.items() if identity == "blue_subscriber"]
    civilians = [name for name, identity in identities.items() if identity == "civilian"]
    mole = [name for name, identity in identities.items() if identity == "mole"][0]
    
    pbp_logger.info(f"=== GAME START [{timestamp}] ===")
    pbp_logger.info(f"Game ID: {game_id}")
    pbp_logger.info(f"Red Team: {red_model} ({len(red_subs)} subscribers)")
    pbp_logger.info(f"Blue Team: {blue_model} ({len(blue_subs)} subscribers)")
    starting_team = "RED" if len(red_subs) == 9 else "BLUE"
    pbp_logger.info(f"Starting Team: {starting_team}")
    pbp_logger.info("")
    pbp_logger.info("BOARD:")
    for i in range(0, 25, 5):
        row = " | ".join(f"{name:>12}" for name in board[i:i+5])
        pbp_logger.info(f"  {row}")
    pbp_logger.info("")
    pbp_logger.info(f"RED SUBSCRIBERS ({len(red_subs)}): {', '.join(red_subs)}")
    pbp_logger.info(f"BLUE SUBSCRIBERS ({len(blue_subs)}): {', '.join(blue_subs)}")
    pbp_logger.info(f"CIVILIANS ({len(civilians)}): {', '.join(civilians)}")
    pbp_logger.info(f"THE MOLE: {mole}")
    pbp_logger.info("=" * 50)
    pbp_logger.info("")


def format_turn_label(turn_count: int, team: str, starting_team: str) -> str:
    """Format turn label as 1a/1b style."""
    # turn_count starts at 0, so turn 0 = Turn 1a, turn 1 = Turn 1b, etc.
    turn_number = (turn_count // 2) + 1
    
    # Determine if this is the 'a' or 'b' phase based on turn order
    # Starting team always gets 'a', other team gets 'b'
    if team.lower() == starting_team.lower():
        turn_phase = "a"
    else:
        turn_phase = "b"
    
    return f"{turn_number}{turn_phase}"


def log_operator_clue(team: str, model: str, clue: str, number: int|str, turn_count: int, starting_team: str):
    """Log operator clue."""
    pbp_logger = logging.getLogger("switchboard.play_by_play")
    turn_label = format_turn_label(turn_count, team, starting_team)
    pbp_logger.info(f"Turn {turn_label} - {team.upper()} OPERATOR ({model}): \"{clue}\" ({number})")


def log_lineman_guess(team: str, model: str, guess: str, result: str, turn_count: int, starting_team: str):
    """Log lineman guess and result."""
    pbp_logger = logging.getLogger("switchboard.play_by_play")
    
    # Format result for display
    if result == "correct":
        icon = "✓"
        result_text = "CORRECT - Allied Subscriber"
    elif result == "civilian":
        icon = "○"
        result_text = "CIVILIAN"
    elif result == "enemy":
        icon = "✗"
        result_text = "ENEMY SUBSCRIBER"
    elif result == "mole":
        icon = "💀"
        result_text = "THE MOLE - GAME OVER!"
    else:
        icon = "?"
        result_text = result
    
    turn_label = format_turn_label(turn_count, team, starting_team)
    pbp_logger.info(f"Turn {turn_label} - {team.upper()} LINEMAN ({model}): {guess} → {icon} {result_text}")


def log_turn_end_status(red_remaining: int, blue_remaining: int):
    """Log remaining subscribers after turn ends."""
    pbp_logger = logging.getLogger("switchboard.play_by_play")
    pbp_logger.info(f"Status: Red {red_remaining} remaining, Blue {blue_remaining} remaining")
    pbp_logger.info("")


def log_game_end(winner: str, turns: int, duration: float):
    """Log game end."""
    pbp_logger = logging.getLogger("switchboard.play_by_play")
    
    pbp_logger.info("")
    pbp_logger.info("=" * 50)
    if winner:
        pbp_logger.info(f"WINNER: {winner.upper()} TEAM")
    else:
        pbp_logger.info("GAME ENDED IN DRAW")
    pbp_logger.info(f"Total Turns: {turns}")
    pbp_logger.info(f"Duration: {duration:.1f} seconds")
    pbp_logger.info("=" * 50)
    pbp_logger.info("")


def log_box_score(game_id: str, red_model: str, blue_model: str, result: dict):
    """Log team performance summary as JSONL."""
    box_logger = logging.getLogger("switchboard.box_score")
    
    # Calculate team stats
    red_moves = [move for move in result['moves'] if move['team'] == 'red']
    blue_moves = [move for move in result['moves'] if move['team'] == 'blue']
    
    red_stats = {
        "total_moves": len(red_moves),
        "correct_moves": sum(1 for move in red_moves if move['correct']),
        "incorrect_moves": sum(1 for move in red_moves if not move['correct']),
        "accuracy": sum(1 for move in red_moves if move['correct']) / len(red_moves) if red_moves else 0,
    }
    
    blue_stats = {
        "total_moves": len(blue_moves),
        "correct_moves": sum(1 for move in blue_moves if move['correct']),
        "incorrect_moves": sum(1 for move in blue_moves if not move['correct']),
        "accuracy": sum(1 for move in blue_moves if move['correct']) / len(blue_moves) if blue_moves else 0,
    }
    
    box_score = {
        "timestamp": time.time(),
        "game_id": game_id,
        "winner": result.get('winner'),
        "duration": result.get('duration', 0),
        "total_turns": result.get('turns', 0),
        "red_team": {
            "model": red_model,
            **red_stats
        },
        "blue_team": {
            "model": blue_model,
            **blue_stats
        }
    }
    
    box_logger.info(json.dumps(box_score))


def log_game_result(result: Dict[str, Any]):
    """Log final game result."""
    log_game_event("game_result", result)
