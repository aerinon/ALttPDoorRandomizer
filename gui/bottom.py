from tkinter import ttk, filedialog, messagebox, IntVar, StringVar, Button, Checkbutton, Entry, Frame, Label, OptionMenu, Spinbox, E, W, LEFT, RIGHT, X
from argparse import Namespace
import logging
import os
import random
from Utils import is_bundled, local_path, output_path, open_file

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
        guiargs.create_spoiler = bool(self.createSpoilerVar.get())
        guiargs.skip_playthrough = not bool(self.createSpoilerVar.get())
        guiargs.suppress_rom = bool(self.suppressRomVar.get())
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
        guiargs.custom = bool(parent.romOptionsWindow.customVar.get())
        guiargs.customitemarray = [int(parent.customWindow.bowVar.get()), int(parent.customWindow.silverarrowVar.get()), int(parent.customWindow.boomerangVar.get()), int(parent.customWindow.magicboomerangVar.get()), int(parent.customWindow.hookshotVar.get()), int(parent.customWindow.mushroomVar.get()), int(parent.customWindow.magicpowderVar.get()), int(parent.customWindow.firerodVar.get()),
                                   int(parent.customWindow.icerodVar.get()), int(parent.customWindow.bombosVar.get()), int(parent.customWindow.etherVar.get()), int(parent.customWindow.quakeVar.get()), int(parent.customWindow.lampVar.get()), int(parent.customWindow.hammerVar.get()), int(parent.customWindow.shovelVar.get()), int(parent.customWindow.fluteVar.get()), int(parent.customWindow.bugnetVar.get()),
                                   int(parent.customWindow.bookVar.get()), int(parent.customWindow.bottleVar.get()), int(parent.customWindow.somariaVar.get()), int(parent.customWindow.byrnaVar.get()), int(parent.customWindow.capeVar.get()), int(parent.customWindow.mirrorVar.get()), int(parent.customWindow.bootsVar.get()), int(parent.customWindow.powergloveVar.get()), int(parent.customWindow.titansmittVar.get()),
                                   int(parent.customWindow.proggloveVar.get()), int(parent.customWindow.flippersVar.get()), int(parent.customWindow.pearlVar.get()), int(parent.customWindow.heartpieceVar.get()), int(parent.customWindow.fullheartVar.get()), int(parent.customWindow.sancheartVar.get()), int(parent.customWindow.sword1Var.get()), int(parent.customWindow.sword2Var.get()),
                                   int(parent.customWindow.sword3Var.get()), int(parent.customWindow.sword4Var.get()), int(parent.customWindow.progswordVar.get()), int(parent.customWindow.shield1Var.get()), int(parent.customWindow.shield2Var.get()), int(parent.customWindow.shield3Var.get()), int(parent.customWindow.progshieldVar.get()), int(parent.customWindow.bluemailVar.get()),
                                   int(parent.customWindow.redmailVar.get()), int(parent.customWindow.progmailVar.get()), int(parent.customWindow.halfmagicVar.get()), int(parent.customWindow.quartermagicVar.get()), int(parent.customWindow.bcap5Var.get()), int(parent.customWindow.bcap10Var.get()), int(parent.customWindow.acap5Var.get()), int(parent.customWindow.acap10Var.get()),
                                   int(parent.customWindow.arrow1Var.get()), int(parent.customWindow.arrow10Var.get()), int(parent.customWindow.bomb1Var.get()), int(parent.customWindow.bomb3Var.get()), int(parent.customWindow.rupee1Var.get()), int(parent.customWindow.rupee5Var.get()), int(parent.customWindow.rupee20Var.get()), int(parent.customWindow.rupee50Var.get()), int(parent.customWindow.rupee100Var.get()),
                                   int(parent.customWindow.rupee300Var.get()), int(parent.customWindow.rupoorVar.get()), int(parent.customWindow.blueclockVar.get()), int(parent.customWindow.greenclockVar.get()), int(parent.customWindow.redclockVar.get()), int(parent.customWindow.progbowVar.get()), int(parent.customWindow.bomb10Var.get()), int(parent.customWindow.triforcepieceVar.get()),
                                   int(parent.customWindow.triforcecountVar.get()), int(parent.customWindow.triforceVar.get()),  int(parent.customWindow.rupoorcostVar.get()), int(parent.customWindow.universalkeyVar.get())]
        guiargs.rom = self.romVar.get()
        guiargs.sprite = parent.romOptionsWindow.sprite
        guiargs.outputpath = args.outputpath
        # get default values for missing parameters
        for k,v in vars(parent.parse_arguments(['--multi', str(guiargs.multi)])).items():
            if k not in vars(guiargs):
                setattr(guiargs, k, v)
            elif type(v) is dict: # use same settings for every player
                setattr(guiargs, k, {player: getattr(guiargs, k) for player in range(1, guiargs.multi + 1)})
        try:
            if guiargs.count is not None:
                seed = guiargs.seed
                for _ in range(guiargs.count):
                    parent.main(seed=seed, args=guiargs)
                    seed = random.randint(0, 999999999)
            else:
                parent.main(seed=guiargs.seed, args=guiargs)
        except Exception as e:
            logging.exception(e)
            messagebox.showerror(title="Error while creating seed", message=str(e))
        else:
            messagebox.showinfo(title="Success", message="Rom patched successfully")

    ## Generate Button
    generateButton = Button(self, text='Generate Patched Rom', command=generateRom)
    generateButton.pack(side=LEFT)

    def open_output():
        if args.outputpath:
            open_file(output_path(args.outputpath))
        else:
            open_file(output_path(''))

    openOutputButton = Button(self, text='Open Output Directory', command=open_output)
    openOutputButton.pack(side=RIGHT)

    if os.path.exists(local_path('README.html')):
        def open_readme():
            open_file(local_path('README.html'))
        openReadmeButton = Button(self, text='Open Documentation', command=open_readme)
        openReadmeButton.pack()

    return self
