# Playbook - Core Game Rules

## Game Overview
Playbook is a strategic deduction game where two teams (Red and Blue) compete to identify all their targets while avoiding enemy, fake, and illegal targts. There is a list of 25 targets (single words), 8 allocated to Red, 8 allocated to Blue, 1 allocated to the team that goes first (Red or Blue), 7 which are fake (neutral), and 1 illegal (instant loss).

## Turn Structure
1. **Coach Phase**: Current team's Coach provides a play and number (see "Play Validation Rules")
2. **Referee Phase**: Referee validates the play for rule compliance
3. **Player Phase**: Current team's Player takes shots (See "Shot Outcomes")
4. **Resolution**: Process shoots and determine turn outcome
5. **Team Switch**: If turn ends, Check Win Conditions and if false, switch to other team

## Shot Outcomes
- **Friendly Target**: ✓ Correct! Continue shooting (up to limit)
- **Enemy Target**: ✗ Help enemy team, end turn immediately  
- **Fake Target**: ○ Waste a shot, end turn immediately
- **Illegal Targets**: 💀 Instant game loss for shooting team

## Win Conditions
- **Victory**: Find all your Targets first
- **Defeat**: Hit the Illegal Target (instant loss)
- **Defeat**: Enemy team finds all their Targets first

## Roles & Responsibilities

### Coach
- Has complete intelligence about all Targets on the board
- Provides Plays to guide their Players
- Must follow strict play rules (see "Play Validation Rules")

### Players  
- Only sees the list of Targets
- Receives Play from their Coach
- Takes shots based on the play
- Can shoot up to **NUMBER + 1** names per turn (N+1 rule), with limited exceptions (See "Rules for Experts")

### Referee
- Validates that Coach plays comply with "Play Validation Rules"
- Can reject invalid plays

## Play Validation Rules

### Valid Plays Must:
1. **ALWAYS a single word, with some limited exceptions** (no sentences or explanations)
2. **NEVER be a name currently on the field** (exact match forbidden)
3. **NEVER be a direct variant of a word on the field** (plural, past tense, etc.)
4. **NEVER reference the number of letters** in target words
5. **NEVER reference positions** on the board (row, column, location)

### Single Word Exceptions
1. English has three ways to write compound words. "Greenhouse" is one word. "Pack rat" is two words. "Mother-in-law" is hyphentated. Technically, only "Greenhouse" is a one-word play. Compound words are allowed when describing specific ideas.
2. Proper Names are ALWAYS valid plays if they follow the other rules. Proper Names, such as "George Washington" or "The Three Musketeers" are valid words, as is "New York" or "The Big Apple".
3. Acronymns and Abbreviations are allowed when they are commonly referred to as a single word. Examples include CIA, UK, PhD and technical words like SQL, Radar, or Sonar.

### Penalty for Invalid Play
If an operator gives an invalid play, the team's turn ends immediately. As an additional penalty, the Referee removes a target for the opposing team before the next turn begins.

## Rules for Experts
- **Expert Play: Zero**: You are allowed to use 0 as the number part of your play. For example, "Feathers (0)" means "None of our targets related to 'Feathers'". If 0 is the number, the usual limit on guess does not apply. Players can shoot as many targets as they want. They still must shoot at least one target.
- **Expert Play: Unlimited**: Sometimes you may have multiple unguessed targets related to your plays from previous turns. If you want your team to shoot more than one of them, you may say unlimited instead of a number. This disadvantage is that the players do not know how many targets are related to the new play. The advantage is that they may guess as many targets as they want.