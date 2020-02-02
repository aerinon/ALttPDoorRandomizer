from tkinter import ttk, IntVar, StringVar, Checkbutton, Frame, Label, OptionMenu, E, W, LEFT, RIGHT

def dungeon_page(parent):
    self = ttk.Frame(parent)

    # Dungeon Shuffle options
    ## Dungeon Item Shuffle
    mcsbshuffleFrame = Frame(self)
    mcsbshuffleFrame.pack(anchor=W)
    mcsbLabel = Label(mcsbshuffleFrame, text="Shuffle: ")
    mcsbLabel.grid(row=0, column=0)
    ## Map Shuffle
    self.mapshuffleVar = IntVar()
    mapshuffleCheckbutton = Checkbutton(mcsbshuffleFrame, text="Maps", variable=self.mapshuffleVar)
    mapshuffleCheckbutton.grid(row=0, column=1)
    ## Compass Shuffle
    self.compassshuffleVar = IntVar()
    compassshuffleCheckbutton = Checkbutton(mcsbshuffleFrame, text="Compasses", variable=self.compassshuffleVar)
    compassshuffleCheckbutton.grid(row=0, column=2)
    ## Small Key Shuffle
    self.keyshuffleVar = IntVar()
    keyshuffleCheckbutton = Checkbutton(mcsbshuffleFrame, text="Keys", variable=self.keyshuffleVar)
    keyshuffleCheckbutton.grid(row=0, column=3)
    ## Big Key Shuffle
    self.bigkeyshuffleVar = IntVar()
    bigkeyshuffleCheckbutton = Checkbutton(mcsbshuffleFrame, text="BigKeys", variable=self.bigkeyshuffleVar)
    bigkeyshuffleCheckbutton.grid(row=0, column=4)
    ## Dungeon Door Shuffle
    doorShuffleFrame = Frame(self)
    self.doorShuffleVar = StringVar()
    self.doorShuffleVar.set('basic')
    doorShuffleOptionMenu = OptionMenu(doorShuffleFrame, self.doorShuffleVar, 'vanilla', 'basic', 'crossed', 'experimental')
    doorShuffleOptionMenu.pack(side=RIGHT)
    doorShuffleLabel = Label(doorShuffleFrame, text='Door shuffle algorithm')
    doorShuffleLabel.pack(side=LEFT)
    doorShuffleFrame.pack(anchor=W)

    return self
