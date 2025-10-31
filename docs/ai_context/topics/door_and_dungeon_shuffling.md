# Door and Dungeon Shuffling

This document provides an LLM-oriented overview of the algorithms and logic for door and dungeon shuffling in this project. It is designed to help AI agents and developers quickly understand the key concepts, data flows, and code structure.

---

## Overview

Door and dungeon shuffling randomizes the connections and requirements within dungeons, affecting how players progress and what keys/items are needed. The logic is implemented across several modules, with a focus on:

- Door selection and pairing
- Key door assignment and validation
- Key logic (small/big keys, prize locks)
- Reachability and softlock prevention

---

## Key Modules and Files

- [`KeyDoorShuffle.py`](KeyDoorShuffle.py)
- [`source/dungeon/NewKeyLogic.py`](source/dungeon/NewKeyLogic.py)
- [`source/dungeon/SmallKeyDoorShuffle.py`](source/dungeon/SmallKeyDoorShuffle.py)

---

## Main Concepts

### 1. Door Pool Construction

- Candidate doors are identified for shuffling using functions like `find_small_key_door_candidates()` and `find_key_door_candidates()`.
- Doors are filtered and paired as needed (see `build_pair_list()`).

### 2. Key Door Assignment

- The number of key doors per dungeon is determined based on configuration and logic constraints.
- Assignment is handled by algorithms such as `shuffle_small_key_doors()` and validated with `find_valid_combination()`.

### 3. Key Logic and Reachability

- The core logic for key requirements and reachability is encapsulated in the [`NewKeyLogic`](source/dungeon/NewKeyLogic.py) class.
- Key spheres are constructed to represent progressive access as keys are collected.
- Functions like `calculate_reachability()` and `can_reach()` determine which regions and locations are accessible given the current key state.
- **Complex Scenarios**: Multiple paths to the same location, redundant keys, and partial protection edge cases are handled conservatively.
- See [Key Logic Edge Cases Deep Dive](key_logic_edge_cases_deep_dive.md) for detailed analysis of complex scenarios.

### 4. Placement Rules and Validation

- Placement rules are generated to ensure that key and item placement does not result in softlocks.
- The system uses exhaustive and Monte Carlo algorithms to validate that all locations remain accessible.
- Contradictions in placement rules are detected and resolved.

### 5. Special Cases

- Handles big key doors, prize locks, and crystal switch logic.
- Special logic for self-locking doors and blue barrier islands is included.
- **Edge Case Handling**: Complex scenarios like GTBKC (Ganon's Tower Big Key Chest) with multiple access paths.
- **Partial Protection**: Conservative logic to prevent softlocks, may require more keys than theoretically optimal.

---

## Data Flow

1. **Door Candidates** are identified and filtered.
2. **Key Layouts** are proposed and validated for each dungeon.
3. **Key Spheres** are built to model access progression.
4. **Placement Rules** are generated and checked for contradictions.
5. **Final Assignments** are made, ensuring all locations are accessible.

---

## References

- [`shuffle_small_key_doors()`](source/dungeon/SmallKeyDoorShuffle.py)
- [`find_small_key_door_candidates()`](source/dungeon/SmallKeyDoorShuffle.py)
- [`NewKeyLogic`](source/dungeon/NewKeyLogic.py)
- [`calculate_reachability()`](source/dungeon/NewKeyLogic.py)
- [`KeyLayout`](KeyDoorShuffle.py)
- [`KeyLogic`](KeyDoorShuffle.py)
- [`PlacementRule`](KeyDoorShuffle.py)

---

## Common Issues and Debugging

### Key Logic Edge Cases

- **Multiple Path Scenarios**: When several routes lead to the same location, the algorithm may not optimize key requirements
- **Conservative Reachability**: System errs on the side of caution, potentially requiring excess keys
- **Self-Lock Detection**: May incorrectly identify or miss self-locking scenarios in complex layouts

### Debugging Steps

1. Examine key counters using [`create_key_counters()`](../../KeyDoorShuffle.py)
2. Trace sphere construction in [`determine_small_key_logic_exhaustive()`](../../source/dungeon/NewKeyLogic.py)
3. Analyze placement rules from [`create_exhaustive_placement_rules()`](../../KeyDoorShuffle.py)
4. For GT specifically, compare against [`val_ganons()`](../../KeyDoorShuffle.py) expectations

## Diagrams

Consider adding flowcharts for:
- Door candidate selection
- Key sphere progression
- Placement rule validation
- Edge case resolution paths

---

## Best Practices for Documentation

- Reference relevant classes and functions with file and line links.
- Summarize algorithms and their purpose.
- Note edge cases and special logic.
- Keep explanations concise and LLM-friendly.
