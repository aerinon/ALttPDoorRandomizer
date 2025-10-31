# Key Logic Architecture Deep Dive

## Overview

This document provides detailed architectural documentation for the key logic systems, covering class hierarchies, function interactions, and data flow across the three main key logic modules: [`NewKeyLogic.py`](../../source/dungeon/NewKeyLogic.py), [`KeyDoorShuffle.py`](../../KeyDoorShuffle.py), and [`SmallKeyDoorShuffle.py`](../../source/dungeon/SmallKeyDoorShuffle.py).

## NewKeyLogic.py - Modern Key Logic System

### Core Classes

#### [`NewKeyLogic`](../../source/dungeon/NewKeyLogic.py) Class
The main orchestration class for the modern key logic algorithm.

**Key Methods:**
- [`__init__()`](../../source/dungeon/NewKeyLogic.py): Initializes region and location caches
- [`get_relevant_regions_and_locations()`](../../source/dungeon/NewKeyLogic.py): Builds accessibility mappings
- [`build_cache_key()`](../../source/dungeon/NewKeyLogic.py): Creates state fingerprints for caching
- [`can_reach()`](../../source/dungeon/NewKeyLogic.py): Tests entrance accessibility
- [`can_reach_location()`](../../source/dungeon/NewKeyLogic.py): Tests location accessibility
- [`calculate_reachability()`](../../source/dungeon/NewKeyLogic.py): Core sphere-based reachability analysis

**Crystal Switch Detection:**
- [`detect_crystal_switch_bypass()`](../../source/dungeon/NewKeyLogic.py): Identifies crystal switch bypass scenarios
- [`_analyze_crystal_reachability()`](../../source/dungeon/NewKeyLogic.py): Analyzes crystal switch accessibility
- [`_find_crystal_switches_in_regions()`](../../source/dungeon/NewKeyLogic.py): Locates crystal switches
- [`_find_blue_barrier_islands()`](../../source/dungeon/NewKeyLogic.py): Identifies isolated blue barrier regions

#### [`BlueIsland`](../../source/dungeon/NewKeyLogic.py) Class
Represents isolated regions accessible only through blue barriers.

**Structure:**
- [`__init__(regions, blue_barriers, open_list)`](../../source/dungeon/NewKeyLogic.py): Initializes island data
- `regions`: Set of regions in the island
- `blue_barriers`: Barriers that can access the island
- `open_list`: Available entrances

#### [`KeySphere`](../../source/dungeon/NewKeyLogic.py) Class
Represents accessibility spheres for progressive key analysis.

**Methods:**
- [`__init__(code)`](../../source/dungeon/NewKeyLogic.py): Creates sphere with accessibility code
- [`get_accessible_locations(key_logic)`](../../source/dungeon/NewKeyLogic.py): Returns accessible locations

### Core Analysis Functions

#### [`analyze_dungeon(key_layout, world, player)`](../../source/dungeon/NewKeyLogic.py)
Main entry point for NewKeyLogic analysis.

**Process Flow:**
1. Creates NewKeyLogic instance
2. Calls appropriate logic determination function
3. Handles big key and small key logic separately

#### [`determine_big_key_logic(key_layout, world, player)`](../../source/dungeon/NewKeyLogic.py)
Determines big key accessibility requirements.

**Algorithm:**
- Uses progressive key count analysis
- Identifies minimum keys needed for big key access
- Handles conditional big key placement scenarios

#### [`determine_small_key_logic_fast(key_layout, start_state, world, player)`](../../source/dungeon/NewKeyLogic.py)
Fast small key logic determination for simple cases.

#### [`determine_small_key_logic_exhaustive(key_layout, world, player)`](../../source/dungeon/NewKeyLogic.py)
Comprehensive small key analysis for complex scenarios.

**Process:**
1. Progressive key count evaluation
2. Sphere-based reachability calculation
3. Self-lock detection and prevention
4. Conservative decision making through intersection

### Helper Functions

#### [`detect_self_locks(sphere, parent_sphere, key_layout)`](../../source/dungeon/NewKeyLogic.py)
Identifies and prevents self-locking key placements.

#### [`sphere_id(bk_flag, open_door_set, flat_proposal, use_prize, prize_flag)`](../../source/dungeon/NewKeyLogic.py)
Generates unique identifiers for accessibility spheres.

## KeyDoorShuffle.py - Comprehensive Key Door Logic

### Core Classes

#### [`KeyLayout`](../../KeyDoorShuffle.py) Class
Represents the overall key and door layout for a dungeon.

**Properties:**
- [`__init__(name, sector, starts, proposal)`](../../KeyDoorShuffle.py): Initializes layout structure
- [`reset(proposal, builder, world, player)`](../../KeyDoorShuffle.py): Resets layout for new proposal
- `name`: Dungeon name
- `sector`: Dungeon sector data
- `starts`: Starting regions
- `proposal`: Door placement proposal

#### [`KeyLogic`](../../KeyDoorShuffle.py) Class
Manages key logic rules and validation.

**Methods:**
- [`__init__(dungeon_name)`](../../KeyDoorShuffle.py): Initializes for specific dungeon
- [`check_placement(unplaced_keys, wild_keys, reached_keys, self_locking_keys, ...)`](../../KeyDoorShuffle.py): Validates key placements
- [`reset()`](../../KeyDoorShuffle.py): Resets logic state

#### [`PlacementRule`](../../KeyDoorShuffle.py) Class
Represents conditional logic rules for key placement.

**Key Methods:**
- [`__init__()`](../../KeyDoorShuffle.py): Initializes rule structure
- [`contradicts(rule, unplaced_keys, big_key_loc)`](../../KeyDoorShuffle.py): Checks rule conflicts
- [`is_satisfiable(outside_keys_locations, wild_keys, reached_keys, ...)`](../../KeyDoorShuffle.py): Validates rule satisfaction

#### [`KeyCounter`](../../KeyDoorShuffle.py) Class
Tracks key availability and usage in different states.

**Properties:**
- [`__init__(max_chests)`](../../KeyDoorShuffle.py): Initializes counter with chest limits
- `max_chests`: Maximum available chest locations
- Tracks small keys, big keys, and door states

### Key Analysis Functions

#### [`analyze_dungeon(key_layout, world, player)`](../../KeyDoorShuffle.py)
Main analysis function for KeyDoorShuffle algorithm.

**Process:**
1. Creates exhaustive placement rules
2. Refines rules based on constraints
3. Validates key layout feasibility
4. Handles special dungeon logic (GT, etc.)

#### [`create_exhaustive_placement_rules(key_layout, world, player)`](../../KeyDoorShuffle.py)
Generates comprehensive placement rules for all scenarios.

**Algorithm:**
- Analyzes all possible key count scenarios
- Creates conditional rules based on big key placement
- Handles multiple path access patterns
- Generates placement restrictions

#### [`validate_key_layout(key_layout, world, player)`](../../KeyDoorShuffle.py)
Validates that generated key layout is completable.

**Validation Process:**
1. State space exploration
2. Key availability checking
3. Self-lock detection
4. Progress validation

### Door and Key Management

#### [`find_valid_combination(builder, target, start_regions, world, player, drop_keys)`](../../source/dungeon/SmallKeyDoorShuffle.py)
Finds valid combinations of key doors for small key shuffling.

#### [`shuffle_small_key_doors(door_type_pools, used_doors, start_regions_map, all_custom, world, player)`](../../source/dungeon/SmallKeyDoorShuffle.py)
Main entry point for small key door shuffling.

**Process:**
1. Analyzes door type pools
2. Finds valid key door candidates
3. Applies placement algorithms
4. Validates resulting layout

### Specialized Logic Functions

#### Dungeon-Specific Validation
- [`val_hyrule(key_logic, world, player)`](../../KeyDoorShuffle.py): Hyrule Castle logic
- [`val_eastern(key_logic, world, player)`](../../KeyDoorShuffle.py): Eastern Palace logic
- [`val_desert(key_logic, world, player)`](../../KeyDoorShuffle.py): Desert Palace logic
- [`val_ganons(key_logic, world, player)`](../../KeyDoorShuffle.py): Ganon's Tower logic

#### Key Counter Management
- [`create_key_counters(key_layout, world, player)`](../../KeyDoorShuffle.py): Creates counter hierarchy
- [`find_counter(opened_doors, bk_hint, key_layout, prize_flag, raise_on_error)`](../../KeyDoorShuffle.py): Locates specific counters
- [`create_key_counter(state, key_layout, world, player)`](../../KeyDoorShuffle.py): Creates state-specific counters

## SmallKeyDoorShuffle.py - Small Key Door Specialized Logic

### Main Algorithm Functions

#### [`monte_carlo_algorithm(builder, key_door_pool, key_doors_needed, start_regions, event_starts, custom, world, player)`](../../source/dungeon/SmallKeyDoorShuffle.py)
Uses Monte Carlo method for key door placement optimization.

#### [`exhaustive_key_logic_algorithm(builder, key_door_pool, key_doors_needed, start_regions, event_starts, custom, world, player)`](../../source/dungeon/SmallKeyDoorShuffle.py)
Exhaustive search algorithm for small key door placement.

### Door Management Functions

#### [`find_small_key_door_candidates(builder, start_regions, used, world, player)`](../../source/dungeon/SmallKeyDoorShuffle.py)
Identifies potential small key door locations.

#### [`reassign_key_doors(small_map, used_doors, world, player)`](../../source/dungeon/SmallKeyDoorShuffle.py)
Reassigns doors based on new key requirements.

#### [`add_pair(door_a, door_b, world, player)`](../../source/dungeon/SmallKeyDoorShuffle.py)
Links door pairs for coordinated access.

### Validation and Constraint Functions

#### [`validate_key_proposal_large(proposal, init_state, all_smalls, builder, start_regions, world, player)`](../../source/dungeon/SmallKeyDoorShuffle.py)
Validates large key proposals for feasibility.

#### [`find_contradiction_in_rules(rules, num_to_choose)`](../../source/dungeon/SmallKeyDoorShuffle.py)
Identifies contradictory placement rules.

## Data Flow and Integration

### Cross-Module Interaction

#### Algorithm Selection Flow
1. [`DoorShuffle.py`](../../DoorShuffle.py) determines algorithm type
2. Routes to appropriate module based on `key_logic_algorithm` setting
3. Calls main analysis function with shared data structures

#### Data Structure Sharing
- `KeyLayout` objects passed between modules
- `World` and `Player` objects provide context
- Shared utility functions for state management

#### Error Handling
- Consistent exception handling across modules
- Fallback algorithms for failed placements
- Validation at multiple stages

### Performance Considerations

#### Caching Strategies
- [`NewKeyLogic`](../../source/dungeon/NewKeyLogic.py) uses state caching for performance
- [`KeyDoorShuffle`](../../KeyDoorShuffle.py) caches placement rules
- Progressive refinement reduces computation

#### Algorithm Complexity
- **NewKeyLogic**: O(k²) where k is key count, optimized for small dungeons
- **KeyDoorShuffle**: Exponential worst case, practical for most scenarios
- **SmallKeyDoorShuffle**: Monte Carlo provides bounded execution time

## Debugging and Maintenance

### Key Debugging Points
- State validation at sphere boundaries
- Rule contradiction resolution
- Self-lock detection triggers
- Performance bottlenecks in large dungeons

### Common Issues
- Algorithm selection mismatches
- State cache invalidation
- Rule satisfaction edge cases
- Big key conditional logic errors

### Testing Integration
- Works with [`TestSuite.py`](../../TestSuite.py) for validation
- Supports deterministic testing via [`RaceRandom.py`](../../RaceRandom.py)
- Provides detailed error reporting for failures

## Related Topics
- [Key Logic Edge Cases Deep Dive](key_logic_edge_cases_deep_dive.md) - Specific algorithm behaviors
- [Door and Dungeon Shuffling](door_and_dungeon_shuffling.md) - Integration with door systems
- [Testing Framework and Validation](testing_framework_and_validation.md) - Validation strategies
- [Utility Modules and Data Tables](utility_modules_and_data_tables.md) - Supporting infrastructure