from tkinter import ttk, filedialog, messagebox, IntVar, StringVar, Button, Checkbutton, Entry, Frame, Label, OptionMenu, Spinbox, E, W, LEFT, RIGHT, X
from argparse import Namespace
import logging
import random

def generation_page(parent,working_dirs):
    self = ttk.Frame(parent)

    # Generation Setup options
    ## Generate Spoiler
    self.createSpoilerVar = IntVar()
    createSpoilerCheckbutton = Checkbutton(self, text="Create Spoiler Log", variable=self.createSpoilerVar)
    createSpoilerCheckbutton.pack(anchor=W)
    ## Don't make ROM
    self.suppressRomVar = IntVar()
    suppressRomCheckbutton = Checkbutton(self, text="Do not create patched Rom", variable=self.suppressRomVar)
    suppressRomCheckbutton.pack(anchor=W)
    ## Use Custom Item Pool as defined in Custom tab
    self.customVar = IntVar()
    customCheckbutton = Checkbutton(self, text="Use custom item pool", variable=self.customVar)
    customCheckbutton.pack(anchor=W)
    ## Locate base ROM
    baseRomFrame = Frame(self)
    baseRomLabel = Label(baseRomFrame, text='Base Rom: ')
    self.romVar = StringVar(value=working_dirs["rom.base"])
    def saveBaseRom(caller,_,mode):
        working_dirs["rom.base"] = self.romVar.get()
    self.romVar.trace_add("write",saveBaseRom)
    romEntry = Entry(baseRomFrame, textvariable=self.romVar)

    def RomSelect():
        rom = filedialog.askopenfilename(filetypes=[("Rom Files", (".sfc", ".smc")), ("All Files", "*")])
        self.romVar.set(rom)
    romSelectButton = Button(baseRomFrame, text='Select Rom', command=RomSelect)

    baseRomLabel.pack(side=LEFT)
    romEntry.pack(side=LEFT, fill=X, expand=True)
    romSelectButton.pack(side=LEFT)
    baseRomFrame.pack(fill=X, expand=True)

    return self,working_dirs
