# Door and Dungeon Shuffling - Deep Dive

---

## Glitch Safety and Real-World Implications

- **Partial and Strict algorithms are minor glitch safe**: Partial treats most minor glitches as equivalent to having a full inventory, and strict always requires all keys, so neither can be broken by minor glitches.
- **Dangerous algorithm is NOT minor glitch safe**: It does not account for minor glitches, so players can use glitches to spend keys out of order and break logic. It also has a known multiplayer bug that can create unwinnable seeds.
- **No algorithm is safe from Hybrid Major Glitches (HMG)**: In HMG, players can use keys from one dungeon in another, breaking all intended logic.
- **Practical guidance**: Use partial or strict for safety and competitive play. Dangerous is only for advanced analysis and is discouraged for most use cases. Experimental is under development and adapts logic based on dungeon complexity.

See the summary in [topics.md](topics.md#key-logic-algorithm-summary) for a plain-language overview.
This document provides an algorithmic deep-dive into the door and dungeon shuffling systems of the dungeon randomizer, covering sphere construction, self-locking logic, placement rule contradictions, and the sophisticated algorithms used for door placement and dungeon layout generation.

## Core Components

### Key Door Shuffling System ([`SmallKeyDoorShuffle.py`](../../../source/dungeon/SmallKeyDoorShuffle.py))

The small key door shuffling system is responsible for placing key doors throughout dungeons while maintaining logical solvability.

#### Main Algorithm Flow

The [`shuffle_small_key_doors()`](../../../source/dungeon/SmallKeyDoorShuffle.py) function orchestrates the key door placement process in two phases:

**Phase 1**: Calculate key door distribution across dungeons by calling [`find_small_key_door_candidates()`](../../../source/dungeon/SmallKeyDoorShuffle.py) and determining the number of key doors needed per dungeon.

**Phase 2**: Find valid key door combinations using either exhaustive or Monte Carlo algorithms via [`find_valid_combination()`](../../../source/dungeon/SmallKeyDoorShuffle.py).

### Key Logic Analysis System ([`NewKeyLogic.py`](../../../source/dungeon/NewKeyLogic.py))

The new key logic system analyzes dungeon layouts to create sphere-based progression models.

#### Sphere Construction Algorithm

**Key Sphere Class**: The [`KeySphere`](../../../source/dungeon/NewKeyLogic.py) class represents accessibility spheres with regions, locations, key counters, and child sphere relationships. Critical for self-locking detection through the `self_locking_child_spheres` attribute.

**Sphere Building Process**: The [`determine_small_key_logic_exhaustive()`](../../../source/dungeon/NewKeyLogic.py) function creates sphere hierarchies based on key progression using a breadth-first queue approach. Self-locking scenarios are detected via [`detect_self_locks()`](../../../source/dungeon/NewKeyLogic.py) during sphere construction.

#### Self-Locking Detection Algorithm

**Core Self-Locking Logic**: The [`detect_self_locks()`](../../../source/dungeon/NewKeyLogic.py) function identifies spheres with exactly one new location and one new door difference, marking them as self-locking scenarios. These spheres are added to the parent's `self_locking_child_spheres` list.

**Self-Lock Adjustment in Placement Rules**: Placement rules are adjusted through logic that reduces key requirements for self-locking scenarios when only non-important locations are blocked, allowing controlled self-locking placement.

### Dungeon Generation System ([`DungeonStitcher.py`](../../../source/dungeon/DungeonStitcher.py))

The dungeon stitcher connects door networks to create cohesive dungeon layouts.

#### Door Connection Algorithm

**Main Generation Flow**: The [`generate_dungeon_find_proposal()`](../../../source/dungeon/DungeonStitcher.py) function creates random door connection proposals and iteratively validates and refines them using exploration and validation functions until a valid layout is found.

**Hook-Based Door Matching**: The [`create_random_proposal()`](../../../source/dungeon/DungeonStitcher.py) function groups doors by directional hooks (North, South, East, West, Stairs) and creates connections between matching opposite hooks to ensure proper door alignment.

### Reachability / Stitchability Feasibility Check — "Transitivity" ([`DungeonGenTransitivity.py`](../../../source/dungeon/DungeonGenTransitivity.py))

#### What Question This Answers

Given a set of sectors assigned to one dungeon, **is there any way at all to pair up their loose door ends** ("outstanding doors") into a single, fully-connected, fully-reachable dungeon that also satisfies every per-sector rule (one-way doors, crystal-barrier color requirements, dead-end pairing, portal placement, special puzzle rooms)?

This is a **feasibility check, not the final layout**. It does not decide the randomized door pairing that ships in the seed — [`DungeonStitcherV2.py`](../../../source/dungeon/DungeonStitcherV2.py) does that, proposing random pairings and calling back into this module (`do_transitivity_check()`) to validate each portal placement as it commits to it. [`DungeonGenLocalSearch.py`](../../../source/dungeon/DungeonGenLocalSearch.py) calls it the same way, as the last and most expensive check when scoring a candidate sector grouping — see the "Transitivity Checks" gotcha in the top-level `CLAUDE.md`: it's deliberately ordered after the cheaper polarity/crystal/portal/location/branching checks because it's the most expensive to run.

A concrete failure mode this exists to catch: a sector grouping can look perfectly balanced (right door counts, right crystal switches, right portal counts) and still be **unstitchable** — e.g. two dead-end sectors whose only remaining doors face each other, or a "must enter" door that can only ever be reached from a sector that's already been forced shut elsewhere. Simpler balance checks can't see this; only an actual search over door pairings can.

**On the name "Transitivity":** it describes the underlying data more than the module's job — each sector precomputes an internal reachability relation between its own doors (`sector.descriptor.reachability`, see below), and this module chains those relations transitively across sector boundaries. When explaining this system to someone new, lead with "reachability/stitchability feasibility check" and treat "Transitivity" as the legacy name, not a concept to build the explanation around.

#### Terminology: Hook vs. Hanger

Every door has two direction-derived values, computed by two similarly-named but distinct functions:

- **`hook_from_door(door)`** (defined in [`BaseClasses.py`](../../../BaseClasses.py)) is a **self-description**: it returns the door's own facing direction (a North-facing door → `Hook.North`).
- **`hanger_from_door(door)`** (defined in [`DungeonGenerationCommon.py`](../../../source/dungeon/DungeonGenerationCommon.py)) is a **search key**: it returns the *opposite* direction — the type of door this one needs to connect to (a North-facing door → `Hook.South`).

Two doors can connect exactly when one's hanger equals the other's hook (`hanger_from_door(d) == hook_from_door(match)`). Mnemonic: **hook is home, hanger hunts the opposite** — a hook is the fixed, self-describing side; a hanger is the part reaching for something else. This is provably symmetric for ordinary directional doors (if A's hanger matches B's hook, B's hanger automatically matches A's hook), so it never matters which door you call "A."

Special door types break the self/opposite pattern with fixed constants instead of direction lookups:
- **Spiral stairs**: hook and hanger are both `Hook.Stairs` — self-matching, any spiral stair pairs with any other.
- **Holes/Warps**: hook is `Hook.PitWarp`, hanger is `Hook.Landing` — asymmetric on purpose, since a fall/warp is one-directional.
- **Terminal doors**: hook is `Hook.Landing`; `hanger_from_door` has no case for `Terminal` at all (returns `None`) — a terminal can be *found* by a search but never *initiates* one, matching their role as entry points only.

#### Inputs: Per-Sector Reachability (computed in [`DungeonGenSectorDesc.py`](../../../source/dungeon/DungeonGenSectorDesc.py))

Before this module ever runs, [`SectorDescriptor.analyze_sector()`](../../../source/dungeon/DungeonGenSectorDesc.py) walks each sector's own interior from every one of its outstanding doors, recording which of its *other* outstanding doors that walk can reach and under what crystal-barrier state (`reachability`: `door -> [(reachable_door, crystal_state, crystal_requirement), ...]`, plus separate `blue_reachability`/`orange_reachability` region sets). `SectorDescriptor.classify()` then derives, from that map:

- **`must_enter_reqs`**: doors that are the *only* way to reach part of the sector's interior — these become `MustEnter` constraints.
- **`dead_end`**: sectors with exactly one outstanding door.
- **`is_neutral`**: sectors reachable identically no matter which door you enter through.
- **`special_reqs`** / **`crystal_reqs`**: Ice Cross–style directional puzzles and blue/orange barrier requirements.

This module never looks inside a sector's rooms — it only ever consumes these precomputed per-sector summaries plus the raw door list.

#### Deriving `must_enter_reqs`: A Backward-Reachability Search

`classify()` builds `must_enter_reqs` by inverting the forward reachability map into a `reversed_reachability`: for every pair where entering via `source` lets you reach (exit via) `dest`, it records `dest -> [source, ...]`. Any `dest` reachable from only one `source` — every other outstanding door in the sector fails to reach it internally — gets added to `must_enter_reqs`, not `source`.

This is intentionally a **backward** search: the constraint targets whichever door has *fragile* access, not whichever door happens to grant that access. Requiring only that `source` receive some external connection wouldn't guarantee a player ever actually walks the specific internal path from `source` to `dest` — the global stitching search controls door pairings, not in-game routing choices. Requiring `dest` itself to be paired externally (and forbidding it from pairing to a dead end or another MustEnter door, per the door-matching rules in `ConstraintInfo`) guarantees a player can reach it directly, regardless of how `source`'s own connection turns out. In short: trace reachability backward from the door with the accessibility problem, then require *that* door — not its gatekeeper — to get a real external connection.

If, after collecting single-source destinations, some outstanding doors are still unaccounted for (`unreached`), `classify()` falls back to a door (or small group of doors) whose reachability list alone covers everything left over (`covers_all`), inserting it as an additional must-enter requirement at the front of the list. If no such door exists, it raises `GenerationException("Some edge case where you need two separate doors to cover all: ...")` — a case the code doesn't currently know how to resolve; treat this exception as a genuine known gap, not an ordinary validation failure, if it ever fires.

#### Deriving `crystal_reqs`: AND vs. OR Requirements

`classify_crystals_new()` is the active implementation — `classify_crystals_old_option()`, in the same file, is unused dead code from an earlier approach and should not be mistaken for live behavior. It works per crystal color:

1. Across every door's cached exploration state (`state_cache`), find every region ever marked as requiring that color to reach (`crystal_forced == Blue`/`Orange`) — this is `blue_region_set`/`orange_region_set`.
2. For each such region, split the sector's doors into **`need_color`** (doors that only reached this region by forcing through the barrier — they need the correct crystal state already active to use it) and **`can_reach`** (doors that reached it without needing the barrier at all — already-safe, e.g. doors that pass the switch itself).
3. `reduce_region_requirements()` and `reduce_again()` collapse regions whose door sets are subsets/unions of each other, so multiple regions needing the same access pattern become one combined requirement instead of duplicates.
4. The resulting `CrystalConstraint.type` is **`'all'` (AND logic)** when every remaining requirement group has no `can_reach` fallback — everything flagged genuinely needs its own crystal access, so all of them must be satisfied. Otherwise it's the default **`'any'` (OR logic)** — satisfying just one of the flagged groups (or reaching one of their already-safe doors) is enough.

`ConstraintInfo.__init__` turns `'any'` constraints into a single `Constraint` whose participants are the union of the color-needing and already-safe doors (any one getting a valid connection satisfies it), while `'all'` constraints are split into one separate `Constraint` per group, each independently enforced.

#### Dependent (Linked) Portals

Some dungeon portals aren't independent overworld entrances — they're reachable only via another portal, because their target overworld region is otherwise accessible only from inside the dungeon. `analyze_portals()`/`analyze_portals_altered()` in [`DoorShuffle.py`](../../../DoorShuffle.py) handle this earlier in generation: when several candidate portals all lead to the same practically-inaccessible region, one is chosen as the real, externally-connected entrance (`.destination = True`), and the rest are marked `.dependent = <chosen portal>`. These are the "linked drops" referenced in the `dungeon_entrances` design docs (Sanctuary, Skull 1, Skull 2 East, etc.).

`ConstraintInfo` models this with two maps:
- **`dependent_portals`**: for a sector whose portals are *all* dependent (none independently enterable), every one of its outstanding doors is recorded as `dependent_portals[door] = (sector, enabling_portal)`. Such a sector does **not** get a free starting point the way `init_portals` sectors do (see `append_sector_free`) — it can only become reachable once its enabler is.
- **`dependent_lookup`**: the inverse, keyed by the enabling portal's own door: `dependent_lookup[enabling_portal.door] = dependent_door`.

During the search, `connect_door()` checks whether the sector containing the door just connected (`hanger`) holds a portal registered as someone's enabler in `dependent_lookup`; if so, the dependent sector's door is immediately unlocked — moved from `remaining_doors` into `unconnected_doors` with a default `CrystalBarrier.Orange` state, exactly as if it had been reached through ordinary internal reachability. **Note**: this trigger fires once *any* door in the enabling portal's sector gets connected, not specifically when the enabling portal's own door is used — I haven't verified against a concrete linked-drop example whether that's a deliberate simplification (the sector being connected at all is treated as proof the portal is reachable) or a source of imprecision, so treat it as a plausible-but-unconfirmed reading rather than a settled fact.

#### Constraint Types

The [`ConstraintType`](../../../source/dungeon/DungeonGenTransitivity.py) enum, built up in `ConstraintInfo.__init__` from the descriptor fields above:

| Constraint | Meaning | Source |
|---|---|---|
| `MustEnter` | This door (or one of a small group) must be entered from outside — the sector's only access point for part of its interior | `descriptor.must_enter_reqs` |
| `Special` | Ice Cross–style rooms with unusual directional traversal rules | `descriptor.special_reqs` |
| `Crystal` | A blue/orange crystal barrier must be reachable in the matching color before this door group is usable | `descriptor.crystal_reqs` |
| `DeadEnd` | A sector with exactly one outstanding door — can't pair to another dead end or a MustEnter door | `descriptor.dead_end` |
| `Neutral` | A sector reachable the same way regardless of entry door — mostly exempted from pairing restrictions | `descriptor.is_neutral` |
| `Portal` | This door is a dungeon entrance (overworld portal) and must end up placed, not paired to another interior door | `door.traversal_only` |

#### The Search

`do_transitivity_check()` first tries a **greedy** pass (`do_transitivity_check_main(..., greedy=True)`): at each step, only the single best-scored candidate pairing is explored, no backtracking. If that fails, it falls back to a full **best-first search** over partial pairing states, capped at 20,000 iterations (`GenerationException` if exceeded — a runaway search, not a proof of infeasibility).

- **State** (`Transitivity`): `remaining_doors` (not yet reached), `unconnected_doors` (reached but unpaired, each tagged with the crystal-barrier state you'd arrive with), `connection_map` (hard pairings so far), and satisfied/unsatisfied constraints.
- **Expansion** (`find_connectable_doors`): checks for *forced* connections first — a door with only one legal match left is paired immediately, short-circuiting the rest of that step. Otherwise it generates all legal candidate pairings (hook/hanger direction matching via `hook_from_door`/`hanger_from_door`, portal eligibility via `valid_portal()`) and sorts them by `score_possible_connection()`, a heuristic that prioritizes satisfying MustEnter/Special/Crystal constraints and reaching an unused crystal-switch door early. The specific point values (5/4/3/2/1/0) encode relative priority only — treat them as tuned-by-feel ordering, not values with independent meaning.
- **Committing a pairing** (`connect_door`): merges the two sectors' reachability across the new connection and propagates crystal-barrier state both forward (what's newly reachable, in what state) and backward via a `backprop_queue` (a door already reached with `Either`/`Both` access upgrades everything chained behind it), then marks any constraints the pairing satisfies. **Open question, unresolved even by the original author**: this method expands reachability from both sides of the new connection — the hanger's sector (filtered by whether `crystal_prop` satisfies each edge's crystal requirement) and, separately, the hook's own sector via a block literally commented `# special handling for ice cross and similar cases` (no crystal-requirement filter applied there). Whether that asymmetry is intentional or a latent gap is genuinely unclear — treat crystal-barrier bugs touching this area with extra care, and don't assume either block's behavior is authoritative without re-deriving it from a concrete example.
- **Priority** (`priority()`): a min-heap key that discounts search depth by how many constraints are still unsatisfied, so states satisfying constraints efficiently sort ahead of states just accumulating pairings.
- **Termination**: success when a state has no `remaining_doors`/`unconnected_doors` left and no `unsatisfied_constraints`.

#### Reducing the Branching Factor: Door Equivalence Classes

Naively, `find_connectable_doors` would consider every `doors_to_check` × `doors_to_connect` pair — but many of those doors are functionally identical for this search's purposes, and exploring each separately would blow up the branching factor. The code immediately above `find_connectable_doors` still carries the original open question as a comment: *"a lot of doors are 'equivalent' logically for what we're checking and so shouldn't be explored independently, not sure how to determine that here."* `winnow_doors_to_check()` and `get_unique_unconnected_doors()` are the answer that was later built — one per side of a candidate pairing:

- **`winnow_doors_to_check()`** (for `doors_to_check`, the side initiating a new pairing): collapses doors sharing the same `(hanger_from_door(door), still_blocks_an_unsatisfied_constraint, shape_construct[door])` key down to one representative. `shape_construct` — computed once per door in `SectorDescriptor.analyze_sector()` — is an abstracted fingerprint: `(is_valid_portal, portal_context, sorted_counts_of_(hook_type, crystal_state, crystal_requirement)_reachable_via_this_door)`. It intentionally discards *which specific* doors are reachable and keeps only their hook-type/crystal-state shape. Two doors with an identical fingerprint are indistinguishable to the search — pairing either one leads to the same class of downstream possibilities.
- **`get_unique_unconnected_doors()`** (for `doors_to_connect`, the already-reached pool being paired against): collapses doors sharing the same `(hook_from_door(door), current_crystal_state, exact_reachability_by_door_name)` key — a *finer*-grained equivalence than `shape_construct`, keyed on the literal set of named doors reachable rather than just their type signature.

There's no confirmed reason the two sides use different-granularity keys (an abstracted fingerprint for the side initiating the search vs. exact door identity for the already-reached pool) — plausible, but unverified. What's certain: both exist to collapse "doors that would explore identically" and shrink the search, and the original comment flagging this as unsolved was left in the file even after both functions were added — read that as the author's own assessment that this remains a partial, not fully general, answer.

#### Impossibility Detection (Pruning)

`now_impossible()` runs on every candidate state and is what keeps the search tractable — cheapest checks first, so hopeless branches die before being expanded further:

1. **Already visited** — this exact `connection_map` was tried before (memoized in `visited_states`).
2. **Stuck** — no doors left to connect but constraints remain, or unconnected doors are exhausted while doors still remain.
3. **`quick_door_matches_check`** — propagates remaining legal door-match lists to a fixed point; a door whose candidate list empties out, or more doors forced onto the same match set than can fit, is a contradiction.
4. **Forced-door tally**: walks `unsatisfied_constraints` (MustEnter, Crystal, DeadEnd, Portal) plus single-remaining-door sectors and `detect_forced_loop()` results to build `total_needed_per_type` (doors that *must* connect a given direction) versus `available_per_type` (what's actually left to satisfy them); any per-direction shortfall is an immediate failure.
5. **`check_for_forced_connections`** — chases chains of doors that have exactly one possible reachability path, propagating forced pairings and re-tallying until stable; fails if a single forced door's reachability set would have to cover every remaining candidate of that type.
6. **`detect_problematic_forced_scenarios`** — extends the tally by letting 2-outstanding-door "pass-through" sectors convert an available door of one hook type into a hanger of another type, chained via a small BFS over transfer possibilities; fails if, even after every possible conversion, some required type still comes up short.
7. **`detect_no_path_exists_for_forced`** — for each forced door, walks backward through match/reachability chains to see if it can actually reach something already-connected; fails early if a forced door is provably unreachable from anywhere still open.
8. **Sector loop / closed-pocket detection** — if every outstanding door of an unresolved sector can only match into a closed set of sectors that can only match back into it, that pocket can never connect to the wider dungeon.
9. **Branch/dead-end balance** — sums, per sector, how many doors are "spare" (more reachable options than needed) versus missing or forced-shut, net of detected loop pockets (`count_forced_loops`); a negative total means the group has run out of places to branch and will strand doors it can't pair off.

Each of these is a progressively more expensive way to prove a partial pairing can never reach a valid end state — the search only expands further once all of them pass.

## Key Algorithms

### 1. Exhaustive Key Logic Algorithm

For dungeons with ≤8 key doors, the [`exhaustive_key_logic_algorithm()`](../../../source/dungeon/SmallKeyDoorShuffle.py) function uses complete enumeration analysis. It generates combinations using [`kth_combination()`](../../../source/dungeon/SmallKeyDoorShuffle.py), builds key layouts, creates placement rules via [`create_exhaustive_placement_rules()`](../../KeyDoorShuffle.py), and checks for contradictions using [`find_contradiction_in_rules()`](../../../source/dungeon/SmallKeyDoorShuffle.py).

### 2. Monte Carlo Algorithm

For larger key door counts, the [`monte_carlo_algorithm()`](../../../source/dungeon/SmallKeyDoorShuffle.py) function uses statistical sampling with pre-filtering. It eliminates candidates based on reachability analysis, samples from surviving candidates, and validates proposals using [`validate_key_proposal_large()`](../../../source/dungeon/SmallKeyDoorShuffle.py).

### 3. Placement Rule Contradiction Detection

The [`find_contradiction_in_rules()`](../../../source/dungeon/SmallKeyDoorShuffle.py) function detects logical contradictions in key placement by building a constraint satisfaction problem and using backtracking search with pruning to find valid assignments. Returns `True` if contradictions are found.

## Reachability and Progression Analysis

### Cache-Based Reachability System

The [`can_reach()`](../../../source/dungeon/NewKeyLogic.py) method uses sophisticated caching for reachability calculations. It builds cache keys via [`build_cache_key()`](../../../source/dungeon/NewKeyLogic.py) and calculates reachability through [`calculate_reachability()`](../../../source/dungeon/NewKeyLogic.py) when cache misses occur.

### Sphere-Based Progression Analysis

The [`calculate_reachability()`](../../../source/dungeon/NewKeyLogic.py) method performs breadth-first search through the sphere hierarchy, handling key acquisition and spending logic. It processes root spheres based on big key state and advances through child spheres while managing self-locking placement scenarios through `self_locking_child_spheres`.

## Advanced Features

### Crystal Switch Bypass Detection

The [`detect_crystal_switch_bypass()`](../../../source/dungeon/NewKeyLogic.py) method analyzes crystal switch mechanics for advanced routing by finding crystal switches in reachable regions and identifying blue barrier islands accessible via crystal switches using helper methods like [`_find_crystal_switches_in_regions()`](../../../source/dungeon/NewKeyLogic.py) and [`_find_blue_barrier_islands()`](../../../source/dungeon/NewKeyLogic.py).

### Forced Loop Detection

The [`detect_forced_loop()`](../../../source/dungeon/DungeonGenTransitivity.py) method detects forced routing loops by checking if all door matches are in the same sector or neutral sectors, preventing impossible connection scenarios.

## Performance Characteristics

### Computational Complexity

- **Exhaustive Algorithm**: O(C(n,k) * V) where n=candidates, k=doors needed, V=validation cost
- **Monte Carlo Algorithm**: O(S * V) where S=sample size, V=validation cost  
- **Transitivity Check**: O(2^D * C) where D=doors, C=constraints
- **Self-Lock Detection**: O(S^2) where S=spheres

### Optimization Strategies

1. **Early Pruning**: Eliminate impossible configurations before full validation
2. **Constraint Ordering**: Process most restrictive constraints first
3. **Caching**: Extensive reachability and state caching
4. **Sampling**: Statistical sampling for large search spaces
5. **Incremental Validation**: Validate changes incrementally rather than full re-validation

### Memory Management

- Sphere hierarchies use shared region/location references
- Connection maps use efficient door indexing
- Cache keys use frozen sets for immutable hashing
- Constraint graphs use sparse representations

## Integration Points

### With Item Placement System
- Key door placement must coordinate with item pool generation
- Self-locking spheres affect item accessibility calculations
- Big key placement interacts with door unlock requirements

### With Logic System  
- Door connections create new logical dependencies
- Sphere construction feeds into accessibility rules
- Crystal switch analysis affects barrier traversal logic

### With Validation System
- Door layouts must pass beatable checks
- Key placement validates against soft-lock prevention
- Sphere analysis contributes to completion verification

This sophisticated door and dungeon shuffling system ensures that randomized layouts maintain logical solvability while maximizing variety and challenge through advanced algorithmic techniques including sphere construction, self-locking detection, constraint satisfaction, and statistical sampling methods.
