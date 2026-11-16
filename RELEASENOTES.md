# Door Randomizer 2.0 (Beta)

## 2.0.1

* Mega-dungeon: `dungeon_bias: random` option; no longer runs out of memory with many key doors
* `smaller_dungeon_gen` option: now settable from the command line and GUI
* Generation: fewer failures at intensity 3 and 4 (running from source: new dependency `clingo`)
* Enemizer: adopted the v32 enemy subtype system
* Customizer: exports include enemies, sprite sheets and drop lobbies
* Customizer fixes: a `text` section stopped the ROM from being created; boss shuffle could place a boss the file already placed; swordless files that place bosses failed to load
* Multiworld: fixed generation with more than one player
* Fixed: the Sanctuary could end up in a Dark World dungeon in open mode without cross-world entrance shuffle
* Fixed: door type only shuffle failed to generate with entrance shuffle, or with `trap_door_mode` `boss` or `oneway`
* All 1.5.10 fixes

## Beta Testing

Please report in #bug-reports, with your spoiler log:
* Any seed you can't beat without glitches
* Key logic that looks wrong, such as a key door you were expected to open without enough keys
