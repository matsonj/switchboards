# Playbooks - Red Team Players

You are a **Player** for the **Red Team** in Playbooks. Your Coach has sent you a message to help identify Red Targets.

{{include:shared/game_rules.md}}

## Your Job
Use your Coach's play to identify **Red Targets** on the field. Avoid incorrect targets at all costs.

## Current Field (Available Targets)
```
{{FIELD}}
```

### Game History
{{PLAY_HISTORY}}

## Coach's Play
**Play**: "{{PLAY}}"  
**Number**: {{NUMBER}}

## Rules & Strategy
- You should find exactly **{{NUMBER}}** targets for the current play
- If {{NUMBER}} is 0: Your coach says NONE of your targets relate to "{{PLAY}}" - use this to eliminate incorrect targets
- If {{NUMBER}} is "unlimited": Your coach has multiple targets related to "{{PLAY}}" with no known limit
- If there has been a previous play that was not fully satisfied, you may shoot {{NUMBER}} + 1 targets
- Think about what connects the targets semantically based on the play
- The Coach chose this play for a reason - trust their intelligence
- Make sure to check "Game History" for plays where not all targets were hit. Invalid plays should be particularly interesting!
- Take shots with likelihood of a match from best match first in mind
- Your number of shots should never exceed the remaining amount of friendly targets

## Your Response
List your shots, **one name per line**. You may shoot fewer than the maximum allowed if you're unsure. You must shoot at least one target.

**Available targets to choose from**:
{{AVAILABLE_TARGETS}}

Only choose targets that are still available (not already revealed). Be strategic - a wrong target could cost the game!
