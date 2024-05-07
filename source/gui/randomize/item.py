from tkinter import ttk, font, Frame, E, W, NW, TOP, LEFT, RIGHT, Y, Label
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

    # Item Randomizer option frames
    self.frames["checkboxes"] = Frame(self)
    self.frames["checkboxes"].pack(anchor=W)

    various_options = Label(self.frames["checkboxes"], text="Options: ")
    various_options.pack(side=LEFT)

    self.frames["mainFrame"] = Frame(self)
    self.frames["mainFrame"].pack(side=TOP, pady=(20,0))

    self.frames["poolFrame"] = Frame(self)
    self.frames["poolFrame"].pack(fill=Y)

    self.frames["leftItemFrame"] = Frame(self.frames["mainFrame"])
    self.frames["leftItemFrame"].pack(side=LEFT)
    self.frames["rightItemFrame"] = Frame(self.frames["mainFrame"])
    self.frames["rightItemFrame"].pack(side=RIGHT)
    
    self.frames["leftPoolContainer"] = Frame(self.frames["poolFrame"])
    self.frames["leftPoolContainer"].pack(side=LEFT, padx=(0,20))
    
    base_font = font.nametofont('TkTextFont').actual()
    underline_font = f'"{base_font["family"]}" {base_font["size"]} underline'
    various_options = Label(self.frames["leftPoolContainer"], text="Pool Expansions", font=underline_font)
    various_options.pack(side=TOP, pady=(20,0))

    self.frames["leftPoolHeader"] = Frame(self.frames["leftPoolContainer"])
    self.frames["leftPoolHeader"].pack(side=TOP, anchor=W)

    self.frames["leftPoolFrame"] = Frame(self.frames["leftPoolContainer"])
    self.frames["leftPoolFrame"].pack(side=TOP, fill=Y)

    self.frames["leftPoolFrame2"] = Frame(self.frames["leftPoolContainer"])
    self.frames["leftPoolFrame2"].pack(side=LEFT, fill=Y)
    
    self.frames["rightPoolFrame"] = Frame(self.frames["poolFrame"])
    self.frames["rightPoolFrame"].pack(side=RIGHT)

    various_options = Label(self.frames["rightPoolFrame"], text="Pool Modifications", font=underline_font)
    various_options.pack(side=TOP, pady=(20,0))

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
                if key == "retro":
                    packAttrs["side"] = RIGHT
                if self.widgets[key].type == "checkbox" or framename.startswith("leftPoolFrame"):
                    packAttrs["anchor"] = W
                if framename == "checkboxes":
                    packAttrs["side"] = LEFT
                    packAttrs["padx"] = (10, 0)
                elif framename == "leftPoolHeader":
                    packAttrs["side"] = LEFT
                    packAttrs["padx"] = (0, 20)
                packAttrs = widgets.add_padding_from_config(packAttrs, theseWidgets[key])
                self.widgets[key].pack(packAttrs)

    return self
