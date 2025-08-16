# Prompt Template Schema

This document defines the expected template variables for each prompt template to ensure proper hydration and prevent runtime errors.

## Template Variable Conventions

- All template variables use `{{VARIABLE_NAME}}` format
- Variable names are UPPERCASE with underscores
- The PromptManager automatically converts lowercase context keys to uppercase placeholders
- Example: context key `"clue"` becomes placeholder `{{CLUE}}`

## Coach Templates

### red_coach.md & blue_coach.md
**Required Variables:**
- `{{FIELD}}` - Game board as 5x5 grid (list of 25 names)
- `{{REVEALED}}` - Comma-separated list of revealed target names
- `{{TEAM}}` - Team name ("red" or "blue")
- `{{RED_REMAINING}}` - Number of red targets remaining
- `{{BLUE_REMAINING}}` - Number of blue targets remaining
- `{{RED_TARGETS}}` - Comma-separated list of red team targets (hidden from blue coach)
- `{{BLUE_TARGETS}}` - Comma-separated list of blue team targets (hidden from red coach)
- `{{FAKES}}` - Comma-separated list of civilian (fake) targets
- `{{ILLEGAL}}` - The illegal target name
- `{{PLAY_HISTORY}}` - Game history of previous plays and outcomes

**Context Keys (from code):**
```python
{
    "field": board_state["board"],
    "revealed": ", ".join(revealed_names),
    "team": self.current_team,
    "red_remaining": red_remaining,
    "blue_remaining": blue_remaining,
    "red_targets": ", ".join(red_subscribers),
    "blue_targets": ", ".join(blue_subscribers),
    "fakes": ", ".join(civilians),
    "illegal": illegal_target[0],
    "play_history": clue_history
}
```

## Player Templates

### red_player.md & blue_player.md
**Required Variables:**
- `{{FIELD}}` - Game board as 5x5 grid
- `{{AVAILABLE_TARGETS}}` - Comma-separated list of unrevealed names
- `{{PLAY}}` - Current play word from coach
- `{{NUMBER}}` - Number of targets related to play (int or "unlimited")
- `{{TEAM}}` - Team name ("red" or "blue")
- `{{PLAY_HISTORY}}` - Game history of previous plays and outcomes

**Context Keys (from code):**
```python
{
    "field": board_state["board"],
    "available_targets": ", ".join(available_names),
    "play": play,
    "number": number,
    "team": team,
    "play_history": clue_history
}
```

## Referee Template

### referee.md
**Required Variables:**
- `{{PLAY}}` - Proposed play word to validate
- `{{NUMBER}}` - Proposed number (int or "unlimited")
- `{{TEAM}}` - Team making the play ("red" or "blue")
- `{{FIELD}}` - Current board state as comma-separated list
- `{{ALLIED_TARGETS}}` - Comma-separated list of current team's targets

**Context Keys (from code):**
```python
{
    "play": play,
    "number": parsed_number,
    "team": team,
    "field": ", ".join(field_state["board"]),
    "allied_targets": ", ".join(allied_targets)
}
```

## Shared Includes

### shared/game_rules.md
This file is included in other templates via `{{include:shared/game_rules.md}}` and contains no template variables itself.

## Validation

The PromptManager now includes strict validation that:
1. Identifies all template variables in loaded templates using regex `\{\{([A-Z_]+)\}\}`
2. Checks that all template variables have corresponding context values
3. Raises `PromptHydrationError` if any variables are missing
4. Causes the program to fail fast rather than continue with malformed prompts

## Adding New Templates

When adding new prompt templates:
1. Use consistent variable naming following the conventions above
2. Document required variables in this schema
3. Test with validation enabled to ensure all variables are properly hydrated
4. Use consistent terminology (prefer "play" over "clue", "targets" over "subscribers" in display text)
