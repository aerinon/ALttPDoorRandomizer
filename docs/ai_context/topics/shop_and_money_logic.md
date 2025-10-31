# Shop and Money Logic

This document describes the comprehensive shop and money logic system in the randomizer, including shop creation, inventory management, pricing, and economic balancing. The implementation spans multiple modules and provides both vanilla and customizable shop experiences.

---

## Overview

The shop and money system manages the in-game economy through shop creation, inventory customization, dynamic pricing, and economic balancing to ensure fair progression and prevent money grinding.

---

## Core Architecture

### Shop Creation and Management

#### [`Regions.py`](../../Regions.py) - Shop Infrastructure
- **[`create_shops(world, player)`](../../Regions.py:1146)**: Main shop creation function
- **[`shop_table`](../../Regions.py:1282)**: Defines all shop configurations (room ID, type, shopkeeper, inventory)
- **[`shop_to_location_table`](../../Regions.py:1300)**: Maps shop regions to location names for shopsanity
- **[`Shop`](../../BaseClasses.py:2466)** class: Core shop data structure

#### Shop Types and Configuration
Shop configurations are defined in the [`shop_table`](../../Regions.py) dictionary, specifying room IDs, shop types, shopkeeper configurations, custom flags, lock status, default inventories, and SRAM addresses.

### Shopsanity Integration

#### [`ItemList.py`](../../ItemList.py) - Shop Customization
- **[`set_up_shops(world, player)`](../../ItemList.py:622)**: Configures shops for different modes
- **[`customize_shops(world, player)`](../../ItemList.py:676)**: Full shop customization for shopsanity
- **[`create_dynamic_shop_locations(world, player)`](../../ItemList.py:572)**: Creates location objects for shop items

#### Shopsanity Logic Flow
1. **Shop Setup**: Configure basic shop inventories and special cases (retro bow, universal keys)
2. **Customization**: Replace vanilla items with randomized pool items
3. **Location Creation**: Generate location objects for each shop slot
4. **Price Balancing**: Adjust prices based on economy targets

### Economic Balancing System

#### [`Fill.py`](../../Fill.py) - Money Balance Logic
- **[`balance_money_progression(world)`](../../Fill.py:908)**: Main economic balancing function
- **[`balance_prices(world, player)`](../../ItemList.py:789)**: Adjusts shop prices to match economy targets
- **[`lock_shop_locations(world, player)`](../../Fill.py:684)**: Handles non-shopsanity shop locking

#### Economic Calculation
The system calculates base money availability from rupee rooms and required purchase costs, then applies dynamic balancing using the [`world.money_balance`](../../BaseClasses.py) modifier to determine pricing targets.

### Special Shop Logic

#### Take Any Caves
- **[`fill_specific_items(world, player)`](../../ItemList.py:491)**: Creates take-any cave logic
- Supports both regular shop mode and take-any mode based on settings
- Special handling for old man sword cave and capacity upgrades

#### Universal Key and Retro Bow Integration
- **Retro Bow Mode**: Adds Single Arrow to multiple shops
- **Universal Keys**: Places universal keys in select shop locations
- **Bomb Bag Mode**: Modifies capacity upgrade availability

## Key Functions and Data Flow

### Shop Initialization Flow
1. **[`create_shops(world, player)`](../../Regions.py:1146)**: Creates shop objects from shop_table
2. **[`set_up_shops(world, player)`](../../ItemList.py:622)**: Applies mode-specific configurations
3. **[`create_dynamic_shop_locations(world, player)`](../../ItemList.py:572)**: Creates location objects if shopsanity

### Shopsanity Customization Flow
1. **[`customize_shops(world, player)`](../../ItemList.py:676)**: Main customization entry point
2. **[`change_shop_items_to_rupees(world, player, shops)`](../../ItemList.py:775)**: Converts overflow items to rupees
3. **[`balance_prices(world, player)`](../../ItemList.py:789)**: Economic balancing

### Economic Balancing Flow
1. **[`balance_money_progression(world)`](../../Fill.py:908)**: Analyzes sphere-by-sphere costs
2. **Price Adjustment**: Modifies shop prices to prevent money grinding
3. **Item Swapping**: Swaps items between locations to improve economic balance

## ROM Integration

### [`Rom.py`](../../Rom.py) - Shop Writing
- **[`write_custom_shops(rom, world, player)`](../../Rom.py:1466)**: Writes shop data to ROM
- **Shop Data Structure**: Handles shop bytes, item data, pricing, and SRAM addresses
- **Shopsanity Flags**: Sets appropriate flags for shop item collection tracking

## Data Structures

### Shop Class Structure
The [`Shop`](../../BaseClasses.py) class manages shop data including region, room ID, shop type, shopkeeper configuration, inventory slots (up to 3 items), custom flag, and lock status.

### Inventory Item Format
Each inventory slot contains item name, price, maximum quantity (0 for unlimited), optional replacement item and price, and player assignment for multiworld support.

## Configuration and Settings

### Money Balance Setting
- **[`world.money_balance[player]`](../../BaseClasses.py:160)**: Percentage modifier (default 100%)
- Controls economic strictness vs generosity
- Affects sphere-by-sphere cost calculations

### Shopsanity Mode
- **[`world.shopsanity[player]`](../../BaseClasses.py:162)**: Boolean flag
- Enables shop location creation and item randomization
- Integrates with location filtering and accessibility logic

## Integration Points

### Rule System Integration
- **[`Rules.py`](../../Rules.py)**: Shop accessibility rules and bomb shop logic
- **[`source/logic/Rule.py`](../../source/logic/Rule.py)**: Unlimited item purchase rules
- **[`BaseClasses.py`](../../BaseClasses.py)**: Shop item purchase logic in CollectionState

### Multiworld Support
- **[`MultiClient.py`](../../MultiClient.py)**: Shop item collection tracking
- **Cross-player items**: Supports items from different players in shops
- **SRAM tracking**: Manages shop purchase state across players

## Testing and Validation

### [`TestSuite.py`](../../TestSuite.py) Integration
- Tests shopsanity mode across different configurations
- Validates economic balance under various settings
- Ensures shop accessibility and item placement

## Design Considerations

### Performance
- Shop data cached during creation phase
- Economic calculations optimized for sphere-based analysis
- ROM writing batched for efficiency

### Flexibility
- Modular shop configuration via shop_table
- Support for custom shop inventories via customizer
- Dynamic pricing based on economic analysis

### Maintainability
- Clear separation between shop creation, customization, and economic balancing
- Centralized shop data definitions
- Consistent data structures across modules

## Related Topics
- [Item Pool Generation and Placement](item_pool_generation_and_placement.md) - Integration with item placement
- [Logic and Rule Setup](logic_and_rule_setup.md) - Shop accessibility rules
- [ROM Patching and Output](rom_patching_and_output.md) - Shop data writing
- [Main Algorithm Flow](main_algorithm_flow.md) - Integration with generation pipeline
