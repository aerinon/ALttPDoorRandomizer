# Entrance Linking: Deep Dive

This document provides an in-depth exploration of the entrance linking logic and algorithms implemented in [`EntranceShuffle2.py`](../../source/overworld/EntranceShuffle2.py). This is a complex system that handles the randomization of overworld entrances while maintaining logical accessibility and game balance.

---

## 1. Core Architecture

### EntrancePool Class
The [`EntrancePool`](../../source/overworld/EntranceShuffle2.py:11) class is the central data structure that manages:
- Available entrances and exits
- Coupling modes (coupled vs decoupled)
- Inverted mode handling
- Default mappings and one-way connections
- Restrictions and constraints

### Key Components
- **Entrances**: Entry points into areas (caves, dungeons, etc.)
- **Exits**: Exit points from areas back to the overworld
- **Coupled Mode**: Entrances and exits are linked bidirectionally
- **Decoupled Mode**: Entrances and exits can be shuffled independently
- **Swapped Mode**: Special shuffle that swaps entrance-exit pairs

---

## 2. Main Algorithm Flow

### Entry Point: `link_entrances_new()`
The main function [`link_entrances_new()`](../../source/overworld/EntranceShuffle2.py:45) orchestrates the entire process:

1. **Pool Setup**: Creates entrance pool with available entrances/exits
2. **Inverted Substitution**: Handles inverted mode entrance/exit mapping
3. **Mandatory Connections**: Establishes required non-shuffleable connections
4. **Custom Connections**: Applies user-defined entrance connections
5. **Mode-Specific Shuffling**: Applies the selected shuffle algorithm
6. **Post-Processing**: Handles special cases and patches

### Shuffle Modes
The system supports multiple shuffle modes defined in the [`modes`](../../source/overworld/EntranceShuffle2.py:1512) dictionary:
- `vanilla`: No shuffling
- `dungeonssimple`: Basic dungeon entrance shuffling
- `dungeonsfull`: Full dungeon entrance shuffling with same-world restrictions
- `lite`: Limited shuffling with world restrictions
- `lean`: Cross-world shuffling with some restrictions
- `simple`: Basic shuffling with connector handling
- `restricted`: Highly constrained shuffling
- `full`: Comprehensive shuffling
- `swapped`: Entrance-exit pair swapping
- `crossed`: Cross-world shuffling
- `insanity`: Fully decoupled random shuffling

---

## 3. Advanced Algorithms

### Mandatory Exit Logic
The [`do_mandatory_connections()`](../../source/overworld/EntranceShuffle2.py:1085) function ensures that certain entrances maintain accessibility:

- **Must-Exit Entrances**: Certain locations must be accessible from specific worlds
- **Cave Validation**: Multi-exit caves are validated for proper connectivity
- **Invalid Connection Tracking**: Prevents circular dependencies and soft-locks
- **Constraint Propagation**: Ensures all placement rules are satisfied

### Same-World vs Cross-World Logic
Two major branching paths handle different connectivity requirements:

#### Same-World Restrictions ([`figure_out_must_exits_same_world()`](../../source/overworld/EntranceShuffle2.py:703))
- Separates Light World and Dark World entrances
- Ensures mandatory exits remain in their required world
- Handles world-specific connector caves

#### Cross-World Freedom ([`figure_out_must_exits_cross_world()`](../../source/overworld/EntranceShuffle2.py:747))
- Allows entrances to connect across worlds
- More flexibility but requires careful validation
- Special handling for mandatory connections

### Drop and Hole Linking
The [`do_holes_and_linked_drops()`](../../source/overworld/EntranceShuffle2.py:424) function handles special entrance types:

- **Linked Drops**: Holes that are connected to specific entrances
- **Keep Together Mode**: Maintains logical pairings
- **Cross-World Considerations**: Handles world restrictions for drops
- **Special Cases**: Sanctuary Grave, Skull Woods holes, etc.

---

## 4. Connector and Cave Logic

### Multi-Exit Caves
The system handles caves with multiple entrances/exits:

- **Connector Detection**: [`figure_out_connectors()`](../../source/overworld/EntranceShuffle2.py:644) identifies multi-exit locations
- **Exit Shuffling**: [`shuffle_connector_exits()`](../../source/overworld/EntranceShuffle2.py:1275) randomizes exit order while maintaining logic
- **Constraint Validation**: Ensures all exits remain accessible

### Special Location Handling
Certain locations require special logic:

- **Links House**: Complex placement rules based on mode and accessibility
- **Old Man Cave**: Special handling for both entrances with different requirements  
- **Blacksmith**: Restricted placement options
- **Bomb Shop**: Mode-dependent placement with forbidden locations

---

## 5. Swapped Mode Algorithm

The swapped mode ([`connect_swapped()`](../../source/overworld/EntranceShuffle2.py:1353)) implements a unique shuffling strategy:

1. **Pair Identification**: Identifies entrance-exit pairs
2. **Swap Logic**: [`connect_swap()`](../../source/overworld/EntranceShuffle2.py:1381) swaps the destinations of paired locations
3. **Constraint Handling**: Ensures swaps don't create impossible situations
4. **Forbidden Swaps**: Certain entrances cannot be swapped due to logic requirements

---

## 6. Validation and Error Handling

### Soft-Lock Prevention
Multiple layers prevent unbeatable seeds:
- **Accessibility Checks**: Ensures all required locations remain reachable
- **Dependency Validation**: Prevents circular item requirements
- **World Connectivity**: Maintains ability to travel between worlds when required

### Constraint Satisfaction
The system tracks and enforces various constraints:
- **Dungeon Restrictions**: Some dungeon exits must remain in specific worlds
- **Mandatory Connections**: Certain entrance-exit pairs cannot be broken
- **Invalid Connection Matrix**: Prevents problematic entrance-exit combinations

---

## 7. Key Data Structures

### Entrance and Exit Maps
- [`entrance_map`](../../source/overworld/EntranceShuffle2.py:1967): Bidirectional entrance-exit pairs
- [`single_entrance_map`](../../source/overworld/EntranceShuffle2.py:2040): One-way connections
- [`drop_map`](../../source/overworld/EntranceShuffle2.py:1935): Hole-to-location mappings
- [`linked_drop_map`](../../source/overworld/EntranceShuffle2.py:1952): Hole-entrance linkages

### World Classification
- [`LW_Entrances`](../../source/overworld/EntranceShuffle2.py:2113): Light World entrance list
- [`DW_Entrances`](../../source/overworld/EntranceShuffle2.py:2133): Dark World entrance list
- [`LW_Must_Exit`](../../source/overworld/EntranceShuffle2.py:2147): Required Light World exits
- [`DW_Must_Exit`](../../source/overworld/EntranceShuffle2.py:2149): Required Dark World exits

### Connection Validation
- [`Must_Exit_Invalid_Connections`](../../source/overworld/EntranceShuffle2.py:2241): Forbidden entrance-exit combinations
- [`Connector_List`](../../source/overworld/EntranceShuffle2.py:2196): Multi-exit cave definitions

---

## 8. Performance Considerations

The entrance linking system is computationally intensive due to:

- **Constraint Satisfaction**: Multiple overlapping constraints must be satisfied
- **Backtracking**: Failed placements require trying alternative configurations  
- **Validation Overhead**: Extensive checks to prevent soft-locks
- **Mode Complexity**: Different shuffle modes have vastly different requirements

---

## 9. Integration Points

### With Door Shuffling
Entrance linking interacts with door shuffling systems:
- **Dungeon Entry Points**: Entrance shuffling affects which dungeons are accessible
- **Key Logic**: Changes to dungeon access can affect key placement logic
- **Cross-Dungeon Travel**: Some modes allow travel between different dungeons

### With Item Logic
- **Accessibility Updates**: Item placement must account for shuffled entrances
- **Progression Requirements**: Shuffled entrances can change item progression logic
- **Beatable Validation**: Final seed validation must account for all entrance changes

---

## 10. References

- [`EntranceShuffle2.py`](../../source/overworld/EntranceShuffle2.py): Main implementation
- [`EntranceData.py`](../../source/overworld/EntranceData.py): Door addresses and data
- [`door_and_dungeon_shuffling.md`](door_and_dungeon_shuffling.md): Related door shuffling logic
- [`logic_and_rule_setup.md`](logic_and_rule_setup.md): Integration with game logic
