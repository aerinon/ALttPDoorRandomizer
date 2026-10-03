# Standard Escape in Transitivity

Transitivity accepts Hyrule Castle Dungeon sector sets in standard mode that the stitcher cannot realize, because only the
stitcher knows the escape route. The stitcher then exhausts its proposals and raises "Generation taking too long. Ref
Hyrule Castle Dungeon". This plan teaches Transitivity the escape requirement.

## Requirement

The mirror scroll returns Link to the last save point, Cellblock or Throne Room. The logic assumes Link can always get
back to the lobby, so a one-way on the way back would make an escape item missable. In the Hyrule Castle Dungeon builder
in standard mode:

- the south lobby reaches every region (the existing Transitivity check);
- Cellblock reaches the lobby and Throne Room;
- Throne Room reaches the lobby or Cellblock.

One-ways elsewhere are fine: they may lead to dead ends or loops, and the mirror scroll returns Link.

**Equivalent form.** Given the lobby reaches everything, the requirement holds exactly when every region is reachable
from each of three roots: the lobby, Cellblock and Throne Room. Every step of the argument follows edges forward:
Cellblock → lobby → everything, and Throne Room → (lobby or Cellblock) → everything. The converse is immediate. This is
the property Transitivity already checks for one root, applied to three.

The stitcher's paths in `DungeonStitcherV2.determine_paths_for_dungeon` encode the same requirement and stay as they are.

## Scope rule

Only the Hyrule Castle Dungeon builder in standard mode changes. Everything new is gated on `c_info.escape`, which is set
only for that builder when `flags.std_flag` is set. Any change in behavior outside standard is a bug.

## Design

The requirement is checked on Transitivity's witnesses by `EscapeCheck` (`DungeonGenTransitivity.py`), built only for
the Hyrule Castle Dungeon builder in standard.

- **Walk.** It starts from Cellblock and from Throne Room, using an exploration of the root region. It crosses only
  connections the witness made (`connection_map`). It enters each sector through its directional
  `descriptor.reachability`, carrying crystal state the way `connect_door` does. Region targets are read from the
  descriptor's exploration of the entered door (`state_cache[door].visited_map`). The lobby is the region the South
  portal leads into. A door the descriptor never explored as an entry (a pit or warp source) is never entered, so a
  walk cannot climb a pit.
- **Completion.** `Transitivity.is_complete` adds the walk to the existing test. A complete state that fails it goes
  back on the queue, where its reached-but-unpaired doors can still be paired.
- **Pruning.** `now_impossible` runs the walk optimistically: a door not yet connected may lead into any unconnected
  door in `door_matches`. That is an over-approximation, so a state it rejects has no valid completion.
- **Crystal state.** Walks start in Orange (`ESCAPE_START_COLORS`). A mirror scroll respawn resets the crystal state to
  Orange (confirmed by the ROM side). Adding Blue would also require each path to work from Blue; that would be nice to
  have, but it is not required.

Roots are tracked by the walk alone; the search's moves, scoring and priority are unchanged. Scoring connections that
extend Cellblock or Throne Room and weighting unmet requirements in `priority()` were tried and had no measurable
effect: unrelated options score as high, and the requirements stay unmet until nearly the whole layout is built.

## Results

Standard, crossed, seeds 1–100, stopped after doors:

| | Before | After |
|---|---|---|
| Intensity 1 | 95 | 97 |
| Intensity 3 | 73 | 82 |
| Hyrule Castle "Generation taking too long" | 13 | 0 |

- Of the 23 recorded Hyrule Castle stitcher failures, 15 no longer fail.
- Open mode at intensities 1 and 3 (60 seeds each) gives the same door layout hash per seed before and after.
- Intensity-3 seeds 51 and 74 passed before and now hit the 20k cap in the Hyrule Castle Dungeon check. On seed 74 a
  valid layout exists (the old stitcher built one); the search does not find it within the cap.

## Known follow-ups

- **Search cost.** Seeds 51 and 74 above. They belong with the general Transitivity cap work.
- **Descriptor/stitcher disagreement.** Recorded seed 687172270 (crossed i2, vanilla entrances, keysanity, key drops):
  Transitivity accepts a witness that meets the escape. The stitcher's exploration of that same witness also meets every
  escape path. But from the lobby the stitcher cannot reach Desert Tiles 2, Desert Wall Slide, or most of GT Warp Maze
  and Double Switch, which the descriptors say are reachable. This is a wrong True from the base check, independent of
  the escape.
- **Hyrule Castle Sewers caps.** Six in the intensity-3 standard sweep, unchanged by this work.

## Verification

- `test/dungeon/TestStandardEscape.py`: seed 382466786 (crossed i1, vanilla entrances, shopsanity) is rejected by
  Transitivity on both passes (its Cellblock can only attach to GT Four Torches, which Bob's Room drops into but never
  leads back from), and its stitched layout satisfies `EscapeCheck`.
- `gen_check.py replay` on the recorded Hyrule Castle failures and before/after `sweep` in standard, `--stop doors`.
- Scope: per-seed layout hashes in open mode, before and after, must be identical.
