# Changelog

# 0.7.1.1
- 2026 Easter Festive Fixes

# 0.7.1.0
- 2026 Easter Festive

# 0.7.0.3
- Further updates and new yamls for Grid OW Shuffle
- Further customizer options for Grid OW Shuffle like defining screens that should stay together
- Fix buffer sword slash when dashing into water
- Fixed bug with MSU-1 GT2 track not falling back to GT track
- Fix for Kiki unfollowing after certain entrance transition conditions
- Fixed bug/oversight with vanilla_fill and prize_shuffle
- Changed big bomb shop vendor text to be follower agnostic
- Updated crosskeys winners (thanks clearmouse)
- Fixed bug with potential locale determination (thanks Esme)
- \~Merged in DR v1.5.6~

# 0.7.0.2
- Fixed money error for bombbag/take-anys
- Fixed palette issue for map check/flute menu
- Fixed issue with dungeon icons showing in opposite world in Inverted
- Fixed Links position in map checks when in Special OW areas
- Fixed buffered sword issue in OW Shuffle water transitions
- Added PlasmaKappa tribute TF room text

# 0.7.0.1
- Fixed buggy sprites in post-Aga Zora's Domain
- Fixed L/R map switch when in special OW screens
- Fixes issue not able to screen transition if bumped by enemy in water

# 0.7.0.0
- New OW Layout Shuffle Mode: Grid
- Implemented Fog of War for Tile Flip

# 0.6.1.11
- Fixed bonk drops duplicate counting and potentially overwriting arbitrary values
- Fixed boss icons on dungeon map check
- Fixed dungeon counters to autotrack correctly
- Key and chest counts in menu now display consistently (must have dungeon item or have visited dungeon to see the HUD)
- Money balancing will fail in less scenarios
- Fixed issue with Sanc pots not collecting
- Enemizer now allows more enemies on water
- Fix infinite pit fall issue with Old Man follower location
- Fix bad overworld tilemap drawing on HC and Pyramid screens in OW Layout Shuffle

## 0.6.1.10
- Emergency fix for bonk functionality

## 0.6.1.9
- Fixed follower shuffle placement errors
- Fixed pseudoboots ability to open Kings Tomb
- Implemented better accurate coordinates on map check locations
- Fixed janky icons on zoomed-in map check screen

## 0.6.1.8
- Fixed follower placement and logic
- Fixed error with HC Courtyard Tree Pull

## 0.6.1.7
- \~Merged in DR v1.5.2~
  - Reverted key count update

## 0.6.1.6
- Fixed bonk drop sparkles in DW
- \~Merged in DR v1.5.1~
  - Fixed key count issues

## 0.6.1.5
- Fixed error with non-prize shuffle

## 0.6.1.4
- Fixes for Glitched Rain State (Bonk Shuffle included)
- \~Merged in DR v1.5.0~
  - GT Key Logic fix
  - New HUD key count behavior
  - Pot uncoloring on collection

## 0.6.1.3
- Added new post-gen option to change Triforce Piece GFX
- Added new GFX for 10/11 keys to replace the A/B GFX
- Fixed issue with Follower Sprite GFX after mirroring
- Fixed VRAM issue with Crystal Maiden cutscene
- Some performance updates
- \~Merged in DR v1.4.11~
  - Enemizer bans update

## 0.6.1.2
- Various fixes for Custom Goal Framework
- Added custom gfx for Pedestal and Murahdahla
- Re-fixed purple chest follower dupe
- Updated tournament winners texts

## 0.6.1.1
- Fixed issue with Bosses goals in Custom Goal Framework
- Fixed error when using Custom Goals with no extra values
- Added more Custom Goal detail in Spoiler Log

## 0.6.1.0
- New Custom Goal framework (see Customizer.md)
- New 'logic' hint terminology to replace vital/useful terminology
- Removed possibility of duplicated hints
- New fix for hammering pot drops when at sprite limit
- Fixed issue with incorrect Ganon silvers hint
- Fixed issue with Locksmith despawning after purple chest if a follower is stored
- Fixed pogdor glitch (frogdor but at PoD entrance and Kiki following)
- Fixed issue with Duck gfx overwriting GT Cutscene gfx
- New CLI argument to allow external generators to supply a custom ROM Header
- Fixed error with extra argument in MultiServer call
- Added new text if Link's House is placed at any Snitch Lady house

## 0.6.0.8
- Re-fixed issue with Old Man spawning on pyramid
- Allowing Zelda to be in TT Prison for follower shuffle escape
- Fixed error with placing Old Man Cave in ER
- Fixed error when plando'ing followers at locations

## 0.6.0.7
- Emergency fix for GT cutscene GFX

## 0.6.0.6
- Added ability to change GT entry cutscene GFX thru customizer
- Chicken as a standing item is no longer a star gfx
- Fix issue in DR with music silence in pre-Aga room
- Other various music fixes
- Fixed issue with Mystery subweights not correctly evaluating boolean settings

## 0.6.0.5
- Emergency fix for map/key totals in non-DR

## 0.6.0.4
- Fixed pause menu to show compass count and prizes to also show if you've seen them
- Fixed crash when Old Man follower exits with you at his destination entrance
- Old Man fetch cave is no longer restricted from exiting at his destination cave in ER
- Kodongo AI is returned to its vanilla behavior in their vanilla rooms

## 0.6.0.3
- Arrghus' Room has water floor restored in boss shuffle
- Fixed no music in Links House when S+Q from Kakariko
- Fixed issue with Boots not showing in pause menu after collection
- Fixed issue with Kiki running away outside the PoD maze
- Fixed issue with Kiki running away when using Quake
- Fixed issue with lingering purple chest after dropping and mirroring
- Getting Locksmith to follow behaves closer to vanilla
- Fixed issue with Locksmith follower despawning after purple chest item get
- Possible fix for prizes getting placed in major locations
- \~Merged in DR v1.4.10~
  - Helmacopter fix

## 0.6.0.2
- Fixed issue with item pool placing items on Zelda Drop Off
- Fix issue with infinite purple chest item get
- Fix issue with Kiki running away on i-frame ledge hops
- Fix issue with bad follower gfx on screens with followers
- Fix issue with Zelda appearing in conditional follower locations

## 0.6.0.1
- Emergency fix for generation errors

## 0.6.0.0
- New Follower Shuffle option (See Readme)
- HMG fixes for key pickup behavior
- Fixed some errors with starting equipment
- Added documentation for some unknown/obscure starting inventory options
- Possible fix for ignorable error message for EXE users
- \~Merged in DR v1.4.9~
  - Fixed Moth conveyor issue

## 0.5.1.5
- Fixed rare overworld map check VRAM crash
- Fixed cavestate dark room hidden item issue
- Removed dungeon items from hint pool for nearby dungeon items
- Fixed generation error with shopsanity
- Fixed generation error in ER: empty cave lists being added as candidates

## 0.5.1.4
- Fixed incorrect ganon silvers hint
- \~Merged in DR v1.4.8.1~

## 0.5.1.3
- Fixed some minor issues with mystery multiworld
- Corrected some generation issues with Nearby dungeon item shuffles

## 0.5.1.2
- Many fixes to HMG logic, generation, key collection issues
- Fixed issue with In-Dungeon Prizes getting placed in the same dungeon
- Fixed issue with Old Man getting placed outside of DM in glitched modes
- Fixed issue with Free Terrain water transitions not checking for Pearl requirement

## 0.5.1.0 (+ Hotfix 0.5.1.1)
- New "Nearby" Dungeon Item Shuffle option
- Fixed issue with smith follower getting deleted incorrectly on s+q
- Various generation and logic fixes for HMG/NL
- \~Merged in DR v1.4.6.2~

## 0.5.0.6
- New improved Pseudoboots behavior
- Fixed issue with missing Blue Potion in Dark Lake Shop in Inverted
- Various generation and logic fixes for HMG/NL
- Fixed error with prize plando
- Fixed error with District ER
- Added TT Maiden pathing to spoiler log
- Corrected and improved some pathing logic

## 0.5.0.5
- Fixed issue with vanilla HCBK acting like a small key

## 0.5.0.4
- Fixed dark room item gfx
- Fixed dungeon item pickup behavior in cross-dungeon glitched scenarios
- \~Merged in DR v1.4.6~
  - Fixed Sanc & Quit behavior

## 0.5.0.3
- Fixed crash on pedestal

## 0.5.0.2
- \~Merged in DR v1.4.5~
  - ER - SW Shuffle Options
  - ER - Linked Drops Options
- Many GFX fixes
- Fixes to MSU/music
- No longer delete smith with prize shuffle
- Fixed screen scroll issue in Zora's Domain
- Fixed HUD when drawing A items on DR menu

## 0.5.0.1
- Fixed HP refill interrupting boss cutscenes
- Fixed incorrect compass counts in Prize Shuffle
- Various QoL to Prize Shuffle for less confusion on map checks
- Color-blind support for red crystals (item receipt and map check)
- Added X icon on flute map to indicate you can cancel out of flute menu (Flute Shuffle only)

## 0.5.0.0
- Overworld Map Check has been overhauled
- Dungeon Prize Indicators have changed: P/C no longer display, replaced by G/B/R/1-7
- New Mode: Prize Shuffle
- Death Mountain Return Cave and Paradox Cave (Top) are no longer bunny passable
- \~Merged in DR v1.4.1.12~

## 0.4.0.2
- Fixed issue with Inverted GT entrance not opening
- Potential fox for bonk items duplicating onto other OW items

## 0.4.0.1
- \~Merged in DR v1.4.1.10~
- Fixed issue with bonk items for MW players
- Fixed fake world issues in Glitched modes
- Fixed issue with Flute getting canceled in OWR Layout modes
- Various GFX Fixes

## 0.4.0.0
- Fully merged big base ROM changes from upstream, including FastROM
- \~Merged up to date with DR v1.4.1.8~
- Various GFX re-implementation including new GFX for bee traps, bomb bags, etc.

## 0.3.4.2
- Added Shuffle SFX Instruments as post-gen option
- Fixed some issues with Swapped ER failing to place Old Man Cave
- Changed Inverted 2.0 spawn prompt to display Bomb Shop
- Fixed some minor issues with ER and Vanilla GT

## 0.3.4.1
- Implemented new District ER mode option
- Added alternate boss logic when in GT Ice Basement
- Updated Inverted 2.0 to start in Bomb Shop regardless of ER mode
- Fixed broken customizer features with OWR Tile Flip
- Allowing Insanity ER + Standard to decouple standard entrances

## 0.3.4.0
- \~Merged in DR v1.2.0.23~
  - Improved bunny-walking algorithm
  - Improved multiworld balancing
- \~Merged in some things from DR v1.4.0.0-v~
- Implemented Hybrid Major Glitches logic (thanks Muffins/Espeon)
- Added sparkles to Bonk Drop locations for better visibility
- Some tweaks/improvements to Shuffle Song Instruments
- Replaced Save Settings on Exit with Settings on Load
- Added new button in GUI to export a Yaml file based on current settings
- Allow starting Aga-Defeated and Old-Man-Rescued in inventory

## 0.3.3.2
- \~Merged in DR v1.2.0.22~
- Added Shuffle Song Instruments as post-gen option
- Allow user to change and save output directory within the GUI
- Fixed issue with Smith not deleting on S+Q when no path is possible
- Fixed various MSU inaccuracies

## 0.3.3.1
- \~Merged in DR v1.2.0.21~
- Fixed issue with Old Man death spawning on Pyramid/Castle
- Fixed issue with Mixed OWR + Flute Shuffle placing spots on large screens
- Fixed issue with mirror portals disappearing in Crossed OWR
- Added more OWR preset yamls + some fixes to the existing ones

## 0.3.3.0
- Added Customizer support for all remaining OWR options
- Added several OWR preset yamls (many ideas are thanks to Catobat)
- Removed Limited Crossed OWR and renamed Chaos Crossed to Unrestricted Crossed

## 0.3.2.2
- Added Customizer support for Flute Shuffle (thanks Catobat)
- Fixed bad Old Man rescue possibility in Swapped ER
- Fixed vanilla placement issue in Swapped ER
- Removed entrance hints in Swapped ER
- Fixed various generation/validation errors

## 0.3.2.1
- \~Merged in DR v1.2.0.20~
- Some minor Swapped ER improvements
- Fixed generation error with Flute Activation

## 0.3.2.0
- New Swapped ER mode option
- Fixed issue with flipper rules not properly getting pearl requirement added
- Fixed minor issues in generating non-crossed ER on subsequent attempts

## 0.3.1.2
- Retro now gives a universal key from bottle vendor fish prize
- Fixed issue with Aga Door preventing Murahduhla Cutscene
- Fixed issue with Ice Cave/Shopping Mall water transitions not flipping in Mixed OWR
- Minor improvements to item GFX draw routine

## 0.3.1.1
- \~Merged in DR v1.2.0.17~
- Various renames/reorganizations of region/rule definition to match upcoming DR world remodel
- Minor improvements to item GFX draw routine
- Minor change to terrain/logic of Spiral/Mimic Ledge in Inverted 2.0

## 0.3.1.0
- Added new Triforce Cutscene when getting Triforce item (turning in TF Pieces)
- Fixed issue with enemy key drops displaying the wrong GFX
- Fixed issue with boss music playing in Hera after boss is defeated
- Fixed issue that limited the Bonk count to cap at 99
- Made Murahdahla interactable on Pyramid in Rainstate

## 0.3.0.8
- All Bonk prize GFX are no longer using the Power Star placeholder GFX
- Fixed issue with dislaying Key GFX during tablet animations
- Fixed issue with DPad input being disabled in Pause Menu if an item GFX is on screen

## 0.3.0.7
- \~Merged in DR v1.2.0.16~
- Major overhaul of how item GFX are drawn on screen
  - Bonk prize GFX can now all be displayed simultaneously
  - Rupee items that are in-plain-sight are now animated
  - Narrow items are now centered within their tile space
  - Fixed issue with pottery items showing bad GFX after map check or medallion use
- Fixed issue with bonk drop items causing duplicate sprite spawns

## 0.3.0.6
- \~Merged in DR v1.2.0.15~
- Fixed Tower of Hera music silence issue
- Improved symmetrical GT crystal cutscene
- Changed bonk prizes to not mark as collected unless it is visible on screen

## 0.3.0.5
- Major reorganization to GUI Options
- Corrected various fake world behavior in glitched modes
- Fixed various issues with glitched mode logic
- Various minor logic fixes

## 0.3.0.4
- \~Merged in DR v1.2.0.14~
  - Fixed issue with enemy drops on OW enemies
  - Fixed issue with magically opened doors
- Inverted + Vanilla ER can now generate
- Fixed issue with Multiworld bonk items not sending to correct player
- Minor improvements to OW Palettes on screen transition

## 0.3.0.3
- Fixed issue with new Cold Fairy Statue location not dropping correct item
- Fixed issue with Multiworld due to new Cold Fairy Statue location
- Improved water collision to only target Heart Piece sprites (rando items)

## 0.3.0.2
- \~Merged in DR v1.2.0.12~
  - Fixed some door landing issues
- Added Cold Fairy Statue as a new Bonk Location in Bonk Drop Shuffle
- Added Customizer support for enabling OWR Options
- Removed `Arrows (5)` item from Item Table, replaces with `Arrows (10)`

## 0.3.0.1
- \~Merged in DR v1.2.0.10~
  - Fixed some door landing issues
- Added Customizer support for OWR Tile Flips
  - Added 'Standard+Inverted' template customizer yaml
- Fixed some ER issues with placing Sanc Drop in non-crossed ER

## 0.3.0.0
- \~Merged in all DR Customizer features since its initial release up to v1.2.0.9~
- Major revamp of Aerinon's ER 2.0 to better support OWR modes
- Fixed various incorrect logic issues (Inverted flute spots, Bomb Shop start, etc)
- Flute is disabled in rain state except glitched modes

## 0.2.11.4
- Fixed broken OWG logic issues
- Gave chickens a base price for shopsanity
- Modeled TR entrance opening to use a logical pseudo-item

## 0.2.11.3
- Fixed error during multiworld generation
- Added proper Old Man pathing to the logic and spoiler playthru
- Removed the delay in spawning sprites when bonking items out of bonk locations
- Removed useless hints in Lite/Lean ER that are already categorically assumed
- Added GT and Links House entrance hints when either are shuffled in the pool

## 0.2.11.2
- Implemented proper Districting with Mixed OWR, affecting Hints and District modes
- Suppressed item locations in spoiler log that are junk or logical

## 0.2.11.1
- Renamed mode: Tile Swap (Mixed) is now called Tile Flip (Mixed)
- Fixed generation errors due to issue with new Farmable item locations

## 0.2.11.0
- New OWR mode option: Free Terrain
  - When used with OW Layout Shuffle, land and water transitions are combined into one pool and shuffled, this means land transitions can lead to water and vice versa. There is already tracker support for this change on DunkaTracker. Thanks @Catobat for the work on all of this.
- Glitched modes now have correct fake world behavior in all modes, including Inverted and even Mixed OWR
- Glitched + Mixed OWR now has correct logic (previously it was completely unimplemented)
- Lite ER is back and working!
- There was an issue with ER resulting in regions being inaccessible, this has been fixed.
- Changed Crossworld ER modes so that DW inaccessible areas are resolved before considering LW inaccessible areas, to give the algo a chance to make some of the LW areas accessible thru the DW
- Added new Bomb/Rupee farm logic, which uses pseudo-items, simplifies the graph searching and they even show up in the Playthru Calc (shows a logical path to Farmable Bombs if you ever question how you are able to get early bombs when the opening area is limited)
- Fixed issue with grabbing an item near Murahduhla and freezing the game
- Various logic corrections, including the DR Bumper Cave fix for pottery logic

## 0.2.10.1
- \~Merged v1.0.1.3~
  - Fixed Zelda despawn in TT Prison
  - Fixed issue with key door usage in rainstate
- Added missing modes to example mystery yaml

## 0.2.10.0
- \~Merged v1.0.1.1-1.0.1.2~
  - Removed text color from hint tiles
  - Removed Good Bee requirement from Mothula
  - Some keylogic/generation fixes
  - Fixed a Pottery logic issue in the playthru
- Fixed a generation error in Mixed OWR, resulting in more possible Mixed scenarios (thanks Catobat)
- Added more scenarios where OW Map Checks in Mixed OWR show dungeon prizes in their respective worlds 
- Fixed rupee logic to consider Pottery option and lack of early rupees
- Changed Lean ER + Inverted Dark Chapel start is guaranteed to be in DW
- Fixed graphical issue with Hammerpeg Cave
- Fixed logic rule with HC Main Gate to not require mirror if screen is swapped
- Removed Crossed OWR option: "None (Allowed)"

### 0.2.9.1
- Lite/Lean ER now includes Cave Pot locations with various Pottery options
- Changed Unique Boss Shuffle so that GT Bosses are unique amongst themselves
- Changed MSU-1 in Inverted to trigger DW2 track with Aga1 kill and LW2 with 7 crystals
- Fixed disappearing mirror portal issue in Inverted (Hopefully for good)
- Fixed issue with TR Peg Puzzle not spawning portal in some Mixed OWR scenarios
- Removed ability to roll Myserty with phantom Crossed OWR options

### 0.2.9.0
- Added Bonk Drop Shuffle
- Fixed disappearing mirror portal issue in Inverted+Crossed OWR
- Fixed 4-digit collection rate in credits
- Fixed Ganon vulnerability to reference Aga2 boss flag rather than pyramid hole
- Fixed issue with pre-opened pyramid when not expected

### 0.2.8.0
- \~Merged DR v1.0.1.0 - Pottery options, BPS support, MSU Resume, Collection Rate Counter~
- Various improvements to increase generation success rate and reduce generation time
- Fixed issue with playthru recognizing Aga accessibility
- Fixed issue with applying rules correctly to Murahdahla, fixing Murahdahla+Beatable issues
- Fixed issue with Flute+Rainstate, flute use is no longer in logic until Zelda is delivered

### 0.2.7.3
- Restructured OWR algorithm to include some additional scenarios not previously allowed
- Added new Inverted D-pad controls for Social Distortion (ie. Mirror Mode) support
- Crossed OWR/Special OW Areas are now included in the spoiler log
- Fixed default TF pieces with Trinity in Mystery
- Added bush crabs to rupee farm logic (only in non-enemizer)
- Updated tree pull logic to also require ability to kill most things

### 0.2.7.2
- Special OW Areas are now shuffled in Layout Shuffle (Zora/Hobo/Pedestal)
- Fixed some broken water region graph modelling, fixed some reachability logic
- Some minor code simplifications

### 0.2.7.1
- Map checks in Mixed OWR now will show the proper tile images when screens are swapped (ie. Pyramid shows in the LW if that screen is swapped)
- Added mystery seed number to spoiler log, so it is easier to match a spoiler log to a rom filename
- Added proper branch-specific versioning (ie. Dev branch has '-u' suffixing the version number while Release/Main branch does not)

### 0.2.7.0
- \~Merged DR v1.0.0.3 - MANY changes, major things listed below~
  - New Item Fills (Districts/Vanilla/Major Location/Dungeon)
  - New OW Map Prize Indicators (In ER, map checks can spoil dungeon locations with a user setting)
  - Forbidden Boss Items (Exclude certain dungeon items from dropping on bosses)
- Map checks in Mixed OWR now will show dungeon prizes for dungeons actually in the world you map check on
- In Mixed OWR, Sanc screen must stay in LW if the starting location is guaranteed to exit at the Sanc entrance
- Fixed various issues with Flute logic
- Fixed issue that resulted in infinite loops in Flute Shuffle
- Changed map in attract mode to always show a vanilla LW map
- Various improvements to increase generation success rate

### 0.2.6.1
- Fixed issue with mirror bonking deleting portal in Crossed OW
- Fixed issue with mirror portal not spawning when entering the OW from the DW, in Crossed OW
- Updated some text with proper capitalization/spacing
- Updated tournament winners text

### 0.2.6.0
- New text engine font!
- Fixed invisible Witch item bug
- Added 'O' to ROM Header for autotrackers
- Fixed generation error with Shopsanity + OWR Layout
- Fixed OWR validation error with Insanity ER + OWR Layout
- Fixed issue with TR Peg Puzzle not spawning a valid portal

### 0.2.5.3
- Changed AT/GT Swap to favor vanilla, only swapping if GT entrance is the only choice in starting world
- Fixed issue with Links House not swapping in OW Mixed
- Added Flute Spots to spoiler log
- Fixed issue with Light Hype Fairy excluded from bombable door list

### 0.2.5.1
- Fixed missing rule for Inverted VoO Portal access

### 0.2.5.0
- Many updates to Inverted OW Terrain:
    - Links House start now spawns in Big Bomb Shop
    - Old Man Cave/Bumper Cave returned to vanilla
    - Mountain Cave S+Q now spawns in his usual Cave
    - Flute Spot 1 is moved to Top of Dark Death Mountain
    - Ladder is removed from West Dark Death Mountain
    - When finding Flute, it comes pre-activated (will hear SFX on collecting)
    - Spiral and Mimic Cave are now bridged together
    - TR Peg Puzzle is restored but instead reveals a ladder
    - Houlihan now exits same place as Big Bomb Shop does (OWR branch always had this)
    - Ice Palace has been re-sealed to vanilla, portal moved to outer edge of moat
    - Glitched modes will now use vanilla terrain except where necessary
- Fixed errors with OW Layout Shuffle
- Fixed issue with incorrect Mirror bonking
- Fixed issue with old man follower death to Pyramid
- Fixed Hera boss music not playing when boss not defeated
- \~Merged DR v0.5.1.7 - TT boss trap door fix/Applied Glitched flag~

### 0.2.4.0
- Added Guaranteed OWR Reachability
- Fixed incorrect parity calc for Whirlpool Shuffle
- Fixed error with generating seeds with GUI
- CLI fixes for triforce piece arguments

### 0.2.3.6
- Added Trinity goal (8/10 default TF pieces)
- Many improvements to TFH pool allocation
- Fixed some issues with Multiworld generation with Custom Item Pools

### 0.2.3.5
- Fixed issue with multiworld generation
- Added infinite loop detection
- Move mirror portal off screen during mirror bonk in Crossed OW

### 0.2.3.4
- Fixed major issue with subsequent seeds using same seed/settings resulting different
- Flute Shuffle now awards separated regions a prorated number of flute spots based on size
- Fixed spoiler log, was missing OW Tile Swap map
- Fixed spoiler log JSON output
- Fake flipper damage fix improved to skip the long delay after the scroll
- Fixed missing Blue Potion in Lake Shop in Inverted
- Added legacy OW Crossed option 'None (Allowed)' to support old behavior when invalid option was used in Mystery
- \~Merged DR v0.5.1.6 - Money balancing fix/Boss logic fixes with Bombbag~

### 0.2.3.3
- Added OW Layout validation that reduces the cases where some screens are unreachable
- Fixed issue with mirror portals showing up in DW in Crossed OW
- Corrected Lost/Skull Woods Pass regions to be more accurate

### 0.2.3.0/1/2
- Fixed issue in Crossed OW where mirror portal sprites would disappear when changing worlds
- Added Big Red Bomb logic to support using residual mirror portals for later re-entry
- Suppressed irrelevant paths in spoiler playthru
- Suppressed identical paths in spoiler playthru if multiple locations within the same region contain progression

### 0.2.2.3
- Fixed GT entrance not being opened when Inverted and WDM is Tile Swapped
- The Goal sign is moved to the area where the hole will be (always in opposite world as starting)

### 0.2.2.2
- Fixed Whirlpool Shuffle with Grouped Crossed OW
- Made filename not spoil OWR in Mystery
- Fixed Triforce Hunt goal

### 0.2.2.1
- Allow normal Link speed with Old Man following if not in his cave or WDM
- Fixed issue with Flute exits not getting placed on the correct tiles
- Hints in Lite/Lean ER no longer refer to entrances that are guaranteed vanilla
- Added Links House entrance to hint candidate list in ER when it is shuffled
- Added Tile Swaps ASCII map to Spoiler Log when Tile Swap is enabled
- Fixed issue with Whirlpool Shuffle not abiding by Polar rules

### 0.2.2.0
- Delivering Big Red Bomb is now in logic
- Smith/Purple Chest have proper dynamic pathing to fix logical issues
- Fixed issue with bomb walls in OW not requiring moon pearl in DW

### 0.2.1.3
- New fake flipper handling to allow S+Q rather than insta-kill
- Fixed whirlpools in Crossed OW
- Spoiler fixes, incl. missing Starting Inventory in Spoiler
- Fixed music track change to Sanc music when Standard mode is delivering Zelda
- Fixed SP flooding issue
- Fixed issue with Shuffle Ganon in CLI/GUI
- \~Merged DR v0.5.1.5 - Mystery subweights~

### 0.2.1.2
- Fixed issue with whirlpools not changing world when in Crossed OW

### 0.2.1.1
- Many fixes to ER: infinite loops, preventing cross-world scenarios in non-cross-world modes
- Spoiler log improvements, outputs in stages so a Spoiler is available if an error occurs
- Added no_race option for Mystery
- Fixed output_path in Mystery to use the saved setting if none is specified on CLI

### 0.2.1.0
- Implemented Whirlpool Shuffle

### 0.2.0.0
- Massive overhaul of ER algorithm
- Added 2 new ER modes (Lite and Lean)
- Added new mystery options (Logic/Shuffle Ganon)
- Smith deletion on S+Q only occurs if Blacksmith not reachable from starting locations
- Spoiler log improvements to prevent spoiling in the beginning 'meta' section
- Various minor fixes and improvements
- \~Merged DR v0.5.1.4 - ROM bug fixes/keylogic improvements~

### 0.1.9.4
- Hotfix for bad 0.1.9.3 version

### 0.1.9.3
- Moved flute spot from Northwest Lake Hylia to Southeast Lake Hylia
- Fixed Links House start in Inverted ER
- Minor accuracy improvements to ER, mostly preparations for future work

### 0.1.9.2
- Fixed spoiler log and mystery for new Crossed/Mixed structure
- Minor preparations and tweaks to ER framework (added global Entrance/Exit pool)
- \~Merged DR v0.5.1.2 - Blind Prison shuffled outside TT/Keylogic Improvements~

### 0.1.9.1
- Fixed logic issue with leaving IP entrance not requiring flippers
- \~Merged DR v0.5.1.1 - Map Indicator Fix/Boss Shuffle Bias/Shop Hints~

### 0.1.9.0
- Expanded Crossed OW to four separate options, see Readme for details
- Crossed OW will now play a short SFX when changing worlds
- Improved Link/Bunny state in Crossed OW
- Fixed issue with TR Pegs when fluting directly from an area with hammerpegs
- Updated OW GUI layout

### 0.1.8.2
- Fixed issue with game crashing on using Flute
- Fixed issues with Link/Bunny state in Crossed OW
- Fixed issue with Standard+Parallel not using vanilla connections for Escape
- Fixed issue with Mystery for OW boolean options
- \~Merged DR v0.5.1.0 - Major Keylogic Update~

### 0.1.8.1
- Fixed issue with activating flute in DW (OW Mixed)
- Fixed issue with Parallel+Crossed not generating
- Fixed issue with Standard not generating
- Fixed issue with Swordless not generating
- Fixed logic for Graveyard Ledge and Kings Tomb

### 0.1.8.0
- Moved Crossed to its own checkbox option
- Removed Legacy ER shuffles
- Added OW Shuffle support for Plando module (needs user testing)
- Fixed issue with Sanc start at TR as bunny when it is LW
- Fixed issue with Pyramid Hole not getting shuffled
- \~Merged DR v0.5.0.3 - Minor DR fixes~

### 0.1.7.4
- Fixed issue with Mixed OW failing to generate when HC/Pyramid is swapped
- Various fixes to improve generation rates for Mixed OW Shuffle
- \~Merged DR v0.5.0.2 - Shuffle SFX~

### 0.1.7.3
- Fixed minor issue with ambient SFX stopping and starting on OW screen load
- MSU-1 changed to play LW2 (track 60) when Aga1 is killed instead of ped pull
- Added dynamic flute exits for all LW OW regions
- Improved spoiler log playthru pathing accuracy by including flute routing
- Fixed issue with generating a filename for vanilla OW settings

### 0.1.7.2
- Fixed music algorithm to play correct track in OW Shuffle
- Removed convenient portal on WDM in OW Layout Shuffle
- Fixed Mystery to not spoil OW Shuffle in filename

### 0.1.7.1
- Improved bomb logic to consider tree pulls, bush crabs, and stun prize
- Fixed Mystery to use new updated OW mode terminology

### 0.1.7.0
- Expanded new DR bomb logic to all modes (bomb usage in logic only if there is an unlimited supply of bombs available)
- \~Merged DR v0.5.0.1 - Bombbag mode / Enemizer fixes~

### 0.1.6.9
- \~Merged DR v0.4.0.12 - Secure random update / Credits fix~

### 0.1.6.8
- Implemented a smarter Balanced Flute Shuffle algorithm
- Fixed Collection Rate in credits
- Removed sortedcontainers dependency

### 0.1.6.7
- Mountain Pass and West Death Mountain are now Swapped independently (Old Man rescue is always in your starting world)
- Fixed issue with AT/GT access logic
- Improved spoiler log playthru accuracy
- Fixed Boss Music when boss room is entered thru straight stairs
- Suppressed in-dungeon music changes when DR is enabled
- Fixed issue with Pyramid Exit exiting to wrong location in ER
- \~Merged DR v0.4.0.11 - Various DR changes~

### 0.1.6.6
- \~Merged DR v0.4.0.9 - P/C Indicator / Credits fix / CLI Hints Fix~

### 0.1.6.5
- Reduced chance of diagonal flute spot in Balanced
- \~Merged DR v0.4.0.8 - Boss Indicator / Psuedo Boots / Quickswap Update / Credits Updates~

### 0.1.6.4
- Fixed Frogsmith and Stumpy and restored progression in these locations
- Added Blacksmith/Hammer Pegs to OW Tile Swap pool

### 0.1.6.3
- Fixed borked credits (and missing Sprite Author) when collection rate isn't 216 or if GTBK count isn't /22
- Added OW Rando in credits
- Actually merged in DR v0.4.0.7 (with no thanks to GitHub)

### 0.1.6.2
- Added Balanced option for Flute Shuffle
- Fixed issue with Flute Spot to Mountain Pass softlocking
- Fixed logic bug with Inverted Kakariko Portal

### 0.1.6.1
- Fixed issue with Flute Spot to VoO softlocking
- Fixed Houlihan to exit where Link's House does
- Fixed issue with jsonout not correctly showing rom mods for some OW Shuffle data

### 0.1.6.0
- Added Flute Shuffle setting
- Minor GUI changes

### 0.1.5.3
- Fixed issue with Aga portal mirror bonking in Mixed Shuffle
- Fixed issue with Frog/Dig Game edges duplicating in edge pool, causing Insanity-like behavior

### 0.1.5.2
- Partial revert of horizontal VRAM fix from v0.1.5.0

### 0.1.5.1
- Fixed issue with Flute Spot 7 logically connecting to the wrong area in Mixed/Crossed OW Shuffle
- Fixed issue with TR portal not requiring mitts when tile is swapped

### 0.1.5.0
- Added OW Tile Swap setting
- Fixed horizontal VRAM visual loading glitch on megatiles
- ~\~Merged DR v0.4.0.7 - Fast Credits / Reduced Flashing / Sprite Author in Credits~~ Didn't fully merge

### 0.1.4.3
- \~Merged DR v0.4.0.6 - TT Maiden Attic Hint / DR Entrance Floor Mat Mods / Hard/Expert Item Pool Fix~

### 0.1.4.2
- Modified various OW map terrain specific to OW Shuffle
- Changed World check to table-based vs OW ID-based (should have no effect with current modes)
- \~Merged DR v0.4.0.5 - Mystery Boss Shuffle Fix / Swordless+Hard Item Pool Fix / Insanity+Inverted ER Fixes~

### 0.1.4.1
- Moved Inverted Pyramid Entrance to top of HC Ledge
- Fixed various issues with Inverted and Insanity

### 0.1.4.0
- Initial Inverted Implementation
- Fix for Kakariko Pond no longer requiring fake flipper

### 0.1.3.1
- Various logic fixes and region prep for Inverted
- Fixed muted MSU-1 music in door rando when descending GT Climb stairs
- Fixed Standard + Vanilla (thanks compiling)
- \~Merged DR v0.4.0.4 - Shuffle Link's House / Experimental Bunny Start / 10 Bomb Fix~

### 0.1.3.0
- Added OWG Logic for OW Shuffle
- \~Merged DR v0.4.0.2 - OWG Framework / YAML~

### 0.1.2.2
- Re-purposed OW Shuffle setting to Layout Shuffle
- Merged Parallel Worlds setting into Layout Shuffle
- Added guaranteed Flute hint for OW Shuffle modes

### 0.1.2.1
- Made possible fix for Standard
- \~Merged DR v0.3.1.10 - Fixed Standard generation~

### 0.1.2.0
- Added 'Parallel Worlds' toggle option
- Updated shuffle algorithm
- Renamed some OW areas

### 0.1.1.2
- If Link's current position fits within the incoming gap, Link will not get re-centered to the incoming gap
- Added Rule for Pearl required to drop down back of SW
- \~Merged DR v0.3.1.8 - Improved Shopsanity pricing - Fixed Retro generation~

### 0.1.1.1
- Fixed camera unlocking issue
- Changed default setting for DR to Vanilla

### 0.1.1.0
- Added 'Keep Similar Edges Together' toggle option
- Removed Duplicate Pyramid Ledge location, causing a Warning of unfilled location on generation

### 0.1.0.3
- Modified various logic rule for some OW locations

### 0.1.0.2
- Fixed error generating a bad Spoiler log

### 0.1.0.1
- Separated DR versioning from OR versioning
- Removed LW/DW flag toggle on transitions

### 0.1.0.0
- Initial release