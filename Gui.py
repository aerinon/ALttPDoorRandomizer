#!/usr/bin/env python3
import argparse
import json
import random
import os
import sys
from tkinter import BOTTOM, TOP, INSERT, Frame, Text, W, E, X, Button, Tk, ttk

import gui.randomize.item as ItemPage
import gui.randomize.entrando as EntrandoPage
import gui.randomize.enemizer as EnemizerPage
import gui.randomize.dungeon as DungeonPage
import gui.randomize.multiworld as MultiworldPage
import gui.randomize.gameoptions as GameOptionsPage
import gui.randomize.generation as GenerationPage
import gui.adjust.overview as AdjustPage
import gui.custom.overview as CustomPage
import gui.bottom as BottomFrame
from CLI import parse_arguments, get_working_dirs
from GuiUtils import set_icon
from Main import main, __version__ as ESVersion
from Rom import Sprite


def guiMain(args=None):
    print(args)
    def save_working_dirs():
        user_resources_path = os.path.join(".","resources","user")
        working_dirs_path = os.path.join(user_resources_path)
        if not os.path.exists(working_dirs_path):
            os.makedirs(working_dirs_path)
        with open(os.path.join(working_dirs_path,"working_dirs.json"),"w+") as f:
            f.write(json.dumps(self.working_dirs,indent=2))
        os.chmod(os.path.join(working_dirs_path,"working_dirs.json"),0o755)

    def guiExit():
        save_working_dirs()
        sys.exit(0)

    args = parse_arguments(args)

    # make main window
    # add program title & version number
    mainWindow = Tk()
    self = mainWindow
    mainWindow.wm_title("Door Shuffle %s" % ESVersion)
    mainWindow.protocol("WM_DELETE_WINDOW",guiExit) # intercept when user clicks the X

    # set program icon
    set_icon(mainWindow)

    # get working dirs
    self.working_dirs = get_working_dirs()

    # make notebook pages: Randomize, Adjust, Custom
    #  Randomize: Main randomizer settings
    #  Adjust:    Alter existing game file
    #  Custom:    Custom item pool
    #  About:     About Page
    notebook = ttk.Notebook(self)
    self.randomizerWindow = ttk.Frame(notebook)
    self.adjustWindow = ttk.Frame(notebook)
    self.customWindow = ttk.Frame(notebook)
    self.aboutWindow = ttk.Frame(notebook)
    notebook.add(self.randomizerWindow, text='Randomize')
    notebook.add(self.adjustWindow, text='Adjust')
    notebook.add(self.customWindow, text='Custom')
    notebook.add(self.aboutWindow, text='About')
    notebook.pack()

    # Shared Controls

    # bottom of window: Open Output Directory, Open Documentation (if exists)
    farBottomFrame = BottomFrame.bottom_frame(self,self,args)
    # set bottom frame to main window
    farBottomFrame.pack(side=BOTTOM, fill=X, padx=5, pady=5)

    # randomizer controls

    # Randomize notebook page:
    #  make notebook pages: Item, Entrances, Enemizer, Dungeon Shuffle, Multiworld, Game Options, Generation Setup
    #   Item:             Item Randomizer settings
    #   Entrances:        Entrance Randomizer settings
    #   Enemizer:         Enemy Randomizer settings
    #   Dungeon Shuffle:  Dungeon Door Randomizer settings
    #   Multiworld:       Multiworld settings
    #   Game Options:     Cosmetic settings that don't affect logic/placement
    #   Generation Setup: Primarily one&done settings
    self.randomizerNotebook = ttk.Notebook(self.randomizerWindow)

    # Item Randomizer
    self.itemWindow = ItemPage.item_page(self.randomizerNotebook)
    self.randomizerNotebook.add(self.itemWindow, text="Item")

    # Entrance Randomizer
    self.entrandoWindow = EntrandoPage.entrando_page(self.randomizerNotebook)
    self.randomizerNotebook.add(self.entrandoWindow, text="Entrances")

    # Enemizer
    self.enemizerWindow,self.working_dirs = EnemizerPage.enemizer_page(self.randomizerNotebook,self.working_dirs)
    self.randomizerNotebook.add(self.enemizerWindow, text="Enemizer")

    # Dungeon Shuffle
    self.dungeonRandoWindow = DungeonPage.dungeon_page(self.randomizerNotebook)
    self.randomizerNotebook.add(self.dungeonRandoWindow, text="Dungeon Shuffle")

    # Multiworld
    self.multiworldWindow,self.working_dirs = MultiworldPage.multiworld_page(self.randomizerNotebook,self.working_dirs)
    self.randomizerNotebook.add(self.multiworldWindow, text="Multiworld")

    # Game Options
    self.romOptionsWindow = GameOptionsPage.gameoptions_page(self.randomizerNotebook)
    self.randomizerNotebook.add(self.romOptionsWindow, text="Game Options")

    # Generation Setup
    self.generationSetupWindow,self.working_dirs = GenerationPage.generation_page(self.randomizerNotebook,self.working_dirs)
    self.randomizerNotebook.add(self.generationSetupWindow, text="Generation Setup")

    # add randomizer notebook to main window
    self.randomizerNotebook.pack()

    # Adjuster Controls
    self.adjustContent,self.working_dirs = AdjustPage.adjust_page(self,self.adjustWindow,self.working_dirs)
    self.adjustContent.pack(side=TOP, pady=70)

    # Custom Controls
    self.customContent = CustomPage.custom_page(self,self.customWindow)
    self.customContent.pack(side=TOP, pady=(17,0))

    def txtEvent(event):
      return "break"

    aboutFrame = Frame(self.aboutWindow)
    aboutText = Text(aboutFrame, bg='#f0f0f0', font='TkDefaultFont')
    aboutText.insert(INSERT, "Entrance Randomizer:" + "\n")
    aboutText.insert(INSERT, "  LLCoolDave" + "\n")
    aboutText.insert(INSERT, "  KevinCathcart" + "\n")
    aboutText.insert(INSERT, "  AmazingAmpharos" + "\n")
    aboutText.insert(INSERT, "  qwertymodo" + "\n")
    aboutText.insert(INSERT, "Enemizer:" + "\n")
    aboutText.insert(INSERT, "  Zarby89" + "\n")
    aboutText.insert(INSERT, "  Sosuke3" + "\n")
    aboutText.insert(INSERT, "Dungeon Door Randomizer:" + "\n")
    aboutText.insert(INSERT, "  Aerinon" + "\n")
    aboutText.insert(INSERT, "  compiling" + "\n")
    aboutText.insert(INSERT, "GUI Adjustments:" + "\n")
    aboutText.insert(INSERT, "  Mike Trethewey" + "\n")

    aboutText.pack()
    aboutText.configure(cursor="arrow")
    aboutText.bind("<Button-1>", lambda e: txtEvent(e))
    aboutFrame.pack()

    if args is not None:
        for k,v in vars(args).items():
            if type(v) is dict:
                setattr(args, k, v[1]) # only get values for player 1 for now
        # load values from commandline args
        self.generationSetupWindow.createSpoilerVar.set(int(args.create_spoiler))
        self.generationSetupWindow.suppressRomVar.set(int(args.suppress_rom))
        self.dungeonRandoWindow.mapshuffleVar.set(args.mapshuffle)
        self.dungeonRandoWindow.compassshuffleVar.set(args.compassshuffle)
        self.dungeonRandoWindow.keyshuffleVar.set(args.keyshuffle)
        self.dungeonRandoWindow.bigkeyshuffleVar.set(args.bigkeyshuffle)
        self.itemWindow.retroVar.set(args.retro)
        self.entrandoWindow.openpyramidVar.set(args.openpyramid)
        self.romOptionsWindow.quickSwapVar.set(int(args.quickswap))
        self.romOptionsWindow.disableMusicVar.set(int(args.disablemusic))
        if args.multi:
            self.multiworldWindow.worldVar.set(str(args.multi))
        if args.count:
            self.farBottomFrame.countVar.set(str(args.count))
        if args.seed:
            self.generationSetupWindow.seedVar.set(str(args.seed))
        self.itemWindow.modeVar.set(args.mode)
        self.itemWindow.swordVar.set(args.swords)
        self.itemWindow.difficultyVar.set(args.difficulty)
        self.itemWindow.itemfunctionVar.set(args.item_functionality)
        self.itemWindow.timerVar.set(args.timer)
        self.itemWindow.progressiveVar.set(args.progressive)
        self.itemWindow.accessibilityVar.set(args.accessibility)
        self.itemWindow.goalVar.set(args.goal)
        self.itemWindow.crystalsGTVar.set(args.crystals_gt)
        self.itemWindow.crystalsGanonVar.set(args.crystals_ganon)
        self.itemWindow.algorithmVar.set(args.algorithm)
        self.entrandoWindow.shuffleVar.set(args.shuffle)
        self.dungeonRandoWindow.doorShuffleVar.set(args.door_shuffle)
        self.romOptionsWindow.heartcolorVar.set(args.heartcolor)
        self.romOptionsWindow.heartbeepVar.set(args.heartbeep)
        self.romOptionsWindow.fastMenuVar.set(args.fastmenu)
        self.itemWindow.logicVar.set(args.logic)
        self.generationSetupWindow.romVar.set(args.rom)
        self.entrandoWindow.shuffleGanonVar.set(args.shuffleganon)
        self.romOptionsWindow.hintsVar.set(args.hints)
        self.enemizerWindow.enemizerCLIpathVar.set(args.enemizercli)
        self.enemizerWindow.potShuffleVar.set(args.shufflepots)
        self.enemizerWindow.enemyShuffleVar.set(args.shuffleenemies)
        self.enemizerWindow.enemizerBossVar.set(args.shufflebosses)
        self.enemizerWindow.enemizerDamageVar.set(args.enemy_damage)
        self.enemizerWindow.enemizerHealthVar.set(args.enemy_health)
        self.romOptionsWindow.owPalettesVar.set(args.ow_palettes)
        self.romOptionsWindow.uwPalettesVar.set(args.uw_palettes)
#        if args.sprite is not None:
#            self.romOptionsWindow.set_sprite(Sprite(args.sprite))

    mainWindow.mainloop()

if __name__ == '__main__':
    guiMain()
