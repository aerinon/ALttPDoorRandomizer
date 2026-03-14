# Past Feature Notes

1.5.0
* Enemy Drop: Added "spies" and shadows for hidden enemies when enemy drop shuffled is enabled
* Pottery: Pots will uncolor when the item inside is collected next time the room is loaded

1.4.3
* File Select/End Game screen: Mirror Scroll and Pseudoboots added (Thanks Hiimcody!)

# Patch Notes

Changelog archive
* 1.5.5
  * Logic: Fixed an issue where PoD Bridge lead to Arena Main instead of Arena Landing Area. (Potentially unnecessarily requiring bombs or Somaria to progress)
  * HUD: Key counters are correct even when door shuffle is off
* 1.5.4
  * Documentation: New AI-assisted documentation [Site](https://aerinon.github.io/ALttPDoorRandomizer)
  * Generation Error: Fixed Issue with Shop Code and Take Any Caves (thanks Codemann for assistance)
* 1.5.3
  * Logic: Key logic fix for part of a dungeon located at Skull 3 (or other similar restricted entrancs). Appropriate key logic was not being applied, causing progression issues. This mostly affect crosskey style seeds.
  * Standard: Rupee balancing algorithm can no longer switch out the weapon on uncle for money.
  * Dungeon Counters: Some fixes for inconsistent tracking and display of dungeon counters on the keysanity menu.
  * Text: Updated main tournament winner (Thanks clearmouse!)
* 1.5.1
  * Bugfix: Fixed an issue with keys not counting correctly
* 1.5.0
  * Logic: Fixed vanilla key logic for GT basement
  * Logic (Playthrough): Fixed an issue where enemy kill rules were not applied during playthrough calculation. (Thanks Catobat for the catch)
  * Keysanity/Keydrop Menu for DR:
    * Map key information is now controlled by the Dungeon Chest Counts setting. If set to always on, this information will be available right away in the menu and will be on the HUD even when the map is not obtained.
    * The key counter on the HUD for the current dungeon now accounts for keys from enemies or pots that are from vanilla key locations.
    * The first number on the HUD represents all keys collected either in that dungeon or elsewhere.
    * The second number on the HUD is the total keys that can be collected either in that dungeon or elsewhere.
    * The key counter on inside the Menu is unchanged. (At the bottom near A button items)
    * The first number in the Menu is the current number of keys in your inventory
    * The second number is how many keys left to find in chests (not those from pots/enemies unless those item pools are enabled)
  * Customizer: free_lamp_cone option added. The logic will account for this, and place the lamp without regard to dark rooms.
  * Customizer: force_enemy option added that makes all enemies the specified type if possible. There are known gfx glitches in the overworld.
  * Optimization: Improved generation performance (Thanks Catobat!)
* 1.4.11
  * Rom fixes (all thanks to Codemann, I believe)
    * Pot bug when at sprite limit
    * Kodongo AI vanilla in vanilla rooms
    * Issue with music silencing across certain room transitions
  * Glitched: Some HMG logic fixed. Thanks Muffins! (Sorry it took me forever to get this PR in)
  * Glitched: Blind fight VRAM fix. Thanks Mufffins!
  * Text: Updated tourney winners. Thanks clearmouse!
  * Enemizer: Banned Swamola enemy everywhere as they may be causing crashes
  * Enemizer: Enemy bans from Q2 and Q3. Thank you for all the reports.
* 1.4.10
    * Logic: Changed the rule surrounding the Bumper Cave Ledge Drop (the murderdactyl) to only require Pearl AND (Cape OR Byrna OR a Sword) in OHKO mode for now. This is a temporary solution until a better way to prevent needing to use a framerule to get past the bird is invented.
    * Helmacopter Fix.
    * Fixed a bug in shopsanity that caused the generation to fail with certain prices.
    * Enemizer: fairies were invalid on the overworld (unless a bonk occurred nearby), so they will no longer be randomized there.
* 1.4.9
    * Attempted fix for Moth conveyor room timing. Thanks for many people's input. Unsure if Helmacopter is still acceptable.
    * Mirror scroll will show up on file start screen if enabled (thanks Clearmouse!)
    * Fixes for HMG by Muffins
    * Various fixes for Enemizer by Codemann (gfx fixes, more randomization options)
    * Vanilla door shuffle prevents big key doors changes from door_type_mode
    * Couple of minor fixes to custom generation. Deals with a complete specification of all dungeons
    * Various enemizer bans for blocked paths (thanks to all the reports, Q1 2025)
* 1.4.8.1
    - Fixed broken doors generation
    - Fixed bomb/arrow upgrade ignoring custom pricing
    - Extended `money_balance` to apply to price balancing for non-custom shops.
* 1.4.8
    - New option: Mirror Scroll - to add the item to the starting inventory in non-doors modes (Thanks Telethar!)
    - Customizer: Ability to customize shop prices and control money balancing. `money_balance` is a percentage betwen 0 and 100 that attempts to ensure you have that much percentage of money available for purchases. (100 is default, 0 essentially ignores money considerations)
    - Fixed a key logic bug with decoupled doors when a big key door leads to a small key door (the small key door was missing appropriate logic)
    - Fixed an ER bug where Bonk Fairy could be used for a mandatory connector in standard mode (boots could allow escape to be skipped)
    - Fixed an issue with flute activation in rain mode. (thanks Codemann!)
    - Fixed an issue with enemies in TR Dark Ride room not requiring Somaria. (Refactored the room for decoupled logic better)
    - More HMG fixes by Muffins
    - Fixed an issue with multi-player HMG
    - Fixed an issue limiting number of items specified in the item pool on the GUI
    - Minor documentation fixes (thanks Codemann!)
* 1.4.7.2
    - Fixed an issue with shuffle_ganon/fix_gtower_exit causing a generation failure
    - More HMG fixes by Muffins
* 1.4.7.1
    - Fixed an issue with the repaired "beemizer" setting not being backwards compatible
* 1.4.7
    - Fixed generation error with Big Key in starting inventory (thanks Cody!)
    - HMG/NL logic fixes by Muffins
    - Enemizer: Disabled Walking Zora in the UW due to crash with Swamola (they ignore a lot of collison anyway)
    - Enemizer: Fixed an issue with enemizer bush sprites
    - Enemizer: Banned new Mimics from being the randomized bush sprite due to crash
    - "Beatable" or "accessibility: none" can now use randomized trap doors to seal off entire parts of dungeons (was intended, bug prevented the logic skip)
    - Logic error with enemizer and standard should use new enemy logic rules
    - Fixed a bug with the inconsistent treatment of the beemizer setting
    - Fixed an issue with returning Blacksmith in Simple shuffle (when blacksmith is at Link's House)
    - Fixed an issue with dark sanctuary spawn at tavern north door (thanks Codemann!)
    - Various enemy bans for the last few months
* 1.4.6
    - Restores original Sanc & Quit behavior, if Aga1 is not dead, then no quick pyramid warp
    - Fixed problem with Lite/Lean shuffling some fairy caves unnecessarily
    - The 300 Rupees item is now marked as priority, so it will not be used as GT junk fill (this matches a change in the VT randomizer)
    - Murahdahla is now logically accessible in inverted mode as a bunny. May affect some beatable-only TFH seeds by allowing Moon Pearl to be inaccessible.
    - Fixed an issue around PreferredLocationGroups in customizer which would not work with pre-activated Ocraina or priority items.
    - Minor fix on triforce text
    - Enemy bans for poor placements
* 1.4.5
    - Logic: Added appropriate enemy logic to GT Mimics 1 and 2 rooms
    - Logic: Added appropriate enemy logic to Mire 2 room. Note this does change the default logical strats, due to how enemy kill logic works.
        - Ice Rod + 1 Bomb is now out of logic
        - Fire Rod + 1 Bomb is now out of logic
        - Fire Rod + 1 magic extension is still in logic
        - Byrna + 1 magic extension is newly in logic

      (One magic extension is either half magic or a bottle with the ability to purchase a blue or green potion) In general, making up for a lack of magic extension with a few bombs is something that could be added to the logic. Using the ice rod to freeze an enemy and then using that enemy to deal blunt damage and then using bombs to clear the frozen enemy is another strategy that could be added to the logic someday. If these are important to you, let me know.
    - Generation: Fixed an issue with dungeonsfull shuffle
* 1.4.4
    - Fixed a crash near the end of the credits when total collection rate was over 1000
* 1.4.3
    * Key Logic Algorithm: Renamed "Default" to "Dangerous" to indicate the potential soft-lock issues
    * Hera Basement Cage: Fix for small key counting multiple times (again)
    * Generation: Fixed several generation problems with ER and intensity 3
    * Customizer: Generation bug when attempting to place small keys
    * Hints: Updated pedestal/tablet text to be more clear
    * Enemizer: Various enemy bans
* 1.4.2
    * New ER Options:
        * [Skull Woods shuffle options](#skull-woods-shuffle)
        * [New option](#linked-drops-override) to override linked drop down behavior
    * Customizer: You can now start with a "RandomWeapon" in the start inventory section
    * Customizer: You may now start with "Big Magic" or "Small Magic" items
    * Customizer: Suppress warning for missing items if they are in start inventory
    * MultiClient: change default port to 23074 for newer SNI versions
    * Generation: Fixed typo causing ER gen failure with Bomb Shop at Graveyard Ledge
* 1.4.1.12u
    * New Entrance Shuffle Algorithm no longer experimental
    * Back of Tavern Shuffle now on by default
    * Enemizer: Wallmasters banned from tiles where spiral staircases are. (Softlock issue)
    * Packaged build of unstable now available
    * Customizer: New PreferredLocationGroup for putting a set of items in a set of locations. See customizer docs.
    * Customizer: Fixed an issue with starting with `Ocarina` and flute_mode is active
    * Spoiler: Some reformatting. Crystal req. for GT/Ganon moved to requirements section so randomized requirements don't show up in the meta section
    * Algorithm: Major_Only. Supports up to 16 extra locations (the visible heart pieces) for when major item count exceeds major location count. Examples: Triforce Hunt, Trinity (Triforce on Ped), Bombbag shuffle
    * Fix: HC Big Key drop doesn't count on Basic Doors
    * Fix: Small Key for this dungeon in Hera Basement doesn't count twice for the key counter
    * Fix: All cross-dungeon modes with restrict boss items should require map/compass for the boss
    * Fixed a small bug with traversal algorithm
    * Enemizer: Enemy bans+
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