# Patch Notes

* 1.5.8
  * Key Logic: Static key logic requires Enemy Logic "Forbid special enemies" (`any_enemy_logic: none`) when enemies are shuffled.
  * Enemizer: `force_enemy` respects kill room and key drop restrictions.
  * Enemizer: Fixed a rare generation crash when a shuffled boss lands in a Ganon's Tower boss room.
  * Logic: Eastern Palace Big Key Chest requires defeating the room's enemies under enemy shuffle.
  * Logic: Fixed Old Man Cave Dropdown leading to Old Man Cave (East) instead of Old Man Cave (West).
  * Money Balancing: Without shopsanity, vanilla shop stock is no longer counted as required purchases.
  * Dungeon Items: Unshuffled big keys, maps, and compasses use native item codes, and the HUD item counter only shows when relevant. (Thanks homemadebeer!)
  * Fixes for hybrid major glitches ROM flags and Swamp pot key placement, and for static Turtle Rock key logic at TR Pokey 2. (Thanks homemadebeer!)
  * Docs: Corrected location hint wording in ER_hint_reference.txt. (Thanks dc-alcoba!)
