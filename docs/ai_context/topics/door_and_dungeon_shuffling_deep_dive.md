# Door and Dungeon Shuffling - Deep Dive

This document provides an algorithmic deep-dive into the door and dungeon shuffling systems of the dungeon randomizer, covering sphere construction, self-locking logic, placement rule contradictions, and the sophisticated algorithms used for door placement and dungeon layout generation.

## Core Components

### Key Door Shuffling System ([`SmallKeyDoorShuffle.py`](../../../source/dungeon/SmallKeyDoorShuffle.py))

The small key door shuffling system is responsible for placing key doors throughout dungeons while maintaining logical solvability.

#### Main Algorithm Flow

The [`shuffle_small_key_doors()`](../../../source/dungeon/SmallKeyDoorShuffle.py) function orchestrates the key door placement process in two phases:

**Phase 1**: Calculate key door distribution across dungeons by calling [`find_small_key_door_candidates()`](../../../source/dungeon/SmallKeyDoorShuffle.py) and determining the number of key doors needed per dungeon.

**Phase 2**: Find valid key door combinations using either exhaustive or Monte Carlo algorithms via [`find_valid_combination()`](../../../source/dungeon/SmallKeyDoorShuffle.py).

### Key Logic Analysis System ([`NewKeyLogic.py`](../../../source/dungeon/NewKeyLogic.py))

The new key logic system analyzes dungeon layouts to create sphere-based progression models.

#### Sphere Construction Algorithm

**Key Sphere Class**: The [`KeySphere`](../../../source/dungeon/NewKeyLogic.py) class represents accessibility spheres with regions, locations, key counters, and child sphere relationships. Critical for self-locking detection through the `self_locking_child_spheres` attribute.

**Sphere Building Process**: The [`determine_small_key_logic_exhaustive()`](../../../source/dungeon/NewKeyLogic.py) function creates sphere hierarchies based on key progression using a breadth-first queue approach. Self-locking scenarios are detected via [`detect_self_locks()`](../../../source/dungeon/NewKeyLogic.py) during sphere construction.

#### Self-Locking Detection Algorithm

**Core Self-Locking Logic**: The [`detect_self_locks()`](../../../source/dungeon/NewKeyLogic.py) function identifies spheres with exactly one new location and one new door difference, marking them as self-locking scenarios. These spheres are added to the parent's `self_locking_child_spheres` list.

**Self-Lock Adjustment in Placement Rules**: Placement rules are adjusted through logic that reduces key requirements for self-locking scenarios when only non-important locations are blocked, allowing controlled self-locking placement.

### Dungeon Generation System ([`DungeonStitcher.py`](../../../source/dungeon/DungeonStitcher.py))

The dungeon stitcher connects door networks to create cohesive dungeon layouts.

#### Door Connection Algorithm

**Main Generation Flow**: The [`generate_dungeon_find_proposal()`](../../../source/dungeon/DungeonStitcher.py) function creates random door connection proposals and iteratively validates and refines them using exploration and validation functions until a valid layout is found.

**Hook-Based Door Matching**: The [`create_random_proposal()`](../../../source/dungeon/DungeonStitcher.py) function groups doors by directional hooks (North, South, East, West, Stairs) and creates connections between matching opposite hooks to ensure proper door alignment.

### Transitivity and Constraint System ([`DungeonGenTransitivity.py`](../../../source/dungeon/DungeonGenTransitivity.py))

The transitivity system ensures dungeon layouts satisfy complex constraints through sophisticated graph analysis.

#### Constraint Types and Validation

**Constraint Categories**: The [`ConstraintType`](../../../source/dungeon/DungeonGenTransitivity.py) enum defines six constraint categories including MustEnter, Special, Crystal, DeadEnd, Neutral, and Portal constraints for comprehensive layout validation.

**Transitivity Check Algorithm**: The [`do_transitivity_check_main()`](../../../source/dungeon/DungeonGenTransitivity.py) function uses a priority queue-based constraint satisfaction approach to find valid door connections while respecting all defined constraints.

#### Impossibility Detection

**Advanced Contradiction Detection**: The [`now_impossible()`](../../../source/dungeon/DungeonGenTransitivity.py) method performs comprehensive impossibility checks including fundamental constraint violations, door matching validation, and constraint-specific analysis for MustEnter and Crystal switch requirements.

## Key Algorithms

### 1. Exhaustive Key Logic Algorithm

For dungeons with ≤8 key doors, the [`exhaustive_key_logic_algorithm()`](../../../source/dungeon/SmallKeyDoorShuffle.py) function uses complete enumeration analysis. It generates combinations using [`kth_combination()`](../../../source/dungeon/SmallKeyDoorShuffle.py), builds key layouts, creates placement rules via [`create_exhaustive_placement_rules()`](../../KeyDoorShuffle.py), and checks for contradictions using [`find_contradiction_in_rules()`](../../../source/dungeon/SmallKeyDoorShuffle.py).

### 2. Monte Carlo Algorithm

For larger key door counts, the [`monte_carlo_algorithm()`](../../../source/dungeon/SmallKeyDoorShuffle.py) function uses statistical sampling with pre-filtering. It eliminates candidates based on reachability analysis, samples from surviving candidates, and validates proposals using [`validate_key_proposal_large()`](../../../source/dungeon/SmallKeyDoorShuffle.py).

### 3. Placement Rule Contradiction Detection

The [`find_contradiction_in_rules()`](../../../source/dungeon/SmallKeyDoorShuffle.py) function detects logical contradictions in key placement by building a constraint satisfaction problem and using backtracking search with pruning to find valid assignments. Returns `True` if contradictions are found.

## Reachability and Progression Analysis

### Cache-Based Reachability System

The [`can_reach()`](../../../source/dungeon/NewKeyLogic.py) method uses sophisticated caching for reachability calculations. It builds cache keys via [`build_cache_key()`](../../../source/dungeon/NewKeyLogic.py) and calculates reachability through [`calculate_reachability()`](../../../source/dungeon/NewKeyLogic.py) when cache misses occur.

### Sphere-Based Progression Analysis

The [`calculate_reachability()`](../../../source/dungeon/NewKeyLogic.py) method performs breadth-first search through the sphere hierarchy, handling key acquisition and spending logic. It processes root spheres based on big key state and advances through child spheres while managing self-locking placement scenarios through `self_locking_child_spheres`.

## Advanced Features

### Crystal Switch Bypass Detection

The [`detect_crystal_switch_bypass()`](../../../source/dungeon/NewKeyLogic.py) method analyzes crystal switch mechanics for advanced routing by finding crystal switches in reachable regions and identifying blue barrier islands accessible via crystal switches using helper methods like [`_find_crystal_switches_in_regions()`](../../../source/dungeon/NewKeyLogic.py) and [`_find_blue_barrier_islands()`](../../../source/dungeon/NewKeyLogic.py).

### Forced Loop Detection

The [`detect_forced_loop()`](../../../source/dungeon/DungeonGenTransitivity.py) method detects forced routing loops by checking if all door matches are in the same sector or neutral sectors, preventing impossible connection scenarios.

## Performance Characteristics

### Computational Complexity

- **Exhaustive Algorithm**: O(C(n,k) * V) where n=candidates, k=doors needed, V=validation cost
- **Monte Carlo Algorithm**: O(S * V) where S=sample size, V=validation cost  
- **Transitivity Check**: O(2^D * C) where D=doors, C=constraints
- **Self-Lock Detection**: O(S^2) where S=spheres

### Optimization Strategies

1. **Early Pruning**: Eliminate impossible configurations before full validation
2. **Constraint Ordering**: Process most restrictive constraints first
3. **Caching**: Extensive reachability and state caching
4. **Sampling**: Statistical sampling for large search spaces
5. **Incremental Validation**: Validate changes incrementally rather than full re-validation

### Memory Management

- Sphere hierarchies use shared region/location references
- Connection maps use efficient door indexing
- Cache keys use frozen sets for immutable hashing
- Constraint graphs use sparse representations

## Integration Points

### With Item Placement System
- Key door placement must coordinate with item pool generation
- Self-locking spheres affect item accessibility calculations
- Big key placement interacts with door unlock requirements

### With Logic System  
- Door connections create new logical dependencies
- Sphere construction feeds into accessibility rules
- Crystal switch analysis affects barrier traversal logic

### With Validation System
- Door layouts must pass beatable checks
- Key placement validates against soft-lock prevention
- Sphere analysis contributes to completion verification

This sophisticated door and dungeon shuffling system ensures that randomized layouts maintain logical solvability while maximizing variety and challenge through advanced algorithmic techniques including sphere construction, self-locking detection, constraint satisfaction, and statistical sampling methods.
