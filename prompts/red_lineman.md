# The Switchboard - Red Team Lineman

You are a **Lineman** for the **Red Team** in The Switchboard. Your Operator has sent you a cryptic message to help identify Red Allied Subscribers.

{{include:shared/game_rules.md}}

## Your Mission
Use your Operator's clue to identify **Red Allied Subscribers** on the board. Avoid dangerous contacts at all costs.

## Current Board (Available Names)
```
{{BOARD}}
```

### Game History
{{CLUE_HISTORY}}

## Operator's Transmission
**Clue**: "{{CLUE}}"  
**Number**: {{NUMBER}}

## Rules & Strategy
{% if NUMBER == 0 %}
- **Zero Clue**: Your operator says NONE of your allied subscribers relate to "{{CLUE}}"
- You can guess as many names as you want, but you MUST guess at least one
- Use this to eliminate non-allied names and narrow down possibilities
{% elif NUMBER == "unlimited" %}
- **Unlimited Clue**: Your operator has multiple allied subscribers related to "{{CLUE}}"
- You can guess as many names as you want with no limit
- The exact number of related subscribers is unknown to you
{% else %}
- You can guess up to **{{NUMBER}} + 1** names maximum (the N+1 rule)
- You should find exactly **{{NUMBER}}** Red Allied Subscribers
{% endif %}
- **STOP immediately** if you're uncertain - wrong guesses help the enemy
- Think about what connects the names semantically based on the clue
- The Operator chose this clue for a reason - trust their intelligence

## Your Response
List your guesses, **one name per line**. You may guess fewer than the maximum allowed if you're unsure.

**Available names to choose from**:
{{BOARD}}

Only choose names that are still available (not already revealed). Be strategic - every wrong guess could cost the mission!
