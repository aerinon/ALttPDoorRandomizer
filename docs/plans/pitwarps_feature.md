# Pitwarps Feature — Implementation Plan

## Overview

**Pitwarps** shuffles the one-way internal pit-fall and warp-tile connections within (and
eventually between) dungeon sectors. Currently `falldown_pits` and `dungeon_warps` in
`DoorShuffle.py` are hardcoded fixed source→destination lists. This feature makes them
randomizable, adds a new intensity level, and integrates with lobby shuffle and the
`dungeon_entrances` redistribution pipeline.

---

## Current State

- Phases 1 and 2 are implemented (intensity 4 shuffles pits and warps in logic and in dungeon generation).
  Phase 5 (ROM write) is not started, so an intensity-4 ROM still sends every pit to its vanilla room.
- `data/terminals.yaml` defines 27 pit Terminals (33 sources) and 26 warp Terminals (26 sources).
- Verification and the Transitivity design history are in `docs/plans/transitivity_pitwarp_verification.md`.

---

## Prerequisite: Data Collection

Before writing any ROM output code, run the collector scripts to document:
- Vanilla source room + tile coordinates for every pit/warp
- Vanilla destination room + spawn coordinates
- Any coordinate offsets or entry animations that the ROM data structure requires

This data is needed for Phase 5 (ROM write) and to verify the `falldown_pits` /
`dungeon_warps` lists are complete and correct. Collection is in progress.

---

## Phase 1 — Settings & Infrastructure ✓ COMPLETE

### 1a. New intensity level 4 ✓

- Added `"4"` to `intensity.choices` in `resources/app/cli/args.json`
- `DoorFlags.from_world` in `DungeonGenLocalSearch.py` sets `pit_warps = 'both'` at intensity >= 4 (implies lobbies via >= 3 check)
- Added option 4 to GUI intensity dropdown (`resources/app/gui/randomize/dungeon/widgets.json`)
- Added label strings to `resources/app/gui/lang/en.json` and `resources/app/cli/lang/en.json`
- `Main.py` random intensity updated to `randint(1, 4)`
- Settings string 3-bit encoding already accommodates value 4 — no change needed

### 1b. Custom intensity pitwarp field ✓

`pit_warps` added as a field on `DoorFlags` (`none | pits | warps | both`):

```yaml
intensity:
  pit_warps: both   # none | pits | warps | both
```

- Parsed via `DoorFlags.from_custom()` — same pattern as `lobbies`, `spiral`, etc.
- Default when intensity=4: `both`; intensity<4: `none`
- No separate world attribute — lives entirely in `DoorFlags`

### 1c. World object wiring ✓

- `pit_warps` is a `DoorFlags` field only — not a top-level world attribute
- `DoorFlags.for_player(world, player)` derives it from `world.intensity[player]` and applies any customizer intensity override

---

## Phase 2 — Dungeon Generation Updates ✓ COMPLETE (logic)

### Model

A pit or warp is **one directed edge** from a **group source** to a **Terminal**. Pits and warps share one pool:
any group may land on any Terminal, including one in its own room or sector.

| Door | `hook_from_door` (can leave through) | `hanger_from_door` (can enter through) |
|---|---|---|
| `DoorType.Hole` / `DoorType.Warp` (source) | `Hook.PitWarp` | none |
| `DoorType.Terminal` (landing, value 10) | none | `Hook.PitWarp` |

- A missing hook or hanger means *impossible in that direction*. `hook_key`/`hanger_key` in
  `DungeonGenerationCommon` raise on it, so a direction lookup that forgets one-wayness fails loudly.
  `can_connect(hanger_door, hook_door)` is the direction-aware compatibility test.
- **Groups**: several sources that land together share `door.group` (the Terminal's name). After
  sectors are formed, `collapse_pit_groups` keeps one representative per group as the sector's
  outstanding door (`group_rep`, `group_barrier`, `group_members`). It raises if a group spans sectors
  (a sector-formation bug) or mixes Blue and Orange barriers.
- **Terminals** are plain `Door` objects wired as incoming entrances on their landing region (not
  region exits); `door.entrance.parent_region` is the landing region.
- **Balance**: per dungeon, source groups (`one_ways`) must equal Terminals (`landings`).
- `Hook.Landing` is kept only for the legacy `DungeonGenerator`.

### 2a–2c. Data model, `BaseClasses.py`, `Doors.py` ✓

`create_terminal_doors` loads `data/terminals.yaml`: one Terminal door per entry, wired as an entrance
on its region, and `door.group` set on each listed source. `data/terminals.yaml` is the source of truth
for names, regions, groupings and (Phase 5) ROM data; `falldown_pits`/`dungeon_warps` remain flat lists
for vanilla wiring.

### 2d. `DoorShuffle.py` ✓

- When pits are not shuffled, `connect_terminal_door` wires each source to its vanilla landing and marks
  the Terminal used (`terminal.dest`), in both the classic (`link_doors_prep`) and NewGeneration
  (`prep_world_for_doors_prototype` / `handle_intensity_settings`) paths. An unused Terminal would
  otherwise become an outstanding door with no partner.
- `main_dungeon_pool_prototype` calls `collapse_pit_groups` after `merge_sectors`.
- The door spoiler lists each shuffled pit as source → landing region (one-way).

### 2e. `DungeonGenLocalSearch.py` ✓

- `Balance` counts one representative per group into `one_ways` and each Terminal into `landings`;
  balanced requires equality. `Polarity` has a fourth slot for pits.
- Drop-down lobbies stay locked to their vanilla dungeon unless both lobbies and pits shuffle
  (`drop_lobbies_locked`).

### 2f. `DungeonGenTransitivity.py` ✓

Standard matching (an unreached hanger attaches to a reached hook) produces exactly the legal falls; there
is no pit-specific connection branch. One-wayness is handled explicitly where the search reasons in
both directions: crystal back-propagation and the hook-side walk never climb back up a pit, a fall
leaves in the source's barrier color, and pit doors are exempt from the two-way "wasted loop"
heuristics. Details and verification: `docs/plans/transitivity_pitwarp_verification.md`.

### 2g. `DungeonStitcherV2.py` ✓

Pit assignments are part of the proposal search, validated jointly with door pairings (a Terminal
choice decides which regions are reachable, and in which crystal color):

- A pit is a one-way `proposed_map` entry `representative → Terminal`; `propose_pits` pairs them at
  random, and `proposal_hash` skips Terminals.
- Exploration sends a source to its Terminal's landing region; a sibling source follows its
  representative; each physical source's own crystal barrier applies.
- `modify_proposal` swaps pits as a permutation: a visited group moves onto a Terminal whose landing
  region was not visited.
- `create_dungeon` connects every physical source of a group to the landing region and marks the
  Terminal used.

---

## Phase 3 — OW Pit Dropdown with Lobbies

When `intensity >= 3` (lobbies) **and** pitwarps enabled:

- OW "dropdown" entrances (e.g. `Skull Pinball`, `Skull Left Drop`, `Skull Pot Circle`,
  `Skull Back Drop`, `Sewers Rat Path`) are currently fixed to their dungeon sector
- When a sector moves to a different dungeon (crossed door shuffle), its OW dropdown
  must move with it
- This requires the same kind of dynamic connector logic being built for `dungeon_entrances`

### Tasks

- Identify all OW-facing pit exits (exits that drop the player to the overworld or to a
  specific dungeon lobby from outside)
- Mark these in `DungeonGenerationCommon.py` alongside `dungeon_portals`
- During sector assignment, carry OW pit exits with their sector (not hardcoded to
  the dungeon)
- Update `EntranceShuffle2.py` connector logic to account for re-parented OW pit exits
- Evaluate: do OW pit exits affect inaccessible-region detection? They are one-way in,
  so they do not provide OW escape — probably safe, but verify

---

## Phase 4 — Entrance Redistribution Integration

**Dependency**: `dungeon_entrances` feature (Phase 3 of that plan) must be substantially
complete before this phase is possible.

When `dungeon_entrances: free` (or any redistributed mode) is active:

- OW dropdown entrances that have moved with their sector now need to be placed on the
  overworld by the portal redistribution algorithm, not hardcoded
- Evaluate per shuffle mode:

| Mode              | Pitwarp + Entrances interaction |
|-------------------|---------------------------------|
| vanilla           | N/A — portals fixed, dropdowns fixed |
| simple/restricted | Cluster assignment; dropdowns follow sector cluster |
| full/lite         | Portal-level; dropdown exits get OW slot from pool |
| crossed/lean      | Cross-world; dropdown exit world must be consistent with dungeon world |
| insanity          | Same as crossed; linked drops off by default, no extra constraint |
| swapped           | `dungeon_entrances: free` is a no-op; pitwarps intra-dungeon only |

- The four connector OW locations (Desert East, TR Isolated Ledge, TR Bridge, SW West)
  are for portal connectors — dropdown exits are a separate pool and should not compete
  for these slots

---

## Phase 5 — ROM Write

### 5a. Obtain the ROM data structure spec from the baserom branch

- The ROM pitwarp data structure is reportedly in development elsewhere — obtain its
  specification before writing code
- Identify: address in ROM, record format (source room ID, dest room ID, coordinates,
  entry animation type), table size limits

### 5b. Rom.py output

- Add a `write_pitwarps(world, rom, player)` function in `Rom.py`
- Write the shuffled pit/warp mapping in the format the data structure expects
- Vanilla (no shuffle) must produce identical output to unpatched ROM behavior

### 5c. Validate output

- Test that vanilla-assignment pitwarp write is byte-for-byte equivalent to unmodified
  ROM behavior (or matches documented vanilla values from Phase 0 data collection)

---

## Phase 6 — Testing & Spoiler Log

### 7a. Spoiler log

- ✓ The door spoiler lists each shuffled pit source and its landing region (one-way). A dedicated
  pitwarps section in the spoiler text is still open.

### 7b. TestSuite.py

- Add `--pitwarps` flag to `TestSuite.py` for batch generation testing
- Add per-dungeon pitwarp logic tests (similar to `test/dungeons/`) that verify
  all locations remain reachable when pitwarps are shuffled

### 7c. Regression

- Ensure intensity 1–3 seeds are unaffected by the new intensity 4 infrastructure
- Ensure custom intensity `pit_warps: none` produces identical output to pre-feature
  behavior at any intensity level

---

## Open Questions

1. **OW dropdown world constraint**: If a sector with an OW dropdown moves to the wrong
   world (e.g., a LW dropdown sector ends up in a DW dungeon), the OW spawn point may
   not exist or be unreachable. Need a hard constraint in DungeonGenLocalSearch that
   prevents this, or ensure the portal redistribution algorithm handles it.

2. **Linked drops interaction**: The `dungeon_entrances` design doc distinguishes
   "linked drops" (Sanctuary, Skull 1, Skull 2 East) from regular drops. Do any
   pitwarp OW exits fall into the linked-drop category? Verify before Phase 4.

## Resolved

- **Intra- vs inter-dungeon scope**: Controlled by `door_shuffle` mode. Basic shuffles
  within a dungeon; crossed allows pitwarps to cross dungeon boundaries.
- **Landing zone scope**: Fixed to exactly the current destination regions in
  `falldown_pits`/`dungeon_warps`. One Terminal door per pit/warp destination, no
  additional regions eligible.
- **Pit and warp pools**: One shared pool; any source group may land on any Terminal. No option to separate them.
- **Same-room landings**: Allowed. Spatial constraints are outside the dungeon algorithm's scope.
- **Balance feasibility**: Deferred — the algorithm is expected to handle it.
- **ROM data structure spec**: In active development on a branch of the baserom repo.
  Obtain spec before Phase 5 begins.

---

## Dependency Order

```
Phase 0 (data collection) ──────────────────────────────── Phase 5 (ROM write)
Phase 1 (settings) ─┬─── Phase 2 (gen)
                     └─── Phase 3 (OW+lobbies) ─── Phase 4 (entrance redistrib)
                                                         │
                                         dungeon_entrances Phase 3 ─────────────┘
```

## Planned Implementation Order

1. **Phase 2** (dungeon generation) — done (logic)
2. **Phase 5** (ROM write) — obtain ROM spec from baserom branch, implement alongside Phase 2
3. **Phase 6** (testing & spoiler log) — validate the feature end-to-end with Phases 2+5 complete
4. **Phase 3** (OW pit dropdowns) — after basic feature is tested and stable
5. **Phase 4** — deferred until `dungeon_entrances` Phase 3 is ready to integrate

Phase 4 is explicitly deferred — no work until both pitwarps and `dungeon_entrances` are independently stable.
