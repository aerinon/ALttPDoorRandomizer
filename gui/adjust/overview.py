from tkinter import ttk, filedialog, messagebox, IntVar, StringVar, Button, Checkbutton, Entry, Frame, Label, OptionMenu, Spinbox, E, W, LEFT, RIGHT, X, BOTTOM
from AdjusterMain import adjust
from argparse import Namespace
from classes.SpriteSelector import SpriteSelector
import logging

def adjust_page(top,parent,working_dirs):
    self = ttk.Frame(parent)

    rightHalfFrame2 = Frame(self)
    checkBoxFrame2 = Frame(rightHalfFrame2)

    quickSwapCheckbutton2 = Checkbutton(checkBoxFrame2, text="Enabled L/R Item quickswapping", variable=top.romOptionsWindow.quickSwapVar)
    disableMusicCheckbutton2 = Checkbutton(checkBoxFrame2, text="Disable game music", variable=top.romOptionsWindow.disableMusicVar)

    quickSwapCheckbutton2.pack(anchor=W)
    disableMusicCheckbutton2.pack(anchor=W)

    fileDialogFrame2 = Frame(rightHalfFrame2)

    romDialogFrame2 = Frame(fileDialogFrame2)
    baseRomLabel2 = Label(romDialogFrame2, text='Rom to adjust')
    romVar2 = StringVar(value=working_dirs["adjust.rom"])
    romEntry2 = Entry(romDialogFrame2, textvariable=romVar2)

    def RomSelect2():
        rom = filedialog.askopenfilename(filetypes=[("Rom Files", (".sfc", ".smc")), ("All Files", "*")])
        if rom:
            working_dirs["adjust.rom"] = rom
            romVar2.set(rom)
    romSelectButton2 = Button(romDialogFrame2, text='Select Rom', command=RomSelect2)

    baseRomLabel2.pack(side=LEFT)
    romEntry2.pack(side=LEFT)
    romSelectButton2.pack(side=LEFT)

    spriteDialogFrame2 = Frame(fileDialogFrame2)
    baseSpriteLabel2 = Label(spriteDialogFrame2, text='Link Sprite')
    spriteEntry2 = Label(spriteDialogFrame2, textvariable=top.romOptionsWindow.spriteNameVar)

    def set_sprite(sprite_param):
        if sprite_param is None or not sprite_param.valid:
            sprite = None
            top.romOptionsWindow.spriteNameVar.set('(unchanged)')
        else:
            sprite = sprite_param
            top.romOptionsWindow.spriteNameVar.set(sprite.name)

    def SpriteSelectAdjuster():
        SpriteSelector(parent, set_sprite, adjuster=True)

    spriteSelectButton2 = Button(spriteDialogFrame2, text='Select Sprite', command=SpriteSelectAdjuster)

    baseSpriteLabel2.pack(side=LEFT)
    spriteEntry2.pack(side=LEFT)
    spriteSelectButton2.pack(side=LEFT)

    romDialogFrame2.pack()
    spriteDialogFrame2.pack()

    checkBoxFrame2.pack()
    fileDialogFrame2.pack()

    drowDownFrame2 = Frame(self)
    heartbeepFrame2 = Frame(drowDownFrame2)
    heartbeepOptionMenu2 = OptionMenu(heartbeepFrame2, top.romOptionsWindow.heartbeepVar, 'double', 'normal', 'half', 'quarter', 'off')
    heartbeepOptionMenu2.pack(side=RIGHT)
    heartbeepLabel2 = Label(heartbeepFrame2, text='Heartbeep sound rate')
    heartbeepLabel2.pack(side=LEFT)

    heartcolorFrame2 = Frame(drowDownFrame2)
    heartcolorOptionMenu2 = OptionMenu(heartcolorFrame2, top.romOptionsWindow.heartcolorVar, 'red', 'blue', 'green', 'yellow', 'random')
    heartcolorOptionMenu2.pack(side=RIGHT)
    heartcolorLabel2 = Label(heartcolorFrame2, text='Heart color')
    heartcolorLabel2.pack(side=LEFT)

    fastMenuFrame2 = Frame(drowDownFrame2)
    fastMenuOptionMenu2 = OptionMenu(fastMenuFrame2, top.romOptionsWindow.fastMenuVar, 'normal', 'instant', 'double', 'triple', 'quadruple', 'half')
    fastMenuOptionMenu2.pack(side=RIGHT)
    fastMenuLabel2 = Label(fastMenuFrame2, text='Menu speed')
    fastMenuLabel2.pack(side=LEFT)

    owPalettesFrame2 = Frame(drowDownFrame2)
    owPalettesOptionMenu2 = OptionMenu(owPalettesFrame2, top.romOptionsWindow.owPalettesVar, 'default', 'random', 'blackout')
    owPalettesOptionMenu2.pack(side=RIGHT)
    owPalettesLabel2 = Label(owPalettesFrame2, text='Overworld palettes')
    owPalettesLabel2.pack(side=LEFT)

    uwPalettesFrame2 = Frame(drowDownFrame2)
    uwPalettesOptionMenu2 = OptionMenu(uwPalettesFrame2, top.romOptionsWindow.uwPalettesVar, 'default', 'random', 'blackout')
    uwPalettesOptionMenu2.pack(side=RIGHT)
    uwPalettesLabel2 = Label(uwPalettesFrame2, text='Dungeon palettes')
    uwPalettesLabel2.pack(side=LEFT)

    heartbeepFrame2.pack(anchor=E)
    heartcolorFrame2.pack(anchor=E)
    fastMenuFrame2.pack(anchor=E)
    owPalettesFrame2.pack(anchor=E)
    uwPalettesFrame2.pack(anchor=E)

    bottomFrame2 = Frame(self)

    def adjustRom():
        guiargs = Namespace()
        guiargs.heartbeep = top.romOptionsWindow.heartbeepVar.get()
        guiargs.heartcolor = top.romOptionsWindow.heartcolorVar.get()
        guiargs.fastmenu = top.romOptionsWindow.fastMenuVar.get()
        guiargs.ow_palettes = top.romOptionsWindow.owPalettesVar.get()
        guiargs.uw_palettes = top.romOptionsWindow.uwPalettesVar.get()
        guiargs.quickswap = bool(top.romOptionsWindow.quickSwapVar.get())
        guiargs.disablemusic = bool(top.romOptionsWindow.disableMusicVar.get())
        guiargs.rom = romVar2.get()
        guiargs.baserom = top.generationSetupWindow.romVar.get()
#        guiargs.sprite = sprite
        try:
            adjust(args=guiargs)
        except Exception as e:
            logging.exception(e)
            messagebox.showerror(title="Error while creating seed", message=str(e))
        else:
            messagebox.showinfo(title="Success", message="Rom patched successfully")

    adjustButton = Button(bottomFrame2, text='Adjust Rom', command=adjustRom)

    adjustButton.pack(side=LEFT, padx=(5, 0))

    drowDownFrame2.pack(side=LEFT, pady=(0, 40))
    rightHalfFrame2.pack(side=RIGHT)
    bottomFrame2.pack(side=BOTTOM, pady=(180, 0))

    return self,working_dirs
