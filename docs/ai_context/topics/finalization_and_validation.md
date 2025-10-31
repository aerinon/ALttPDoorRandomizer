# Finalization and Validation

This document describes the finalization and validation steps in the randomizer, focusing on beatable checks, sanity checks, and item placement validation. It is structured for LLMs and developers to quickly understand the main concepts and code structure.

---

## Overview

Finalization and validation ensure that the generated game is beatable, all logic constraints are satisfied, and no softlocks or unreachable locations exist.

---

## Key Concepts

- **Beatable Check:**  
  - Verifies that the game can be completed with the current item and location setup.
  - Uses logic simulation to ensure all required progression is possible.

- **Sanity Checks:**  
  - Additional checks for edge cases, unreachable locations, or invalid item placements.
  - May include checks for excessive or missing items, duplicate placements, etc.

- **Item Placement Validation:**  
  - Ensures that all placed items are accessible and do not violate logic constraints.
  - Validates that progression items are not locked behind themselves.

---

## Main Steps

1. **Run Beatable Check:**  
   - Simulate game progression to verify completion is possible.
   - Reference: [`beatable_check()`](../../Fill.py)

2. **Perform Sanity Checks:**  
   - Check for unreachable locations, duplicate items, and other edge cases.
   - Reference: sanity check logic in [`Fill.py`](../../Fill.py)

3. **Validate Item Placement:**  
   - Ensure all progression items are accessible and logic is not violated.
   - Reference: [`validate_item_placement()`](../../Fill.py)

---

## Relevant Files and Functions

- [`Fill.py`](../../Fill.py)
- [`Algorithm.md`](../../Algorithm.md) (for validation overview)

---

## Best Practices for Documentation

- Reference all relevant modules and functions.
- Summarize the logic and purpose of each step.
- Note any extensibility points or custom logic.
- Keep explanations concise and LLM-friendly.
