from tkinter import ttk, Frame, Label, E, W, LEFT, RIGHT
import source.gui.widgets as widgets
import json
import os

def item_page(parent):
    # Item Randomizer
    self = ttk.Frame(parent)

    # Item Randomizer options
    self.widgets = {}

    # Item Randomizer option sections
    self.frames = {}
    self.frames["futuro"] = Frame(self)
    self.frames["futuro"].pack(anchor=W)

    ## Dungeon Item Shuffle
    mscbLabel = Label(self.frames["futuro"], text="Futuro: ")
    mscbLabel.pack(side=LEFT)

    # Load Dungeon Shuffle option widgets as defined by JSON file
    # Defns include frame name, widget type, widget options, widget placement attributes
    # This first set goes in the Keysanity frame
    with open(os.path.join("resources","app","gui","randomize","item","futuro.json")) as futuroItems:
        myDict = json.load(futuroItems)
        myDict = myDict["futuro"]
        dictWidgets = widgets.make_widgets_from_dict(self, myDict, self.frames["futuro"])
        for key in dictWidgets:
            self.widgets[key] = dictWidgets[key]
            self.widgets[key].pack(side=LEFT)


    # Item Randomizer option frames
    self.frames["checkboxes"] = Frame(self)
    self.frames["checkboxes"].pack(anchor=W)

    self.frames["leftItemFrame"] = Frame(self)
    self.frames["rightItemFrame"] = Frame(self)
    self.frames["leftItemFrame"].pack(side=LEFT)
    self.frames["rightItemFrame"].pack(side=RIGHT)

    # Load Item Randomizer option widgets as defined by JSON file
    # Defns include frame name, widget type, widget options, widget placement attributes
    # Checkboxes go West
    # Everything else goes East
    with open(os.path.join("resources","app","gui","randomize","item","widgets.json")) as widgetDefns:
        myDict = json.load(widgetDefns)
        for framename,theseWidgets in myDict.items():
            dictWidgets = widgets.make_widgets_from_dict(self, theseWidgets, self.frames[framename])
            for key in dictWidgets:
                self.widgets[key] = dictWidgets[key]
                packAttrs = {"anchor":E}
                if self.widgets[key].type == "checkbox":
                    packAttrs["anchor"] = W
                self.widgets[key].pack(packAttrs)

    return self
