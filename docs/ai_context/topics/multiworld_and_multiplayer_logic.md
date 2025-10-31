# Multiworld and Multiplayer Logic

This document describes the multiworld and multiplayer logic in the randomizer, focusing on team/slot handling and multidata output. It is structured for LLMs and developers to quickly understand the main concepts and code structure.

---

## Overview

Multiworld and multiplayer logic enables multiple players to participate in a shared or interconnected game world, with items and progression distributed across different players' games.

The main randomizer algorithm generates multidata output files that encode all player data for multiworld sessions. Real-time networking and synchronization during gameplay are handled separately by the MultiServer and MultiClient modules, which communicate between players while the game is being played.

---

## Key Concepts

- **Team/Slot Handling:**  
  - Supports multiple teams and player slots.
  - Manages item sharing and progression between players in the generated game data.
  - Real-time communication and synchronization during play are handled by the server/client modules, not by the randomizer itself.

- **Multidata Output:**  
  - Generates output files that encode all player data for multiworld sessions.
  - Ensures compatibility and correct mapping across all participants.

---

## Main Steps

1. **Initialize Multiworld State:**  
   - Set up teams, slots, and player-specific data.
   - Reference: multiworld setup logic in [`MultiServer.py`](../../MultiServer.py) and [`MultiClient.py`](../../MultiClient.py)

2. **Distribute Items and Progression:**  
   - Assign items and progression logic across all players.
   - Reference: item distribution logic in [`Fill.py`](../../Fill.py)

3. **Generate Multidata Output:**  
   - Create output files for all players, ensuring correct mapping for multiworld sessions.
   - Reference: multidata output logic in [`MultiServer.py`](../../MultiServer.py)

---

## Relevant Files and Functions

- [`MultiServer.py`](../../MultiServer.py)
- [`MultiClient.py`](../../MultiClient.py)
- [`Fill.py`](../../Fill.py)

---

## Best Practices for Documentation

- Reference all relevant modules and functions.
- Summarize the logic and purpose of each step.
- Note any extensibility points or custom logic.
- Keep explanations concise and LLM-friendly.
