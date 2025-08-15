# Agent Instructions for The Playbook AI Game Simulator

## Project Overview
This is a Python implementation of "Playbook" - a strategic deduction game where teams use AI coaches and players to identify allied targets while avoiding The Illegal Target.

## Development Environment

### Key Commands
- **Install dependencies**: `uv sync`
- **Run game**: `uv run playbook run --red gpt4 --blue claude`
- **Interactive mode**: `uv run playbook run --red gpt4 --interactive`
- **Test prompts**: `uv run playbook prompt coach --seed 42`
- **Run tests**: `uv run pytest`
- **Format code**: `uv run black . && uv run isort .`
- **Type check**: `uv run mypy playbook/`

### Project Structure
```
playbook/                   # Main package
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
├── red_coach.md
├── red_player.md
├── blue_coach.md
└── blue_player.md

logs/                       # Game logs and analysis data
├── playbook_*.log          # Detailed debug logs
├── play_by_play_*.log      # Clean game events (plays, shots, results)
├── box_scores_*.jsonl      # Team performance summaries with formatted boards
├── game_metadata_*.jsonl   # AI call metrics (tokens, costs, latency, results)
└── referee_*.log           # Consolidated referee validation logs
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
1. **Board Setup**: 25 names assigned random identities (9 red, 8 blue, 7 civilians, 1 illegal target)
2. **Turn Loop**: Teams alternate Coach → Player phases
3. **Coach Phase**: AI/Human gives cryptic play + number
4. **Player Phase**: AI/Human makes up to N+1 shots
5. **Win Conditions**: Find all allied targets OR opponent hits The Illegal Target

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

### Testing AI Prompts
- **Test coach prompts**: `uv run playbook prompt coach --seed 42 --team red`
- **Test player prompts**: `uv run playbook prompt player --seed 42 --play "TOOLS" --number 3`
- **Test referee prompts**: `uv run playbook prompt referee --seed 42 --play "WEAPONS" --number 2`
- **Test expert plays**: `uv run playbook prompt player --play "ANIMALS" --number 0` or `--number unlimited`

### Adding New AI Models
1. Update `model_mappings` in `openrouter_adapter.py`
2. Test with `uv run playbook run --red NEW_MODEL --blue claude`

### Modifying Game Rules
- Edit board setup logic in `game.py`
- Update win/lose conditions in `process_guess()`
- Adjust N+1 rule implementation in lineman shot handling

### Customizing AI Prompts
- Edit Markdown files in `prompts/` directory
- Use template variables: `{{BOARD}}`, `{{IDENTITIES}}`, `{{PLAY}}`, etc.
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
   - Shows board state, plays, shots, and results
   - Perfect for understanding game flow

2. **Box Score Data** (`box_scores_*.jsonl`)
   - Team performance summaries in JSONL format
   - Includes accuracy, move counts, win/loss data
   - Features formatted 5x5 board showing revealed names
   - Ideal for model performance comparison over time

3. **Game Metadata** (`game_metadata_*.jsonl`)
   - Detailed AI call metrics (tokens, costs, latency)
   - Turn-by-turn results and success/failure tracking
   - Model performance analytics for cost optimization
   - Essential for model comparison and evaluation

4. **Referee Logs** (`referee_*.log`)
   - Consolidated clue validation logs with team headers
   - Shows all referee decisions and reasoning
   - Helps debug prompt quality and fairness issues

## Known Issues & TODOs
- [x] Implement model listing command (`list-models`) ✅
- [x] Add configuration file support for model mappings ✅
- [x] Implement expert clue types (0 and unlimited) ✅
- [x] Implement comprehensive logging with cost tracking ✅
- [x] Clean up duplicate names in inputs/names.yaml ✅
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
