# Agent Instructions for The Switchboard AI Game Simulator

## Project Overview
This is a Python implementation of "The Switchboard" game - a strategic deduction game where teams use AI operators and linemen to identify allied subscribers while avoiding The Mole.

## Development Environment

### Key Commands
- **Install dependencies**: `uv sync`
- **Run game**: `uv run switchboard run --red gpt4 --blue claude`
- **Interactive mode**: `uv run switchboard run --red gpt4 --interactive`
- **Run tests**: `uv run pytest`
- **Format code**: `uv run black . && uv run isort .`
- **Type check**: `uv run mypy switchboard/`

### Project Structure
```
switchboard/                 # Main package
├── cli.py                  # Typer CLI interface
├── game.py                 # Core game logic and board management
├── player.py               # AIPlayer and HumanPlayer classes
├── prompt_manager.py       # Markdown template loader
├── adapters/
│   └── openrouter_adapter.py  # OpenRouter API client
└── utils/
    └── logging.py          # Logging configuration

inputs/
└── names.yaml              # Name bank for game boards

prompts/                    # Markdown prompt templates
├── red_operator.md
├── red_lineman.md
├── blue_operator.md
└── blue_lineman.md

logs/                       # Game logs and JSONL data
├── switchboard_*.log       # Detailed debug logs
├── switchboard_*.jsonl     # Structured event data
├── play_by_play_*.log      # Clean game events (clues, guesses, results)
└── box_scores_*.jsonl      # Team performance summaries
```

## Code Style & Conventions
- Use **type hints** throughout
- Follow **PEP 8** formatting
- Use **rich** for console output formatting
- Use **typer** for CLI interface
- Use **pydantic** for data validation where applicable
- Log structured data to **JSONL** for analysis

## Architecture Notes

### Game Flow
1. **Board Setup**: 25 names assigned random identities (9 red, 8 blue, 7 civilians, 1 mole)
2. **Turn Loop**: Teams alternate Operator → Lineman phases
3. **Operator Phase**: AI/Human gives cryptic clue + number
4. **Lineman Phase**: AI/Human makes up to N+1 guesses
5. **Win Conditions**: Find all allied subscribers OR opponent hits The Mole

### Key Design Principles
- **Stateless AI Calls**: Each OpenRouter request is independent (security requirement)
- **External Prompts**: All AI prompts loaded from Markdown files for easy tuning
- **Flexible Player Types**: Same interface for AI and Human players
- **Comprehensive Logging**: Both human-readable and structured machine-readable logs

### Testing Strategy
- Unit tests for game logic (board setup, identity assignment, win conditions)
- Integration tests for AI player interactions
- Mock OpenRouter API calls for reliable testing
- Test both AI vs AI and Human vs AI modes

## Environment Variables
- `OPENROUTER_API_KEY`: Required for AI model access

## Common Development Tasks

### Adding New AI Models
1. Update `model_mappings` in `openrouter_adapter.py`
2. Test with `uv run switchboard run --red NEW_MODEL --blue claude`

### Modifying Game Rules
- Edit board setup logic in `game.py`
- Update win/lose conditions in `process_guess()`
- Adjust N+1 rule implementation in lineman guess handling

### Customizing AI Prompts
- Edit Markdown files in `prompts/` directory
- Use template variables: `{{BOARD}}`, `{{IDENTITIES}}`, `{{CLUE}}`, etc.
- Test changes with `--verbose` flag to see full AI exchanges

### Debugging AI Behavior
1. Use `--verbose` to see all AI exchanges
2. Check `logs/` directory for detailed JSONL data
3. Modify prompt templates to adjust AI strategy
4. Test with `--seed` for reproducible games

### Game Analysis & Performance Tracking
The simulator produces multiple log formats for different analysis needs:

1. **Play-by-Play Logs** (`play_by_play_*.log`)
   - Clean, human-readable game events
   - Shows board state, clues, guesses, and results
   - Perfect for understanding game flow

2. **Box Score Data** (`box_scores_*.jsonl`)
   - Team performance summaries in JSONL format
   - Includes accuracy, move counts, win/loss data
   - Ideal for model performance comparison over time

3. **Structured Event Data** (`switchboard_*.jsonl`)
   - Detailed technical logs with full AI exchanges
   - Includes prompts, responses, timing data
   - For deep technical analysis

## Known Issues & TODOs
- [x] Implement model listing command (`list-models`) ✅
- [x] Add configuration file support for model mappings ✅
- [ ] Improve AI response parsing robustness
- [ ] Add game replay functionality from JSONL logs
- [ ] Implement tournament mode for model evaluation

## Dependencies
- **typer**: CLI framework
- **rich**: Terminal formatting
- **openai**: OpenRouter API client
- **pyyaml**: Configuration files
- **tenacity**: Retry logic for API calls
- **pydantic**: Data validation
