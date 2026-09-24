# Dungeon Generation Algorithms and Variations

This section provides a detailed overview of the dungeon generation algorithms, their variations, and the main code paths involved. The logic is distributed across several modules in [`source/dungeon/`](../../source/dungeon/), including:

- [`DungeonStitcher.py`](../../source/dungeon/DungeonStitcher.py)
- [`DungeonStitcherV2.py`](../../source/dungeon/DungeonStitcherV2.py)
- [`DungeonGenLocalSearch.py`](../../source/dungeon/DungeonGenLocalSearch.py)
- [`DungeonGen3.py`](../../source/dungeon/DungeonGen3.py)
- [`DungeonGenSectorDesc.py`](../../source/dungeon/DungeonGenSectorDesc.py)
- [`DungeonGenTransitivity.py`](../../source/dungeon/DungeonGenTransitivity.py)
- [`DungeonGenerationCommon.py`](../../source/dungeon/DungeonGenerationCommon.py)

---

## Overview

Dungeon generation is responsible for constructing the internal structure of each dungeon, including room connectivity, sector assignment, door placement, and logic constraints. The process supports multiple algorithms and modes, allowing for extensive randomization and replayability.

---

## Main Algorithms

### 1. Stitching and Proposal

- The core entry point is typically `generate_dungeon()` in [`DungeonStitcher.py`](../../source/dungeon/DungeonStitcher.py) or `create_dungeon()` in [`DungeonStitcherV2.py`](../../source/dungeon/DungeonStitcherV2.py).
- These functions attempt to build a valid dungeon layout by proposing and validating room/door arrangements.
- If a valid proposal is not found, the algorithm iterates or backtracks to try alternative configurations.

### 2. Local Search and Sector Assignment

- [`DungeonGenLocalSearch.py`](../../source/dungeon/DungeonGenLocalSearch.py) implements local search strategies for sector and portal assignment.
- Functions like `main_dungeon_builders()` and `create_dungeon_builders_prototype()` generate candidate layouts and log generation attempts.
- Sectors are described and assigned using [`DungeonGenSectorDesc.py`](../../source/dungeon/DungeonGenSectorDesc.py).

### 3. Reachability / Stitchability Feasibility Check ("Transitivity")

- [`DungeonGenTransitivity.py`](../../source/dungeon/DungeonGenTransitivity.py) answers a yes/no feasibility question: for a given set of sectors, does *any* pairing of their loose door ends exist that connects everything, keeps every part of the dungeon reachable, and satisfies every per-sector constraint (one-way "must enter" doors, crystal-barrier color requirements, dead-end pairing rules, portal placement)?
- It is not the generator itself — [`DungeonGenLocalSearch.py`](../../source/dungeon/DungeonGenLocalSearch.py) calls it to reject sector groupings that can't actually be stitched together, and [`DungeonStitcherV2.py`](../../source/dungeon/DungeonStitcherV2.py) calls it to validate each portal placement as it commits to a proposal.
- "Transitivity" is the module's legacy name, describing the transitive-reachability data it works over (`sector.descriptor.reachability`, computed in [`DungeonGenSectorDesc.py`](../../source/dungeon/DungeonGenSectorDesc.py)) rather than its purpose — see the [full algorithm write-up](door_and_dungeon_shuffling_deep_dive.md#reachability--stitchability-feasibility-check--transitivity-dungeongentransitivitypy) for the constraint types, search strategy, and pruning heuristics.

### 4. Algorithm Variations

- Multiple generation strategies are supported, including:
  - Stitching-based generation
  - Local search with sector descriptors
  - Reachability/stitchability feasibility checking ("Transitivity")
- The system can switch between algorithms based on configuration or randomization mode.

---

## Key Concepts

- **Builder Objects:** Maintain the current state of the dungeon during generation.
- **Proposals:** Candidate dungeon layouts that are validated before acceptance.
- **Sectors and Portals:** Logical groupings of rooms and connections.
- **Constraint Propagation:** Ensures that all rules (e.g., required keys, boss placement) are satisfied.

---

## References

- [`DungeonStitcher.py`](../../source/dungeon/DungeonStitcher.py)
- [`DungeonStitcherV2.py`](../../source/dungeon/DungeonStitcherV2.py)
- [`DungeonGenLocalSearch.py`](../../source/dungeon/DungeonGenLocalSearch.py)
- [`DungeonGen3.py`](../../source/dungeon/DungeonGen3.py)
- [`DungeonGenSectorDesc.py`](../../source/dungeon/DungeonGenSectorDesc.py)
- [`DungeonGenTransitivity.py`](../../source/dungeon/DungeonGenTransitivity.py)
- [`DungeonGenerationCommon.py`](../../source/dungeon/DungeonGenerationCommon.py)
