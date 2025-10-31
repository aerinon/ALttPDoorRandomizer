# Logic and Rule Setup

This document describes the logic and rule setup process in the randomizer, focusing on access rules, district pools, and tracking. It is structured for LLMs and developers to quickly understand the main concepts, code structure, and extensibility points.

---

## Overview

Logic and rule setup ensures that the game world is traversable and that item and location access is governed by well-defined rules. This includes:

- Defining access requirements for regions and locations
- Managing district pools (groupings of locations/regions)
- Tracking player progress and rule satisfaction

---

## Key Concepts

- **Access Rules:**  
  - Functions and data structures that determine if a player can access a region or location.
  - May depend on items, keys, dungeon state, or game settings.

- **District Pools:**  
  - Logical groupings of regions or locations for rule evaluation.
  - Used for advanced logic modes and custom setups.

- **Tracking:**  
  - Monitors which rules are satisfied as the player progresses.
  - Supports logic debugging and validation.

---

## Main Steps

1. **Define Access Rules:**  
   - Implement functions to check if a region/location is accessible.
   - Reference: [`Rule.py`](../../source/logic/Rule.py)

2. **Setup District Pools:**  
   - Group regions/locations for logic evaluation.
   - Reference: [`District.py`](../../source/item/District.py)

3. **Track Rule Satisfaction:**  
   - Monitor which rules are met as the game progresses.
   - Reference: tracking logic in [`Fill.py`](../../Fill.py) and related modules.

---

## Relevant Files and Functions

- [`Rule.py`](../../source/logic/Rule.py)
- [`District.py`](../../source/item/District.py)
- [`Fill.py`](../../Fill.py)

---

## Best Practices for Documentation

- Reference all relevant modules and functions.
- Summarize the logic and purpose of each step.
- Note any extensibility points or custom logic.
- Keep explanations concise and LLM-friendly.
