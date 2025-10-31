# Utility Modules and Data Tables

## Overview

This topic covers the utility modules that provide essential data structures and helper functions for the Door Randomizer, including data table lookups and randomization utilities.

## Tables.py - Data Table Lookups

### Purpose
[`Tables.py`](../../Tables.py) contains lookup tables and offset mappings used throughout the randomizer for door placement, room identification, and memory address calculations.

### Key Data Structures

#### Door Offset Tables
- **`normal_offset_table`**: Maps room IDs to normalized offsets for standard door placement
- **`spiral_offset_table`**: Maps room IDs to offsets for spiral staircase configurations  
- **`door_pair_offset_table`**: Maps room IDs to door pair offset values for linked door systems

#### Mathematical Lookup Tables
- **`multiply_lookup`**: Provides multiplication factors for door calculations based on room dimensions
- **`divisor_lookup`**: Contains divisor values for door position calculations

### Usage Patterns
These tables are primarily used by:
- Door shuffling algorithms to determine valid door placements
- Room generation logic to calculate proper door positioning
- Memory patching routines to write correct offset values to ROM

### Data Format
All tables use hexadecimal room IDs as keys, with calculated offset values as results. The offset calculations follow specific mathematical formulas based on the original game's memory layout.

## RaceRandom.py - Randomization Utilities

### Purpose
[`RaceRandom.py`](../../RaceRandom.py) provides a wrapper around Python's random module that allows switching between deterministic (PRNG) and cryptographically secure (CPRNG) random number generation.

### Core Architecture

#### Random Number Generation Modes
The module maintains two random number generator instances: a deterministic PRNG for seedable generation and a cryptographically secure CPRNG for secure randomization when needed.

#### Mode Switching
- **`use_secure(secure=True)`**: Switches between PRNG and CPRNG modes
- Default mode is PRNG for reproducible seed-based generation
- CPRNG mode used for cryptographically secure randomization when needed

### Function Wrapping
The module dynamically wraps all random module functions to automatically use the appropriate random instance:
- [`choice()`](../../RaceRandom.py) - Random selection from sequence
- [`randint()`](../../RaceRandom.py) - Random integer generation
- [`shuffle()`](../../RaceRandom.py) - In-place sequence shuffling
- [`seed()`](../../RaceRandom.py) - Seed initialization for reproducible results
- And all other standard random module functions

### Usage in Door Randomizer
- **Seed-based generation**: Used for reproducible randomizer runs
- **Deterministic testing**: Ensures consistent results for regression testing
- **Race conditions**: Provides secure randomization when needed for competitive play

### Integration Points
- [`DungeonRandomizer.py`](../../DungeonRandomizer.py) imports as `RaceRandom as random`
- [`Bosses.py`](../../Bosses.py) uses for boss placement randomization
- All shuffling algorithms depend on this module for consistent randomization

## Design Considerations

### Performance
- Table lookups provide O(1) access to precalculated values
- Function wrapping adds minimal overhead while providing flexibility

### Maintainability  
- Centralized data tables make offset calculations easier to modify
- Random wrapper allows easy switching between random modes without code changes

### Testing
- Deterministic PRNG mode ensures reproducible test results
- Lookup tables can be validated against known good values

## Dependencies

### Tables.py
- No external dependencies
- Pure data structure definitions

### RaceRandom.py
- Python standard library `random` module
- `functools.update_wrapper` for proper function wrapping

## Related Topics
- [Main Algorithm Flow](main_algorithm_flow.md) - Uses both modules extensively
- [Door and Dungeon Shuffling](door_and_dungeon_shuffling.md) - Relies on table lookups
- [Logic and Rule Setup](logic_and_rule_setup.md) - Uses randomization utilities