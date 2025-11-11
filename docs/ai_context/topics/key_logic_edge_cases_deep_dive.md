# Key Logic Edge Cases and Algorithm Selection Deep Dive

This document provides a detailed analysis of key logic algorithm selection, edge cases, and how different algorithms handle complex scenarios. It addresses the critical distinction between algorithm types and their respective code paths.

---

## Glitch Safety and Real-World Implications

- **Partial and Strict algorithms are minor glitch safe**: Partial treats most minor glitches as equivalent to having a full inventory, and strict always requires all keys, so neither can be broken by minor glitches.
- **Dangerous algorithm is NOT minor glitch safe**: It does not account for minor glitches, so players can use glitches to spend keys out of order and break logic. It also has a known multiplayer bug that can create unwinnable seeds.
- **No algorithm is safe from Hybrid Major Glitches (HMG)**: In HMG, players can use keys from one dungeon in another, breaking all intended logic.
- **Practical guidance**: Use partial or strict for safety and competitive play. Dangerous is only for advanced analysis and is discouraged for most use cases. Experimental is under development and adapts logic based on dungeon complexity.

See the summary in [topics.md](topics.md#key-logic-algorithm-summary) for a plain-language overview.
---

## Algorithm Selection Overview

The key logic system uses different algorithms based on the `key_logic_algorithm` setting:

### Algorithm Types and Code Paths

**From [`DoorShuffle.py`](../../DoorShuffle.py:269-272):** The algorithm selection logic routes to [`analyze_dungeon()`](../../KeyDoorShuffle.py) for non-experimental algorithms or [`analyze_dungeon_new()`](../../source/dungeon/NewKeyLogic.py) for experimental algorithms.

**Critical Distinction:**
- **Partial Algorithm**: Uses [`KeyDoorShuffle.py`](../../KeyDoorShuffle.py) exclusively via `analyze_dungeon()`
- **Strict Algorithm**: Uses [`NewKeyLogic.py`](../../source/dungeon/NewKeyLogic.py) via `analyze_dungeon_new()`
- **Experimental Algorithm**: Also uses [`NewKeyLogic.py`](../../source/dungeon/NewKeyLogic.py)

### Triggering Conditions

**From algorithm selection logic:**
- **Partial**: `key_logic_algorithm != 'experimental'` AND typically `≤8 doors`
- **Strict**: `key_logic_algorithm == 'strict'` OR `>8 doors` (falls back to NewKeyLogic)
- **Experimental**: `key_logic_algorithm == 'experimental'`

---

## Partial Algorithm (KeyDoorShuffle)

### Core Implementation

**Primary Function**: [`exhaustive_key_logic_algorithm()`](../../KeyDoorShuffle.py) in KeyDoorShuffle.py

**Key Features:**
- Uses exhaustive placement rule generation
- Creates conditional logic based on big key placement
- Handles multiple path scenarios through rule intersection
- Confined entirely to KeyDoorShuffle.py code path

### Placement Rule System

The [`create_exhaustive_placement_rules()`](../../KeyDoorShuffle.py) function creates comprehensive rules that handle big key conditional logic by selecting appropriate location sets based on big key placement scenarios.

**Rule Contradictions**: [`PlacementRule.contradicts()`](../../KeyDoorShuffle.py) resolves conflicts between different placement scenarios.

### Edge Case Handling

**Multiple Path Scenarios:**
- Algorithm generates separate rules for each valid path
- May require more keys than optimal if paths aren't recognized as equivalent
- Prioritizes safety over optimization

---

## Strict Algorithm (NewKeyLogic)

### Core Implementation

**Primary Function**: [`determine_small_key_logic_fast()`](../../source/dungeon/NewKeyLogic.py)

**Key Features:**
- Uses sphere-based reachability analysis
- Progressive key count evaluation
- Intersection-based conservative decision making

### Reachability Analysis

The [`calculate_reachability()`](../../source/dungeon/NewKeyLogic.py) function:

1. **Sphere Construction**: Each key count creates accessibility "spheres"
2. **Conservative Aggregation**: Takes intersection of terminal spheres
3. **Self-Lock Detection**: [`detect_self_locks()`](../../source/dungeon/NewKeyLogic.py) prevents invalid placements

### Limitations

**Intersection Approach**: May be overly conservative when multiple valid paths exist, requiring more keys than theoretically necessary.

---

## Common Edge Cases by Algorithm

### 1. Big Key Conditional Logic

**Partial Algorithm (KeyDoorShuffle):**
- Uses placement rules with big key location conditionals
- Creates separate rule sets for different big key scenarios
- Handles contradictions through rule priority system

**Strict Algorithm (NewKeyLogic):**
- Evaluates accessibility with and without big key
- Uses sphere analysis to determine minimum requirements
- May be more conservative in complex scenarios

### 2. Multiple Path Access

**Example: GTBKC Access Scenario**
- Path A: Firesnake Room → GTBKC (4 keys needed)
- Path B: Tile Room → Star Pits Pot Key → GTBKC (4 keys needed)

**Partial Algorithm Response:**
- Creates separate placement rules for each path
- May require 5+ keys if paths aren't recognized as equivalent
- Depends on rule generation and contradiction resolution

**Strict Algorithm Response:**
- Uses reachability sphere intersection
- Conservative approach may also require additional keys
- Different reasoning but potentially similar result

### 3. Self-Locking Prevention

**Partial Algorithm:**
- [`invalid_self_locking_key()`](../../KeyDoorShuffle.py) prevents problematic placements
- Rule-based approach to identifying locks

**Strict Algorithm:**
- [`detect_self_locks()`](../../source/dungeon/NewKeyLogic.py) sphere-based detection
- Analyzes progression availability within spheres

---

## Debugging by Algorithm Type

### For Partial Algorithm Issues:
1. **Examine Placement Rules**: Check [`create_exhaustive_placement_rules()`](../../KeyDoorShuffle.py) output
2. **Rule Contradictions**: Analyze [`PlacementRule.contradicts()`](../../KeyDoorShuffle.py) resolution
3. **Key Counters**: Use [`create_key_counters()`](../../KeyDoorShuffle.py) data
4. **Validation**: Check [`val_ganons()`](../../KeyDoorShuffle.py) for GT-specific logic

### For Strict Algorithm Issues:
1. **Sphere Analysis**: Trace [`calculate_reachability()`](../../source/dungeon/NewKeyLogic.py) progression
2. **Self-Lock Detection**: Examine [`detect_self_locks()`](../../source/dungeon/NewKeyLogic.py) results
3. **Fast Logic**: Check [`determine_small_key_logic_fast()`](../../source/dungeon/NewKeyLogic.py) behavior

---

## Algorithm Selection Best Practices

### When to Expect Each Algorithm:
- **Partial**: Default for most dungeons with reasonable door counts
- **Strict**: Large dungeons (>8 doors) or explicit strict setting
- **Experimental**: Explicit experimental setting only

### Troubleshooting Algorithm Issues:
1. **Verify Algorithm in Use**: Check `key_logic_algorithm` setting and door count
2. **Match Code Path**: Ensure you're analyzing the correct algorithm's code
3. **Understand Triggering**: Know when the system switches between algorithms
4. **Test Edge Cases**: Use known problematic scenarios to verify behavior

---

## References

### Partial Algorithm (KeyDoorShuffle):
- [`analyze_dungeon()`](../../KeyDoorShuffle.py) - Main entry point
- [`create_exhaustive_placement_rules()`](../../KeyDoorShuffle.py) - Rule generation
- [`PlacementRule.contradicts()`](../../KeyDoorShuffle.py) - Conflict resolution
- [`invalid_self_locking_key()`](../../KeyDoorShuffle.py) - Self-lock prevention

### Strict Algorithm (NewKeyLogic):
- [`analyze_dungeon_new()`](../../source/dungeon/NewKeyLogic.py) - Main entry point
- [`calculate_reachability()`](../../source/dungeon/NewKeyLogic.py) - Sphere analysis
- [`detect_self_locks()`](../../source/dungeon/NewKeyLogic.py) - Self-lock detection
- [`determine_small_key_logic_fast()`](../../source/dungeon/NewKeyLogic.py) - Fast logic

### Algorithm Selection:
- [`DoorShuffle.py:269-272`](../../DoorShuffle.py:269-272) - Selection logic