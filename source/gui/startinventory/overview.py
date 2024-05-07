from tkinter import ttk, Frame, N, E, W, LEFT, TOP, X, VERTICAL, Y
import source.gui.widgets as widgets
import json
import os

import source.classes.constants as CONST

def startinventory_page(top,parent):
    # Starting Inventory
    self = ttk.Frame(parent)

    # Create uniform list columns
    def create_list_frame(parent, framename):
        self.frames[framename] = Frame(parent)
        self.frames[framename].pack(side=LEFT, padx=(0,0), anchor=N)
        self.frames[framename].thisRow = 0
        self.frames[framename].thisCol = 0

    # Create a vertical rule to help with splitting columns visually
    def create_vertical_rule(num=1):
        for _ in range(0,num):
            ttk.Separator(self, orient=VERTICAL).pack(side=LEFT, anchor=N, fill=Y)

    # This was in Custom Item Pool, I have no idea what it was but I left it just in case: MikeT
    def validation(P):
        if str.isdigit(P) or P == "":
            return True
        else:
            return False
    vcmd=(self.register(validation), '%P')

    # Starting Inventory options
    self.startingWidgets = {}

    # Starting Inventory option sections
    self.frames = {}
    self.frames["startHeader"] = Frame(self)
    self.frames["startHeader"].pack(side=TOP, anchor=W)
    # Create 5 columns with 2 vertical rules in between each
    create_list_frame(self,"itemList1")
    create_vertical_rule(2)
    create_list_frame(self,"itemList2")
    create_vertical_rule(2)
    create_list_frame(self,"itemList3")
    create_vertical_rule(2)
    create_list_frame(self,"itemList4")
    create_vertical_rule(2)
    create_list_frame(self,"itemList5")

    # Load Starting Inventory option widgets as defined by JSON file, ignoring the ones to be excluded
    # Defns include frame name, widget type, widget options, widget placement attributes
    with open(os.path.join("resources","app","gui","custom","overview","widgets.json")) as widgetDefns:
        myDict = json.load(widgetDefns)
        for key in CONST.CANTSTARTWITH:
            for num in range(1, 5 + 1):
                thisList = "itemList" + str(num)
                if key in myDict[thisList]:
                    del myDict[thisList][key]
        for framename,theseWidgets in myDict.items():
            if framename in self.frames:
                dictWidgets = widgets.make_widgets_from_dict(self, theseWidgets, self.frames[framename])
                for key in dictWidgets:
                    self.startingWidgets[key] = dictWidgets[key]
                    if framename == "startHeader":
                        packAttrs = {"anchor":W}
                        packAttrs = widgets.add_padding_from_config(packAttrs, theseWidgets[key])
                        self.startingWidgets[key].pack(packAttrs)

    # Load Custom Starting Inventory settings from settings file, ignoring ones to be excluded
    for key in CONST.CUSTOMITEMS:
        if key not in CONST.CANTSTARTWITH:
            val = 0
            if key in top.settings["startinventoryarray"]:
                val = top.settings["startinventoryarray"][key]
            self.startingWidgets[key].storageVar.set(val)

    return self
