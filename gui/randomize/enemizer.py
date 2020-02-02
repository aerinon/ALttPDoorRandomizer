from tkinter import ttk, filedialog, IntVar, StringVar, Button, Checkbutton, Entry, Frame, Label, LabelFrame, OptionMenu, E, W, LEFT, RIGHT, X

def enemizer_page(parent,working_dirs):
    self = ttk.Frame(parent)

    # Enemizer
    enemizerFrame = LabelFrame(self, text="Enemizer")
    enemizerFrame.columnconfigure(0, weight=1)
    enemizerFrame.columnconfigure(1, weight=1)
    enemizerFrame.columnconfigure(2, weight=1)
    enemizerFrame.columnconfigure(3, weight=1)

    ## Enemizer CLI Path
    enemizerPathFrame = Frame(self)
    enemizerPathFrame.grid(row=0, column=0, columnspan=3, sticky=W+E)
    enemizerCLIlabel = Label(enemizerPathFrame, text="EnemizerCLI path: ")
    enemizerCLIlabel.pack(side=LEFT)
    self.enemizerCLIpathVar = StringVar(value=working_dirs["enemizer.cli"])
    def saveEnemizerPath(caller,_,mode):
        working_dirs["enemizer.cli"] = self.enemizerCLIpathVar.get()
    self.enemizerCLIpathVar.trace_add("write",saveEnemizerPath)
    enemizerCLIpathEntry = Entry(enemizerPathFrame, textvariable=self.enemizerCLIpathVar)
    enemizerCLIpathEntry.pack(side=LEFT, fill=X, expand=True)
    def EnemizerSelectPath():
        path = filedialog.askopenfilename(filetypes=[("EnemizerCLI executable", "*EnemizerCLI*")])
        if path:
            self.enemizerCLIpathVar.set(path)
            working_dirs["enemizer.cli"] = path
    enemizerCLIbrowseButton = Button(enemizerPathFrame, text='...', command=EnemizerSelectPath)
    enemizerCLIbrowseButton.pack(side=LEFT)

    ## Pot Shuffle
    self.potShuffleVar = IntVar()
    potShuffleButton = Checkbutton(self, text="Pot shuffle", variable=self.potShuffleVar)
    potShuffleButton.grid(row=0, column=3)

    ## Randomize Enemies
    enemizerEnemyFrame = Frame(self)
    enemizerEnemyFrame.grid(row=1, column=0)
    enemizerEnemyLabel = Label(enemizerEnemyFrame, text='Enemy shuffle')
    enemizerEnemyLabel.pack(side=LEFT)
    self.enemyShuffleVar = StringVar()
    self.enemyShuffleVar.set('none')
    enemizerEnemyOption = OptionMenu(enemizerEnemyFrame, self.enemyShuffleVar, 'none', 'shuffled', 'chaos')
    enemizerEnemyOption.pack(side=LEFT)

    ## Randomize Bosses
    enemizerBossFrame = Frame(self)
    enemizerBossFrame.grid(row=1, column=1)
    enemizerBossLabel = Label(enemizerBossFrame, text='Boss shuffle')
    enemizerBossLabel.pack(side=LEFT)
    self.enemizerBossVar = StringVar()
    self.enemizerBossVar.set('none')
    enemizerBossOption = OptionMenu(enemizerBossFrame, self.enemizerBossVar, 'none', 'basic', 'normal', 'chaos')
    enemizerBossOption.pack(side=LEFT)

    ## Enemy Damage
    enemizerDamageFrame = Frame(self)
    enemizerDamageFrame.grid(row=1, column=2)
    enemizerDamageLabel = Label(enemizerDamageFrame, text='Enemy damage')
    enemizerDamageLabel.pack(side=LEFT)
    self.enemizerDamageVar = StringVar()
    self.enemizerDamageVar.set('default')
    enemizerDamageOption = OptionMenu(enemizerDamageFrame, self.enemizerDamageVar, 'default', 'shuffled', 'chaos')
    enemizerDamageOption.pack(side=LEFT)

    ## Enemy Health
    enemizerHealthFrame = Frame(self)
    enemizerHealthFrame.grid(row=1, column=3)
    enemizerHealthLabel = Label(enemizerHealthFrame, text='Enemy health')
    enemizerHealthLabel.pack(side=LEFT)
    self.enemizerHealthVar = StringVar()
    self.enemizerHealthVar.set('default')
    enemizerHealthOption = OptionMenu(enemizerHealthFrame, self.enemizerHealthVar, 'default', 'easy', 'normal', 'hard', 'expert')
    enemizerHealthOption.pack(side=LEFT)

    return self,working_dirs
