from tkinter import ttk, IntVar, StringVar, Checkbutton, Frame, Label, OptionMenu, E, W, LEFT, RIGHT

def entrando_page(parent):
    # Entrance Randomizer
    self = ttk.Frame(parent)

    # Entrance Randomizer options
    ## Pyramid pre-opened
    self.openpyramidVar = IntVar()
    openpyramidCheckbutton = Checkbutton(self, text="Pre-open Pyramid Hole", variable=self.openpyramidVar)
    openpyramidCheckbutton.pack(anchor=W)
    ## Shuffle Ganon
    self.shuffleGanonVar = IntVar()
    self.shuffleGanonVar.set(1) #set default
    shuffleGanonCheckbutton = Checkbutton(self, text="Include Ganon's Tower and Pyramid Hole in shuffle pool", variable=self.shuffleGanonVar)
    shuffleGanonCheckbutton.pack(anchor=W)
    ## Entrance Shuffle
    shuffleFrame = Frame(self)
    self.shuffleVar = StringVar()
    self.shuffleVar.set('vanilla')
    shuffleOptionMenu = OptionMenu(shuffleFrame, self.shuffleVar, 'vanilla', 'simple', 'restricted', 'full', 'crossed', 'insanity', 'restricted_legacy', 'full_legacy', 'madness_legacy', 'insanity_legacy', 'dungeonsfull', 'dungeonssimple')
    shuffleOptionMenu.pack(side=RIGHT)
    shuffleLabel = Label(shuffleFrame, text='Entrance shuffle algorithm')
    shuffleLabel.pack(side=LEFT)
    shuffleFrame.pack(anchor=W)

    return self
