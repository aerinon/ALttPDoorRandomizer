from tkinter import ttk, messagebox, StringVar, Button, Entry, Frame, Label, Spinbox, E, W, LEFT, RIGHT, X
from argparse import Namespace
import logging
import os
import random
from CLI import parse_arguments
from Main import main
from Utils import local_path, output_path, open_file

def bottom_frame(self,parent,args):
    self = ttk.Frame(parent)
    seedCountFrame = Frame(self)
    seedCountFrame.pack()
    ## Seed #
    seedLabel = Label(self, text='Seed #')
    self.seedVar = StringVar(value=parent.working_dirs["gen.seed"])
    def saveSeed(caller,_,mode):
        parent.working_dirs["gen.seed"] = self.seedVar.get()
    self.seedVar.trace_add("write",saveSeed)
    seedEntry = Entry(self, width=15, textvariable=self.seedVar)
    seedLabel.pack(side=LEFT)
    seedEntry.pack(side=LEFT)
    ## Number of Generation attempts
    countLabel = Label(self, text='Count')
    self.countVar = StringVar()
    countSpinbox = Spinbox(self, from_=1, to=100, width=5, textvariable=self.countVar)
    countLabel.pack(side=LEFT)
    countSpinbox.pack(side=LEFT)

    def generateRom():
        guiargs = Namespace()
        guiargs.remote_items = None
        guiargs.multi = int(parent.multiworldWindow.worldVar.get())
        guiargs.names = parent.multiworldWindow.namesVar.get()
        guiargs.seed = int(self.seedVar.get()) if self.seedVar.get() else None
        guiargs.count = int(self.countVar.get()) if self.countVar.get() != '1' else None
        guiargs.mode = parent.itemWindow.modeVar.get()
        guiargs.logic = parent.itemWindow.logicVar.get()

        guiargs.goal = parent.itemWindow.goalVar.get()
        guiargs.crystals_gt = parent.itemWindow.crystalsGTVar.get()
        guiargs.crystals_ganon = parent.itemWindow.crystalsGanonVar.get()
        guiargs.swords = parent.itemWindow.swordVar.get()
        guiargs.difficulty = parent.itemWindow.difficultyVar.get()
        guiargs.item_functionality = parent.itemWindow.itemfunctionVar.get()
        guiargs.timer = parent.itemWindow.timerVar.get()
        guiargs.progressive = parent.itemWindow.progressiveVar.get()
        guiargs.accessibility = parent.itemWindow.accessibilityVar.get()
        guiargs.algorithm = parent.itemWindow.algorithmVar.get()
        guiargs.shuffle = parent.entrandoWindow.shuffleVar.get()
        guiargs.door_shuffle = parent.dungeonRandoWindow.doorShuffleVar.get()
        guiargs.heartbeep = parent.romOptionsWindow.heartbeepVar.get()
        guiargs.heartcolor = parent.romOptionsWindow.heartcolorVar.get()
        guiargs.fastmenu = parent.romOptionsWindow.fastMenuVar.get()
        guiargs.create_spoiler = bool(parent.generationSetupWindow.createSpoilerVar.get())
        guiargs.skip_playthrough = not bool(parent.generationSetupWindow.createSpoilerVar.get())
        guiargs.suppress_rom = bool(parent.generationSetupWindow.suppressRomVar.get())
        guiargs.openpyramid = bool(parent.entrandoWindow.openpyramidVar.get())
        guiargs.mapshuffle = bool(parent.dungeonRandoWindow.mapshuffleVar.get())
        guiargs.compassshuffle = bool(parent.dungeonRandoWindow.compassshuffleVar.get())
        guiargs.keyshuffle = bool(parent.dungeonRandoWindow.keyshuffleVar.get())
        guiargs.bigkeyshuffle = bool(parent.dungeonRandoWindow.bigkeyshuffleVar.get())
        guiargs.retro = bool(parent.itemWindow.retroVar.get())
        guiargs.quickswap = bool(parent.romOptionsWindow.quickSwapVar.get())
        guiargs.disablemusic = bool(parent.romOptionsWindow.disableMusicVar.get())
        guiargs.ow_palettes = parent.romOptionsWindow.owPalettesVar.get()
        guiargs.uw_palettes = parent.romOptionsWindow.uwPalettesVar.get()
        guiargs.shuffleganon = bool(parent.entrandoWindow.shuffleGanonVar.get())
        guiargs.hints = bool(parent.romOptionsWindow.hintsVar.get())
        guiargs.enemizercli = parent.enemizerWindow.enemizerCLIpathVar.get()
        guiargs.shufflebosses = parent.enemizerWindow.enemizerBossVar.get()
        guiargs.shuffleenemies = parent.enemizerWindow.enemyShuffleVar.get()
        guiargs.enemy_health = parent.enemizerWindow.enemizerHealthVar.get()
        guiargs.enemy_damage = parent.enemizerWindow.enemizerDamageVar.get()
        guiargs.shufflepots = bool(parent.enemizerWindow.potShuffleVar.get())
        guiargs.custom = bool(parent.generationSetupWindow.customVar.get())
        guiargs.customitemarray = [int(parent.customContent.bowVar.get()), int(parent.customContent.silverarrowVar.get()), int(parent.customContent.boomerangVar.get()), int(parent.customContent.magicboomerangVar.get()), int(parent.customContent.hookshotVar.get()), int(parent.customContent.mushroomVar.get()), int(parent.customContent.magicpowderVar.get()), int(parent.customContent.firerodVar.get()),
                                   int(parent.customContent.icerodVar.get()), int(parent.customContent.bombosVar.get()), int(parent.customContent.etherVar.get()), int(parent.customContent.quakeVar.get()), int(parent.customContent.lampVar.get()), int(parent.customContent.hammerVar.get()), int(parent.customContent.shovelVar.get()), int(parent.customContent.fluteVar.get()), int(parent.customContent.bugnetVar.get()),
                                   int(parent.customContent.bookVar.get()), int(parent.customContent.bottleVar.get()), int(parent.customContent.somariaVar.get()), int(parent.customContent.byrnaVar.get()), int(parent.customContent.capeVar.get()), int(parent.customContent.mirrorVar.get()), int(parent.customContent.bootsVar.get()), int(parent.customContent.powergloveVar.get()), int(parent.customContent.titansmittVar.get()),
                                   int(parent.customContent.proggloveVar.get()), int(parent.customContent.flippersVar.get()), int(parent.customContent.pearlVar.get()), int(parent.customContent.heartpieceVar.get()), int(parent.customContent.fullheartVar.get()), int(parent.customContent.sancheartVar.get()), int(parent.customContent.sword1Var.get()), int(parent.customContent.sword2Var.get()),
                                   int(parent.customContent.sword3Var.get()), int(parent.customContent.sword4Var.get()), int(parent.customContent.progswordVar.get()), int(parent.customContent.shield1Var.get()), int(parent.customContent.shield2Var.get()), int(parent.customContent.shield3Var.get()), int(parent.customContent.progshieldVar.get()), int(parent.customContent.bluemailVar.get()),
                                   int(parent.customContent.redmailVar.get()), int(parent.customContent.progmailVar.get()), int(parent.customContent.halfmagicVar.get()), int(parent.customContent.quartermagicVar.get()), int(parent.customContent.bcap5Var.get()), int(parent.customContent.bcap10Var.get()), int(parent.customContent.acap5Var.get()), int(parent.customContent.acap10Var.get()),
                                   int(parent.customContent.arrow1Var.get()), int(parent.customContent.arrow10Var.get()), int(parent.customContent.bomb1Var.get()), int(parent.customContent.bomb3Var.get()), int(parent.customContent.rupee1Var.get()), int(parent.customContent.rupee5Var.get()), int(parent.customContent.rupee20Var.get()), int(parent.customContent.rupee50Var.get()), int(parent.customContent.rupee100Var.get()),
                                   int(parent.customContent.rupee300Var.get()), int(parent.customContent.rupoorVar.get()), int(parent.customContent.blueclockVar.get()), int(parent.customContent.greenclockVar.get()), int(parent.customContent.redclockVar.get()), int(parent.customContent.progbowVar.get()), int(parent.customContent.bomb10Var.get()), int(parent.customContent.triforcepieceVar.get()),
                                   int(parent.customContent.triforcecountVar.get()), int(parent.customContent.triforceVar.get()),  int(parent.customContent.rupoorcostVar.get()), int(parent.customContent.universalkeyVar.get())]
        guiargs.rom = parent.generationSetupWindow.romVar.get()
        guiargs.sprite = parent.romOptionsWindow.spriteNameVar
        guiargs.outputpath = args.outputpath if args else None
        # get default values for missing parameters
#        for k,v in vars(parse_arguments(['--multi', str(guiargs.multi)])).items():
#            if k not in vars(guiargs):
#                setattr(guiargs, k, v)
#            elif type(v) is dict: # use same settings for every player
#                setattr(guiargs, k, {player: getattr(guiargs, k) for player in range(1, guiargs.multi + 1)})
        try:
            if guiargs.count is not None:
                seed = guiargs.seed
                for _ in range(guiargs.count):
                    main(seed=seed, args=guiargs)
                    seed = random.randint(0, 999999999)
            else:
                main(seed=guiargs.seed, args=guiargs)
        except Exception as e:
            logging.exception(e)
            messagebox.showerror(title="Error while creating seed", message=str(e))
        else:
            messagebox.showinfo(title="Success", message="Rom patched successfully")

    ## Generate Button
    generateButton = Button(self, text='Generate Patched Rom', command=generateRom)
    generateButton.pack(side=LEFT)

    def open_output():
        if args and args.outputpath:
            open_file(output_path(args.outputpath))
        else:
            open_file(output_path(os.path.join(".")))

    openOutputButton = Button(self, text='Open Output Directory', command=open_output)
    openOutputButton.pack(side=RIGHT)

    if os.path.exists(local_path('README.html')):
        def open_readme():
            open_file(local_path('README.html'))
        openReadmeButton = Button(self, text='Open Documentation', command=open_readme)
        openReadmeButton.pack()

    return self
