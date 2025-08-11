# The Switchboard - Core Game Rules

## Game Overview
The Switchboard is a strategic deduction game where two teams (Red and Blue) compete to identify all their Friendly Subscribers while avoiding dangerous contacts. There is a list of 25 subscribers (single words), 8 allocated to Red, 8 allocated to Blue, 1 allocated to the team that goes first (Red or Blue), 7 which are non-subscribers (neutral), and 1 mole (instant loss if contacted.)

## Turn Structure
1. **Operator Phase**: Current team's Operator provides a clue and number (see "Clue Validation Rules")
2. **Umpire Phase**: Umpire validates the clue for rule compliance
3. **Lineman Phase**: Current team's Lineman makes guesses (See "Guess Outcomes")
4. **Resolution**: Process guesses and determine turn outcome
5. **Team Switch**: If turn ends, Check Win Conditions and if false, switch to other team

## Guess Outcomes
- **Friendly Subscriber**: ✓ Correct! Continue guessing (up to limit)
- **Enemy Subscriber**: ✗ Help enemy team, end turn immediately  
- **Non-Subscriber**: ○ Waste a guess, end turn immediately
- **The Mole**: 💀 Instant game loss for guessing team

## Win Conditions
- **Victory**: Find all your Subscribers first
- **Defeat**: Contact The Mole (instant loss)
- **Defeat**: Enemy team finds all their Subscribers first

## Roles & Responsibilities

### Operator
- Has complete intelligence about all identities on the board
- Provides clues to guide their Linemen
- Must follow strict clue rules (see "Clue Validation Rules")

### Lineman  
- Only sees the list of Subscribers
- Receives clues from their Operator
- Makes guesses based on the clue
- Can guess up to **NUMBER + 1** names per turn (N+1 rule), with limited exceptions (See "Rules for Experts")

### Umpire
- Validates that Operator clues comply with "Clue Validation Rules"
- Can reject invalid clues

## Clue Validation Rules

### Valid Clues Must:
1. **ALWAYS a single word, with some limited exceptions** (no sentences or explanations)
2. **NEVER be a name currently on the board** (exact match forbidden)
3. **NEVER be a direct variant of a word on the board** (plural, past tense, etc.)
4. **NEVER reference the number of letters** in target words
5. **NEVER reference positions** on the board (row, column, location)

### Single word Exceptions
1. English has three ways to write compound words. "Greenhouse" is one word. "Pack rat" is two words. "Mother-in-law" is hyphentated. Technically, only "Greenhouse" is a one-word clue. Compound words are allowed when describing specific ideas.
2. Proper Names are ALWAYS valid clues if they follow the other rules. Proper Names, such as "George Washington" or "The Three Musketeers" are valid words, as is "New York" or "The Big Apple".
3. Acronymns and Abbreviations are allowed when they are commonly referred to as a single word. Examples include CIA, UK, PhD and technical words like SQL, Radar, or Sonar.

### Penalty for Invalid Clues
If an operator gives an invalid clue, the team's turn ends immediately. As an additional penalty, the Umpire removes a word for the opposing team before the next turn begins.

## Rules for Experts
- **Expert Clue: Zero**: You are allowed to use 0 as the number part of your clue. For example, "Feathers (0)" means "None of our words related to 'Feathers'". If 0 is the number, the usual limit on guess does not apply. Operatos can guess as many words as they want. They still must guess at least one word.
- **Expert Clue: Unlimited**: Sometimes you may have multiple unguessed words related to your clues from previous rounds. If you want your team to guess more than one of them, you may say unlimited instead of a number. This disadvantage is that the Linemen do not know how many words are related to the new clue. The advantage is that they may guess as many words as they want.