# Module and Data Structure Creation

This topic details how the randomizer creates and initializes the core modules and data structures for regions, dungeons, shops, doors, and rooms.

## Overview

- Each player/world instance requires a complete set of regions, dungeons, shops, doors, and rooms.
- These structures are created in a specific order to ensure dependencies are satisfied.
- Specialized modules handle the creation and configuration of each type.

## Key Steps

1. **Region Creation**
   - Regions are created for each player using [`create_regions`](../../Regions.py).
   - Regions represent distinct areas in the game world and are the foundation for entrances, exits, and locations.

2. **Dungeon Creation**
   - Dungeons are initialized with [`create_dungeons`](../../Dungeons.py).
   - Each dungeon contains its own regions, bosses, and item locations.

3. **Shop Creation**
   - Shops are created and assigned to regions with [`create_shops`](../../Regions.py).
   - Shop inventories and logic are configured per player.

4. **Door Creation**
   - Doors and entrances are created with [`create_doors`](../../Doors.py).
   - Handles both standard and shuffled door configurations.

5. **Room Creation**
   - Rooms are initialized with [`create_rooms`](../../RoomData.py).
   - Rooms are linked to regions and may contain special logic or item locations.

6. **Data Table Initialization**
   - Data tables for damage, enemy logic, and other mechanics are initialized per player.
   - See [`init_data_tables`](../../source/rom/DataTables.py).

## Relevant Code

- [`main()` in Main.py](../../Main.py:220)
- [`create_regions`](../../Regions.py)
- [`create_dungeons`](../../Dungeons.py)
- [`create_shops`](../../Regions.py)
- [`create_doors`](../../Doors.py)
- [`create_rooms`](../../RoomData.py)
- [`init_data_tables`](../../source/rom/DataTables.py)

## Notes

- The order of creation is important: regions → dungeons → shops → doors → rooms.
- These structures are referenced throughout the randomizer for logic, item placement, and patching.