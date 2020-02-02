from tkinter import ttk, IntVar, StringVar, Checkbutton, Frame, Label, OptionMenu, E, W, LEFT, RIGHT

def item_page(parent):
    # Item Randomizer
    self = ttk.Frame(parent)

    # Item Randomizer options
    ## Retro (eventually needs to become a World State)
    self.retroVar = IntVar()
    retroCheckbutton = Checkbutton(self, text="Retro mode (universal keys)", variable=self.retroVar)
    retroCheckbutton.pack(anchor=W)

    leftItemFrame = Frame(self)
    rightItemFrame = Frame(self)
    leftItemFrame.pack(side=LEFT)
    rightItemFrame.pack(side=RIGHT)

    ## World State
    modeFrame = Frame(leftItemFrame)
    self.modeVar = StringVar()
    self.modeVar.set('open')
    modeOptionMenu = OptionMenu(modeFrame, self.modeVar, 'standard', 'open', 'inverted')
    modeOptionMenu.pack(side=RIGHT)
    modeLabel = Label(modeFrame, text='World State')
    modeLabel.pack(side=LEFT)
    modeFrame.pack(anchor=E)

    ## Logic Level
    logicFrame = Frame(leftItemFrame)
    self.logicVar = StringVar()
    self.logicVar.set('noglitches')
    logicOptionMenu = OptionMenu(logicFrame, self.logicVar, 'noglitches', 'minorglitches', 'nologic')
    logicOptionMenu.pack(side=RIGHT)
    logicLabel = Label(logicFrame, text='Game Logic')
    logicLabel.pack(side=LEFT)
    logicFrame.pack(anchor=E)

    ## Goal
    goalFrame = Frame(leftItemFrame)
    self.goalVar = StringVar()
    self.goalVar.set('ganon')
    goalOptionMenu = OptionMenu(goalFrame, self.goalVar, 'ganon', 'pedestal', 'dungeons', 'triforcehunt', 'crystals')
    goalOptionMenu.pack(side=RIGHT)
    goalLabel = Label(goalFrame, text='Goal')
    goalLabel.pack(side=LEFT)
    goalFrame.pack(anchor=E)

    ## Number of crystals to open GT
    crystalsGTFrame = Frame(leftItemFrame)
    self.crystalsGTVar = StringVar()
    self.crystalsGTVar.set('7')
    crystalsGTOptionMenu = OptionMenu(crystalsGTFrame, self.crystalsGTVar, '0', '1', '2', '3', '4', '5', '6', '7', 'random')
    crystalsGTOptionMenu.pack(side=RIGHT)
    crystalsGTLabel = Label(crystalsGTFrame, text='Crystals to open Ganon\'s Tower')
    crystalsGTLabel.pack(side=LEFT)
    crystalsGTFrame.pack(anchor=E)

    ## Number of crystals to damage Ganon
    crystalsGanonFrame = Frame(leftItemFrame)
    self.crystalsGanonVar = StringVar()
    self.crystalsGanonVar.set('7')
    crystalsGanonOptionMenu = OptionMenu(crystalsGanonFrame, self.crystalsGanonVar, '0', '1', '2', '3', '4', '5', '6', '7', 'random')
    crystalsGanonOptionMenu.pack(side=RIGHT)
    crystalsGanonLabel = Label(crystalsGanonFrame, text='Crystals to fight Ganon')
    crystalsGanonLabel.pack(side=LEFT)
    crystalsGanonFrame.pack(anchor=E)

    ## Weapons
    swordFrame = Frame(leftItemFrame)
    self.swordVar = StringVar()
    self.swordVar.set('random')
    swordOptionMenu = OptionMenu(swordFrame, self.swordVar, 'random', 'assured', 'swordless', 'vanilla')
    swordOptionMenu.pack(side=RIGHT)
    swordLabel = Label(swordFrame, text='Sword availability')
    swordLabel.pack(side=LEFT)
    swordFrame.pack(anchor=E)

    ## Item Pool
    difficultyFrame = Frame(rightItemFrame)
    self.difficultyVar = StringVar()
    self.difficultyVar.set('normal')
    difficultyOptionMenu = OptionMenu(difficultyFrame, self.difficultyVar, 'normal', 'hard', 'expert')
    difficultyOptionMenu.pack(side=RIGHT)
    difficultyLabel = Label(difficultyFrame, text='Difficulty: item pool')
    difficultyLabel.pack(side=LEFT)
    difficultyFrame.pack(anchor=E)

    ## Item Functionality
    itemfunctionFrame = Frame(rightItemFrame)
    self.itemfunctionVar = StringVar()
    self.itemfunctionVar.set('normal')
    itemfunctionOptionMenu = OptionMenu(itemfunctionFrame, self.itemfunctionVar, 'normal', 'hard', 'expert')
    itemfunctionOptionMenu.pack(side=RIGHT)
    itemfunctionLabel = Label(itemfunctionFrame, text='Difficulty: item functionality')
    itemfunctionLabel.pack(side=LEFT)
    itemfunctionFrame.pack(anchor=E)

    ## Timer setting
    timerFrame = Frame(rightItemFrame)
    self.timerVar = StringVar()
    self.timerVar.set('none')
    timerOptionMenu = OptionMenu(timerFrame, self.timerVar, 'none', 'display', 'timed', 'timed-ohko', 'ohko', 'timed-countdown')
    timerOptionMenu.pack(side=RIGHT)
    timerLabel = Label(timerFrame, text='Timer setting')
    timerLabel.pack(side=LEFT)
    timerFrame.pack(anchor=E)

    ## Progressives: On/Off
    progressiveFrame = Frame(rightItemFrame)
    self.progressiveVar = StringVar()
    self.progressiveVar.set('on')
    progressiveOptionMenu = OptionMenu(progressiveFrame, self.progressiveVar, 'on', 'off', 'random')
    progressiveOptionMenu.pack(side=RIGHT)
    progressiveLabel = Label(progressiveFrame, text='Progressive equipment')
    progressiveLabel.pack(side=LEFT)
    progressiveFrame.pack(anchor=E)

    ## Accessibilty
    accessibilityFrame = Frame(rightItemFrame)
    self.accessibilityVar = StringVar()
    self.accessibilityVar.set('items')
    accessibilityOptionMenu = OptionMenu(accessibilityFrame, self.accessibilityVar, 'items', 'locations', 'none')
    accessibilityOptionMenu.pack(side=RIGHT)
    accessibilityLabel = Label(accessibilityFrame, text='Item accessibility')
    accessibilityLabel.pack(side=LEFT)
    accessibilityFrame.pack(anchor=E)
    accessibilityFrame.pack(anchor=E)

    ## Item Sorting Algorithm
    algorithmFrame = Frame(rightItemFrame)
    self.algorithmVar = StringVar()
    self.algorithmVar.set('balanced')
    algorithmOptionMenu = OptionMenu(algorithmFrame, self.algorithmVar, 'freshness', 'flood', 'vt21', 'vt22', 'vt25', 'vt26', 'balanced')
    algorithmOptionMenu.pack(side=RIGHT)
    algorithmLabel = Label(algorithmFrame, text='Item distribution algorithm')
    algorithmLabel.pack(side=LEFT)
    algorithmFrame.pack(anchor=E)

    return self
