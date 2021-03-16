# Ordered list of items in Custom Item Pool page and Starting Inventory page
CUSTOMITEMS = [
  "bow",                "progressivebow",   "boomerang",          "redmerang",        "hookshot",
  "mushroom",           "powder",           "firerod",            "icerod",           "bombos",
  "ether",              "quake",            "lamp",               "hammer",           "shovel",

  "flute",              "bugnet",           "book",               "bottle",           "somaria",
  "byrna",              "cape",             "mirror",             "boots",            "powerglove",
  "titansmitt",         "progressiveglove", "flippers",           "pearl",            "heartpiece",

  "heartcontainer",     "sancheart",        "sword1",             "sword2",           "sword3",
  "sword4",             "progressivesword", "shield1",            "shield2",          "shield3",
  "progressiveshield",  "mail2",            "mail3",              "progressivemail",  "halfmagic",

  "quartermagic",       "bombsplus5",       "bombsplus10",        "arrowsplus5",      "arrowsplus10",
  "arrow1",             "arrow10",          "bomb1",              "bomb3",            "bomb10",
  "rupee1",             "rupee5",           "rupee20",            "rupee50",          "rupee100",

  "rupee300",           "blueclock",        "greenclock",         "redclock",         "silversupgrade",
  "generickeys",        "triforcepieces",   "triforcepiecesgoal", "triforce",         "rupoor",
  "rupoorcost"
]

# These can't be in the Starting Inventory page
CANTSTARTWITH = [
  "triforcepiecesgoal", "triforce", "rupoor",
  "rupoorcost"
]

# In the same order as CUSTOMITEMS, these are Pretty Labels for each option
CUSTOMITEMLABELS = [
  "Bow", "Progressive Bow", "Blue Boomerang", "Red Boomerang", "Hookshot",
  "Mushroom", "Magic Powder", "Fire Rod", "Ice Rod", "Bombos",
  "Ether", "Quake", "Lamp", "Hammer", "Shovel",

  "Ocarina", "Bug Catching Net", "Book of Mudora", "Bottle", "Cane of Somaria",
  "Cane of Byrna", "Magic Cape", "Magic Mirror", "Pegasus Boots", "Power Glove",
  "Titans Mitts", "Progressive Glove", "Flippers", "Moon Pearl", "Piece of Heart",

  "Boss Heart Container", "Sanctuary Heart Container", "Fighter Sword", "Master Sword", "Tempered Sword",
  "Golden Sword", "Progressive Sword", "Blue Shield", "Red Shield", "Mirror Shield",
  "Progressive Shield", "Blue Mail", "Red Mail", "Progressive Armor", "Magic Upgrade (1/2)",

  "Magic Upgrade (1/4)", "Bomb Upgrade (+5)", "Bomb Upgrade (+10)", "Arrow Upgrade (+5)", "Arrow Upgrade (+10)",
  "Single Arrow", "Arrows (10)", "Single Bomb", "Bombs (3)", "Bombs (10)",
  "Rupee (1)", "Rupees (5)", "Rupees (20)", "Rupees (50)", "Rupees (100)",

  "Rupees (300)", "Blue Clock", "Green Clock", "Red Clock", "Silver Arrows",
  "Small Key (Universal)", "Triforce Piece", "Triforce Piece Goal", "Triforce", "Rupoor",
  "Rupoor Cost"
]

# Stuff on each page to save, according to internal names as defined by the widgets definitions
#  and how it eventually translates to YAML/JSON weight files
SETTINGSTOPROCESS = {
  "randomizer": {
    "item": {
      "retro": "retro",
      "futuro": "futuro",
      "shopsanity": "shopsanity",
      "worldstate": "mode",
      "logiclevel": "logic",
      "goal": "goal",
      "crystals_gt": "crystals_gt",
      "crystals_ganon": "crystals_ganon",
      "weapons": "swords",
      "itempool": "difficulty",
      "itemfunction": "item_functionality",
      "timer": "timer",
      "progressives": "progressive",
      "accessibility": "accessibility",
      "sortingalgo": "algorithm"
    },
    "entrance": {
      "openpyramid": "openpyramid",
      "shuffleganon": "shuffleganon",
      "entranceshuffle": "shuffle"
    },
    "enemizer": {
      "enemyshuffle": "shuffleenemies",
      "bossshuffle": "shufflebosses",
      "enemydamage": "enemy_damage",
      "enemyhealth": "enemy_health"
    },
    "dungeon": {
      "mapshuffle": "mapshuffle",
      "compassshuffle": "compassshuffle",
      "smallkeyshuffle": "keyshuffle",
      "bigkeyshuffle": "bigkeyshuffle",
      "keydropshuffle": "keydropshuffle",
      "dungeondoorshuffle": "door_shuffle",
      "dungeonintensity": "intensity",
      "potshuffle": "shufflepots",
      "experimental": "experimental",
      "dungeon_counters": "dungeon_counters",
      "mixed_travel": "mixed_travel",
      "standardize_palettes": "standardize_palettes",
    },
    "gameoptions": {
      "hints": "hints",
      "nobgm": "disablemusic",
      "quickswap": "quickswap",
      "heartcolor": "heartcolor",
      "heartbeep": "heartbeep",
      "menuspeed": "fastmenu",
      "owpalettes": "ow_palettes",
      "uwpalettes": "uw_palettes"
    },
    "generation": {
      "createspoiler": "create_spoiler",
      "createrom": "create_rom",
      "calcplaythrough": "calc_playthrough",
      "usestartinventory": "usestartinventory",
      "usecustompool": "custom",
      "saveonexit": "saveonexit"
    }
  },
  "bottom": {
    "content": {
      "names": "names",
      "seed": "seed",
      "generationcount": "count"
    }
  }
}
