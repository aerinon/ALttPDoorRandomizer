# New Features

One major change with this update is that big key doors and certain trap doors are no longer guaranteed to be vanilla in Dungeon Door Shuffle modes even if you choose not to shuffle those types. A newer algorithm for putting dungeons together has been written and it will remove big key doors and trap doors when necessary to ensure progress can be made.

Please note that retro features are now independently customizable as referenced below. Selecting Retro mode or World State: Retro will change Bow Mode to Retro (Progressive). Take Anys to Random, and Small Keys to Universal.

## Flute Mode

Normal mode for flute means you need to activate it at the village statue after finding it like usual.
Activated flute mode mean you can use it immediately upon finding it. the flute SFX plays to let you know this is the case.

## Bow Mode

Four options here:

* Progressive. Standard progressive bows.
* Silvers separate. One bow in the pool and silvers are a separate item.
* Retro (progressive). Arrows cost rupees. You need to purchase the single arrow item at a shop and there are two progressive bows places.
* Retro + Silvers. Arrows cost rupees. You need to purchase the single arrow item or find the silvers, there is only one bow, and silvers are a separate item (but count for the quiver if found).

## Dungeon Shuffle Features

### Small Keys

There are three options now available:

* In Dungeon: The small key will be in their own dungeon
* Randomized: Small keys can be shuffled outside their own dungeon 
* Universal: Retro keys without the other options

### Dungeon Door Shuffle

New mode: Partitioned. Partly between basic and crossed, dungeons are shuffled in 3 pools:

* Light World dungeons, Hyrule Castle and Aga Tower are mixed together
* Palace of Darkness, Swamp Palace, Skull Woods, and Thieves Town are mixed together 
* The other dark world dungeons including Ganons Tower are mixed together

### Door Types to Shuffle

Four options here, and all of them only take effect if Dungeon Door Shuffle is not Vanilla:

* Small Key Doors, Bomb Doors, Dash Doors: This is what was normally shuffled previously
* Adds Big Keys Doors: Big key doors are now shuffled in addition to those above, and Big Key doors are enabled to be on in both vertical directions thanks to a graphic that ended up on the cutting room floor. This does change
* Adds Trap Doors: All trap doors that are permanently shut in vanilla are shuffled.
* Increases all Door Types: This is a chaos mode where each door type per dungeon is randomized between 1 less and 4 more.

Note: Boss Trap doors are removed currently and not added into the trap door pool as extra trap doors. This may not be a permanent change

### Decouple Doors

This is similar to insanity mode in ER where door entrances and exits are not paired anymore. Tends to remove more logic from dungeons as many rooms will not be required to traverse to explore. Hope you like transitions.

## Customizer

Please see [Customizer documentation](docs/Customizer.md) on how to create custom seeds.

## New Goals

### Triforce Hunt + Ganon
Collect the requisite triforce pieces, then defeat Ganon. (Aga2 not required). Use `ganonhunt` on CLI

### Completionist
All dungeons not enough for you? You have to obtain every item in the game too. This option turns on the collection rate counter and forces accessibility to be 100% locations. Finish by defeating Ganon.


## Standard Generation Change

Hyrule Castle in standard mode is generated a little differently now. The throne room is guaranteed to be in Hyrule Castle and the Sanctuary is guaranteed to be beyond that. Additionally, the Mirror Scroll will bring you back to Zelda's Cell or the Throne Room depending on what save point you last obtained, this is to make it consistent with where you end up if you die. If you are lucky enough to find the Mirror, it behaves differently and brings you the last entrance used - giving you more options for exploration in Hyrule Castle.

## ER Features

### New Experimental Algorithm

To accommodate future flexibility the ER algorithm was rewritten for easy of use. This allows future modes to be added more easily. This new algorithm is only used when the experimental flag is turned on.

### Lite/Lean ER (Experimental required)

Designed by Codemann, these are available now (only with experimental turned on - they otherwise fail)

#### Lite
- Dungeon and multi-entrance caves can only lead to dungeon and multi-entrance caves
- Dropdowns can only lead to dropdowns, with them staying coupled to their appropriate exits
- Cave entrances that normally lead to items can only lead to caves that have items (this includes Potion Shop and Big Bomb Shop)
- All remaining entrances remain vanilla
- Multi-entrance caves are connected same-world only
- LW is guaranteed to have HC/EP/DP/ToH/AT and DW: IP/MM/TR/GT
- Shop locations are included in the Item Cave pool if Shopsanity is enabled
- Houses with pots are included in the Item Cave pool if Pottery is enabled

#### Lean
- Same grouping/pooling mechanism as in Lite ER
- Both dungeons and connectors can be cross-world connections
- No dungeon guarantees like in Lite ER

### Back of Tavern Shuffle (Experimental required)

Thanks goes to Catobat which now allows the back of tavern to be shuffled anywhere and any valid cave can be at the back of tavern with this option checked. Available in experimental only for now as it requires the new algorithm to be shuffled properly.

#### Take Any Caves

These are now independent of retro mode and have three options: None, Random, and Fixed. None disables the caves. Random works as take-any caves did before. Fixed means that the take any caves replace specific fairy caves in the pool and will be at those entrances unless ER is turned on (then they can be shuffled wherever). The fixed entrances are:

* Desert Healer Fairy
* Swamp Healer Fairy (aka Light Hype Cave)
* Dark Death Mountain Healer Fairy
* Dark Lake Hylia Ledge Healer Fairy (aka Shopping Mall Bomb)
* Bonk Fairy (Dark)

# Bug Fixes and Notes

* 1.2.0.17u
  * Fixed logic bug that allowed Pearl to be behind Graveyard Cave or King's Tomb entrances with only Mirror and West Dark World access (cross world shuffles only) 
  * Removed backup locations for Dungeon Only and Major Only algorithms. If item cannot be placed in the appropriate location, the seed will fail to generate instead 
  * Fix for Non-ER Inverted Experimental (Aga and GT weren't logically swapped)
  * Fix for customizer setting crystals to 0 for either GT/Ganon
* 1.2.0.16u
  * Fix for partial key logic on vanilla Mire
  * Fix for Kholdstare Shell collision when at Lanmo 2
  * Fix for Mire Attic Hint door (direction was swapped)
  * Dungeon at Chest Game displays correctly on OW map option
* 1.2.0.15u
  * GUI reorganization
  * Logic fix for pots in GT conveyor cross
  * Auto option for pyramid open (trinity or ER + crystals goal)
  * World model refactor (combining inverted and normal world models)
  * Partitioned fix for lamp logic and links house
  * Fix starting flute logic
  * Reduced universal keys in pool slightly for non-vanilla dungeons
  * Fake world fix finally
  * Some extra restrictions on links house placement for lite/lean
  * Collection_rate works in customizer files
* 1.2.0.14u
  * Small fix for key logic validation (got rid of a false negative)
  * Customized doors in ice cross work properly now
* 1.2.0.13u
  * Allow green/blue potion refills to be customized
  * OW Map showing dungeon entrance at Snitch Lady (West) fixed (instead of @ HC Courtyard)
  * Standing item data is cleared on transition to overworld (enemy drops won't bleed to overworld sprites)
  * Escape assist won't give you a free quiver in retro bow mode 
  * Fixed an issue where a door would be opened magically (due to original pairing)
  * MultiServer can now disable forfeits if desired
* 1.2.0.12u
  * Fix for mirror portal in inverted
  * Yet another fix for blocked door in Standard ER
* 1.2.0.11u
  * Fixed an issue with lower layer doors in Standard
  * Fix for doors in cave state (will no longer be vanilla)
  * Added a logic rule for th murderdactyl near bumper ledge for OHKO purposes
  * Enemizer alteration for Hovers and normal enemies in shallow water
  * Fix for beemizer including modes with an increased item pool 
  * Fix for district algorithm
* 1.2.0.10u
  * Fixed overrun issues with edge transitions
  * Better support for customized start_inventory with dungeon items
  * Colorized pots now available with lottery. Default is on.
  * Dungeon_only support pottery
  * Fix AllowAccidentalGlitches flag in OWG
  * Potential fix for mirror portal and entering cave on same frame
  * A few other minor issues, generation and graphical
* 1.2.0.9-u
  * Disallowed standard exits (due to ER) are now graphically half blocked instead of missing
  * Graphical issues with Sanctuary and Swamp Hub lobbies are fixed
  * Fixes an issue surrounding door state and decoupled doors leading to blocked doors
  * Customizer improvements:
    * Better logic around customized lobbies
    * Better logic around customized door types
  * Fix to key doors that was causing extra key doors
  * Generation improvement around crystal switches
  * Fix bug in dungeon_only that wasn't using pot key locations (known issue still exists in pottery modes)
  * Fixes for multiworld:
    * Fixes an issue when keys are found in own dungeon for another player when using the bizhawk plugin.
    * Fixes an issue with absorbables for another player also being received by the player picking it up.
* 1.2.0.8-u
  * New Features: trap_door_mode and key_logic_algorithm 
  * Change S&Q in door shuffle + standard during escape to spawn as Uncle
  * Fix for vanilla doors + certain ER modes
  * Fix for unintentional decoupled door in standard
  * Fix a problem with BK doors being one-sided
  * Change to how wilds keys are placed in standard, better randomization
  * Removed a Triforce text
  * Fix for Desert Tiles 1 key door
* 1.2.0.7-u
  * Fix for some misery mire key logic
  * Minor standard generation fix
  * Fix for inactive flute start
  * Settingsfile for multiworld generation support
  * Fix for duped HC/AT Maps/Compasses
* 1.2.0.6-u
  * Fix for light cone in Escape when entering from Dark World post-zelda
  * Fix for light cone in Escape when lighting a torch with fire rod
* 1.2.0.5.u
  * Logic fix for Sanctuary mirror (it wasn't resetting the crystal state) 
  * Minor bugfixes for customizer
* 1.2.0.4-u
  * Starting inventory fixes if item not present in the item pool.
  * Support for Assured sword setting and OWG Boots when using a custom item pool. (Customizer or GUI)
  * Logic fix for the skull woods star tile that lets you into the X pot room. Now accounts for small key or big key door there blocking the way from the star tile. A trap door is not allowed there.
  * Standard logic improvement that requires a path from Zelda to the start so that you cannot get softlocked by rescuing Zelda. Standard mirror scroll change may need to be reverted if impossible seed are still generated.
* 1.2.0.3-u
  * Starting inventory taken into account with default item pool. (Custom pools must do this themselves)
  * Fast ROM update
  * Fix for restricted boss item counting maps & compasses as vital 
  * Bug fix for vanilla ER + inverted + experimental
* 1.2.0.2-u
  * Fixed a bug with certain trap doors missing
  * Added a hint reference for district hints
* 1.2.0.1-u
  * Added new ganonhunt and completionist goals 
  * Fixed the issue when defeating Agahnim and standing in the doorway can cause door state to linger.
  * Fix for Inverted Lean/Lite ER
  * Fix for vanilla Doors + Standard + ER
  * Added a limit per dungeon on small key doors to ensure reasonable generation
  * Fixed many small bugs

# Known Issues

* Decoupled doors can lead to situations where you aren't logically supposed to go back through a door without a big key or small key, but you can if you press the correct direction back through the door first. There are some transitions where you may get stuck without a bomb. These problems are planned to be fixed.
* Logic getting to Skull X room may be wrong if a trap door, big key door, or bombable wall is shuffled there. A bomb jump to get to those pot may be required if you don't have boots to bonk across.