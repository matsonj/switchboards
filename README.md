# The Playbook AI Game Simulator

A Python simulation of **The Playbook**, a strategic deduction game where Coaches give cryptic plays to their Players to help them identify Allied Targets while avoiding The Illegal Target.

## Game Overview

In The Playbook:
- **25 names** are arranged on a board with hidden identities
- **Red Team**: 9 Allied Targets
- **Blue Team**: 8 Allied Targets  
- **7 Innocent Civilians**
- **1 The Illegal Target** (instant loss if shot)

Teams alternate turns:
1. **Coach** gives a cryptic play and number
2. **Player** takes up to N+1 shots based on the play
3. First team to find all their Allied Targets wins
4. Hit The Illegal Target = instant loss

## Features

- **AI vs AI**: Different models for each team
- **Human vs AI**: Interactive mode for human players
- **Flexible AI Configuration**: Separate model assignment per team
- **External Prompt Templates**: Markdown files for easy prompt tuning
- **Expert Play Types**: Support for zero plays (0) and unlimited plays
- **Referee Validation**: AI-powered play validation for fair play
- **Prompt Testing**: Built-in tools to test and debug AI prompts
- **Comprehensive Logging**: Detailed game logs and statistics
- **OpenRouter Integration**: Access to 200+ AI models

## Installation

Requires Python ≥3.12 and [uv](https://github.com/astral-sh/uv).

```bash
git clone <repository>
cd switchboards
uv sync
```

## Quick Start

### Set Up API Key
```bash
export OPENROUTER_API_KEY="your-key-here"
```

### Run AI vs AI Game
```bash
uv run playbook run --red gpt4 --blue claude
```

### Interactive Mode (Human vs AI)
```bash
uv run playbook run --red gpt4 --interactive
```

### Multiple Games
```bash
uv run playbook run --red gpt4 --blue claude --num-puzzles 5
```

### Test AI Prompts
```bash
# Test coach prompts
uv run playbook prompt coach --seed 42 --team red

# Test player prompts with regular plays
uv run playbook prompt player --seed 42 --play "TOOLS" --number 3

# Test expert play types
uv run playbook prompt player --play "ANIMALS" --number 0
uv run playbook prompt player --play "FRUITS" --number unlimited

# Test referee validation
uv run playbook prompt referee --seed 42 --play "MILITARY" --number 2
```

## Command Line Options

```bash
uv run playbook run [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--red MODEL` | AI model for Red Team |
| `--blue MODEL` | AI model for Blue Team |
| `--interactive` | Enable human player mode |
| `--num-puzzles N` | Number of games to play (default: 1) |
| `--seed N` | Random seed for reproducible games |
| `--names-file PATH` | Path to names YAML file |
| `--red-coach-prompt PATH` | Red coach prompt file |
| `--red-player-prompt PATH` | Red player prompt file |
| `--blue-coach-prompt PATH` | Blue coach prompt file |
| `--blue-player-prompt PATH` | Blue player prompt file |
| `--referee MODEL` | AI model for referee validation |
| `--no-referee` | Disable referee validation |
| `--log-path PATH` | Directory for log files |
| `--verbose` | Enable verbose logging |

### Prompt Testing Commands

```bash
uv run playbook prompt [coach|player|referee] [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--team red/blue` | Team color (red or blue) |
| `--seed N` | Random seed for reproducible boards |
| `--play TEXT` | Sample play for player/referee testing |
| `--number N` | Sample number (supports 0, unlimited, or integers) |

## Available Models

The simulator supports 45+ models through OpenRouter. Use the `list-models` command to see all available options:

```bash
uv run playbook list-models
```

**Popular models include:**
- `gpt4`, `gpt5`, `o3`, `o1` - OpenAI models
- `claude`, `sonnet`, `opus-4.1` - Anthropic models  
- `gemini`, `gemini-flash` - Google models
- `grok3`, `grok4` - xAI models
- `llama-3.3`, `qwen3`, `deepseek` - Open source models

**Reasoning models** (o1, o3, grok4, etc.) are automatically detected and configured with appropriate parameters.

## Architecture

The Playbook simulator uses a modular design with three key submodules that handle different aspects of AI-driven gameplay:

**Key Submodules:**
- **Prompt Manager**: Builds formatted prompts from markdown templates with variable substitution
- **OpenRouter Adapter**: Handles AI API calls with cost tracking and retry logic  
- **Referee**: Validates coach plays for fairness (coach phase only)

**Flow:** Build Prompt → Get AI Response → (Referee Validation for Coaches) → Process Results

```mermaid
flowchart TD
    %% Game Initialization
    A[Game Start] --> B[Load Names from YAML]
    B --> C[Random Field Setup<br/>9 Red, 8 Blue, 7 Civilians, 1 Illegal Target]
    C --> D[Choose Starting Team]
    
    %% Main Game Loop
    D --> E{Game Over?}
    E -->|No| F[Current Team Turn]
    E -->|Yes| Z[Game End]
    
    %% Turn Structure
    F --> G[COACH PHASE]
    G --> H[PLAYER PHASE]
    H --> I[Switch Teams]
    I --> E
    
    %% Coach Phase
    G --> G1[Build Coach Prompt]
    G1 --> G2[Get AI Response]
    G2 --> G3[Validate Play with Referee]
    G3 --> G4{Valid Play?}
    G4 -->|Yes| H
    G4 -->|No| G5[End Turn with Penalty]
    G5 --> I
    
    %% Player Phase
    H --> H1[Build Player Prompt]
    H1 --> H2[Get AI Response]
    H2 --> H3[Parse Field Names]
    H3 --> H4[Process Each Shot]
    H4 --> H5{Correct Shot?}
    H5 -->|Allied Target| H6[Continue Shooting<br/>up to N+1 total]
    H5 -->|Wrong Target| H7[End Turn]
    H5 -->|The Illegal Target| H8[Instant Loss]
    H6 --> H9{More Shots<br/>Available?}
    H9 -->|Yes| H4
    H9 -->|No| I
    H7 --> I
    H8 --> Z
    
    %% Referee Validation Details
    G6 --> U1[Load Referee Prompt Template]
    U1 --> U2[PromptManager:<br/>Insert Play,<br/>Number,<br/>Field Names,<br/>Validation Rules]
    U2 --> U3[AI Player: Call OpenRouter API]
    U3 --> U4[Parse Response:<br/>VALID/INVALID + Reasoning]
    U4 --> G7
    
    %% OpenRouter Integration
    G3 --> API[OpenRouterAdapter]
    H3 --> API
    U3 --> API
    API --> API1[Map Model Name<br/>gpt4 → openai/gpt-4]
    API1 --> API2[Build API Request<br/>with Usage Tracking]
    API2 --> API3[Call OpenRouter API<br/>with Retry Logic]
    API3 --> API4[Parse Response +<br/>Extract Metadata]
    API4 --> API5[Log AI Call Metrics:<br/>Tokens, Cost, Latency]
    API5 --> API6[Return Response + Metadata]
    
    %% Prompt Template System
    G1 --> PM[PromptManager]
    H1 --> PM
    U1 --> PM
    PM --> PM1[Load Markdown Template]
    PM1 --> PM2[Process VARIABLES:<br/>FIELD, IDENTITIES,<br/>PLAY_HISTORY, etc.]
    PM2 --> PM3[Handle include:shared/game_rules.md]
    PM3 --> PM4[Return Formatted Prompt]
    
    %% Logging System
    API5 --> L1[Game Metadata JSONL<br/>Tokens, Costs, Latency]
    H5 --> L2[Play-by-Play Log<br/>Human Readable Events]
    Z --> L3[Box Score JSONL<br/>Team Performance + Field]
    U4 --> L4[Referee Log<br/>Validation Decisions]
    
    %% Styling
    classDef gameLogic fill:#1f2937,stroke:#10b981,color:#fff
    classDef aiSystem fill:#1e293b,stroke:#3b82f6,color:#fff
    classDef promptSystem fill:#292524,stroke:#f59e0b,color:#fff
    classDef logging fill:#1c1917,stroke:#ef4444,color:#fff
    
    class A,B,C,D,E,F,G,H,I,Z gameLogic
    class G3,H3,U3,API,API1,API2,API3,API4,API5,API6 aiSystem
    class G1,G2,H1,H2,U1,U2,PM,PM1,PM2,PM3,PM4 promptSystem
    class L1,L2,L3,L4 logging
```

## Project Structure

```
playbook/
├── cli.py              # Command-line interface
├── game.py             # Core game logic
├── player.py           # Player classes (AI & Human)
├── prompt_manager.py   # Prompt template management
├── adapters/
│   └── openrouter_adapter.py  # OpenRouter API integration
└── utils/
    └── logging.py      # Logging utilities

inputs/
└── names.yaml          # Name bank for games

prompts/
├── red_coach.md        # Red team coach prompts
├── red_player.md       # Red team player prompts
├── blue_coach.md       # Blue team coach prompts
├── blue_player.md      # Blue team player prompts
├── referee.md          # Referee play validation prompts
└── shared/
    └── game_rules.md   # Shared game rules for all prompts

logs/                   # Game logs and performance analytics
```

## Advanced Game Features

### Expert Play Types

The Playbook supports advanced play strategies:

- **Zero Plays (0)**: "None of our targets relate to this play" - unlimited shots, must shoot at least one
- **Unlimited Plays**: Multiple related targets from previous rounds - unlimited shots, no minimum

```bash
# Examples in interactive mode
Red Coach: "ANIMALS" (0)        # Zero play
Blue Coach: "FRUITS" (unlimited) # Unlimited play
```

### Referee Validation

AI-powered play validation ensures fair play by checking:
- Single word requirement (with exceptions for compound words, proper names, abbreviations)
- No direct field name matches
- No variants of field words
- No letter count references
- No position references

### Game History Tracking

Players receive comprehensive game history showing all previous plays and outcomes:

```
Turn 1a: Red Play: "FRUITS" (3)
  → APPLE ✓, BANANA ✓, COCONUT ○ (civilian)

Turn 1b: Blue Play: "METALS" (2)
  → IRON ✓, STEEL ✗ (enemy)
```

## Customization

### Prompt Templates

Modify the Markdown files in `prompts/` to customize AI behavior. Templates support variable substitution:

**Coach Prompts:**
- `{{RED_TARGETS}}` - Your allied targets
- `{{BLUE_TARGETS}}` - Enemy targets  
- `{{CIVILIANS}}` - Innocent civilians
- `{{ILLEGAL_TARGET}}` - The dangerous illegal target

**Player Prompts:**
- `{{FIELD}}` - Current 5x5 field grid
- `{{AVAILABLE_NAMES}}` - Available names to shoot
- `{{PLAY_HISTORY}}` - Formatted game history
- `{{PLAY}}` - Current play
- `{{NUMBER}}` - Current number (supports 0, unlimited)

**Shared Rules:**
Use `{{include:shared/game_rules.md}}` to include common game rules across prompts.

### Model Configuration

Add new models by editing `inputs/model_mappings.yml`:

```yaml
models:
  # Add custom model mappings
  my-model: "provider/model-id"
  custom-gpt: "openai/gpt-4-custom"
  # ... etc
```

### Name Banks

Edit `inputs/names.yaml` to customize the name pool:

```yaml
names:
  - ALPHA
  - BRAVO
  - CHARLIE
  # ... add more names
```

## Example Game

```bash
$ uv run playbook run --red gpt4 --blue claude --verbose

🎯 The Playbook Game Starting!

Turn 1 - Red Team
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃    ALPHA    ┃    BRAVO    ┃   CHARLIE   ┃    DELTA    ┃     ECHO    ┃
┃   FOXTROT   ┃     GOLF    ┃    HOTEL    ┃    INDIA    ┃   JULIET    ┃
┃     KILO    ┃     LIMA    ┃     MIKE    ┃  NOVEMBER   ┃    OSCAR    ┃
┃     PAPA    ┃    QUEBEC   ┃    ROMEO    ┃   SIERRA    ┃    TANGO    ┃
┃   UNIFORM   ┃    VICTOR   ┃   WHISKEY   ┃     XRAY    ┃   YANKEE    ┃
┗━━━━━━━━━━━━━┻━━━━━━━━━━━━━┻━━━━━━━━━━━━━┻━━━━━━━━━━━━━┻━━━━━━━━━━━━━┛

Red Team Remaining: 9  Blue Team Remaining: 8

Red Coach: "Military phonetic alphabet" (3)
Red Player shoots: ALPHA
✓ Correct! ALPHA is an Allied Target
Red Player shoots: BRAVO
✓ Correct! BRAVO is an Allied Target
Red Player shoots: CHARLIE
✗ CHARLIE is an Innocent Civilian

Turn 2 - Blue Team
...
```

## Logging & Analytics

The simulator creates comprehensive logs for analysis and debugging:

### Log Types

1. **Play-by-Play Logs** (`logs/play_by_play_*.log`)
   - Human-readable game events and field states
   - Perfect for understanding game progression
   - Shows plays, shots, results, and team performance

2. **Box Score Analytics** (`logs/box_scores_*.jsonl`)
   - Team performance summaries in structured format
   - Includes accuracy metrics, move counts, win/loss data
   - Features formatted 5x5 fields showing all revealed names
   - Ideal for comparing model performance across games

3. **AI Call Metadata** (`logs/game_metadata_*.jsonl`)
   - Detailed metrics for every AI interaction
   - Tracks tokens used, API costs, response latency
   - Turn-by-turn success/failure analysis
   - Essential for cost optimization and model comparison

4. **Referee Validation Logs** (`logs/referee_*.log`)
   - Consolidated play validation decisions
   - Shows reasoning for accepting/rejecting plays
   - Helps debug prompt quality and game fairness

5. **Debug Logs** (`logs/playbook_*.log`)
   - Technical debug information
   - Full API request/response details when using `--verbose`

### Performance Tracking

The JSONL logs enable powerful analysis:

```bash
# Analyze model costs across games
cat logs/game_metadata_*.jsonl | jq '.cost_usd' | awk '{sum+=$1} END {print "Total cost: $" sum}'

# Compare model accuracy by team
cat logs/box_scores_*.jsonl | jq '{team: .team, accuracy: .accuracy, model: .model}'

# Track token usage patterns
cat logs/game_metadata_*.jsonl | jq '{model: .model, tokens: .tokens_used, role: .role}'
```

## Security Features

- **Context Separation**: Each AI call is stateless and independent
- **No Conversation History**: Prevents information leakage between calls
- **Role-based Access**: Coaches see all identities, Players see only public field

## Development

### Running Tests
```bash
uv run pytest
```

### Code Formatting
```bash
uv run black .
uv run isort .
```

### Type Checking
```bash
uv run mypy playbook/
```

### Debugging AI Prompts

Use the built-in prompt testing tools to debug and optimize AI behavior:

```bash
# Test with different seeds to see various field configurations
uv run playbook prompt coach --seed 42
uv run playbook prompt coach --seed 100

# Test different play scenarios
uv run playbook prompt player --play "WEAPONS" --number 2
uv run playbook prompt player --play "NATURE" --number unlimited
uv run playbook prompt player --play "FOOD" --number 0

# Test referee validation with edge cases
uv run playbook prompt referee --play "DELTA" --number 1  # Should be invalid (field name)
uv run playbook prompt referee --play "MILITARY" --number 3  # Should be valid
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
