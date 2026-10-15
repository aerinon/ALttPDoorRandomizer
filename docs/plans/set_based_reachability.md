# Set-based reachability for the experimental key logic

Status: implemented and validated (Validation results). Measurement in Validation plan item 5.

Code: `CollectionState.inject_guaranteed_regions` and `reach_with_keys` (BaseClasses), called from the
`update_reachable_regions` loop; `NewKeyLogic.query_guarantee` and the per-cache-key `crystal_cache`; test
`test/dungeon/TestSetReachability.py`.

## Problem

The experimental key logic (`source/dungeon/NewKeyLogic.py`) guarantees sets: a region is guaranteed when it is reached
in every terminal sphere, by whichever route the worst case took. The traversal (`CollectionState.traverse_world`) counts
a region only when a contiguous chain of passable entrances leads to it, with crystal state carried along the chain, and
every entrance into a dungeon's relevant regions carries `create_rule_for_key_access`, which passes only when
`entrance.connected_region` is guaranteed.

Where a guaranteed region is reachable by one route or another, each route's first room is not guaranteed on its own, so
every key door toward the region is refused and no sweep reaches it.

Seed 9 (`--door_shuffle vanilla --shuffle vanilla --keysanity`, key logic experimental), fill step 103 (Swamp big key at
`Turtle Rock - Big Key Chest`): Ganons Tower guarantees 61 regions, 11 of them unreached (Big Key Room, Ice Armos, Four
Torches, Invisible Catwalk, Big Chest, Bob's Room, Blocked Stairs, Fairy Abyss, three Warp Maze regions). The key doors
toward them (`GT Hookshot ES`, `GT Firesnake Room SW`, `GT Tile Room EN`, `GT Crystal Circles SW`) open onto rooms that
aren't guaranteed. Turtle Rock's sixth key sits in `GT - Big Key Room - Left`, so the spot is refused; static accepts it,
correctly.

## Inventory: what assumes "reached means connected by a path"

| Consumer | Where | Assumes | With path-less regions | Needs |
|---|---|---|---|---|
| Traversal | `BaseClasses.traverse_world` | regions enter `reachable_regions` only through a passable entrance; exits are queued when a region is entered | injected regions must be roots: their exits queued into `blocked_connections` | inject with exits queued, inside the update loop |
| Crystal state | `reachable_regions` values; `should_visit`, `valid_crystal`, `can_reach_blue/orange` (Thieves Attic, Hera barriers) | a region's crystal state is what the path brought | an injected region needs a state, or barrier rules from it fail | crystal from the spheres (below) |
| Key access rule | `Rules.create_rule_for_key_access` on every entrance into relevant regions | per-door: the connected region must be guaranteed | still refuses key doors into transit rooms; injection makes the guaranteed regions reachable anyway | keep as is for reach; see semantics for transit |
| Isolated regions | `CollectionState.check_for_isolated_regions` (removed) | added unvisited guaranteed regions, only while a small key is placed, crystal `Null`, exits not queued | the partial version of this design | replaced by general injection |
| Repeat loop | `update_reachable_regions` (`a509ab4a`) | traverses again while the accessible lobby set changes | injection can open lobbies and more injection | loop until neither lobbies nor injected regions change |
| Path record | `state.path`, set in `traverse_world`, `Region.can_reach_private`, `Entrance.can_reach` | every reached region has a route | injected regions have none | a synthetic path: the region, then the path of a reached lobby of the dungeon |
| Spoiler paths | `Main.create_playthrough` → `get_path` | `state.path` gives the route | falls back to `(region, None)`: the region alone | deferred (display question shelved) |
| Kiki | `Fill.balance_money_progression.kiki_required` | a location's path names the `Palace of Darkness` region | `None` path ⇒ Kiki not counted for PoD regions | the synthetic path through the reached lobby keeps this right |
| Bunny routes | `Rules.get_rule_to_add` / `path_to_access_rule` | `state.can_reach(entrance)` on a route's last entrance | works from `reachable_regions`; unchanged | none |
| Zelda delivery | `Rules.delivery_routes` | walks exits evaluating `ext.access_rule(state)` from the Cellblock | key access rules refuse transit rooms the same way | follows the key access rule decision below |
| Dangerous algorithm | `check_key_doors_in_dungeons`, `apply_dungeon_exploration`, `exp_cache`, `dungeon_limits`, door counters | only runs for `key_logic_algorithm dangerous` | none | none |
| Door bookkeeping | `reached_doors`, `opened_doors`, `door_counter`, `dungeons_to_check` updated in `traverse_world` | used only by the dangerous algorithm | none | none |

Hardest parts: crystal state for injected regions, item requirements (below), and keeping the update loop terminating
and cheap.

## Semantics

**A guaranteed region that items can reach is reachable.**
- Per dungeon on the experimental exhaustive logic, after each traversal pass: take the dungeon's guaranteed regions
  (`query_reachability`, the meet over futures).
- Of those not yet reached, inject the ones the traversal reaches from the current state holding every key of the
  dungeon (`reach_with_keys`: a copy of the state with the dungeon's small keys and big key added, traversed). Item
  rules stay in force; key doors and key access rules pass. This keeps item requirements, which the key counters
  ignore, in force.
- An injected region becomes a traversal root: its crystal state from the spheres, its exits queued; normal traversal
  continues from it (so it can lead out of the dungeon, to the overworld or other dungeons, and to inaccessible regions
  explored as dungeon space).
- Transit rooms (on a route, not guaranteed) are not injected: their locations stay uncollectable and nothing leaves
  through them. The player passes through some route, but which one is undetermined.
- Rules that require a path (Zelda delivery, crystal barrier rules) may be relaxed to "some valid path exists": a
  guaranteed region counts as reached without a specific path.
- Key doors keep their per-door rule; injection is what reaches the guaranteed side.
- The update loop repeats while lobbies open or new regions are injected; both only grow, so it stops.

Alternative considered: drop per-door gating and gate only locations and exits by the guarantee. Simpler to state, but
every rule that asks `can_reach(region)` (crystal barrier rules, Zelda delivery, bunny routes) would need to tell
transit from guaranteed regions.

**Item requirements.** Two kinds of reachability, with different rules:
- Reachability for wasting keys (where a player may spend keys): item-blind, as the key counters are. Correct, because
  minor glitches mostly get somewhere without an item, so assuming every item is the safe direction for waste.
- Reachability for what is in logic (regions and locations collectable): item-aware. Injection supplies only a
  starting stage; normal traversal, with item rules, continues from it. The item-respecting walk keeps injection itself
  from reaching past an item requirement.
The walk shows that some item route exists with key doors open, not that every key order leaves one. Making the key
counters item-aware would explode combinatorially; closing this needs a different system. Deferred unless shown to cause
keylocks.

## Crystal state

- The key counters' exploration (`DungeonGenerator.ExplorationState`) records each region in `visited_orange` and/or
  `visited_blue`; a reachable switch puts the state in `Either`. A sphere keeps only `regions` (the union), but its
  `key_counter.state_ref` keeps the two lists.
- Injected crystal state: the AND of the guarantee's state and the state `reach_with_keys` reached the region in, so a
  switch the key counters reach without the item it needs doesn't count.
- Guaranteed crystal state: the most restrictive state over every terminal sphere of every future, i.e. the AND of the bits (Blue 1, Orange 2; `Both` counts as both bits). `Either` and `Blue` give `Blue`;
  `Orange` and `Blue` give `Null`. `Either` only when every terminal sphere reached it in both states.
- `Null` is the "neither" state: `valid_crystal` passes no Blue or Orange barrier in it, so no new enum value is
  needed.
- Seed 9, step 103 (prototype `doors-work/tools/inject_probe.py`): 6 terminal spheres; all 11 unreached GT regions are
  `Either` in all of them. Injecting them (exits queued) makes `GT - Big Key Room - Left` reachable; collecting Turtle
  Rock's key then makes `Turtle Rock - Big Key Chest` guaranteed and reachable, so step 103 would be accepted, matching
  static.
- Precision risks: exploration reaches a region in a crystal state along some path; a terminal sphere may record both
  states through different internal paths, which the player may not both have. Dungeons whose barriers depend on
  switch order (Thieves Attic, Hera, Ice) are where to check. A `Null` result leaves barrier exits closed until the
  traversal reaches a switch: conservative.

## Interactions

- **Futures / lobbies:** injection uses the meet over futures, so it inherits order independence; injected regions can
  open lobbies, handled by the loop.
- **Fill re-check** (`Fill.keeps_dungeon_guaranteed`): compares guaranteed sets; unchanged. With injection, guaranteed
  items become collectable, so fewer placements are refused downstream.
- **Post-fill `KeylockCheck`:** a door-order search over counters; unchanged. Its outside-key supply sweep gains reach.
- **Standard escape:** `EscapeCheck` is a generation-time check, unchanged; Zelda delivery follows the key access rule
  (decision above).
- **Keysanity:** the main beneficiary (keys outside dungeons make multi-route guarantees common).
- **Fast logic (>8 key doors):** count rules, no `create_rule_for_key_access`; nothing to inject.
- **Classic and other algorithms:** no `new_logic`; injection never runs.

## Decisions

1. Item requirements: the guarantee stays item-blind (waste reachability); logic reachability is item-aware through the
   item-respecting walk and normal traversal from the injected stage (Semantics, Item requirements).
2. Transit rooms stay unreachable; rules that need a path may accept "some valid path exists".
3. Crystal state: most restrictive over all terminal spheres; disagreement on color gives `Null` (neither).
4. Cost is not a constraint: this is a correctness change. Measure it, but don't trade correctness for it.

Deferred: what the spoiler shows for an item reached without a path (synthetic lobby-rooted path vs. other display).

## Validation plan

1. Static lockstep comparison (`doors-work/tools/sve_*.py`): seed 9's first disagreement (step 103) disappears; no new
   first disagreements, judged with a search independent of both algorithms' rules.
2. Monotone sweep (`doors-work/tools/monotone_sweep.py`): no new shrinks, every update a fixed point.
3. Keylock audits and the post-fill check across settings: no locks.
4. Generation A/B against HEAD, including keysanity and crystal-heavy settings.
5. Measurement (`doors-work/tools/set_gap_measure.py`, data in `doors-work/data/set_gap/`, genfix `49706f96`, 100 seeds
   per config). A "gap" refusal is a refused fill spot whose region the dungeon's key logic guarantees, the traversal
   hasn't reached, and an item-respecting walk with that dungeon's key doors open reaches: the refusals injection rescues.

   | Config | Refused | Guaranteed, unreached | Gap | Seeds with a gap |
   |---|---|---|---|---|
   | vanilla keysanity | 2,907 | 1,362 | 26 | 19 |
   | basic i2 | 3,957 | 610 | 10 | 7 |
   | crossed i2 open | 3,639 | 394 | 6 | 4 |
   | crossed i3 open | 3,173 | 332 | 1 | 1 |
   | crossed i3 standard | 9,252 | 2,012 | 20 | 7 |
   | crossed i2 inverted | 5,162 | 736 | 11 | 7 |
   | crossed i2 keysanity | 1,539 | 539 | 0 | 0 |

   Most guaranteed-but-unreached refusals are item-gated or in dungeons not yet entered (the counters are item-blind,
   Decision 1); injection would not help them. The path gap is about 1–2% of refusals. No finished world has a filled
   location in a guaranteed-but-unreached region. 3 of 11 crossed i3 standard fill failures (seeds 3, 44, 59) saw a gap
   refusal of the item that failed; no other fill failure did. Rate effect is small; the case for the redesign is
   correctness (seed 9's step 103), not rate.

## Validation results

Data in `doors-work/data/sbr/`, baseline `49706f96`.

- Lockstep, vanilla keysanity, seeds 1–30: 0 disagreements in each of experimental → static, static → experimental and
  the experimental control (3,319 checks each). Seed 9's steps 103, 104 and 107 now agree with static.
- Keylock audit, 100 seeds × 7 configs (vanilla keysanity, basic i2, crossed i2/i3, crossed i3 standard, crossed i2
  inverted, crossed i2 small keysanity): 0 keylocks, 0 audit errors.
- Monotone sweep, 30 seeds each: crossed i2 clean; vanilla keysanity seed 10 shrinks GT's Compass Room after GT's own
  big key is collected there, identically at the baseline (the own-big-key restart pessimism on the worklist).
- Generation A/B, 100 seeds per config: rates equal except crossed i3 standard 73 → 75. Time up 0–87% (vanilla
  keysanity 69 → 129 s, basic i2 46 → 71 s, crossed i3 84 → 107 s, crossed i2 109 → 112 s); the state copy in
  `reach_with_keys`, repeated for item-gated guaranteed regions on every update, is the cost.

