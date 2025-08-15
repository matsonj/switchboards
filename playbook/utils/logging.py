"""Logging utilities for The Playbook."""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict


def setup_logging(log_dir: Path, verbose: bool = False):
    """Setup logging configuration."""
    log_dir.mkdir(exist_ok=True)

    # Configure root logger
    level = logging.DEBUG if verbose else logging.WARNING

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
    log_file = log_dir / f"playbook_{timestamp}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


    
    # Play-by-play logger for clean game events
    play_by_play_file = log_dir / f"play_by_play_{timestamp}.log"
    setup_play_by_play_logger(play_by_play_file)
    
    # Box score logger for team summaries
    box_score_file = log_dir / f"box_scores_{timestamp}.jsonl"
    setup_box_score_logger(box_score_file)
    
    # Game metadata logger for detailed metrics
    metadata_file = log_dir / f"game_metadata_{timestamp}.jsonl"
    setup_metadata_logger(metadata_file)

    logging.info(f"Logging initialized. Log file: {log_file}")
    logging.info(f"Play-by-play log: {play_by_play_file}")
    logging.info(f"Box score log: {box_score_file}")
    logging.info(f"Game metadata log: {metadata_file}")


def setup_jsonl_logger(jsonl_file: Path):
    """Setup JSONL logger for structured game data."""
    jsonl_logger = logging.getLogger("playbook.jsonl")
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
    jsonl_logger = logging.getLogger("playbook.jsonl")

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
    pbp_logger = logging.getLogger("playbook.play_by_play")
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
    box_logger = logging.getLogger("playbook.box_score")
    box_logger.setLevel(logging.INFO)
    box_logger.propagate = False

    # Create box score handler
    box_handler = logging.FileHandler(box_score_file)
    box_handler.setLevel(logging.INFO)

    # Simple formatter for JSONL (just the message)
    box_formatter = logging.Formatter("%(message)s")
    box_handler.setFormatter(box_formatter)

    box_logger.addHandler(box_handler)


def setup_metadata_logger(metadata_file: Path):
    """Setup metadata logger for detailed game metrics."""
    metadata_logger = logging.getLogger("playbook.metadata")
    metadata_logger.setLevel(logging.INFO)
    metadata_logger.propagate = False

    # Create metadata handler
    metadata_handler = logging.FileHandler(metadata_file)
    metadata_handler.setLevel(logging.INFO)

    # Simple formatter for JSONL (just the message)
    metadata_formatter = logging.Formatter("%(message)s")
    metadata_handler.setFormatter(metadata_formatter)

    metadata_logger.addHandler(metadata_handler)


def log_game_start(game_id: str, red_model: str, blue_model: str, field: list, identities: dict):
    """Log game start with initial state."""
    pbp_logger = logging.getLogger("playbook.play_by_play")
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Count identities
    red_targets = [name for name, identity in identities.items() if identity == "red_target"]
    blue_targets = [name for name, identity in identities.items() if identity == "blue_target"]
    fake_targets = [name for name, identity in identities.items() if identity == "fake_target"]
    illegal_target = [name for name, identity in identities.items() if identity == "illegal_target"][0]
    
    pbp_logger.info(f"=== GAME START [{timestamp}] ===")
    pbp_logger.info(f"Game ID: {game_id}")
    pbp_logger.info(f"Red Team: {red_model} ({len(red_targets)} targets)")
    pbp_logger.info(f"Blue Team: {blue_model} ({len(blue_targets)} targets)")
    starting_team = "RED" if len(red_targets) == 9 else "BLUE"
    pbp_logger.info(f"Starting Team: {starting_team}")
    pbp_logger.info("")
    pbp_logger.info("FIELD:")
    for i in range(0, 25, 5):
        row = " | ".join(f"{name:>12}" for name in field[i:i+5])
        pbp_logger.info(f"  {row}")
    pbp_logger.info("")
    pbp_logger.info(f"RED TARGETS ({len(red_targets)}): {', '.join(red_targets)}")
    pbp_logger.info(f"BLUE TARGETS ({len(blue_targets)}): {', '.join(blue_targets)}")
    pbp_logger.info(f"FAKE TARGETS ({len(fake_targets)}): {', '.join(fake_targets)}")
    pbp_logger.info(f"THE ILLEGAL TARGET: {illegal_target}")
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


def log_coach_play(team: str, model: str, play: str, number: int|str, turn_count: int, starting_team: str):
    """Log coach play."""
    pbp_logger = logging.getLogger("playbook.play_by_play")
    turn_label = format_turn_label(turn_count, team, starting_team)
    pbp_logger.info(f"Turn {turn_label} - {team.upper()} COACH ({model}): \"{play}\" ({number})")


def log_player_shot(team: str, model: str, shot: str, result: str, turn_count: int, starting_team: str):
    """Log player shot and result."""
    pbp_logger = logging.getLogger("playbook.play_by_play")
    
    # Format result for display
    if result == "goal":
        icon = "✓"
        result_text = "GOAL - Your Target"
    elif result == "miss":
        icon = "○"
        result_text = "MISS - Fake Target"
    elif result == "own_goal":
        icon = "✗"
        result_text = "OWN GOAL - Opposing Target"
    elif result == "ejection":
        icon = "💀"
        result_text = "THE ILLEGAL TARGET - EJECTION!"
    else:
        icon = "?"
        result_text = result
    
    turn_label = format_turn_label(turn_count, team, starting_team)
    pbp_logger.info(f"Turn {turn_label} - {team.upper()} PLAYER ({model}): {shot} → {icon} {result_text}")


def log_turn_end_status(red_remaining: int, blue_remaining: int):
    """Log remaining targets after turn ends."""
    pbp_logger = logging.getLogger("playbook.play_by_play")
    pbp_logger.info(f"Status: Red {red_remaining} remaining, Blue {blue_remaining} remaining")
    pbp_logger.info("")


def log_game_end(winner: str, turns: int, duration: float):
    """Log game end."""
    pbp_logger = logging.getLogger("playbook.play_by_play")
    
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


def log_referee_rejection(team: str, play: str, number: int|str, reasoning: str):
    """Log referee play rejection."""
    pbp_logger = logging.getLogger("playbook.play_by_play")
    if reasoning in ["Rule violation detected", "Play approved"]:
        pbp_logger.info(f"🔴 REFEREE REJECTION: {team.upper()} team play '{play}' ({number}) - {reasoning} (check detailed logs for specifics)")
    else:
        pbp_logger.info(f"🔴 REFEREE REJECTION: {team.upper()} team play '{play}' ({number}) - {reasoning}")
    pbp_logger.info(f"Turn ended due to invalid play")
    pbp_logger.info("")


def log_referee_penalty(violating_team: str, penalized_team: str, revealed_word: str):
    """Log referee penalty for invalid play."""
    pbp_logger = logging.getLogger("playbook.play_by_play")
    pbp_logger.info(f"⚖️  PENALTY: {revealed_word} revealed for {penalized_team.upper()} team due to {violating_team.upper()} team's invalid play")
    pbp_logger.info("")


def log_box_score(game_id: str, red_model: str, blue_model: str, result: dict):
    """Log team performance summary as JSONL."""
    box_logger = logging.getLogger("playbook.box_score")
    
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
    
    # Format the final board nicely
    final_board = result.get('final_board', {})
    board_layout = []
    if 'board' in final_board and 'identities' in final_board and 'revealed' in final_board:
        board = final_board['board']
        identities = final_board['identities']
        revealed = final_board['revealed']
        
        for i in range(0, 25, 5):
            row = []
            for j in range(5):
                idx = i + j
                name = board[idx]
                identity = identities.get(name, 'unknown')
                is_revealed = revealed.get(name, False)
                
                # Format name with identity and revealed status
                display_name = f"[{name}]" if is_revealed else name
                row.append(f"{display_name:>12} ({identity[0].upper()})")
            board_layout.append(" | ".join(row))
    
    box_score = {
        "timestamp": time.time(),
        "game_id": game_id,
        "winner": result.get('winner'),
        "duration": result.get('duration', 0),
        "total_turns": result.get('turns', 0),
        "board_layout": board_layout,
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


def log_game_setup_metadata(
    game_id: str,
    red_model: str,
    blue_model: str,
    prompt_files: dict,
    board: list,
    identities: dict
):
    """Log initial game setup metadata."""
    metadata_logger = logging.getLogger("playbook.metadata")
    
    # Organize words by identity
    red_words = [name for name, identity in identities.items() if identity == "red_target"]
    blue_words = [name for name, identity in identities.items() if identity == "blue_target"]
    civilian_words = [name for name, identity in identities.items() if identity == "civilian"]
    illegal_target_words = [name for name, identity in identities.items() if identity == "illegal_target"]
    
    setup_metadata = {
        "timestamp": time.time(),
        "game_id": game_id,
        "type": "game_setup",
        "red_model": red_model,
        "blue_model": blue_model,
        "red_coach_prompt": prompt_files.get("red_coach", ""),
        "red_player_prompt": prompt_files.get("red_player", ""),
        "blue_coach_prompt": prompt_files.get("blue_coach", ""),
        "blue_player_prompt": prompt_files.get("blue_player", ""),
        "referee_prompt": prompt_files.get("referee", ""),
        "words": {
            "red": red_words,
            "blue": blue_words,
            "civilians": civilian_words,
            "illegal_target": illegal_target_words
        }
    }
    
    metadata_logger.info(json.dumps(setup_metadata))


def log_ai_call_metadata(
    game_id: str,
    model_name: str,
    call_type: str,  # coach/player/referee
    team: str,
    turn: str,  # 1a, 1b, 2a, etc.
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    latency_ms: float,
    openrouter_cost: float = 0.0,
    upstream_cost: float = 0.0,
    turn_result: dict = None,
    game_continues: bool = True
):
    """Log detailed AI call metadata for analysis."""
    metadata_logger = logging.getLogger("playbook.metadata")
    
    metadata = {
        "timestamp": time.time(),
        "game_id": game_id,
        "model_name": model_name,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens, 
        "total_tokens": total_tokens,
        "latency_ms": latency_ms,
        "openrouter_cost": openrouter_cost,
        "upstream_cost": upstream_cost,
        "type": call_type,
        "team": team,
        "turn": turn,
        "game_continues": 1 if game_continues else 0
    }
    
    # Add turn-specific results
    if turn_result:
        metadata.update(turn_result)
    
    metadata_logger.info(json.dumps(metadata))
