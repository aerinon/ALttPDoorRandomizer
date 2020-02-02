from tkinter import ttk, IntVar, StringVar, Checkbutton, Entry, Frame, Label, OptionMenu, Spinbox, E, W, LEFT, RIGHT

def multiworld_page(parent,working_dirs):
    self = ttk.Frame(parent)

    # Multiworld
    multiFrame = Frame(self)
    ## Number of Worlds
    worldLabel = Label(multiFrame, text='Worlds')
    self.worldVar = StringVar()
    worldSpinbox = Spinbox(multiFrame, from_=1, to=100, width=5, textvariable=self.worldVar)
    worldLabel.pack(side=LEFT)
    worldSpinbox.pack(side=LEFT)
    ## List of Player Names
    namesLabel = Label(multiFrame, text='Player names')
    self.namesVar = StringVar(value=working_dirs["multi.names"])
    def saveMultiNames(caller,_,mode):
        working_dirs["multi.names"] = self.namesVar.get()
    self.namesVar.trace_add("write",saveMultiNames)
    namesEntry = Entry(multiFrame, textvariable=self.namesVar)
    namesLabel.pack(side=LEFT)
    namesEntry.pack(side=LEFT)
    multiFrame.pack(anchor=W)

    return self,working_dirs
