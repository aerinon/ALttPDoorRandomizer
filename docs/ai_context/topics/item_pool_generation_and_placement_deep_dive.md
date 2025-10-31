# Item Pool Generation and Placement: Deep Dive

This document provides an in-depth exploration of the item pool generation and placement algorithms, including custom/planned placements and weighted/random algorithms. The logic is primarily implemented in [`Fill.py`](../../Fill.py) with additional custom placement functionality in [`Plando.py`](../../Plando.py).

---

## 1. Core Architecture

### Item Pool Structure
The item placement system operates on three main item categories:
- **Advancement Items** (`progitempool`): Items that unlock new areas or provide essential progression
- **Priority Items** (`prioitempool`): Important items like maps, compasses, and other useful but non-essential items
- **Rest Items** (`restitempool`): Filler items, rupees, and other low-priority items

### Key Data Structures
- **`world.itempool`**: Complete list of all items to be placed
- **`fill_locations`**: Available locations where items can be placed
- **`key_pool`**: Special tracking pool for small keys to prevent soft-locks
- **Item Pool Config**: Configuration system for item placement restrictions and preferences

---

## 2. Main Placement Algorithms

### Restrictive Fill Algorithm
The core placement algorithm is [`fill_restrictive()`](../../Fill.py) which ensures logical accessibility:

1. **State Simulation**: Creates a maximum exploration state by collecting all items hypothetically
2. **Accessibility Checking**: Verifies that each item placement maintains game completion possibility
3. **Key Logic Integration**: Special handling for keys to prevent dungeon soft-locks
4. **Fallback Mechanisms**: Recovery placement when standard placement fails

### Algorithm Variants
The system supports multiple placement algorithms via `world.algorithm`:

- **`vanilla_fill`**: Attempts to place items in their original locations first
- **`balanced`**: Distributes progression items evenly across spheres
- **`equitable`**: Ensures fair distribution in multiworld scenarios
- **`dungeon_only`**: Restricts progression items to dungeon locations
- **`major_only`**: Places major items in significant locations only
- **`district`**: Geographic-based placement restrictions

---

## 3. Sphere Construction and Validation

### Sphere-Based Placement
The algorithm builds accessibility spheres iteratively through state simulation that collects all items hypothetically and sweeps for events to determine reachability.

### Placement Verification
Each placement is verified through [`verify_spot_to_fill()`](../../Fill.py):
- **Location Compatibility**: Checks if the item can physically be placed at the location
- **Accessibility**: Ensures the location remains reachable with the current item set
- **Key Logic**: Validates that key placements don't create soft-locks
- **Dungeon Restrictions**: Enforces dungeon-specific item placement rules

---

## 4. Key Logic and Anti-Soft-Lock Systems

### Key Placement Validation
The [`valid_key_placement()`](../../Fill.py) function prevents soft-locks:

- **Self-Locking Prevention**: Ensures keys aren't placed behind doors they unlock
- **Dungeon Matching**: Validates keys are placed in appropriate dungeons when required
- **Logic Mode Handling**: Different validation for different logic modes (hybrid glitches, etc.)
- **Reserve Location Checking**: Respects reserved locations that cannot have certain items

### Small Key Tracking
Small keys require special handling through the `key_pool` system:
- Tracks unplaced keys to prevent logic violations
- Monitors "outside keys" placed in different dungeons
- Validates key accessibility during placement simulation

---

## 5. Custom and Planned Placements

### Plando System
[`Plando.py`](../../Plando.py) provides a system for completely custom item placements through the [`fill_world()`](../../Plando.py) function which parses text files with `Location: Item` syntax and uses [`world.push_item()`](../../BaseClasses.py) to place items directly.

### Custom Placement Features
- **Direct Item-Location Assignment**: `Location: Item` syntax
- **Entrance Connections**: `Entrance <=> Exit` for two-way connections  
- **World State Modification**: Settings like medallion requirements, game modes
- **Text Patches**: Custom in-game text modifications

### Item Pool Configuration
The `world.item_pool_config` system provides:
- **Restricted Items**: Items that require special placement consideration
- **Preferred Placements**: Items that should be placed in specific location groups first
- **Reserved Locations**: Locations that cannot receive certain item types
- **Verification System**: Testing framework for validating placement logic

---

## 6. Weighted and Random Algorithms

### Fast Fill Methods
For non-critical items, the system uses optimized placement:

- **[`fast_fill()`](../../Fill.py)**: Simple random placement for unrestricted items
- **[`fast_vanilla_fill()`](../../Fill.py)**: Attempts vanilla locations first, then falls back
- **[`fast_equitable_fill()`](../../Fill.py)**: Ensures dungeon items stay in dungeons

### Location Filtering
The [`filter_locations()`](../../source/item/FillUtil.py) system provides weighted placement:
- **Item Type Matching**: Certain items can only go in specific location types
- **Player Matching**: Multiworld item-player compatibility
- **Dungeon Restrictions**: Items that must/cannot be in dungeons
- **Special Location Handling**: Shops, pots, enemy drops get special treatment

### Randomization Strategies
The system uses deterministic shuffling of locations with [`random.shuffle()`](../../RaceRandom.py) and priority-based sorting that prioritizes map and compass items during placement.

---

## 7. Recovery and Fallback Mechanisms

### Recovery Placement
When standard placement fails, [`recovery_placement()`](../../Fill.py) attempts:

1. **Algorithm-Specific Recovery**: Different strategies based on `world.algorithm`
2. **Location Group Fallbacks**: Uses predefined location group hierarchies
3. **Item Swapping**: [`try_possible_swaps()`](../../Fill.py) swaps placed items to make room

### Last Ditch Placement
The [`last_ditch_placement()`](../../Fill.py) function handles extreme cases:
- **Item Priority Assessment**: Ranks items by importance for swapping
- **Crystal Handling**: Special logic for crystal swaps
- **Non-Essential Item Displacement**: Moves less important items to accommodate critical ones

---

## 8. Multiworld Considerations

### Progression Balancing  
[`balance_multiworld_progression()`](../../Fill.py) ensures fair multiworld play:

- **Sphere Tracking**: Monitors accessibility progression for each player
- **Threshold Calculation**: Ensures no player falls too far behind in accessibility
- **Item Redistribution**: Moves progression items between worlds to maintain balance
- **Candidate Item Selection**: Identifies items that can be safely moved

### Cross-World Item Placement
- **Player Matching**: Items can be placed in other players' worlds
- **Accessibility Validation**: Ensures moved items maintain logical access
- **Event Collection**: Properly handles cross-world item collection events

---

## 9. Specialized Fill Algorithms

### Dungeon Item Handling
The [`fill_dungeons_restrictive()`](../../Fill.py) function manages dungeon-specific items:

- **Item Classification**: Separates big keys, small keys, and other dungeon items
- **Restricted Placement**: Uses separate state simulation for dungeon items
- **Shuffle Mode Integration**: Handles different key shuffle modes (none, nearby, universal)

### Pot and Drop Handling
Special algorithms handle pottery and enemy drop locations:
- **[`fast_fill_pot_for_multiworld()`](../../Fill.py)**: Manages pot item distribution across players
- **Valid Item Filtering**: Ensures only appropriate items go in pots/drops
- **Multiworld Limitations**: Respects technical limits on cross-world pot items

---

## 10. Money and Economy Balancing

### Money Progression Balance
[`balance_money_progression()`](../../Fill.py) ensures players can afford required purchases:

- **Wallet Tracking**: Monitors each player's available rupees
- **Sphere Cost Calculation**: Determines how much money is needed each sphere
- **Rupee Redistribution**: Swaps rupee values to ensure solvency
- **Shop Integration**: Accounts for shop prices and required purchases

### Economy Validation
- **Required Purchase Tracking**: Monitors locations that require payment
- **Income Calculation**: Tracks rupee rooms and item-based income
- **Balancing Thresholds**: Uses configurable multipliers for difficulty scaling

---

## 11. Integration Points

### With Key Logic Systems
- **Dungeon Layout Integration**: Respects dungeon generation constraints
- **Key Door Validation**: Ensures key placements work with door shuffle
- **Logic Mode Adaptation**: Adjusts validation for different logic modes

### With Entrance Shuffling
- **Accessibility Updates**: Item placement must account for shuffled entrances
- **Cross-Dungeon Validation**: Handles cases where dungeons are connected differently
- **World State Synchronization**: Maintains consistency between entrance and item logic

---

## 12. Performance Optimizations

### Algorithmic Efficiency
- **State Caching**: Reuses exploration states when possible
- **Early Termination**: Stops validation when game completion is confirmed
- **Lazy Evaluation**: Defers expensive checks until necessary

### Memory Management
- **Pool Management**: Efficiently manages large item and location lists
- **State Copying**: Minimizes expensive world state copies
- **Location Filtering**: Pre-filters locations to reduce search space

---

## 13. Configuration and Customization

### Item Pool Modification
Custom item pool configuration is managed through the `world.item_pool_config` system which supports restricted items, preferred placements, and reserved locations through dictionary-based configuration.

### Algorithm Selection
The system allows runtime algorithm selection:
- **Mode-Based Selection**: Automatic algorithm selection based on world settings
- **Performance Tuning**: Different algorithms optimized for different scenarios
- **Fallback Strategies**: Graceful degradation when preferred algorithms fail

---

## 14. Error Handling and Diagnostics

### Placement Failure Handling
- **Detailed Error Reporting**: Specific information about why placements fail
- **Recovery Attempts**: Multiple fallback strategies before giving up
- **Seed Validation**: Confirms completability before finalizing placement

### Debug and Verification Systems
- **Placement Logging**: Detailed logs of item placement decisions
- **Logic Testing**: Automated verification of placement logic
- **Performance Monitoring**: Tracking of algorithm performance metrics

---

## 15. References

- [`Fill.py`](../../Fill.py): Main item placement algorithms
- [`Plando.py`](../../Plando.py): Custom placement system (deprecated but referenced)
- [`source/item/FillUtil.py`](../../source/item/FillUtil.py): Item filtering utilities
- [`ItemList.py`](../../ItemList.py): Item definitions and classifications
- [`logic_and_rule_setup.md`](logic_and_rule_setup.md): Integration with game logic
- [`finalization_and_validation.md`](finalization_and_validation.md): Post-placement validation
