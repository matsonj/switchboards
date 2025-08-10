# The Switchboard AI Game Simulator

A Python simulation of **The Switchboard**, a game of clandestine communication and deduction where Operators pass cryptic messages to their Linemen to help them identify Allied Subscribers while avoiding The Mole.

## Game Overview

In The Switchboard:
- **25 names** are arranged on a board with hidden identities
- **Red Team**: 9 Allied Subscribers
- **Blue Team**: 8 Allied Subscribers  
- **7 Innocent Civilians**
- **1 The Mole** (instant loss if contacted)

Teams alternate turns:
1. **Operator** gives a cryptic clue and number
2. **Linemen** make up to N+1 guesses based on the clue
3. First team to find all their Allied Subscribers wins
4. Contact The Mole = instant loss

## Features

- **AI vs AI**: Different models for each team
- **Human vs AI**: Interactive mode for human players
- **Flexible AI Configuration**: Separate model assignment per team
- **External Prompt Templates**: Markdown files for easy prompt tuning
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
uv run switchboard run --red gpt4 --blue claude
```

### Interactive Mode (Human vs AI)
```bash
uv run switchboard run --red gpt4 --interactive
```

### Multiple Games
```bash
uv run switchboard run --red gpt4 --blue claude --num-puzzles 5
```

## Command Line Options

```bash
uv run switchboard run [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--red MODEL` | AI model for Red Team |
| `--blue MODEL` | AI model for Blue Team |
| `--interactive` | Enable human player mode |
| `--num-puzzles N` | Number of games to play (default: 1) |
| `--seed N` | Random seed for reproducible games |
| `--names-file PATH` | Path to names YAML file |
| `--red-operator-prompt PATH` | Red operator prompt file |
| `--red-lineman-prompt PATH` | Red lineman prompt file |
| `--blue-operator-prompt PATH` | Blue operator prompt file |
| `--blue-lineman-prompt PATH` | Blue lineman prompt file |
| `--log-path PATH` | Directory for log files |
| `--verbose` | Enable verbose logging |

## Available Models

The simulator supports 45+ models through OpenRouter. Use the `list-models` command to see all available options:

```bash
uv run switchboard list-models
```

**Popular models include:**
- `gpt4`, `gpt5`, `o3`, `o1` - OpenAI models
- `claude`, `sonnet`, `opus-4.1` - Anthropic models  
- `gemini`, `gemini-flash` - Google models
- `grok3`, `grok4` - xAI models
- `llama-3.3`, `qwen3`, `deepseek` - Open source models

**Reasoning models** (o1, o3, grok4, etc.) are automatically detected and configured with appropriate parameters.

## Project Structure

```
switchboard/
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
├── red_operator.md     # Red team operator prompts
├── red_lineman.md      # Red team lineman prompts
├── blue_operator.md    # Blue team operator prompts
└── blue_lineman.md     # Blue team lineman prompts

logs/                   # Game logs and statistics
```

## Customization

### Prompt Templates

Modify the Markdown files in `prompts/` to customize AI behavior:

```markdown
# The Switchboard - Red Team Operator

Your mission: Guide your Linemen to find {{TEAM}} Allied Subscribers.

Current Board:
{{BOARD}}

Secret Intelligence:
{{IDENTITIES}}

Provide your clue:
CLUE: [your clue]
NUMBER: [count]
```

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
$ uv run switchboard run --red gpt4 --blue claude --verbose

🎯 The Switchboard Game Starting!

Turn 1 - Red Team
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃    ALPHA    ┃    BRAVO    ┃   CHARLIE   ┃    DELTA    ┃     ECHO    ┃
┃   FOXTROT   ┃     GOLF    ┃    HOTEL    ┃    INDIA    ┃   JULIET    ┃
┃     KILO    ┃     LIMA    ┃     MIKE    ┃  NOVEMBER   ┃    OSCAR    ┃
┃     PAPA    ┃    QUEBEC   ┃    ROMEO    ┃   SIERRA    ┃    TANGO    ┃
┃   UNIFORM   ┃    VICTOR   ┃   WHISKEY   ┃     XRAY    ┃   YANKEE    ┃
┗━━━━━━━━━━━━━┻━━━━━━━━━━━━━┻━━━━━━━━━━━━━┻━━━━━━━━━━━━━┻━━━━━━━━━━━━━┛

Red Team Remaining: 9  Blue Team Remaining: 8

Red Operator: "Military phonetic alphabet" (3)
Red Lineman guesses: ALPHA
✓ Correct! ALPHA is an Allied Subscriber
Red Lineman guesses: BRAVO
✓ Correct! BRAVO is an Allied Subscriber
Red Lineman guesses: CHARLIE
✗ CHARLIE is an Innocent Civilian

Turn 2 - Blue Team
...
```

## Logging

The simulator creates detailed logs:

- **Console logs**: Real-time game progress
- **Text logs**: Detailed debug information
- **JSONL logs**: Structured data for analysis

## Security Features

- **Context Separation**: Each AI call is stateless and independent
- **No Conversation History**: Prevents information leakage between calls
- **Role-based Access**: Operators see all identities, Linemen see only public board

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
uv run mypy switchboard/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
