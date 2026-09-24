# Transitivity and Stitcher Verification for Pit/Warp Shuffle

Trustworthy Transitivity verdicts and stitched layouts for sector sets with Hole/Warp sources and Terminal landings.
Feature plan: `docs/plans/pitwarps_feature.md`.

## Current State

What the pit work changed:

- `BaseClasses.hook_from_door`: Hole/Warp hook `PitWarp`; Terminal has no hook. `DungeonGenerationCommon.hanger_from_door`: Terminal hanger `PitWarp`; Hole/Warp has no hanger. `Hook.Landing` is kept only for the legacy `DungeonGenerator`.
- `DungeonGenerationCommon`: `hook_key`/`hanger_key` (raise on a missing direction), `can_connect`, `crystal_allows`, `pit_barrier`, `collapse_pit_groups` (one representative source per group; raises if a group spans sectors or mixes Blue and Orange barriers). `count_conn_needed_supplied` skips the missing direction.
- `DoorShuffle.main_dungeon_pool_prototype` collapses pit groups after `merge_sectors`.
- `DungeonGenSectorDesc`: a Terminal reaches itself; reaching any group source records the representative (keeping the state that can cross the group barrier); Terminals are excluded from must-access (they are already must-enter).
- `DungeonGenTransitivity`: `door_matches` symmetric via `can_connect`; the special pit branch is gone (standard matching yields falls); `can_fall` checks the group barrier; a fall leaves in the barrier color; crystal back-propagation and the hook-side walk never cross a pit backwards; MustEnter is satisfied only by entering; tallies use `hanger_key`/`hook_key`; transfers and pass-throughs treat a missing direction as impossible; descriptor reachability reads never insert (`.get`); `find_transitivity_solution`/`TransitivitySolution`; general fixes kept: completion checked before `now_impossible`, connected doors not counted as forced.

- `DoorShuffle.link_doors_prep` (classic generation) wires vanilla pits with `connect_terminal_door`, which marks Terminals used. With plain `connect_simple_door`, every landing became an outstanding door with no partner and the legacy generator looped forever at any intensity.
- `DoorFlags.for_player` applies the customizer's intensity everywhere flags are built; `drop_lobbies_locked` keeps drop-down lobbies in their vanilla dungeon unless lobbies and pits both shuffle (the old test treated `pit_warps == 'none'` as enabled, unlocking them at intensity 3).

Further Transitivity changes after the conversion:

- Crystal back-propagation uses the descriptor's arrival state (`c_prop`): a barrier on the way fixes the color, so only an unforced path carries Either. This removed every remaining wrong True in vanilla pairs.
- Pit doors are exempt from two two-way heuristics in `now_impossible`: forced-loop classification and the forced-door cost in the branch balance. `check_for_forced_connections` no longer treats a lone needed Terminal whose feeding pit lies in its own sector as a dead loop.

Search-effort changes:

- Terminals are never merged by `winnow_doors_to_check`: its static shape key ignores which pit sources are still unused behind a landing, so equally shaped Terminals are not interchangeable. This was the main cause of the 20k-iteration cap at intensity 4 (vanilla slow set: about 184,000 `now_impossible` calls down to 4,329).
- `some_door_never_reachable` (relaxed reachability bound, ignoring crystals and partner counts; everything a reached sector could ever reach counts as reachable) prunes states where some remaining door can never be reached.

Results (`PYTHONHASHSEED=0`, seed 1, crossed, experimental; verified = witness checker reports no problems):

| | Intensity 3 | Intensity 4 |
|---|---|---|
| 13 vanilla dungeons | 13 verified | 13 verified |
| 78 vanilla pairs | 78 verified | 78 verified |
| Real LocalSearch calls, seeds 1–12 (every True checked) | 260 calls, 195 True, 0 wrong | 506 calls, 156 True, 0 wrong |
| Seeds whose balancing completes (1–16) | 16 | 12 (the other 4 hit the 20k cap) |
| Small crossed sets vs. exhaustive solver (300 pairable, crystal-free) | 4 of 226 solvable wrongly False (1.8%) | 1 of 185 (0.5%) |
| Seeds 1–16 run through stitching (NewGeneration path) | 11 stitched, 2 stitcher timeouts (Turtle Rock, no pits), 3 hit the 20k cap | 8 stitched, 2 stitcher timeouts, 6 hit the 20k cap (4 in balancing, 2 in the stitcher's portal assignment) |
| Stitched layouts: every region reachable over the applied connections | all | all 8 (58 pit sources connected per seed) |

False verdicts only narrow randomness; the policy is no wrong True anywhere and a wrong-False rate within 3% on the small-set comparison (`TestTransitivityOracle`). No neutral sector holds pit doors (`is_sector_neutral` rejects them), so splicing one-way sectors is not exercised; `TestTerminalGroups` guards that.

Open work, correctness done first:

1. **Search effort.** The 4 intensity-4 seeds (of 16) still capped all end with the only unlanded pit sources being Ice Backwards Room's Blue-gated holes (`Ice Backwards Room Hole`, `Ice Crystal Block Hole`) while that sector is only entered in Orange. The sets may be impossible; no check reasons about which crystal colors remain reachable, so the search cannot prove it. A crystal-aware bound is the next lever and needs a soundness design (switches, back-propagation, Either). Target: generation success no worse than the "2.0.0 2025" tab of the stability matrix (NewGen, 12/10/25, overall 80.95%), measured with `TestSuite.py`. In one environment (Python 3.14 venv) the classic path scores 65.3% on this branch, 64.0% on its base and 65.9% on the sheet's own commit `e0a3c0d8`: the branch is at parity, and the gap to the sheet is environmental. The branch shifts some failures from item fill to "Keylock detected" (68 vs 38 across a full run) without changing the success rate; cause not yet determined.
2. **Stitcher timeouts** ("Generation taking too long", 1000 proposals) occur at both intensities and are not pit-specific so far.

## Pit Model

### Model

A pit/warp is **one directed edge** from a **group source** to a **Terminal**.

- `hook` means "the search can leave through this door" (it is on the reached side); `hanger` means "the search can enter through this door". A connection attaches an unreached hanger to a reached hook.
- Two-way doors have both. A pit has exactly one of each, on different doors:

| Door | hook | hanger |
|---|---|---|
| Hole / Warp (group source) | `Hook.PitWarp` | none — a hole cannot be entered |
| Terminal | none — a terminal cannot be left through | `Hook.PitWarp` |

- The ordinary rule in `find_connectable_doors` ("hanger `d`, reached `available`, `hanger_from_door(d) == hook_from_door(available)`") yields exactly the legal falls: a reached group source onto a free Terminal. There is no pit-specific connection branch.
- A **group is one door in the search.** One representative source door per group is outstanding; its siblings are reached and connected with it. Physical doors reappear only for the stitcher and ROM. Group size never enters a count.
- A missing hook/hanger means *impossible in that direction*. It must never become a key.

### Making two-way assumptions loud

1. **Key helpers that raise.** All tallies and lookups keyed by direction use `hook_key(d)` / `hanger_key(d)`, which raise on `None`. Direct `hook_from_door`/`hanger_from_door` calls remain only where a caller explicitly handles `None` as "impossible". Any missed two-way assumption then fails the vanilla tests with an exception instead of a wrong verdict.
2. **Direction of a connection.** A connection involving a pit door is one-way; `is_one_way(door)` derives that from the door type, so no separate record is kept. Every reverse traversal of `connection_map` (crystal back-propagation, the hook-side walk) checks it and refuses to climb back up a pit. Hook/hanger cannot reveal reverse traversal after connection, so these checks are the only guard for it.

## Stitcher Pit Support (DungeonStitcherV2)

Implemented. Pits and warps share one pool (`Hook.PitWarp`). A pit may land in its own room or sector. ROM output of pit destinations is Phase 5 of `docs/plans/pitwarps_feature.md`; until then intensity 4 builds logic only.

Design:

- **Pit assignments are part of the proposal**, searched and validated jointly with door pairings: which Terminal a group lands on decides which regions are reachable and in which crystal color, and Transitivity's True promises a joint assignment. A pit is a one-way `proposed_map` entry `representative -> Terminal` (no reverse entry), the same shape decoupled doors already use.
- `create_random_proposal` pairs group representatives with Terminals at random (counts equal by Balance; unequal counts raise). `proposal_hash` skips Terminals, which are never keys.
- Exploration resolves a source's target as `terminal.entrance.parent_region` (a Terminal's entrance is not a region exit, so `world.get_entrance` cannot find it). A sibling source follows its representative's assignment; visiting any source marks the representative visited. Each physical source's own crystal barrier applies through the existing `can_traverse`/`append_door_to_list`.
- `modify_proposal` swaps pits as a permutation: a visited group moves onto a Terminal whose landing region was not visited, and that Terminal's former group takes the moved group's old Terminal.
- `create_dungeon` connects every physical source of a group (`group_members`, recorded on the representative by `collapse_pit_groups`) to the landing region, sets `source.dest` and `terminal.dest` to the landing region (as `connect_terminal_door` does for vanilla), and skips the reverse-entry removal for pits.
- The door spoiler lists each shuffled pit (source -> landing region, one-way).
- Verification: after stitching, walk the world graph (applied connections, crystal rules, traps, controller doors) from each builder's non-destination portal lobbies and `default_lobby_drops` regions and require every region. All stitched seeds pass (see Current State).

## Verdict semantics (what "correct" means)

A sector set is transitive when there exists a connection of **all** its outstanding doors such that **every region** is reachable from the start portals.

- Every outstanding door is paired with a compatible door (hook/hanger match).
- Groups and Terminals correspond 1-to-1: all sources sharing a `door.group` land on the same Terminal, and every Terminal receives exactly one group. A mismatch in counts or names means `data/terminals.yaml` is wrong, not the search.
- A Hole/Warp is one-way: reaching it reaches its Terminal's landing region (`terminal.entrance.parent_region`), never the reverse.

Transitivity stops when every door is *reached* (`remaining_doors` empty), leaving some reached doors unpaired. For normal doors this is equivalent to full pairing: LocalSearch only calls Transitivity on sets that already pass Balance (polarity and parity), so leftover reached doors can always be paired among themselves without changing reachability. For pits it is equivalent only if groups stay intact, which the witness checker verifies.

The witness checker walks the world region graph with the crystal rules of `CollectionState.traverse_world` (`valid_crystal`, barrier doors, `c_switch` doors), the descriptor trap rule (`trap_door_mode`), controller/dependent doors (Ice Cross push blocks), dependent portals, and overworld drops. Re-entering a lobby from the overworld resets the crystal state to Orange, even when the lobby was already reached from inside. It ignores key and item requirements.

Consequence for Task 3: randomly sampled subsets do not pass Balance, so the oracle uses the same "every door reached" criterion (plus the group rules) rather than full pairing.

## Tools

Run from the repo root with `PYTHONHASHSEED=0` (door hashing is by name, so set iteration order otherwise varies by process).

| File | Purpose |
|---|---|
| `test/dungeon/transitivity_harness.py` | Captures the real, prepared sector pool by running `Main.main` until `DungeonGenInfo` is built; hard timeouts |
| `test/dungeon/transitivity_witness.py` | Independent checker for the connection plan behind a True: pairing and group rules, world-graph reachability with crystal rules, traps, controller doors, dependent portals, drops |
| `test/dungeon/transitivity_oracle.py` | Exhaustive solver for small sector sets (pairability and portal rules; ignores crystals) |
| `test/dungeon/transitivity_replay.py` | Drives Transitivity along a known-valid vanilla path and reports the first check that rejects a step |
| `test/dungeon/collect_transitivity_corpus.py` | Records every Transitivity call from real LocalSearch runs and checks each True |
| `test/dungeon/TestTransitivityVanilla.py` | Vanilla dungeons and pairs must be True; terminal-group and neutral-sector tripwires |
| `test/dungeon/TestTransitivityWitness.py` | Checker sanity tests, vanilla singles, regression pairs |
| `test/dungeon/TestTransitivityOracle.py` | Small crossed sets vs. the exhaustive solver: no wrong True, wrong False within 3% |
| `test/dungeon/TestDoorFlags.py` | `DoorFlags.for_player` and `drop_lobbies_locked` |

Measure search effort in `now_impossible` calls; wall-clock varies up to 2x on the dev machine.

