# New Features

FastROM changes have been included now.

## Enemizer Features

Please see this document for extensive details. [Enemizer in DR](https://docs.google.com/document/d/1iwY7Gy50DR3SsdXVaLFIbx4xRBqo9a-e1_jAl5LMCX8/edit?usp=sharing)

Key points:
* Enemizer no longer uses a third party program. It is now built-in.
* New option under Shuffle Enemy Drops: Underworld. Any underworld enemy can drop items.
* New option under Enemizer tab: Enemy Logic

Please read the entire document above for extensive details about enemizer and enemy drop shuffle systems.

Enemizer main changes:
* Several sprites added to the pool. Most notable is how enemies behave on shallow water. They work now.
* Clearing rooms, spawnable chests, and enemy keys drops can now have enemies with specific logic in the room. This logic is controlled by the new Enemy Logic option
* New system for banning enemies that cause issue is place. If you see an enemy in a place that would cause issue, please report it and it can be banned to never happen again. Initial bans can be found [in the code](source/enemizer/enemy_deny.yaml) for the curious
* Thieves are always unkillable, but banned from the entire underworld. We can selectively ban them from problematic places in the overworld, and if someone wants to figure out where they could be safe in the underworld, I'll allow them there once the major problems have been banned.
* THe old "random" and "legacy" options have been discarded for enemy shuffle. Tile room patterns are currently shuffled with enemies.

Underworld drops:
 
* A flashing blue square added to help locate enemies that have remaining drops on the supertile. (Dungeons and caves without a compass get this for free.)
* Flying enemies, spawned enemies, and enemies with special death routines will not drop items.
* Pikits do not drop their item if they have eaten a shield.
* Hovers in swamp waterway do no drop items due to a layer issue that's not been solved.
* Enemies that are over pits require boomerang or hookshot to collect the item
* Enemies behind rails require the boomerang (hookshot can sequence break in certain cases)
* Enemies that spawn on walls do not drop items. (Keese normally don't, but in enemizer these can be valid drops otherwise. The document has a visual guide.)

(Older notes below)

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

### Ganonhunt
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

# Patch Notes

* 1.4.1.11u
  * New Feature: Several spoiler levels added: None, Settings-only, Semi, Full, Debug
    * Semi includes only entrances, prizes, and medallions (potential new spoiler mode being worked on, definition may change)
  * Entrance: Lite/Lean support enemy drop shuffle
  * Standard: Re-added tutorial guard near large rock
  * Enemizer
    * Fixed the overwriting of bonk fairies
    * Fixed broken graphics on hyrule castle
    * Enemy bans
  * Customizer: Fixed bug with customizing prize packs
* 1.4.1.10u
  * Vanilla key logic: Fix for vanilla layout Misery Mire which allows more complex key logic. Locations blocked by crystal switch access are only locked by 2 keys thanks to that being the minimum in Mire to reach one of two crystal switches. 
  * Autotracking: Fix for chest turn counter with chest containing multiworld items (Thanks Hiimcody)
  * Enemizer: Enemy bans
  * Rom: Code prettification and fixing byte designations by Codemann
  * Support added for BPS patches via jsonout setting (Thanks Veetorp!)
* 1.4.1.9u
  * Enemy Drop Underworld: Changed enemy drop indicator to not require compass
  * Experimental: Moved dark world bunny spawns out of experimental. (It is now always on)
  * Fix: Red/Blue pendants were swapped for autotracking. (Thanks Muffins!)
  * Fix: Red square sometimes wasn't blinking
  * Updated tournament winners
  * Enemizer: Enemy bans
* 1.4.1.8u
  * HUD: New dungeon indicators based on common abbreviations 
  * OWG+HMG: EG is allowed to be armed
  * Drop Shuffle: Fixed an issue with minor drops counting for the wrong dungeon
  * Enemizer: Trinexx ice breath should be properly disabled if Trinexx is located outside of Turtle Rock
  * Enemizer: Enemy bans
* 1.4.1.7u
  * Some bugs around Triforce Pieces smoothed out
  * Enemizer: No exception for mimics/eyegores in vanilla rooms if enemy logic is turned to off
  * Enemizer: Various enemy bans
* 1.4.1.6u
  * Difficulty: Fixed some issues around item caps not being respected 
  * Enemezier: Tutorial guards remove from South Kakariko
  * Map: Pendant colors fixed
  * Minor rom code cleanup 
  * Enemizer: Hovers added to problematic pool near pits. Some other bans
* 1.4.1.5u
  * Major Fix: Problem with Ganon's Room sprites
  * HMG: Remove extra Swamp Smalls in the pool due to pottery settings
  * Enemizer: Couple enemy bans
* 1.4.1.4u
  * Logic: Fixed logic bugs surrounding dynammic doors missing logic from big keys and other door types 
  * Inverted: Castle warp should not appear after defeating Aga 1
  * Enemzier: Fixed a crash with cached sprites Zora/Swamola 
* 1.4.1.3v
  * Enemizer: Raven/Murderdactyls using the correct damage table 
  * Enemzier: Boss drops only center when boss shuffle is on
* 1.4.1.2v
  * Expert/Hard Item Pool: Capacity fairy no longer gives out free crystal
  * Vanilla door + Universal Keys: Generation fixed
  * Boss Shuffle: Generation fixed (thanks Codemann for easy solution)
  * Vanilla ER: No need for ability to check prizes on keysanity menu
  * Swapped ER: Possible generation issue fixed (thanks Codemann)
  * Enemizer: Roller ban
  * Performance: Faster text boxes. Thanks Kan!
* 1.4.1.1v
  * Logic: Moon pearl logic respects blocked doors 
* 1.4.1.0v
  * World Model Refactor: The overworld has been split up by screen, brings OR and DR a bit closer together in the model sense. A few OWG clips have been rewritten to fit into this new logic better.
  * Logic: New logic for some bosses on ice
    * Helmasaur on Ice: Bombs for mask, sword or arrows for 2nd phase
    * Blind on Ice: Beam sword, Somaria, or Byrna plus magic extension for damage. Red shield or Byrna for protection.
    * Kholdstare on Ice: Three options (after cracking the shell)
      * Beam sword
      * Fire Rod with 1.5 magic extensions
      * Fire Rod & Bombos & any Sword & 1 Magic Extension
    * Vitreous on Ice: Arrows and Bombs or a Beam Sword
    * Trinexx on Ice: Boots always required for dodging. Damage options:
      * Gold sword
      * Tempered sword with magic extension
      * Hammer or Master sword with 3 magic extensions (Rod spam for elemental heads, non-ideal weapon for last phase)
    * Trinexx on Ice forbidden in doors seeds until we can model some health requirements. Low health Trinexx still isn't realistically feasible (bascially playing OHKO)
  * Logic: Added silver arrows as Arrghus damage option when item functionality is not set to hard or expert
  * Logic: Byrna not in logic for laser bridge when item functionality is set to hard or expert   
  * Enemizer Damage Rework:
    * Shuffled: Actually shuffles the damage groups in the table instead of picking random numbers and reducing for mails from there. Enemies will still be assigned to a damage group randomly.
    * There will always be at least one group which does no damage. The thief will always be in that group. Ganon always has his own group.
  * Glitched modes: Aga 1 should be vulnerable in rain state for glitched modes
  * Generation: Trinexx and Lanmolas room allowed as lobbies in intensity 3 (works with enemizer now)
  * Enemy AI: Terrorpin AI code removed. May help with unusual enemy behavior?
* 1.4.0.1v
  * Key logic: Vanilla key logic fixes. Statically set some HC logic and PoD front door
  * Generation: Fix a broken tile pattern
  * Inverted: Castle warp should not appear after defeating Aga 1
  * Murahdahla: Should not disappear after Aga 1. May fix other subtle issues.
  * Shopsanity: Buying multiple of an item in the potion shop should no longer increase item count.
* 1.4.0.0v
  * Initial support for HMG (Thanks Muffins!)
  * Generation: fix for bunny walk logic taking up too much memory
  * Key Logic: Partial is now the new default
  * Enemizer: enemy bans
* 1.3.0.9v
  * ER: New Swapped ER mode borrowed from OWR
  * ER: fixed a generation error where TR chooses all "must-exits"
  * Ganonhunt: playthrough no longer collects crystals
  * Vanilla Fill: Uncle weapon is always a sword, medallions for Mire/TR will be vanilla
  * Customizer: support shufflebosses/shuffleenemies as well as boss_shuffle/enemy_shuffle
  * Enemizer: enemy bans
* 1.3.0.8v
  * Enemizer: Red Mimics correctly banned from challenge rooms in appropriate logic setting
  * No Logic Standard ER: Rain doors aren't blocked if no logic is enabled.
  * Trinexx: attempt to fix early start
  * MW Progression Balancing: Change to be percentage based instead of raw count. (80% threshold)
  * Take anys: Good Bee cave chosen as take any should no longer prevent generation
  * Money balancing: Fixed generation issue  
  * Enemizer: various enemy bans
* 1.3.0.7v
  * Fix for Mimic Cave enemy drops
  * Fix for Spectacle Rock Cave enemy drops (the mini-moldorms)
  * Fix for multiworld lamps with incorrect graphics
  * No longer shuffles fairy bonks (from trees) as part of Enemizer
* 1.3.0.6v
  * Flute can't be activated in rain state (except glitched modes) (Thanks codemann!)
  * Enemizer
    * Arrghus at Lanmo 2 no longer prevents pot pickups
    * Trinexx at Lanmo 2 requires the Cape go backwards to face him
    * Lift-able Blocks require a sprite slot (should help reduce problems)
  * Fixed logic issues:
      * Self-locking key not allowed in Sanctuary in standard (typo fixed)
      * More advanced bunny-walking logic in dungeons (multiple paths considered)
  * ER: Minor fix for Link's House on DM in Insanity (escape cave should not be re-used)
  * MSU: GTBK song fix for DR (Thanks codemann!)
  * District Algorithm: Fails if no available location outside chosen districts
  * Various enemy bans
    * More Gibos near kiki and Old Man
    * Bumper/AntiFairy obstacles
    * Damaging roller
    * Statue + Pots don't mix
    * Statues on Skull Big Key Chest tile  
    * Toppo in challenge rooms
    * Misc others
* 1.3.0.5v
  * Hud/Map Counter: Collecting a keys for this dungeon of a bonk torch no longer increments the counter twice and immediately updates the hud.  
  * Enemizer: Hera basement item counting twice fixed by banning wallmasters on the tile.
  * Enemizer: Statues banned offscreen for pull switches 
  * Enemizer: Several sprite producing enemies have been limited on crowded tiles. Offenders: Hinox, Sluggula, Bomb Guard, Beamos, Gibo, Wall Cannons, Probe using Guards. Others do not spam as many projectiles.
  * Enemizer: More enemy bans (mostly Wizzrobes near walls where they won't spawn, couple missed firebar spots)
* 1.3.0.4v
  * Enemizer: The bunny beam near Lanmo 2 and the 4 fairies near Ice Armos are not shuffled anymore. This is due to how bosses shuffle works and since it cannot be guaranteed to work within the current system, they are vanilla. (Vitreous still overwrites the fairies and Arrghus only lets two spawn, etc.)
  * Dropshuffle: Pokey 1 has been fixed to drop his item
  * Mystery/Customizer: true/false and on/off in yaml files should behave the same.
  * More enemy bans as have been reported
* 1.3.0.3v
  * Faeries now part of the enemy shuffle pool. Take note, this will increase enemy drop locations to include fairy pools both in dungeons and in caves.
  * Enemy drop indicator (blue square) now works in caves based on entrance used
  * Fixes:
    * Collection rate counter is properly hidden in mystery seeds
    * Sprite limit lowered where possible to allow for lifting of pots
    * Hovers in Swamp Waterway properly do not drop items anymore
    * Lots more bans (thanks to jsd in particular but also thanks to all the reports)
    * Minor issue with customizer/mystery files not allowing "true" for booleans
* 1.3.0.2v
  * Fix for multiworld received keys not counting correctly
  * Fix for multiworld lamps incorrect graphics
  * Fix for collection rate decreasing on item "pickup"
  * Fix for pendants as prizes counting as items
  * Fix for castle barrier gfx in rain state
  * Enemizer fixes and bans:
    * Fixed a generation issue where ChainChomp placement would cause a failure. (Invincible enemies banned in Sprial Cave for early game traversal for now)
    * Skull Pot Prison should not be blocked by "impassable" enemies
    * Bumpers banned in Ice Hookshot room
    * Fixed issue in GT Spike Crystal room
    * Fixed blockage issues in TT Ambush and Compass rooms
    * Forbid Bumper in Fairy Ascension cave; needed to clip into wall weirdly to pass.
  * Enemy Drop bans
    * Forbid Stals in many places where they cannot be woken up. Behind rails and on top of blocks, for example.
    * A couple minor wizzrobes bans because of despawns.
    * Enemies over pits and on conveyors near pits have been issued standard bans for falling enemies. Mimics join the ranks here as they don't work well on pits or on conveyors.
    * Mimics banned where conveyors touch walls and could clip out unintentionally
* 1.3.0.1v
  * Fixed bugs with item duping and disappearing drops
  * Fixed multiworld crash
  * Fixed assured sword missing when using start inventory (via GUI/CLI)
  * Forbid extra statues in Swamp Push Statue room
  * Forbid bumpers on OW water
  * Forbid Stal on pits
  * Text fix on sprite author (thanks Synack)
* 1.2.0.23u
  * Generation: fix for bunny walk logic taking up too much memory
  * Key Logic: Partial is now the new default
* 1.2.0.22u
  * Flute can't be activated in rain state (except glitched modes) (Thanks codemann!)
  * ER: Minor fix for Link's House on DM in Insanity (escape cave should not be re-used) 
  * Logic issues:
    * Self-locking key not allowed in Sanctuary in standard (typo fixed)
    * More advanced bunny-walking logic in dungeons (multiple paths considred)
  * MSU: GTBK song fix for DR (Thanks codemann!)
* 1.2.0.21u
  * Fix that should force items needed for leaving Zelda's cell to before the throne room, so S&Q isn't mandatory
  * Small fix for Tavern Shuffle (thanks Catobat)
  * Several small generation fixes 
* 1.2.0.20u
  * New generation feature that allows Spiral Stair to link to themselves (thank Catobat)
  * Added logic for trap doors that could be opened using existing room triggers
  * Fixed a problem with inverted generation and the experimental flag
  * Added a notes field for user added notes either via CLI or Customizer (thanks Hiimcody and Codemann)
  * Fixed a typo for a specific pot hint
  * Fix for Hera Boss music (thanks Codemann)
* 1.1.6 (from Stable)
    * Minor issue with dungeon counter hud interfering with timer
* 1.2.0.19u
  * Added min/max for triforce pool, goal, and difference for CLI and Customizer. (Thanks Catobat)
  * Fixed a bug with dungeon generation
  * Multiworld: Fixed /missing command to not list all the pots
  * Changed the "Ganonhunt" goal to use open pyramid on the Auto setting
  * Customizer: Fixed the example yaml for shopsanity
* 1.2.0.18u
  * Fixed an issue with pyramid hole being in logic when it is not opened.
  * Crystal cutscene at GT use new symmetrical layouts (thanks Codemann)
  * Fix for Hera Boss music (thanks Codemann)
  * Fixed an issue where certain vanilla door types would not allow other types to be placed.
  * Customizer: fixed an issue where last ditch placements would move customized items. Those are now locked and the generation will fail instead if no alternatives are found.
  * Customizer: fixed an issue with assured sword and start_inventory
  * Customizer: warns when trying to specifically place an item that's not in the item pool
  * Fixed "accessibility: none" displaying a spoiling message
  * Fixed warning message about custom item pool when it is fine
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