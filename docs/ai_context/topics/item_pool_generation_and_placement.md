# Item Pool Generation and Placement

This document explains the logic and algorithms for item pool generation and placement in the randomizer. It is structured for LLMs and developers to quickly understand the process, key functions, and relevant files.

---

## Overview

Item pool generation determines which items are available in the game, while placement algorithms decide where those items are distributed. The system ensures that all required items are accessible and that the game remains beatable.

---

## Key Concepts

- **Item Pool Logic:**  
  - Defines the set of items to be distributed (progression, junk, dungeon items, etc.).
  - Handles custom item pools and presets.

- **Verification:**  
  - Ensures the item pool contains all required items and meets configuration constraints.
  - Validates that item counts match the number of available locations.

- **Placement Algorithms:**  
  - Assigns items to locations using logic-based, random, or weighted algorithms.
  - Prevents softlocks and ensures progression is possible.

---

## Main Steps

1. **Generate Item Pool:**  
   - Build the initial item pool based on game mode, settings, and presets.
   - Reference: [`generate_item_pool()`](../../ItemList.py)

2. **Verify Item Pool:**  
   - Check for required items, duplicates, and pool size.
   - Reference: [`verify_item_pool()`](../../ItemList.py)

3. **Place Items:**  
   - Assign items to locations using placement logic.
   - Reference: [`place_items()`](../../Fill.py)

4. **Validate Placement:**  
   - Ensure all progression items are accessible and the game is beatable.
   - Reference: [`validate_item_placement()`](../../Fill.py)

---

## Relevant Files and Functions

- [`ItemList.py`](../../ItemList.py)
- [`Fill.py`](../../Fill.py)
- [`Plando.py`](../../Plando.py) (for custom/planned placements)
- [`Algorithm.md`](../../Algorithm.md) (for algorithmic overview)

---

## Best Practices for Documentation

- Reference all relevant modules and functions.
- Summarize the logic and purpose of each step.
- Note any edge cases, custom logic, or extensibility points.
- Keep explanations concise and LLM-friendly.
