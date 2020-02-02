from tkinter import ttk, IntVar, StringVar, Button, Checkbutton, Entry, Frame, Label, OptionMenu, Spinbox, E, W, LEFT, RIGHT
from classes.SpriteSelector import SpriteSelector

def gameoptions_page(parent):
    self = ttk.Frame(parent)

    # Game Options options
    ## Hints: Useful/Not useful
    self.hintsVar = IntVar()
    self.hintsVar.set(1) #set default
    hintsCheckbutton = Checkbutton(self, text="Include Helpful Hints", variable=self.hintsVar)
    hintsCheckbutton.pack(anchor=W)

    ## Disable BGM
    self.disableMusicVar = IntVar()
    disableMusicCheckbutton = Checkbutton(self, text="Disable music", variable=self.disableMusicVar)
    disableMusicCheckbutton.pack(anchor=W)

    ## L/R Quickswap
    self.quickSwapVar = IntVar()
    quickSwapCheckbutton = Checkbutton(self, text="L/R Quickswapping", variable=self.quickSwapVar)
    quickSwapCheckbutton.pack(anchor=W)

    leftRomOptionsFrame = Frame(self)
    rightRomOptionsFrame = Frame(self)
    leftRomOptionsFrame.pack(side=LEFT)
    rightRomOptionsFrame.pack(side=RIGHT)

    ## Heart Color
    heartcolorFrame = Frame(leftRomOptionsFrame)
    heartcolorLabel = Label(heartcolorFrame, text='Heart color')
    heartcolorLabel.pack(side=LEFT)
    self.heartcolorVar = StringVar()
    self.heartcolorVar.set('red')
    heartcolorOptionMenu = OptionMenu(heartcolorFrame, self.heartcolorVar, 'red', 'blue', 'green', 'yellow', 'random')
    heartcolorOptionMenu.pack(side=RIGHT)
    heartcolorFrame.pack(anchor=E)

    ## Heart Beep Speed
    heartbeepFrame = Frame(leftRomOptionsFrame)
    heartbeepLabel = Label(heartbeepFrame, text='Heart Beep sound rate')
    heartbeepLabel.pack(side=LEFT)
    self.heartbeepVar = StringVar()
    self.heartbeepVar.set('normal')
    heartbeepOptionMenu = OptionMenu(heartbeepFrame, self.heartbeepVar, 'double', 'normal', 'half', 'quarter', 'off')
    heartbeepOptionMenu.pack(side=LEFT)
    heartbeepFrame.pack(anchor=E)

    ## Sprite selection
    spriteDialogFrame = Frame(leftRomOptionsFrame)
    baseSpriteLabel = Label(spriteDialogFrame, text='Sprite:')

    self.spriteNameVar = StringVar()
    sprite = None
    def set_sprite(sprite_param):
        nonlocal sprite
        if sprite_param is None or not sprite_param.valid:
            sprite = None
            self.spriteNameVar.set('(unchanged)')
        else:
            sprite = sprite_param
            self.spriteNameVar.set(sprite.name)

    set_sprite(None)
    self.spriteNameVar.set('(unchanged)')
    spriteEntry = Label(spriteDialogFrame, textvariable=self.spriteNameVar)

    def SpriteSelect():
        SpriteSelector(parent, set_sprite)

    spriteSelectButton = Button(spriteDialogFrame, text='...', command=SpriteSelect)

    baseSpriteLabel.pack(side=LEFT)
    spriteEntry.pack(side=LEFT)
    spriteSelectButton.pack(side=LEFT)
    spriteDialogFrame.pack(anchor=E)

    ## Menu Speed
    fastMenuFrame = Frame(rightRomOptionsFrame)
    fastMenuLabel = Label(fastMenuFrame, text='Menu speed')
    fastMenuLabel.pack(side=LEFT)
    self.fastMenuVar = StringVar()
    self.fastMenuVar.set('normal')
    fastMenuOptionMenu = OptionMenu(fastMenuFrame, self.fastMenuVar, 'normal', 'instant', 'double', 'triple', 'quadruple', 'half')
    fastMenuOptionMenu.pack(side=LEFT)
    fastMenuFrame.pack(anchor=E)

    ## Overworld Palettes (not Enemizer)
    owPalettesFrame = Frame(rightRomOptionsFrame)
    owPalettesLabel = Label(owPalettesFrame, text='Overworld palettes')
    owPalettesLabel.pack(side=LEFT)
    self.owPalettesVar = StringVar()
    self.owPalettesVar.set('default')
    owPalettesOptionMenu = OptionMenu(owPalettesFrame, self.owPalettesVar, 'default', 'random', 'blackout')
    owPalettesOptionMenu.pack(side=LEFT)
    owPalettesFrame.pack(anchor=E)

    ## Underworld Palettes (not Enemizer)
    uwPalettesFrame = Frame(rightRomOptionsFrame)
    uwPalettesLabel = Label(uwPalettesFrame, text='Dungeon palettes')
    uwPalettesLabel.pack(side=LEFT)
    self.uwPalettesVar = StringVar()
    self.uwPalettesVar.set('default')
    uwPalettesOptionMenu = OptionMenu(uwPalettesFrame, self.uwPalettesVar, 'default', 'random', 'blackout')
    uwPalettesOptionMenu.pack(side=LEFT)
    uwPalettesFrame.pack(anchor=E)

    return self
