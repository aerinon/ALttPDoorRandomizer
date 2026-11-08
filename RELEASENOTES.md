# Door Randomizer 2.0 (Beta)

A new dungeon generator, now the default. See [NewGeneration](https://github.com/aerinon/ALttPDoorRandomizer/blob/NewGeneration/docs/NewGeneration.md) for details.

## New Features

* New dungeon generation algorithm: higher generation rates across the board, rewritten key logic
* Intensity 4 (experimental): pits and warps are now able to be shuffled
* Mega-dungeon option: choose a dungeon to get tons of rooms
* Smaller dungeons option: leave out empty filler rooms for tighter dungeons
* More door shuffle options: door type only shuffle, paired dungeons, and door type distribution
* Customizer: choose which dungeons mix, force rooms into dungeons, pick which connections shuffle. Custom rooms, text, and more from recent Limited Run

## Beta Testing

Please report in #bug-reports, with your spoiler log:
* Any seed you can't beat without glitches
* Key logic that looks wrong, such as a key door you were expected to open without enough keys

## Fixes

* Bunny logic generation hangs
* Inverted bomb shop placement issues
* All 1.5.9 fixes

## Compatiblity Note

* New defaults: `dungeon_shuffle_algorithm: experimental`, `key_logic_algorithm: experimental`, `intensity: 3`. Use `classic`, `partial` and `2` for 1.5 behavior
* `door_type_mode: chaos` is now `door_type_distribution: chaos`
