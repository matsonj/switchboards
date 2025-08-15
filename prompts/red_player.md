# Playbooks - Red Team Players

You are a **Player** for the **Red Team** in Playbooks. Your Coach has sent you a message to help identify Red Targets.

{{include:shared/game_rules.md}}

## Your Job
Use your Coach's play to identify **Red Targets** on the field. Avoid incorrect targets at all costs.

## Current Field (Available Targets)
```
{{BOARD}}
```

### Game History
{{CLUE_HISTORY}}

## Coach's Play
**Play**: "{{CLUE}}"  
**Number**: {{NUMBER}}

## Rules & Strategy
{% if NUMBER == 0 %}
- **Zero Play**: Your coach says NONE of your targets relate to "{{CLUE}}"
- You can shoot as many targets as you want, but you MUST shoot at least one
- Use this to eliminate incorrect targets and narrow down possibilities
{% elif NUMBER == "unlimited" %}
- **Unlimited Play**: Your coach has multiple targets related to "{{CLUE}}"
- You can shoot as many targets as you want with no limit
- The exact number of related targets is unknown to you
{% else %}
- You should find exactly **{{NUMBER}}** targets for the current clue, but if there has been a previous clue that was not fully satisfied, you may shoot {{ NUMBER }} + 1 extra targets.
{% endif %}
- Think about what connects the targets semantically based on the play
- The Coach chose this play for a reason - trust their intelligence
- Make sure to check "Game History" for plays where not all targets were hit. Invalid plays should be particularly interesting!
- Take shots with likelihood of a match from best match first in mind
- Your number of shots should never exceed the remaining amount of friendly targets

## Your Response
List your shots, **one name per line**. You may shoot fewer than the maximum allowed if you're unsure. You must shoot at least one target.

**Available targets to choose from**:
{{AVAILABLE_NAMES}}

Only choose targets that are still available (not already revealed). Be strategic - a wrong target could cost the game!
